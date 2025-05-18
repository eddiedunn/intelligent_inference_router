import sys
import types

# --- EARLY PATCHING: FastAPILimiter and redis ---
async def dummy_callback(request, response, pexpire):
    return None

async def dummy_identifier(request):
    return "test-identifier"

class DummyAsyncRedis:
    async def get(self, *a, **k): return None
    async def set(self, *a, **k): return True
    async def evalsha(self, *a, **k): return 1
    async def ping(self, *a, **k): return True
    async def close(self, *a, **k): return None
    async def delete(self, *a, **k): return 1
    async def exists(self, *a, **k): return 0
    async def expire(self, *a, **k): return True
    async def flushdb(self, *a, **k): return True

_dummy_redis = DummyAsyncRedis()
redis_asyncio = types.ModuleType("redis.asyncio")
redis_asyncio.Redis = lambda *a, **k: _dummy_redis
redis_asyncio.client = types.SimpleNamespace(Redis=lambda *a, **k: _dummy_redis)
redis_asyncio.ConnectionPool = lambda *a, **k: None
redis_asyncio.connection = types.SimpleNamespace(Connection=lambda *a, **k: None)
sys.modules["redis.asyncio"] = redis_asyncio
sys.modules["redis.asyncio.client"] = redis_asyncio.client
sys.modules["redis.asyncio.connection"] = redis_asyncio.connection

import fastapi_limiter
fastapi_limiter.FastAPILimiter.redis = _dummy_redis
fastapi_limiter.FastAPILimiter.init = lambda *a, **k: None
fastapi_limiter.FastAPILimiter.identifier = dummy_identifier
fastapi_limiter.FastAPILimiter.callback = dummy_callback
old_init = fastapi_limiter.FastAPILimiter.__init__
def new_init(self, *args, **kwargs):
    old_init(self, *args, **kwargs)
    self.callback = dummy_callback
    self.identifier = dummy_identifier
fastapi_limiter.FastAPILimiter.__init__ = new_init
async def new_call(self, request, response):
    return await dummy_callback(request, response, None)
fastapi_limiter.FastAPILimiter.__call__ = new_call
# --- END PATCHING ---

import pytest
import os

# Set required env var for registry tests
os.environ.setdefault("IIR_API_URL", "http://localhost:8000")

@pytest.fixture
def main_api_server():
    # Dummy fixture to satisfy integration tests
    yield None

@pytest.fixture
def model_registry_server():
    # Dummy fixture to satisfy integration tests
    yield None
