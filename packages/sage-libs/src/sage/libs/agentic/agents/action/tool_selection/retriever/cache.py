"""
Caching utilities for tool selection.

Provides simple in-memory caching for selection results.
"""

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResultCache:
    """
    Simple in-memory cache for tool selection results.

    Supports TTL and size limits.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: Optional[float] = None):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of entries
            ttl_seconds: Time-to-live in seconds (None = no expiry)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict = {}
        self._timestamps: dict = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._misses += 1
            return None

        # Check TTL
        if self.ttl_seconds is not None:
            timestamp = self._timestamps.get(key, 0)
            if time.time() - timestamp > self.ttl_seconds:
                # Expired
                del self._cache[key]
                del self._timestamps[key]
                self._misses += 1
                return None

        self._hits += 1
        return self._cache[key]

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Check size limit
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Evict oldest entry
            oldest_key = min(self._timestamps.keys(), key=self._timestamps.get)
            del self._cache[oldest_key]
            del self._timestamps[oldest_key]
            logger.debug(f"Evicted cache entry: {oldest_key}")

        self._cache[key] = value
        self._timestamps[key] = time.time()

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("Cleared cache")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "max_size": self.max_size,
        }
