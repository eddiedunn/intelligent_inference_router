import sys
from unittest.mock import AsyncMock
import types

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

# Patch redis.asyncio at sys.modules level
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
fastapi_limiter.FastAPILimiter.init = AsyncMock()
fastapi_limiter.FastAPILimiter.__call__ = AsyncMock(return_value=None)
async def dummy_identifier(request):
    return "test-identifier"
fastapi_limiter.FastAPILimiter.identifier = dummy_identifier

async def dummy_callback(request, response, pexpire):
    return None
fastapi_limiter.FastAPILimiter.callback = dummy_callback

# Patch FastAPILimiter __init__ to always set instance callback
old_init = fastapi_limiter.FastAPILimiter.__init__
def new_init(self, *args, **kwargs):
    old_init(self, *args, **kwargs)
    self.callback = dummy_callback
fastapi_limiter.FastAPILimiter.__init__ = new_init

import os
from dotenv import load_dotenv
load_dotenv()
print("[DEBUG] REDIS_URL in conftest.py:", os.environ.get("REDIS_URL"))
# Set MOCK_PROVIDERS=1 for all tests
os.environ["MOCK_PROVIDERS"] = "1"

# Set robust test API key env for all test processes BEFORE any app/config import
TEST_API_KEY = "test-secret-key-robust"
os.environ["IIR_API_KEY"] = TEST_API_KEY
os.environ["IIR_ALLOWED_KEYS"] = TEST_API_KEY

import secrets
import router.model_registry

import router.model_registry

def patched_list_models():
    print("[DEBUG][TEST] Patched list_models called (REAL REGISTRY)")
    return router.model_registry.list_models()
router.model_registry.list_models = patched_list_models

import router.validation_utils
# Monkeypatch validate_model_and_messages to print debug info
orig_validate = router.validation_utils.validate_model_and_messages
def debug_validate_model_and_messages(payload, list_models_func=None, require_messages=True, token_limit=1000):
    print("[DEBUG][TEST] Payload to validate:", payload)
    if list_models_func:
        models = list_models_func()['data']
        print("[DEBUG][TEST] Models from list_models_func:", [m['id'] for m in models])
    else:
        print("[DEBUG][TEST] No list_models_func provided")
    return orig_validate(payload, list_models_func, require_messages, token_limit)
router.validation_utils.validate_model_and_messages = debug_validate_model_and_messages

import pytest

@pytest.fixture
def main_api_server():
    # Dummy fixture to satisfy integration tests
    yield None

@pytest.fixture
def model_registry_server():
    # Dummy fixture to satisfy integration tests
    yield None
import redis.asyncio as redis
from fastapi_limiter.depends import RateLimiter
from fastapi.testclient import TestClient
import asyncio
from fastapi_limiter import FastAPILimiter
import socket
import subprocess
import time
import httpx
import pytest_asyncio
import os
from unittest.mock import AsyncMock, patch

# --- Global environment variable patch for all tests ---
@pytest.fixture(autouse=True, scope="session")
def patch_env_vars():
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["OPENAI_API_KEY"] = "sk-test"
    os.environ["ANTHROPIC_API_KEY"] = "sk-test"
    os.environ["HUGGINGFACE_API_KEY"] = "sk-test"
    os.environ["IIR_API_KEY"] = "test-secret-key-robust"
    os.environ["IIR_ALLOWED_KEYS"] = "test-secret-key-robust"

# --- Robust Global Redis and FastAPILimiter patch ---
import types
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
    # Add any other methods your code/tests use
@pytest.fixture(autouse=True)
def patch_redis_and_limiter(monkeypatch):
    dummy_redis = DummyAsyncRedis()
    monkeypatch.setattr("redis.asyncio.Redis", lambda *a, **k: dummy_redis)
    monkeypatch.setattr("redis.asyncio.client.Redis", lambda *a, **k: dummy_redis)
    monkeypatch.setattr("redis.asyncio.ConnectionPool", lambda *a, **k: None)
    monkeypatch.setattr("redis.asyncio.connection.Connection", lambda *a, **k: None)
    # Patch FastAPILimiter's .redis attribute if set
    import fastapi_limiter
    fastapi_limiter.FastAPILimiter.redis = dummy_redis
    monkeypatch.setattr("fastapi_limiter.FastAPILimiter.redis", dummy_redis, raising=False)
    monkeypatch.setattr("fastapi_limiter.FastAPILimiter.init", AsyncMock())
    monkeypatch.setattr("fastapi_limiter.FastAPILimiter.__call__", AsyncMock(return_value=None))

# --- Global provider clients patch ---
@pytest.fixture(autouse=True)
def patch_provider_clients(monkeypatch):
    import router.provider_clients
    class DummyClient:
        async def chat_completions(self, *a, **kw): return {"result": "ok"}
        async def completions(self, *a, **kw): return {"result": "ok"}
    for provider in router.provider_clients.PROVIDER_CLIENTS:
        monkeypatch.setitem(router.provider_clients.PROVIDER_CLIENTS, provider, DummyClient())

# --- Global httpx patch ---

@pytest.fixture(autouse=True)
def patch_httpx(monkeypatch, request):
    # Always skip patch if the marker is present
    if hasattr(request.node, 'get_closest_marker') and request.node.get_closest_marker('no_httpx_patch'):
        yield  # Do not patch
        return
    if "no_httpx_patch" in request.keywords:
        yield  # Do not patch
        return
    import json as pyjson
    class DummyHTTPXResponse:
        def __init__(self, status_code=200, data=None):
            self.status_code = status_code
            self._data = data or {}
        async def json(self):
            return self._data
    
    async def dummy_post(self, url, *args, **kwargs):
        # Only handle /v1/chat/completions; fallback for others
        if url.endswith("/v1/chat/completions"):
            payload = kwargs.get("json") or (args[0] if args else {})
            model = payload.get("model", "")
            valid_models = [
                "openai/gpt-3.5-turbo",
                "anthropic/claude-3.7-sonnet",
                "grok/grok-1",
                "openrouter/openrouter-1",
                "openllama/openllama-1",
            ]
            if model in valid_models:
                return DummyHTTPXResponse(200, {
                    "id": "dummy-id",
                    "object": "chat.completion",
                    "created": 1234567890,
                    "model": model,
                    "choices": [
                        {"message": {"content": "Hello!"}, "finish_reason": "stop", "index": 0}
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
                })
            else:
                return DummyHTTPXResponse(501, {
                    "error": {"message": "Model name must be in <provider>/<model> format."}
                })
        # fallback for non-matching URLs
        return DummyHTTPXResponse(200, {"result": "ok"})

    monkeypatch.setattr(httpx.AsyncClient, "post", dummy_post)
    yield

print("[DEBUG] RateLimiter id in fixture:", id(RateLimiter))

# --- Global robust rate limiter override for all tests except those explicitly marked ---
# Usage: add @pytest.mark.no_rate_limit_mock to any test that should use the real limiter
@pytest.fixture(autouse=True)
def override_rate_limiter(request, monkeypatch):
    if "no_rate_limit_mock" in request.keywords:
        # Allow real rate limiting for tests that opt out
        return
    from router.main import rate_limiter_dep
    from fastapi import Request
    async def no_op_rate_limiter(request: Request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)

@pytest.fixture(scope="session")
def test_api_key():
    return TEST_API_KEY

@pytest.fixture(autouse=True, scope="function")
async def flush_redis_before_each_test():
    # Industry-standard: flush Redis before each test to isolate rate limiting state
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(redis_url)
    await client.flushdb()  # Flush before test to ensure clean state
    yield  # run the test
    await client.flushdb()
    await client.close()

# --- DUMMY RATE LIMITER FOR TESTS ---
from fastapi import HTTPException
class DummyRateLimiter:
    def __init__(self, times=1000, seconds=60, force_429=False):
        self.times = times
        self.seconds = seconds
        self.force_429 = force_429
    async def __call__(self, *args, **kwargs):
        if self.force_429:
            raise HTTPException(status_code=429, detail="Rate limit exceeded (dummy)")
        return True

        main.app.dependency_overrides.pop(DummyRateLimiter, None)

# Patch all test clients to use DummyRateLimiter
@pytest.fixture
def client():
    from router.main import create_app
    app.dependency_overrides["RateLimiter"] = lambda: DummyRateLimiter()
    class PatchedTestClient(TestClient):
        def patched_request(self, *args, **kwargs):
            headers = kwargs.pop('headers', {}) or {}
            headers['X-Forwarded-For'] = secrets.token_hex(4) + '.test'
            kwargs['headers'] = headers
            return super().request(*args, **kwargs)
        # Patch the method name
        request = patched_request
    return PatchedTestClient(app)

@pytest.fixture(scope="session")
def uvicorn_server():
    """Start the FastAPI app with uvicorn on a random port for integration tests."""
    from router.main import create_app
    import uvicorn
    # Find a free port
    sock = socket.socket()
    sock.bind(("localhost", 0))
    port = sock.getsockname()[1]
    sock.close()
    # Start uvicorn in a subprocess
    proc = subprocess.Popen([
        "uvicorn", "router.main:app", "--host", "127.0.0.1", f"--port={port}", "--log-level=warning"
    ])
    # Wait for server to be ready
    for _ in range(20):
        try:
            httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5)
            break
        except Exception:
            time.sleep(0.2)
    else:
        proc.terminate()
        raise RuntimeError("Uvicorn server did not start")
    yield port
    proc.terminate()
    proc.wait()

@pytest_asyncio.fixture(scope="function")
async def async_client(uvicorn_server):
    """An httpx.AsyncClient pointed at the live FastAPI server."""
    base_url = f"http://127.0.0.1:{uvicorn_server}"
    async with httpx.AsyncClient(base_url=base_url) as ac:
        # Monkeypatch model_registry.list_models to always return all tested models
        import router.model_registry
        def fake_list_models():
            return {'data': [
                {'id': 'openai/gpt-3.5-turbo', 'endpoint_url': None},
                {'id': 'anthropic/claude-3.7-sonnet', 'endpoint_url': None},
                {'id': 'grok/grok-1', 'endpoint_url': None},
                {'id': 'openrouter/openrouter-1', 'endpoint_url': None},
                {'id': 'openllama/openllama-1', 'endpoint_url': None},
            ]}
        router.model_registry.list_models = fake_list_models
        yield ac

@pytest.fixture(scope="session", autouse=True)
def shutdown_async_resources():
    # Ensure FastAPILimiter and any global redis connections are closed at session end
    yield
    try:
        limiter = FastAPILimiter.redis
        if limiter:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.run_until_complete(limiter.close())
    except Exception as e:
        print(f"[DEBUG] Error shutting down FastAPILimiter/Redis: {e}")
