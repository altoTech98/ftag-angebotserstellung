"""
═══════════════════════════════════════════════════════════════════════════════
Memory Cache Service – Production-Grade
Thread-safe, TTL-basiert, Auto-Eviction
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import logging
from collections import OrderedDict
from typing import Any, Optional, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache-Entry mit Metadaten"""
    key: str
    value: Any
    expires_at: float
    size: int
    created_at: datetime
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Prüft ob Entry abgelaufen ist"""
        return time.time() > self.expires_at
    
    def touch(self):
        """Aktualisiert Hit-Count"""
        self.hit_count += 1


class MemoryCache(Generic[T]):
    """
    Thread-sichere, begrenzte, TTL-basierende In-Memory Cache.
    
    Features:
    - TTL-basierte Auto-Expiration
    - LRU-Eviction bei Overflow
    - Thread-Safe mit Lock
    - Memory-Limits
    - Hit/Miss-Statistiken
    """

    def __init__(
        self,
        max_items: int = 100,
        default_ttl: int = 3600,
        max_bytes: int = 100 * 1024 * 1024,
        name: str = "cache"
    ):
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self.max_items = max_items
        self.default_ttl = default_ttl
        self.max_bytes = max_bytes
        self.name = name
        self._total_bytes = 0
        self._hits = 0
        self._misses = 0
        
        logger.debug(
            f"Cache '{name}' initialisiert | "
            f"max_items={max_items}, ttl={default_ttl}s, "
            f"max_bytes={max_bytes / (1024*1024):.1f}MB"
        )

    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[int] = None,
        **metadata
    ) -> bool:
        """
        Speichert einen Wert mit TTL.
        
        Args:
            key: Cache-Key
            value: Zu speichernder Wert
            ttl_seconds: Time-to-live in Sekunden
            **metadata: Zusätzliche Metadaten
            
        Returns:
            True wenn erfolgreich, False wenn zu groß
        """
        ttl = ttl_seconds or self.default_ttl
        
        # Größe schätzen
        try:
            if isinstance(value, (bytes, bytearray)):
                size = len(value)
            elif isinstance(value, str):
                size = len(value.encode('utf-8'))
            else:
                size = 1000  # Fallback
        except Exception as e:
            logger.warning(f"Size-Schätzung fehlgeschlagen: {e}")
            size = 0

        # Zu groß?
        if size > self.max_bytes * 0.9:
            logger.warning(
                f"Cache '{self.name}': Key '{key}' zu groß "
                f"({size / (1024*1024):.1f}MB)"
            )
            return False

        with self._lock:
            # Alten Entry entfernen
            if key in self._data:
                old_entry = self._data.pop(key)
                self._total_bytes -= old_entry.size
                logger.debug(f"Cache '{self.name}': Entry '{key}' überschrieben")

            # Abgelaufene Entries entfernen
            self._evict_expired()

            # LRU-Eviction wenn nötig
            while (
                len(self._data) >= self.max_items
                or self._total_bytes + size > self.max_bytes
            ) and self._data:
                oldest_key, oldest_entry = self._data.popitem(last=False)
                self._total_bytes -= oldest_entry.size
                logger.debug(
                    f"Cache '{self.name}': LRU-Eviction '{oldest_key}' "
                    f"({oldest_entry.hit_count} hits)"
                )

            # Neuen Entry hinzufügen
            entry = CacheEntry(
                key=key,
                value=value,
                expires_at=time.time() + ttl,
                size=size,
                created_at=datetime.now()
            )
            self._data[key] = entry
            self._total_bytes += size
            
            logger.debug(
                f"Cache '{self.name}': '{key}' gespeichert "
                f"({size / 1024:.1f}KB, TTL={ttl}s)"
            )
            return True

    def get(self, key: str) -> Optional[T]:
        """
        Holt einen Wert aus dem Cache.
        
        Returns:
            Wert oder None wenn nicht vorhanden/abgelaufen
        """
        with self._lock:
            entry = self._data.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                del self._data[key]
                self._total_bytes -= entry.size
                self._misses += 1
                logger.debug(f"Cache '{self.name}': '{key}' abgelaufen")
                return None
            
            entry.touch()
            self._hits += 1
            return entry.value

    def exists(self, key: str) -> bool:
        """Prüft ob Key existiert und nicht abgelaufen ist"""
        return self.get(key) is not None

    def delete(self, key: str) -> bool:
        """
        Löscht einen Key.
        
        Returns:
            True wenn gelöscht, False wenn nicht vorhanden
        """
        with self._lock:
            entry = self._data.pop(key, None)
            if entry:
                self._total_bytes -= entry.size
                logger.debug(f"Cache '{self.name}': '{key}' gelöscht")
                return True
            return False

    def clear(self):
        """Löscht alle Entries"""
        with self._lock:
            self._data.clear()
            self._total_bytes = 0
            self._hits = 0
            self._misses = 0
            logger.info(f"Cache '{self.name}': Komplett geleert")

    def _evict_expired(self):
        """Entfernt alle abgelaufenen Entries (mit Lock!)"""
        now = time.time()
        expired_keys = [
            k for k, v in self._data.items() 
            if now > v.expires_at
        ]
        
        for key in expired_keys:
            entry = self._data.pop(key)
            self._total_bytes -= entry.size
        
        if expired_keys:
            logger.debug(
                f"Cache '{self.name}': {len(expired_keys)} abgelaufene "
                f"Entries entfernt"
            )

    def stats(self) -> dict:
        """Gibt Cache-Statistiken zurück"""
        with self._lock:
            self._evict_expired()
            
            total_requests = self._hits + self._misses
            hit_rate = (
                (self._hits / total_requests * 100) 
                if total_requests > 0 else 0
            )
            
            return {
                "name": self.name,
                "items": len(self._data),
                "total_bytes": self._total_bytes,
                "total_mb": round(self._total_bytes / (1024 * 1024), 2),
                "max_items": self.max_items,
                "max_mb": round(self.max_bytes / (1024 * 1024), 2),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2),
                "utilization_percent": round(
                    (len(self._data) / self.max_items * 100) 
                    if self.max_items > 0 else 0, 
                    2
                )
            }

    def info(self) -> str:
        """Gibt lesbare Cache-Info aus"""
        stats = self.stats()
        return (
            f"Cache '{stats['name']}': "
            f"{stats['items']}/{stats['max_items']} items, "
            f"{stats['total_mb']}/{stats['max_mb']}MB, "
            f"Hit: {stats['hit_rate_percent']}%"
        )


# ─────────────────────────────────────────────────────────────────────────────
# GLOBALE CACHE INSTANZEN
# ─────────────────────────────────────────────────────────────────────────────

# Text aus hochgeladenen Dokumenten
text_cache = MemoryCache(
    max_items=100,
    default_ttl=settings.CACHE_TTL_TEXT,
    max_bytes=50 * 1024 * 1024,
    name="text"
)

# Generierte Angebote/Reports (xlsx/docx bytes)
offer_cache = MemoryCache(
    max_items=50,
    default_ttl=settings.CACHE_TTL_OFFER,
    max_bytes=100 * 1024 * 1024,
    name="offer"
)

# Projekt/Ordner-Upload Raw-Bytes
project_cache = MemoryCache(
    max_items=20,
    default_ttl=settings.CACHE_TTL_PROJECT,
    max_bytes=500 * 1024 * 1024,
    name="project"
)

# Produktkatalog-Index (gecacht)
catalog_cache = MemoryCache(
    max_items=10,
    default_ttl=86400,  # 24h
    max_bytes=200 * 1024 * 1024,
    name="catalog"
)

# ERP-Daten Cache (Phase 5)
erp_cache = MemoryCache(
    max_items=1000,
    default_ttl=settings.ERP_CACHE_TTL,
    max_bytes=50 * 1024 * 1024,
    name="erp"
)


def log_all_cache_stats():
    """Gibt Statistiken aller Caches aus"""
    logger.info("═══ CACHE STATISTICS ═══")
    for cache in [text_cache, offer_cache, project_cache, catalog_cache, erp_cache]:
        logger.info(cache.info())
    logger.info("═════════════════════════")


if __name__ == "__main__":
    # Test
    cache = MemoryCache(max_items=5, default_ttl=10, name="test")
    cache.set("key1", "value1")
    cache.set("key2", b"bytes2")
    print(cache.stats())
    print(cache.get("key1"))
    cache.clear()
