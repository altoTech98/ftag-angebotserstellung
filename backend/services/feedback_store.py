"""
Feedback Store – Persistent storage for product matching corrections.
Stores user feedback in a JSON file so Claude can learn from past corrections.
"""

import os
import json
import uuid
import tempfile
import threading
from datetime import datetime
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FEEDBACK_FILE = os.path.join(DATA_DIR, "matching_feedback.json")
MAX_FEEDBACK_ENTRIES = 500

_feedback_lock = threading.Lock()


def load_feedback() -> list[dict]:
    """Load all feedback entries from the JSON file."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _atomic_write_json(filepath: str, data):
    """Write JSON atomically via temp file + os.replace to prevent corruption."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(filepath), suffix=".tmp"
    )
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


def save_feedback_entry(entry: dict) -> dict:
    """Add a new feedback entry and persist to disk."""
    with _feedback_lock:
        entries = load_feedback()
        entry["id"] = f"fb_{uuid.uuid4().hex[:8]}"
        entry["timestamp"] = datetime.now().isoformat()
        entries.append(entry)

        # Enforce maximum entries
        if len(entries) > MAX_FEEDBACK_ENTRIES:
            entries = entries[-MAX_FEEDBACK_ENTRIES:]

        _atomic_write_json(FEEDBACK_FILE, entries)
    return entry


def find_relevant_feedback(
    requirement_text: str,
    requirement_fields: dict,
    limit: int = 8,
) -> list[dict]:
    """
    Find past corrections AND confirmations most relevant to the current requirement.
    Uses keyword overlap scoring to find similar past requirements.
    Returns both corrections (negative) and confirmations (positive) examples.
    """
    entries = load_feedback()
    if not entries:
        return []

    current_keywords = _extract_keywords(requirement_text, requirement_fields)
    if not current_keywords:
        return []

    scored = []
    for entry in entries:
        past_keywords = _extract_keywords(
            entry.get("requirement_text", ""),
            entry.get("requirement_fields", {}),
        )
        overlap = len(current_keywords & past_keywords)
        if overlap > 0:
            # Corrections get a slight boost (more actionable)
            weight = overlap * 1.2 if entry.get("type") != "confirmation" else overlap
            scored.append((weight, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:limit]]


def save_confirmation(
    requirement_text: str,
    requirement_fields: dict,
    confirmed_product: dict,
    position_id: str = "",
    match_status_was: str = "",
) -> dict:
    """Save a positive confirmation (user accepted the match)."""
    return save_feedback_entry({
        "type": "confirmation",
        "requirement_text": requirement_text,
        "requirement_fields": requirement_fields,
        "confirmed_product": confirmed_product,
        "position_id": position_id,
        "match_status_was": match_status_was,
    })


def get_feedback_stats() -> dict:
    """Return summary statistics about stored feedback."""
    entries = load_feedback()
    corrections = [e for e in entries if e.get("type") != "confirmation"]
    confirmations = [e for e in entries if e.get("type") == "confirmation"]
    return {
        "total_corrections": len(corrections),
        "total_confirmations": len(confirmations),
        "total_feedback": len(entries),
        "unique_requirements": len(
            set(e.get("requirement_text", "") for e in entries)
        ),
        "latest_feedback": entries[-1]["timestamp"] if entries else None,
    }


def _extract_keywords(text: str, fields: dict) -> set[str]:
    """Extract normalized keywords from text and structured fields."""
    words = set()
    if text:
        words.update(w.lower() for w in text.split() if len(w) > 2)
    for key in ("tuertyp", "brandschutz", "einbruchschutz", "beschreibung"):
        val = fields.get(key)
        if val and isinstance(val, str):
            words.update(w.lower() for w in val.split() if len(w) > 2)
    return words
