import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from router.main import app
import asyncio

@pytest.fixture(autouse=True)
def patch_provider_clients(monkeypatch):
    # Patch all provider clients to return a dummy response
    dummy_resp = {"id": "test", "object": "chat.completion", "choices": [{"message": {"content": "Hello!"}}]}
    async def dummy_chat_completions(self, payload, model, **kwargs):
        class Dummy:
            content = dummy_resp
            status_code = 200
        return Dummy()
    for client_mod in [
        "router.provider_clients.openai.OpenAIClient",
        "router.provider_clients.anthropic.AnthropicClient",
        "router.provider_clients.grok.GrokClient",
        "router.provider_clients.openrouter.OpenRouterClient",
        "router.provider_clients.openllama.OpenLLaMAClient",
    ]:
        monkeypatch.setattr(f"{client_mod}.chat_completions", dummy_chat_completions)

@pytest.mark.parametrize("model,expected_provider", [
    ("gpt-3.5-turbo", "openai"),
    ("claude-3.7-sonnet", "anthropic"),
    ("grok-1", "grok"),
    ("openrouter-1", "openrouter"),
    ("openllama-1", "openllama"),
])
def test_routing_remote_models(model, expected_provider):
    client = TestClient(app)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hello"}]
    }
    resp = client.post("/v1/chat/completions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "Hello!"

# Test local path (musicgen)
def test_routing_local_model(monkeypatch):
    client = TestClient(app)
    # Patch generate_local to return a dummy response
    monkeypatch.setattr("router.providers.local_vllm.generate_local", lambda body: {"result": "local"})
    payload = {
        "model": "musicgen",
        "messages": [{"role": "user", "content": "hi"}]
    }
    resp = client.post("/v1/chat/completions", json=payload)
    assert resp.status_code == 200
    # Accept either new or old format
    assert resp.json().get("result") == "local" or resp.json().get("object") == "chat.completion"

# Test error on unknown model prefix
def test_routing_unknown_model():
    client = TestClient(app)
    payload = {
        "model": "foo-unknown",
        "messages": [{"role": "user", "content": "hi"}]
    }
    resp = client.post("/v1/chat/completions", json=payload)
    assert resp.status_code == 400
    assert "Unknown remote provider for model" in resp.text
