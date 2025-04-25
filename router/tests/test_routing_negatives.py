import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from router.main import app
import os

@pytest.mark.asyncio
async def test_chat_completions_missing_model(test_api_key):
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    print(f"[DEBUG] missing_model resp.status_code={resp.status_code}")
    print(f"[DEBUG] missing_model resp.body={resp.text}")
    assert resp.status_code == 400
    assert "Missing required fields" in resp.json()["error"]["message"]

@pytest.mark.asyncio
async def test_chat_completions_missing_messages(test_api_key):
    payload = {"model": "gpt-3.5-turbo"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    if resp.status_code != 400 or "Missing required fields" not in resp.json()["error"]["message"]:
        raise AssertionError(f"[DEBUG] missing_messages resp.status_code={resp.status_code}\n[DEBUG] missing_messages resp.text={resp.text}")
    assert resp.status_code == 400
    assert "Missing required fields" in resp.json()["error"]["message"]

@pytest.mark.asyncio
async def test_chat_completions_invalid_payload(test_api_key):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", data="not a json", headers={"Authorization": f"Bearer {test_api_key}"})
    print(f"[DEBUG] invalid_payload resp.status_code={resp.status_code}")
    print(f"[DEBUG] invalid_payload resp.body={resp.text}")
    assert resp.status_code in (400, 422)
    assert "Invalid JSON payload" in resp.json()["error"]["message"]

@pytest.mark.asyncio
async def test_chat_completions_token_limit(test_api_key):
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "x" * 3000}]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    if resp.status_code != 413 or "token limit" not in resp.text:
        raise AssertionError(f"[DEBUG] token_limit resp.status_code={resp.status_code}\n[DEBUG] token_limit resp.text={resp.text}")
    assert resp.status_code == 413
    assert "token limit" in resp.text

@pytest.mark.asyncio
async def test_chat_completions_rate_limit_exceeded(test_api_key, monkeypatch):
    from fastapi import HTTPException
    # Patch get_rate_limiter to always raise HTTPException using a class with async __call__
    class Always429:
        async def __call__(self, request, response, *args, **kwargs):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
    monkeypatch.setattr("router.main.get_rate_limiter", lambda: Always429())
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
    payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 502
    assert "Remote provider error" in resp.text

@pytest.mark.asyncio
async def test_chat_completions_unknown_model(test_api_key):
    payload = {"model": "foo-unknown", "messages": [{"role": "user", "content": "hi"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    print(f"[DEBUG] unknown_model resp.status_code={resp.status_code}")
    print(f"[DEBUG] unknown_model resp.body={resp.text}")
    assert resp.status_code == 400
    assert "Unknown remote provider for model" in resp.json()["error"]["message"]

# If /v1/completions endpoint exists, add similar negative tests here
