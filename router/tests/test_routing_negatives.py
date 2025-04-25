import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from router.main import app

client = TestClient(app)

# --- Negative/edge tests for /v1/chat/completions ---

def test_chat_completions_missing_model(test_api_key):
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    resp = client.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Missing required fields" in resp.text

def test_chat_completions_missing_messages(test_api_key):
    payload = {"model": "gpt-3.5-turbo"}
    resp = client.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Missing required fields" in resp.text

def test_chat_completions_invalid_payload(test_api_key):
    resp = client.post("/v1/chat/completions", data="not a json", headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code in (400, 422)

def test_chat_completions_token_limit(test_api_key):
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "x" * 3000}]
    }
    resp = client.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 413
    assert "token limit" in resp.text

# Simulate rate limit exceeded (FastAPILimiter)
def test_chat_completions_rate_limit_exceeded(test_api_key, monkeypatch):
    # Patch RateLimiter to always raise HTTPException
    from fastapi import HTTPException
    monkeypatch.setattr("fastapi_limiter.depends.RateLimiter.__call__", lambda self, *a, **kw: (_ for _ in ()).throw(HTTPException(status_code=429, detail="Rate limit exceeded")))
    payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    resp = client.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 429
    assert "Rate limit exceeded" in resp.text

# Simulate upstream provider error propagation
def test_chat_completions_upstream_provider_error(test_api_key, monkeypatch):
    # Patch provider client to raise Exception
    from router.provider_clients.openai import OpenAIClient
    async def raise_exc(*a, **kw):
        raise Exception("upstream failure")
    monkeypatch.setattr(OpenAIClient, "chat_completions", raise_exc)
    payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    resp = client.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 502
    assert "Remote provider error" in resp.text

# Unknown model prefix
def test_chat_completions_unknown_model(test_api_key):
    payload = {"model": "foo-unknown", "messages": [{"role": "user", "content": "hi"}]}
    resp = client.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 400
    assert "Unknown remote provider for model" in resp.text

# If /v1/completions endpoint exists, add similar negative tests here
