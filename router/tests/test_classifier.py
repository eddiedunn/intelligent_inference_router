import pytest
from router.classifier import classify_prompt
import asyncio

@pytest.mark.asyncio
def test_classify_prompt_basic(monkeypatch, test_api_key):
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)
    result = asyncio.run(classify_prompt("generate music")) if asyncio.iscoroutinefunction(classify_prompt) else classify_prompt("generate music")
    assert isinstance(result, str)
    assert result in ("musicgen", "textgen", "unknown", "local")

# Add more tests for classifier edge cases as needed
