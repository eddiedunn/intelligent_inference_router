"""In-memory cache with TTL expiration. Fallback when Redis is unavailable."""

from __future__ import annotations

import time
import threading
from typing import Any


class MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.Lock()

    async def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and time.time() > expires_at:
                del self._store[key]
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        expires_at = time.time() + ttl if ttl else None
        with self._lock:
            self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        with self._lock:
            self._store.clear()
