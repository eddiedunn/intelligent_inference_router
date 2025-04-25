import os
import secrets
import pytest
import redis.asyncio as redis
from fastapi_limiter.depends import RateLimiter
from fastapi.testclient import TestClient

# Generate a single random API key for the whole test session
TEST_IIR_API_KEY = "test-" + secrets.token_urlsafe(16)
os.environ["IIR_API_KEY"] = TEST_IIR_API_KEY

@pytest.fixture(scope="session")
def test_api_key():
    return TEST_IIR_API_KEY

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
def override_rate_limiter(monkeypatch):
    """Override the RateLimiter dependency for /v1/chat/completions to allow 1000 requests/minute during most tests."""
    from router import main
    # Find the /v1/chat/completions route and replace its dependencies
    for route in main.app.routes:
        if getattr(route, 'path', None) == '/v1/chat/completions' and hasattr(route, 'dependencies'):
            # Replace RateLimiter(times=100, seconds=60) with RateLimiter(times=1000, seconds=60)
            new_dependencies = []
            for dep in route.dependencies:
                if isinstance(dep.dependency, RateLimiter):
                    new_dependencies.append(
                        main.Depends(RateLimiter(times=1000, seconds=60))
                    )
                else:
                    new_dependencies.append(dep)
            route.dependencies = new_dependencies
