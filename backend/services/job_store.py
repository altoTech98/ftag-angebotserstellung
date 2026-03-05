"""
Simple in-memory job store for background processing.
Solves Render/Railway timeout issues by running long tasks in background threads.
Supports SSE event subscriptions for real-time progress streaming.
"""

import asyncio
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


_job_event_queues: dict[str, list[asyncio.Queue]] = {}
_event_lock = threading.Lock()


def subscribe_job(job_id: str) -> asyncio.Queue:
    """Subscribe to real-time events for a job. Returns an asyncio.Queue."""
    queue = asyncio.Queue(maxsize=100)
    with _event_lock:
        _job_event_queues.setdefault(job_id, []).append(queue)
    return queue


def unsubscribe_job(job_id: str, queue: asyncio.Queue):
    """Unsubscribe from job events."""
    with _event_lock:
        if job_id in _job_event_queues:
            _job_event_queues[job_id] = [q for q in _job_event_queues[job_id] if q is not queue]
            if not _job_event_queues[job_id]:
                del _job_event_queues[job_id]


def _notify_subscribers(job_id: str, event: dict):
    """Send event to all subscribers of a job."""
    with _event_lock:
        queues = _job_event_queues.get(job_id, [])
    for queue in queues:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


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

    # Notify SSE subscribers
    _notify_subscribers(job_id, {
        "job_id": job_id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "result": job.result if job.status == "completed" else None,
    })


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
