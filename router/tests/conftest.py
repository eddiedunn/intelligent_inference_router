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
def override_rate_limiter_dependency():
    """Override the RateLimiter dependency globally for tests except explicit rate limit tests."""
    from router import main
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
    return TestClient(app)
