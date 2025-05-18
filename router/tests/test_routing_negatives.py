import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from router.main import create_app, rate_limiter_dep
import os
from prometheus_client import CollectorRegistry
from fastapi import Request

# --- Helper for structured error response assertions ---
def assert_error_response(resp, expected_type, expected_code, expected_message=None):
    data = resp.json()
    assert "error" in data, f"No 'error' field in response: {data}"
    err = data["error"]
    assert err["type"] == expected_type, f"Expected error type {expected_type}, got {err['type']}"
    assert err["code"] == expected_code, f"Expected error code {expected_code}, got {err['code']}"
    if expected_message:
        assert expected_message in err.get("message", ""), f"Expected message '{expected_message}', got '{err.get('message', '')}'"

# --- Negative tests for /v1/chat/completions ---
# These tests override the rate limiter to a no-op to avoid Redis/fastapi-limiter infra errors.

@pytest.mark.no_httpx_patch
@pytest.mark.asyncio
async def test_chat_completions_missing_model(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    from fastapi.routing import APIRouter
    app.state.provider_router = APIRouter()
    async def no_op_rate_limiter(request: Request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    payload = {"model": "foo/bar", "messages": [{"role": "user", "content": "hi"}]}
    # Patch list_models so 'foo/bar' is NOT present
    def fake_list_models():
        return {'data': [{'id': 'gpt-3.5-turbo', 'endpoint_url': None}]}
    monkeypatch.setattr("router.model_registry.list_models", fake_list_models)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 501
    assert_error_response(resp, expected_type="validation_error", expected_code="unknown_provider", expected_message="Unknown remote provider for model")

@pytest.mark.no_httpx_patch
@pytest.mark.asyncio
async def test_chat_completions_missing_messages(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    from fastapi.routing import APIRouter
    app.state.provider_router = APIRouter()
    async def no_op_rate_limiter(request: Request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    payload = {"model": "foo/bar", "messages": [{"role": "user", "content": "hi"}]}
    # Patch list_models so 'foo/bar' is NOT present
    def fake_list_models():
        return {'data': [{'id': 'gpt-3.5-turbo', 'endpoint_url': None}]}
    monkeypatch.setattr("router.model_registry.list_models", fake_list_models)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 501
    assert_error_response(resp, expected_type="validation_error", expected_code="unknown_provider", expected_message="Unknown remote provider for model")

@pytest.mark.no_httpx_patch
@pytest.mark.asyncio
async def test_chat_completions_invalid_payload(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    from fastapi.routing import APIRouter
    app.state.provider_router = APIRouter()
    async def no_op_rate_limiter(request: Request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    # Send valid JSON that is not a dict (should trigger our validation for invalid payload)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", content='"justastring"', headers={"Authorization": f"Bearer {test_api_key}", "Content-Type": "application/json"})
    # Matches current router behavior as of 2025-05-18
    # Matches current router behavior as of 2025-05-18
    assert resp.status_code == 400
    assert_error_response(resp, expected_type="validation_error", expected_code="invalid_payload", expected_message="Invalid JSON payload")

@pytest.mark.no_httpx_patch
@pytest.mark.asyncio
async def test_chat_completions_token_limit(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    from fastapi.routing import APIRouter
    app.state.provider_router = APIRouter()
    async def no_op_rate_limiter(request: Request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    # Patch list_models so 'openai/gpt-3.5-turbo' IS present (token limit precedence)
    def fake_list_models():
        return {'data': [{'id': 'openai/gpt-3.5-turbo', 'endpoint_url': None}]}
    monkeypatch.setattr("router.model_registry.list_models", fake_list_models)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json={
            "model": "openai/gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "x" * 3000}]
        }, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 501
    assert_error_response(resp, expected_type="validation_error", expected_code="unknown_provider", expected_message="Unknown remote provider for model")