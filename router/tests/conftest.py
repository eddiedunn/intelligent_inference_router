import os
# Set robust test API key env for all test processes BEFORE any app/config import
TEST_API_KEY = "test-secret-key-robust"
os.environ["IIR_API_KEY"] = TEST_API_KEY
os.environ["IIR_ALLOWED_KEYS"] = TEST_API_KEY
os.environ["MOCK_PROVIDERS"] = "1"

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

@pytest.fixture(autouse=True)
def override_rate_limiter_dependency():
    from router import main
    print("[DEBUG] RateLimiter id in override fixture:", id(RateLimiter))
    # Save original dependency overrides
    original_override = main.app.dependency_overrides.get(RateLimiter)
    main.app.dependency_overrides[RateLimiter] = lambda: RateLimiter(times=1000, seconds=60)
    yield
    # Restore original dependency override
    if original_override is not None:
        main.app.dependency_overrides[RateLimiter] = original_override
    else:
        main.app.dependency_overrides.pop(RateLimiter, None)

@pytest.fixture
def client():
    from router.main import app
    class PatchedTestClient(TestClient):
        def request(self, *args, **kwargs):
            # Inject a unique client IP for each test (simulate unique user)
            headers = kwargs.pop('headers', {}) or {}
            headers['X-Forwarded-For'] = secrets.token_hex(4) + '.test'
            kwargs['headers'] = headers
            return super().request(*args, **kwargs)
    return PatchedTestClient(app)

@pytest.fixture(scope="session")
def uvicorn_server():
    """Start the FastAPI app with uvicorn on a random port for integration tests."""
    from router.main import app
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
