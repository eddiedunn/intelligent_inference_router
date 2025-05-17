import pytest
import pytest_asyncio

@pytest_asyncio.fixture(scope="session")
def event_loop():
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

from httpx import AsyncClient, ASGITransport
from router.main import create_app
from prometheus_client import CollectorRegistry
from fastapi import Request, HTTPException

# Regression tests for error precedence: token limit and rate limit must take precedence over unknown provider

@pytest.mark.asyncio
async def test_token_limit_precedence_over_unknown_provider(test_api_key, monkeypatch):
    app = create_app(metrics_registry=CollectorRegistry())
    # Ensure provider_router is set
    if not hasattr(app.state, 'provider_router'):
        from router.provider_router import ProviderRouter
        from router.cache import SimpleCache
        config = {"routing": {"model_prefix_map": {"openai/": "openai"}}}
        cache_backend = SimpleCache()
        cache_type = 'simple'
        app.state.provider_router = ProviderRouter(config, cache_backend, cache_type)
        app.state.provider_router.classify_prompt = lambda *a, **k: ("general", 1.0)
    import sys
    print(f'[DEBUG TEST] app id={id(app)}, module={getattr(app, "__module__", None)}'); sys.stdout.flush()
    async def no_op_rate_limiter(request: Request):
        pass
    monkeypatch.setattr("router.main.rate_limiter_dep", no_op_rate_limiter)
    # Patch model registry so 'openai/gpt-3.5-turbo' IS present (token limit precedence)
    def fake_list_models():
        return {'data': [{'id': 'openai/gpt-3.5-turbo', 'endpoint_url': None}]}
    monkeypatch.setattr("router.model_registry.list_models", fake_list_models)
    payload = {
        "model": "openai/gpt-3.5-turbo",  # IS present in registry
        "messages": [{"role": "user", "content": "x" * 3000}]  # exceeds token limit
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/v1/chat/completions", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
    assert resp.status_code == 413
    data = resp.json()
    assert data["error"]["code"] == "token_limit_exceeded"

@pytest.mark.asyncio
async def test_rate_limit_precedence_over_unknown_provider(test_api_key, monkeypatch):
    # Monkeypatch BEFORE app creation!
    async def always_429_rate_limiter(request: Request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    monkeypatch.setattr("router.main.rate_limiter_dep", always_429_rate_limiter)
    def fake_list_models():
        return {'data': [{'id': 'openai/gpt-3.5-turbo', 'endpoint_url': None}]}
    monkeypatch.setattr("router.model_registry.list_models", fake_list_models)
    app = create_app(metrics_registry=CollectorRegistry())
    # Ensure provider_router is set
    if not hasattr(app.state, 'provider_router'):
        from router.provider_router import ProviderRouter
        from router.cache import SimpleCache
        config = {"routing": {"model_prefix_map": {"openai/": "openai"}}}
        cache_backend = SimpleCache()
        cache_type = 'simple'
        app.state.provider_router = ProviderRouter(config, cache_backend, cache_type)
        app.state.provider_router.classify_prompt = lambda *a, **k: ("general", 1.0)
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
    if resp.status_code != 429:
        print(f"[DEBUG] Unexpected status: {resp.status_code}, body: {resp.text}")
    assert resp.status_code in (429, 400)
    data = resp.json()
    assert data["error"]["code"] == "rate_limit_exceeded"
