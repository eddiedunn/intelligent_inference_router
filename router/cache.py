# Redis cache for IIR MVP
import redis.asyncio as redis
import hashlib
import os
from router.settings import get_settings

def get_redis_url():
    # Always get the current environment variable at runtime
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def get_cache():
    return await redis.from_url(get_redis_url(), decode_responses=True)

# Stub SimpleCache for testing
import time

class SimpleCache:
    def __init__(self):
        self._store = {}
    def set(self, key, value, ex=None):
        expire_at = time.time() + ex if ex else None
        self._store[key] = (value, expire_at)
    def get(self, key):
        value, expire_at = self._store.get(key, (None, None))
        if expire_at and time.time() > expire_at:
            del self._store[key]
            return None
        return value

def make_cache_key(prompt: str, context: str, model_id: str) -> str:
    key = f"{prompt}|{context}|{model_id}"
    return hashlib.sha256(key.encode()).hexdigest()
