import pytest
from router.classifier import classify_prompt

@pytest.mark.asyncio
async def test_classify_prompt(monkeypatch):
    async def fake_classify(prompt):
        return "local"
    monkeypatch.setattr("router.classifier.classify_prompt", fake_classify)
    result = await classify_prompt("Test prompt")
    assert result == "local"
