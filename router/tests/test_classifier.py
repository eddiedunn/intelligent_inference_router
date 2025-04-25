import os
import secrets
import pytest
from router.classifier import classify_prompt

import asyncio

TEST_IIR_API_KEY = "test-" + secrets.token_urlsafe(16)
os.environ["IIR_API_KEY"] = TEST_IIR_API_KEY

@pytest.fixture(scope="session")
def test_api_key():
    return TEST_IIR_API_KEY

@pytest.mark.asyncio
def test_classify_prompt_basic(test_api_key):
    headers = {"Authorization": f"Bearer {test_api_key}"}
    result = asyncio.run(classify_prompt("generate music", headers=headers)) if asyncio.iscoroutinefunction(classify_prompt) else classify_prompt("generate music", headers=headers)
    assert isinstance(result, str)
    assert result in ("musicgen", "textgen", "unknown", "local")

# Add more tests for classifier edge cases as needed
