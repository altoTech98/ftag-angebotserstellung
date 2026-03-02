"""
Feedback Store – Persistent storage for product matching corrections.
Stores user feedback in a JSON file so Claude can learn from past corrections.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
FEEDBACK_FILE = os.path.join(DATA_DIR, "matching_feedback.json")


def load_feedback() -> list[dict]:
    """Load all feedback entries from the JSON file."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_feedback_entry(entry: dict) -> dict:
    """Add a new feedback entry and persist to disk."""
    entries = load_feedback()
    entry["id"] = f"fb_{uuid.uuid4().hex[:8]}"
    entry["timestamp"] = datetime.now().isoformat()
    entries.append(entry)
    os.makedirs(os.path.dirname(FEEDBACK_FILE), exist_ok=True)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    return entry


def find_relevant_feedback(
    requirement_text: str,
    requirement_fields: dict,
    limit: int = 5,
) -> list[dict]:
    """
    Find past corrections most relevant to the current requirement.
    Uses keyword overlap scoring to find similar past requirements.
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
            scored.append((overlap, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:limit]]


def get_feedback_stats() -> dict:
    """Return summary statistics about stored feedback."""
    entries = load_feedback()
    return {
        "total_corrections": len(entries),
        "unique_requirements": len(
            set(e.get("requirement_text", "") for e in entries)
        ),
        "latest_correction": entries[-1]["timestamp"] if entries else None,
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
