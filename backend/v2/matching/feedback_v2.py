"""
V2 Feedback Store - Persistent storage for matching corrections
with TF-IDF-based relevant feedback retrieval.

Corrections are stored as JSON and retrieved using TF-IDF cosine
similarity to find past corrections most relevant to a new requirement.
"""

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Default store path
_DEFAULT_STORE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "matching_feedback_v2.json"
)


class FeedbackEntry(BaseModel):
    """A single matching correction entry."""

    id: str = Field(default_factory=lambda: f"fb_v2_{uuid.uuid4().hex[:8]}")
    positions_nr: str
    requirement_summary: str
    original_match: dict = Field(
        description="Dict with produkt_id and gesamt_konfidenz"
    )
    corrected_match: dict = Field(
        description="Dict with produkt_id and produkt_name"
    )
    correction_reason: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class FeedbackStoreV2:
    """V2 feedback store with TF-IDF-based retrieval.

    Stores corrections as JSON. Uses TF-IDF cosine similarity to
    find past corrections most relevant to a given requirement text.
    """

    def __init__(self, store_path: str = _DEFAULT_STORE_PATH):
        self._store_path = store_path
        self._entries: list[FeedbackEntry] = []
        self._tfidf_dirty = True  # Rebuild TF-IDF on next find call
        self._vectorizer = None
        self._tfidf_matrix = None
        self._load()

    def _load(self):
        """Load existing corrections from JSON file."""
        if os.path.exists(self._store_path):
            try:
                with open(self._store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._entries = [FeedbackEntry(**d) for d in data]
                self._tfidf_dirty = True
            except (json.JSONDecodeError, IOError, Exception) as e:
                logger.warning(f"[FeedbackV2] Failed to load store: {e}")
                self._entries = []

    def _save(self):
        """Write all corrections to JSON file atomically."""
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=os.path.dirname(self._store_path), suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(
                    [e.model_dump() for e in self._entries],
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
            os.replace(tmp_path, self._store_path)
        except BaseException:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def save_correction(self, entry: FeedbackEntry) -> FeedbackEntry:
        """Save a correction entry and persist to disk."""
        self._entries.append(entry)
        self._tfidf_dirty = True
        self._save()
        return entry

    def _rebuild_tfidf(self):
        """Rebuild TF-IDF vectorizer from all stored requirement summaries."""
        if not self._entries:
            self._vectorizer = None
            self._tfidf_matrix = None
            self._tfidf_dirty = False
            return

        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401

        texts = [e.requirement_summary for e in self._entries]
        self._vectorizer = TfidfVectorizer(
            analyzer="word",
            token_pattern=r"(?u)\b[a-zA-ZaeoeueAeOeUess0-9]{2,}\b",
            max_features=2000,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._tfidf_dirty = False

    def find_relevant_feedback(
        self, requirement_text: str, limit: int = 5
    ) -> list[dict]:
        """Find past corrections most relevant to the given requirement text.

        Uses TF-IDF cosine similarity between requirement_text and all
        stored requirement_summary fields.

        Returns formatted dicts suitable for prompt injection.
        """
        if not self._entries:
            return []

        if self._tfidf_dirty:
            self._rebuild_tfidf()

        if self._vectorizer is None or self._tfidf_matrix is None:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        query_vec = self._vectorizer.transform([requirement_text])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Sort by score descending
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in ranked[:limit]:
            if score <= 0:
                continue
            entry = self._entries[idx]
            results.append({
                "requirement_summary": entry.requirement_summary,
                "original_match": entry.original_match,
                "corrected_match": entry.corrected_match,
                "correction_reason": entry.correction_reason,
                "similarity_score": float(score),
            })

        return results

    def get_all(self) -> list[FeedbackEntry]:
        """Return all stored feedback entries."""
        return list(self._entries)


# Module-level singleton
_feedback_store: Optional[FeedbackStoreV2] = None


def get_feedback_store(store_path: str = _DEFAULT_STORE_PATH) -> FeedbackStoreV2:
    """Get or create the module-level FeedbackStoreV2 singleton."""
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStoreV2(store_path=store_path)
    return _feedback_store
