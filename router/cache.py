# Redis cache for IIR MVP
import redis.asyncio as redis
import hashlib
import os
from router.settings import get_settings
from prometheus_client import Counter, Gauge

def get_redis_url():
    # Always get the current environment variable at runtime
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def get_cache():
    return await redis.from_url(get_redis_url(), decode_responses=True)

# Prometheus metrics for cache
cache_hits_total = Counter('router_cache_hits_total', 'Total cache hits', ['backend'])
cache_misses_total = Counter('router_cache_misses_total', 'Total cache misses', ['backend'])
cache_size_gauge = Gauge('router_cache_size', 'Current cache size', ['backend'])

# Stub SimpleCache for testing
import time

class SimpleCache:
    def __init__(self):
        self._store = {}
        self._backend = 'simple'
    def set(self, key, value, ex=None):
        expire_at = time.time() + ex if ex else None
        self._store[key] = (value, expire_at)
        cache_size_gauge.labels(backend=self._backend).set(len(self._store))
    def get(self, key):
        value, expire_at = self._store.get(key, (None, None))
        if expire_at and time.time() > expire_at:
            del self._store[key]
            cache_size_gauge.labels(backend=self._backend).set(len(self._store))
            cache_misses_total.labels(backend=self._backend).inc()
            return None
        if value is not None:
            cache_hits_total.labels(backend=self._backend).inc()
        else:
            cache_misses_total.labels(backend=self._backend).inc()
        return value

# For Redis, metrics are incremented in the wrapper in refresh_models.py

def make_cache_key(prompt: str, context: str, model_id: str) -> str:
    key = f"{prompt}|{context}|{model_id}"
    return hashlib.sha256(key.encode()).hexdigest()
