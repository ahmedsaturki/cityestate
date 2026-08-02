"""
Cache Utilities — CityEstate caching layer
============================================
Simple in-memory cache with TTL for frequently accessed data.
"""

import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    """Time-to-live in-memory cache."""

    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    def get(self, key: str) -> Any | None:
        """Get a cached value if not expired."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.time() > expiry:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set a cached value with optional TTL."""
        expiry = time.time() + (ttl or self._default_ttl)
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        """Delete a cached value."""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def keys(self) -> list[str]:
        """Return all non-expired cache keys."""
        now = time.time()
        return [
            k
            for k, (_, expiry) in self._cache.items()
            if now <= expiry
        ]


# Global cache instance
cache = TTLCache(default_ttl=300)


def cached(ttl: int = 300):
    """Decorator to cache function results with TTL."""

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            key = f"{func.__module__}.{func.__name__}:{hash(str(args) + str(kwargs))}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl)
            return result

        return wrapper

    return decorator