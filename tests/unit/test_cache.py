"""Tests for in-memory cache."""

import pytest

from iir.cache.memory_cache import MemoryCache


@pytest.mark.asyncio
async def test_set_and_get():
    cache = MemoryCache()
    await cache.set("key1", {"value": 42}, ttl=60)
    result = await cache.get("key1")
    assert result == {"value": 42}


@pytest.mark.asyncio
async def test_get_missing_key():
    cache = MemoryCache()
    assert await cache.get("nonexistent") is None


@pytest.mark.asyncio
async def test_delete():
    cache = MemoryCache()
    await cache.set("key1", "value", ttl=60)
    await cache.delete("key1")
    assert await cache.get("key1") is None


@pytest.mark.asyncio
async def test_close_clears():
    cache = MemoryCache()
    await cache.set("key1", "value", ttl=60)
    await cache.close()
    assert await cache.get("key1") is None
