import os
import secrets
import pytest
import redis.asyncio as redis
from fastapi_limiter.depends import RateLimiter
from fastapi.testclient import TestClient

print("[DEBUG] RateLimiter id in fixture:", id(RateLimiter))

@pytest.fixture(scope="function")
def test_api_key():
    # Generate a unique API key per test
    key = "test-" + secrets.token_urlsafe(16)
    os.environ["IIR_API_KEY"] = key
    return key

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
