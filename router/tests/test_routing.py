import pytest
import asyncio
from fastapi import Request
from router.main import create_app, rate_limiter_dep
from prometheus_client import CollectorRegistry
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

# Remove per-file key generation, use test_api_key fixture from conftest.py

# The patch_provider_clients fixture is removed. All provider mocking is now handled at the app module scope via MOCK_PROVIDERS.

@pytest.fixture
def app():
    return create_app(metrics_registry=CollectorRegistry())

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
    assert scrub_data["object"] == "chat.completion"
    assert scrub_data["choices"][0]["message"]["content"] == "Hello!"

# Test local path (gpt-4.1)
@pytest.mark.asyncio
async def test_routing_local_model(test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    async def no_op_rate_limiter(request: Request):
        pass
    app.dependency_overrides[rate_limiter_dep] = no_op_rate_limiter
    payload = {
        "model": "gpt-4.1",
        "messages": [{"role": "user", "content": "hi"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers=headers)
    assert resp.status_code == 501
    assert resp.status_code == 501
    assert resp.json()["error"]["message"] == "Model name must be in <provider>/<model> format."

# Test error on unknown model prefix
@pytest.mark.asyncio
async def test_routing_unknown_model(async_client, test_api_key):
    payload = {
        "model": "foo-unknown",
        "messages": [{"role": "user", "content": "hi"}]
    }
    headers = {"Authorization": f"Bearer {test_api_key}"}
    resp = await async_client.post("/v1/chat/completions", json=payload, headers=headers)
    assert resp.status_code == 501
    assert resp.status_code == 501
    assert resp.json()["error"]["message"] == "Model name must be in <provider>/<model> format."
