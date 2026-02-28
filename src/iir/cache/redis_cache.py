"""Redis async cache with connection management."""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger("iir.cache")


class RedisCache:
    def __init__(self, url: str) -> None:
        self._url = url
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(self._url, decode_responses=True)
        await self._client.ping()
        logger.info("Redis connected at %s", self._url)

    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None

    async def get(self, key: str) -> Any | None:
        if not self._client:
            return None
        raw = await self._client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        if not self._client:
            return
        await self._client.set(key, json.dumps(value), ex=ttl)

    async def delete(self, key: str) -> None:
        if self._client:
            await self._client.delete(key)
