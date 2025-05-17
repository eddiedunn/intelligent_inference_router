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
import pytest
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
        # Patch the routing map for all required providers if possible
        if hasattr(ac, "app") and hasattr(ac.app.state, "provider_router"):
            ac.app.state.provider_router.routing['model_prefix_map'] = {
                'openai/': 'openai',
                'anthropic/': 'anthropic',
                'grok/': 'grok',
                'openrouter/': 'openrouter',
                'openllama/': 'openllama',
            }
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
        # Patch providers registry for all required providers
        ac.app.state.provider_router.providers = {
            'openai': {},
            'anthropic': {},
            'grok': {},
            'openrouter': {},
            'openllama': {},
        }
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
