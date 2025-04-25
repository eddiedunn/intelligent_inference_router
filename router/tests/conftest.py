import os
import secrets
import pytest
import redis.asyncio as redis

# Generate a single random API key for the whole test session
TEST_IIR_API_KEY = "test-" + secrets.token_urlsafe(16)
os.environ["IIR_API_KEY"] = TEST_IIR_API_KEY

@pytest.fixture(scope="session")
def test_api_key():
    return TEST_IIR_API_KEY

@pytest.fixture(autouse=True, scope="function")
def flush_redis_before_each_test():
    # Industry-standard: flush Redis before each test to isolate rate limiting state
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(redis_url)
    import asyncio
    asyncio.run(client.flushdb())  # Flush before test to ensure clean state
    yield  # run the test
    # Flush after test to ensure clean state for next test
    asyncio.run(client.flushdb())
    asyncio.run(client.close())
