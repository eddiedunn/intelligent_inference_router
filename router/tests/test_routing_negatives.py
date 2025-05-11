import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from router.main import create_app, rate_limiter_dep
import os
from prometheus_client import CollectorRegistry

# --- Negative tests for /v1/chat/completions ---
# These tests override the rate limiter to a no-op to avoid Redis/fastapi-limiter infra errors.

@pytest.mark.asyncio
async def test_chat_completions_missing_model(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    async def no_op_rate_limiter(request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Model name must be in <provider>/<model> format." in resp.text

@pytest.mark.asyncio
async def test_chat_completions_missing_messages(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    async def no_op_rate_limiter(request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    payload = {"model": "gpt-3.5-turbo"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Model name must be in <provider>/<model> format." in resp.text

@pytest.mark.asyncio
async def test_chat_completions_invalid_payload(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    async def no_op_rate_limiter(request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    # Send invalid JSON (simulate by sending text instead of JSON)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", content="notjson", headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Invalid JSON payload" in resp.text

@pytest.mark.asyncio
async def test_chat_completions_token_limit(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    async def no_op_rate_limiter(request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "x" * 3000}]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Request exceeds max token limit" in resp.text

@pytest.mark.asyncio
async def test_chat_completions_rate_limit_exceeded(test_api_key, monkeypatch):
    from fastapi import HTTPException
    app = create_app(metrics_registry=CollectorRegistry())
    async def always_429_rate_limiter(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    monkeypatch.setattr("router.main.rate_limiter_dep", always_429_rate_limiter)
    payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 429
    assert "Rate limit exceeded" in resp.text

@pytest.mark.asyncio
@pytest.mark.skipif(os.getenv("MOCK_PROVIDERS") == "1", reason="Mock providers enabled, upstream error not triggered")
async def test_chat_completions_upstream_provider_error(test_api_key, monkeypatch):
    from router.provider_clients.openai import OpenAIClient
    async def raise_exc(*a, **kw):
        raise Exception("upstream failure")
    monkeypatch.setattr(OpenAIClient, "chat_completions", raise_exc)
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 502
    assert "Remote provider error" in resp.text

@pytest.mark.asyncio
async def test_chat_completions_unknown_model(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    async def no_op_rate_limiter(request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    payload = {"model": "foo-unknown", "messages": [{"role": "user", "content": "hi"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Unknown remote provider for model" in resp.text

# If /v1/completions endpoint exists, add similar negative tests here
