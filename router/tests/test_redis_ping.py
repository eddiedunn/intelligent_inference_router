import pytest
import redis.asyncio as redis
import asyncio

def test_redis_ping():
    r = redis.from_url("redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
    pong = asyncio.run(r.ping())
    assert pong is True
