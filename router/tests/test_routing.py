import pytest
import asyncio
from router.main import create_app, rate_limiter_dep
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

# Remove per-file key generation, use test_api_key fixture from conftest.py

# The patch_provider_clients fixture is removed. All provider mocking is now handled at the app module scope via MOCK_PROVIDERS.

@pytest.mark.parametrize("model,expected_provider", [
    ("gpt-3.5-turbo", "openai"),
    ("claude-3.7-sonnet", "anthropic"),
    ("grok-1", "grok"),
    ("openrouter-1", "openrouter"),
    ("openllama-1", "openllama"),
])
@pytest.mark.asyncio
async def test_routing_remote_models(async_client, model, expected_provider, test_api_key):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hello"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    resp = await async_client.post("/v1/chat/completions", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "Hello!"

# Test local path (musicgen)
@pytest.mark.asyncio
async def test_routing_local_model(test_api_key):
    app = create_app()
    async def no_op_rate_limiter(request):
        pass
    app.dependency_overrides[rate_limiter_dep] = no_op_rate_limiter
    payload = {
        "model": "musicgen",
        "messages": [{"role": "user", "content": "hi"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["message"] == "Unknown remote provider for model"

# Test error on unknown model prefix
@pytest.mark.asyncio
async def test_routing_unknown_model(async_client, test_api_key):
    payload = {
        "model": "foo-unknown",
        "messages": [{"role": "user", "content": "hi"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    resp = await async_client.post("/v1/chat/completions", json=payload, headers=headers)
    assert resp.status_code == 400
    assert "Unknown remote provider for model" in resp.text
