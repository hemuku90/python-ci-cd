from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol


class CacheProvider(Protocol):
    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve an item from the cache if it exists and is fresh."""
        ...

    def set(self, key: str, value: List[Dict[str, Any]]) -> None:
        """Store an item in the cache."""
        ...


class InMemoryCache:
    """Simple in-memory dictionary cache implementation."""

    def __init__(self, ttl_minutes: int = 5, max_size: int = 1000):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._max_size = max_size

    def get(self, key: str) -> Optional[List[Dict[str, Any]]]:
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now(timezone.utc) - entry["timestamp"] < self._ttl:
                return entry["data"]
            # Clear expired entry
            del self._cache[key]
        return None

    def set(self, key: str, value: List[Dict[str, Any]]) -> None:
        self._cache[key] = {"timestamp": datetime.now(timezone.utc), "data": value}
        # Evict oldest item if max size exceeded
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)


memory_cache = InMemoryCache()


def get_cache() -> CacheProvider:
    """Return the configured cache provider"""
    return memory_cache
