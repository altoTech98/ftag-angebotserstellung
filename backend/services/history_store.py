"""
History Store – Persistent storage for analysis history.
Stores past analyses so users can review, compare, and re-run matching.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
HISTORY_FILE = os.path.join(DATA_DIR, "analysis_history.json")


def load_history() -> list[dict]:
    """Load all history entries from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_analysis(
    file_id: str,
    filename: str,
    requirements: dict,
    matching: dict,
) -> dict:
    """Save a completed analysis to history."""
    entries = load_history()

    summary = matching.get("summary", {})
    entry = {
        "id": f"hist_{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now().isoformat(),
        "file_id": file_id,
        "filename": filename,
        "projekt": requirements.get("projekt", ""),
        "auftraggeber": requirements.get("auftraggeber", ""),
        "positions_count": summary.get("total_positions", 0),
        "matched_count": summary.get("matched_count", 0),
        "partial_count": summary.get("partial_count", 0),
        "unmatched_count": summary.get("unmatched_count", 0),
        "match_rate": summary.get("match_rate", 0),
        "requirements": requirements,
        "matching": matching,
    }

    entries.append(entry)
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    return entry


def get_history_list() -> list[dict]:
    """Return summary of all analyses (without full results)."""
    entries = load_history()
    return [
        {
            "id": e["id"],
            "timestamp": e["timestamp"],
            "filename": e.get("filename", ""),
            "projekt": e.get("projekt", ""),
            "auftraggeber": e.get("auftraggeber", ""),
            "positions_count": e.get("positions_count", 0),
            "matched_count": e.get("matched_count", 0),
            "partial_count": e.get("partial_count", 0),
            "unmatched_count": e.get("unmatched_count", 0),
            "match_rate": e.get("match_rate", 0),
        }
        for e in reversed(entries)  # newest first
    ]


def get_history_detail(history_id: str) -> Optional[dict]:
    """Return full analysis details by ID."""
    entries = load_history()
    for entry in entries:
        if entry["id"] == history_id:
            return entry
    return None


def delete_history_entry(history_id: str) -> bool:
    """Delete a history entry by ID. Returns True if found and deleted."""
    entries = load_history()
    original_len = len(entries)
    entries = [e for e in entries if e["id"] != history_id]
    if len(entries) == original_len:
        return False
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    return True
