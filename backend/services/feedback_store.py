"""
Feedback Store – Persistent storage for product matching corrections.
Uses database (SQLAlchemy) with JSON file fallback.
"""

import os
import json
import uuid
import tempfile
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FEEDBACK_FILE = os.path.join(DATA_DIR, "matching_feedback.json")
MAX_FEEDBACK_ENTRIES = 500

_feedback_lock = threading.Lock()
_use_db = False


def _check_db():
    """Check if database is available for feedback storage."""
    global _use_db
    try:
        from db.engine import SyncSessionLocal
        from db.models import Feedback  # noqa: F401
        session = SyncSessionLocal()
        session.execute(__import__("sqlalchemy").text("SELECT 1"))
        session.close()
        _use_db = True
    except Exception:
        _use_db = False


# ─────────────────────────────────────────────────────────────────────────────
# JSON fallback helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_feedback_json() -> list[dict]:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _atomic_write_json(filepath: str, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(filepath), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def load_feedback() -> list[dict]:
    """Load all feedback entries."""
    if _use_db:
        try:
            from db.engine import SyncSessionLocal
            from db.models import Feedback
            session = SyncSessionLocal()
            try:
                entries = session.query(Feedback).order_by(Feedback.created_at).all()
                return [
                    {
                        "id": f"fb_{e.id}",
                        "type": e.feedback_type,
                        "requirement_text": e.requirement_text,
                        "requirement_fields": e.requirement_fields or {},
                        "confirmed_product": e.corrected_product,
                        "original_product": e.original_product,
                        "match_status_was": e.match_status_was,
                        "timestamp": e.created_at.isoformat() if e.created_at else "",
                    }
                    for e in entries
                ]
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"[FEEDBACK] DB read failed, using JSON: {e}")

    return _load_feedback_json()


def save_feedback_entry(entry: dict) -> dict:
    """Add a new feedback entry."""
    entry["id"] = f"fb_{uuid.uuid4().hex[:8]}"
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()

    if _use_db:
        try:
            from db.engine import SyncSessionLocal
            from db.models import Feedback
            session = SyncSessionLocal()
            try:
                fb = Feedback(
                    feedback_type=entry.get("type", "correction"),
                    requirement_text=entry.get("requirement_text", ""),
                    requirement_fields=entry.get("requirement_fields"),
                    original_product=entry.get("original_product"),
                    corrected_product=entry.get("confirmed_product") or entry.get("corrected_product"),
                    match_status_was=entry.get("match_status_was"),
                )
                session.add(fb)
                session.commit()
                entry["id"] = f"fb_{fb.id}"
                return entry
            except Exception as e:
                session.rollback()
                logger.warning(f"[FEEDBACK] DB write failed, using JSON: {e}")
            finally:
                session.close()
        except Exception:
            pass

    # JSON fallback
    with _feedback_lock:
        entries = _load_feedback_json()
        entries.append(entry)
        if len(entries) > MAX_FEEDBACK_ENTRIES:
            entries = entries[-MAX_FEEDBACK_ENTRIES:]
        _atomic_write_json(FEEDBACK_FILE, entries)
    return entry


def find_relevant_feedback(
    requirement_text: str,
    requirement_fields: dict = None,
    limit: int = 8,
) -> list[dict]:
    """
    Find past corrections AND confirmations most relevant to the current requirement.
    Uses keyword overlap scoring with synonym expansion and field matching.
    """
    if requirement_fields is None:
        requirement_fields = {}

    entries = load_feedback()
    if not entries:
        return []

    current_keywords = _extract_keywords(requirement_text, requirement_fields)
    if not current_keywords:
        return []

    # Expand keywords with synonyms
    expanded = set(current_keywords)
    try:
        from services.product_matcher import expand_synonyms
        for kw in list(current_keywords):
            expanded.update(s.lower() for s in expand_synonyms(kw))
    except ImportError:
        pass

    scored = []
    for entry in entries:
        past_keywords = _extract_keywords(
            entry.get("requirement_text", ""),
            entry.get("requirement_fields", {}),
        )
        overlap = len(expanded & past_keywords)
        if overlap > 0:
            weight = overlap * 1.2 if entry.get("type") != "confirmation" else overlap

            past_fields = entry.get("requirement_fields", {})
            for f in ("brandschutz", "einbruchschutz", "tuertyp"):
                if (requirement_fields.get(f) and past_fields.get(f)
                        and _normalize_field(requirement_fields[f]) == _normalize_field(past_fields[f])):
                    weight += 3

            scored.append((weight, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:limit]]


def _normalize_field(val: str) -> str:
    return str(val).lower().strip().replace(" ", "").replace("-", "")


def save_confirmation(
    requirement_text: str,
    requirement_fields: dict,
    confirmed_product: dict,
    position_id: str = "",
    match_status_was: str = "",
) -> dict:
    return save_feedback_entry({
        "type": "confirmation",
        "requirement_text": requirement_text,
        "requirement_fields": requirement_fields,
        "confirmed_product": confirmed_product,
        "position_id": position_id,
        "match_status_was": match_status_was,
    })


def get_feedback_stats() -> dict:
    entries = load_feedback()
    corrections = [e for e in entries if e.get("type") != "confirmation"]
    confirmations = [e for e in entries if e.get("type") == "confirmation"]
    return {
        "total_corrections": len(corrections),
        "total_confirmations": len(confirmations),
        "total_feedback": len(entries),
        "unique_requirements": len(set(e.get("requirement_text", "") for e in entries)),
        "latest_feedback": entries[-1]["timestamp"] if entries else None,
    }


def _extract_keywords(text: str, fields: dict) -> set[str]:
    words = set()
    if text:
        words.update(w.lower() for w in text.split() if len(w) > 2)
    for key in ("tuertyp", "brandschutz", "einbruchschutz", "beschreibung"):
        val = fields.get(key)
        if val and isinstance(val, str):
            words.update(w.lower() for w in val.split() if len(w) > 2)
    return words


# Initialize DB check on module load
_check_db()
