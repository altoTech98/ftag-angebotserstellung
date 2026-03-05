"""
Simple in-memory job store for background processing.
Solves Render/Railway timeout issues by running long tasks in background threads.
"""

import threading
import time
import uuid
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

MAX_JOBS = 50
JOB_TTL = 3600  # 1 hour


class Job:
    __slots__ = ("id", "status", "progress", "result", "error", "created_at", "updated_at")

    def __init__(self, job_id: str):
        self.id = job_id
        self.status = "pending"  # pending -> running -> completed | failed
        self.progress = ""
        self.result = None
        self.error = None
        self.created_at = time.time()
        self.updated_at = time.time()

    def to_dict(self):
        return {
            "job_id": self.id,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "result": self.result if self.status == "completed" else None,
        }


_jobs: OrderedDict[str, Job] = OrderedDict()
_lock = threading.Lock()


def create_job() -> Job:
    """Create a new job and return it."""
    job_id = uuid.uuid4().hex[:12]
    job = Job(job_id)
    with _lock:
        _jobs[job_id] = job
        # Evict old jobs
        _cleanup()
    return job


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def update_job(job_id: str, *, status: str = None, progress: str = None, result=None, error: str = None):
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        if status:
            job.status = status
        if progress is not None:
            job.progress = progress
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        job.updated_at = time.time()


_active_count = 0
_active_lock = threading.Lock()


def run_in_background(job: Job, fn, *args, **kwargs):
    """Run fn in a background thread, updating the job with results."""
    from config import settings

    global _active_count
    with _active_lock:
        if _active_count >= settings.MAX_CONCURRENT_JOBS:
            update_job(job.id, status="failed", error="Zu viele gleichzeitige Jobs. Bitte warten.")
            raise RuntimeError("Too many concurrent jobs")
        _active_count += 1

    def wrapper():
        global _active_count
        update_job(job.id, status="running")
        try:
            result = fn(*args, **kwargs)
            update_job(job.id, status="completed", result=result)
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}", exc_info=True)
            update_job(job.id, status="failed", error=str(e))
        finally:
            with _active_lock:
                _active_count -= 1

    t = threading.Thread(target=wrapper, daemon=False)
    t.start()


def _cleanup():
    """Remove expired and excess jobs."""
    now = time.time()
    expired = [k for k, v in _jobs.items() if now - v.created_at > JOB_TTL]
    for k in expired:
        del _jobs[k]
    while len(_jobs) > MAX_JOBS:
        _jobs.popitem(last=False)
