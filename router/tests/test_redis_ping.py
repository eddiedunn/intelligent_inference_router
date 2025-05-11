import pytest
import redis.asyncio as redis
import asyncio

from dotenv import load_dotenv
import os

def test_redis_ping():
    load_dotenv()
    url = os.environ["REDIS_URL"]
    r = redis.from_url(url, encoding="utf-8", decode_responses=True)
    pong = asyncio.run(r.ping())
    assert pong is True
