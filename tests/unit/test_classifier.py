import pytest
from router.classifier import classify_prompt

@pytest.mark.asyncio
async def test_classify_prompt(monkeypatch):
    class FakeClassifier:
        def __call__(self, prompt, labels, hypothesis_template=None):
            return {"labels": ["local", "remote"]}
    monkeypatch.setattr("router.classifier.get_classifier", lambda: FakeClassifier())
    from router.classifier import classify_prompt
    result = await classify_prompt("Test prompt")
    assert result == "local"
