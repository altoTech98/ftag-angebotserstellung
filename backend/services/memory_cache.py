"""
Memory Cache – Bounded in-memory storage replacing disk-based uploads/ and outputs/.

Thread-safe, TTL-expiring, size-bounded cache for transient data.
Used by upload (extracted text), offer generation (document bytes),
and project uploads (raw file bytes for analysis).
"""

import threading
import time
import logging
from collections import OrderedDict
from typing import Any, Optional

logger = logging.getLogger(__name__)


class MemoryCache:
    """Thread-safe, bounded, TTL-expiring in-memory cache."""

    def __init__(
        self,
        max_items: int = 50,
        default_ttl: int = 1800,
        max_bytes: int = 100 * 1024 * 1024,
    ):
        self._data: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()
        self.max_items = max_items
        self.default_ttl = default_ttl
        self.max_bytes = max_bytes
        self._total_bytes = 0

    def store(self, key: str, value: Any, ttl_seconds: int = None, **metadata):
        """Store a value with TTL. Evicts oldest entries if bounds exceeded."""
        ttl = ttl_seconds or self.default_ttl
        size = len(value) if isinstance(value, (bytes, str)) else 0

        with self._lock:
            # Remove existing entry for same key first
            if key in self._data:
                old = self._data.pop(key)
                self._total_bytes -= old.get("_size", 0)

            self._evict_expired()

            # Evict oldest if at capacity
            while (
                len(self._data) >= self.max_items
                or self._total_bytes + size > self.max_bytes
            ) and self._data:
                oldest_key, oldest = self._data.popitem(last=False)
                self._total_bytes -= oldest.get("_size", 0)
                logger.debug(f"Cache evicted: {oldest_key}")

            self._data[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
                "_size": size,
                **metadata,
            }
            self._total_bytes += size

    def get(self, key: str) -> Optional[Any]:
        """Get a value. Returns None if missing or expired."""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if time.time() > entry["expires_at"]:
                del self._data[key]
                self._total_bytes -= entry.get("_size", 0)
                return None
            return entry["value"]

    def delete(self, key: str):
        """Delete a specific key."""
        with self._lock:
            entry = self._data.pop(key, None)
            if entry:
                self._total_bytes -= entry.get("_size", 0)

    def _evict_expired(self):
        """Remove all expired entries. Must be called with lock held."""
        now = time.time()
        expired = [k for k, v in self._data.items() if now > v["expires_at"]]
        for k in expired:
            entry = self._data.pop(k)
            self._total_bytes -= entry.get("_size", 0)

    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            self._evict_expired()
            return {
                "items": len(self._data),
                "total_bytes": self._total_bytes,
                "max_items": self.max_items,
                "max_bytes": self.max_bytes,
            }


# ---------------------------------------------------------------------------
# Global cache instances
# ---------------------------------------------------------------------------

# Extracted text from uploaded documents (single upload)
text_cache = MemoryCache(max_items=100, default_ttl=3600, max_bytes=50 * 1024 * 1024)

# Generated offer/report documents (xlsx/docx bytes)
offer_cache = MemoryCache(max_items=30, default_ttl=1800, max_bytes=50 * 1024 * 1024)

# Raw file bytes for project/folder uploads (needed for analysis phase)
project_cache = MemoryCache(max_items=10, default_ttl=3600, max_bytes=500 * 1024 * 1024)
