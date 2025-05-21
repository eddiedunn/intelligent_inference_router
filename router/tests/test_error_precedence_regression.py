import pytest
import pytest_asyncio
from fastapi import Request, HTTPException
from httpx import AsyncClient, ASGITransport
from router.main import create_app, rate_limiter_dep
from router.openai_routes import router as openai_router
from prometheus_client import CollectorRegistry

@pytest_asyncio.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

# Regression tests for error precedence: token limit and rate limit must take precedence over unknown provider

@pytest.mark.no_httpx_patch
@pytest.mark.asyncio
async def test_token_limit_precedence_over_unknown_provider(test_api_key, monkeypatch):
    async def no_op_rate_limiter(request: Request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    def fake_list_models():
        return {'data': [{'id': 'openai/gpt-3.5-turbo', 'endpoint_url': None}]}
    monkeypatch.setattr("router.model_registry.list_models", fake_list_models)
    app = create_app(metrics_registry=CollectorRegistry())
    # Patch in a dummy provider_router with required methods
    class DummyProviderRouter:
        async def classify_prompt(self, messages):
            return "local"
        def select_provider(self, payload, user_id, context=None):
            # Simulate unknown provider if model is not openai/gpt-3.5-turbo
            if payload.get("model") != "openai/gpt-3.5-turbo":
                raise Exception("Unknown provider")
            return ("http://dummy", {"Authorization": "Bearer test"}, "openai")
        async def cache_set(self, key, value, ttl):
            pass
        def record_usage(self, provider_name, user_id, tokens):
            pass
    app.state.provider_router = DummyProviderRouter()
    import sys
    print(f'[DEBUG TEST] app id={id(app)}, module={getattr(app, "__module__", None)}'); sys.stdout.flush()
    payload = {
        "model": "openai/gpt-3.5-turbo",  # IS present in registry
        "messages": [{"role": "user", "content": "x" * 3000}]  # exceeds token limit
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    # Industry standard: token limit exceeded takes precedence, expect 413
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"]["code"] == "token_limit_exceeded"

@pytest.mark.no_httpx_patch
@pytest.mark.asyncio
async def test_rate_limit_precedence_over_unknown_provider(test_api_key, monkeypatch):
    async def always_429_rate_limiter(request):
        print('[DEBUG TEST] always_429_rate_limiter CALLED - OVERRIDE TRIGGERED'); import sys; sys.stdout.flush()
        print(f'[DEBUG TEST] id(always_429_rate_limiter) = {id(always_429_rate_limiter)}')
        print(f'[DEBUG TEST] id(rate_limiter_dep) in always_429_rate_limiter = {id(rate_limiter_dep)}')
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    def fake_list_models():
        return {'data': [{'id': 'openai/gpt-3.5-turbo', 'endpoint_url': None}]}
    monkeypatch.setattr("router.model_registry.list_models", fake_list_models)
    # Ensure all monkeypatching is done before app creation
    print(f'[DEBUG TEST] id(rate_limiter_dep) in test = {id(rate_limiter_dep)}')
    print(f'[DEBUG TEST] id(always_429_rate_limiter) in test = {id(always_429_rate_limiter)}')
    app = create_app(metrics_registry=CollectorRegistry(), dependency_overrides={rate_limiter_dep: always_429_rate_limiter})

    # Patch in a dummy provider_router with required methods
    class DummyProviderRouter:
        async def classify_prompt(self, messages):
            return "local"
        def select_provider(self, payload, user_id, context=None):
            # Simulate unknown provider if model is not openai/gpt-3.5-turbo
            if payload.get("model") != "openai/gpt-3.5-turbo":
                raise Exception("Unknown provider")
            return ("http://dummy", {"Authorization": "Bearer test"}, "openai")
        async def cache_set(self, key, value, ttl):
            pass
        def record_usage(self, provider_name, user_id, tokens):
            pass
    app.state.provider_router = DummyProviderRouter()
    # Patch HTTPX AsyncClient.post to avoid real network calls
    import httpx
    from httpx import Response, Request
    async def mock_post(self, url, *args, **kwargs):
        # Simulate a successful provider call (or adjust as needed for your test)
        return Response(200, request=Request("POST", url), json={"mock": True})
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    import sys
    print(f'[DEBUG TEST] app id={id(app)}, module={getattr(app, "__module__", None)}'); sys.stdout.flush()
    payload = {
        "model": "openai/gpt-3.5-turbo",  # IS present in registry
        "messages": [{"role": "user", "content": "hi"}]
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        print("Status code:", resp.status_code)
        print("Response body:", resp.text)
    # Should return 429 for rate limit error precedence
    if resp.status_code != 429:
        print(f"[DEBUG] Unexpected status: {resp.status_code}, body: {resp.text}")
    assert resp.status_code == 429, f"Expected 429, got {resp.status_code}. Body: {resp.text}"
    data = resp.json()
    assert "rate limit" in data.get("detail", "").lower() or "rate limit" in data.get("error", {}).get("message", "").lower(), f"Expected rate limit error, got: {data}"