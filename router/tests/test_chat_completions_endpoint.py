import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import pytest
from fastapi.testclient import TestClient
from router.main import create_app
from prometheus_client import CollectorRegistry

def patch_rate_limiter(monkeypatch):
    async def dummy_rate_limiter_dep(request):
        return None
    monkeypatch.setattr("router.main.rate_limiter_dep", dummy_rate_limiter_dep)

def patch_scrubber(monkeypatch):
    monkeypatch.setattr("router.main.hybrid_scrub_and_log", lambda body, direction=None: body)

def auth_header():
    # Use 'changeme' for test mode to always pass authentication
    return {"Authorization": "Bearer changeme"}


def test_chat_completions_valid_multi_slash(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    # Patch load_config so services includes the test model
    monkeypatch.setattr("router.main.load_config", lambda: {"services": {"openrouter/meta-llama/Llama-3-70b-chat-hf": "http://dummy"}})
    class DummyClient:
        async def chat_completions(self, payload, model, **kwargs):
            assert model == "openrouter/meta-llama/Llama-3-70b-chat-hf"
            return type("Resp", (), {"content": {"result": "ok", "model": model}, "status_code": 200})()
    monkeypatch.setitem(
        __import__("router.provider_clients", fromlist=["PROVIDER_CLIENTS"]).PROVIDER_CLIENTS,
        "openrouter", DummyClient()
    )
    app = create_app(metrics_registry=CollectorRegistry())
    # Ensure provider_router is set
    if not hasattr(app.state, 'provider_router'):
        from router.provider_router import ProviderRouter
        from router.cache import SimpleCache
        # Minimal config for test
        config = {"routing": {"model_prefix_map": {"openrouter/": "openrouter"}}}
        cache_backend = SimpleCache()
        cache_type = 'simple'
        app.state.provider_router = ProviderRouter(config, cache_backend, cache_type)
        app.state.provider_router.classify_prompt = lambda *a, **k: ("general", 1.0)

    # Patch classify_prompt for test context
    
        # Patch classify_prompt for test context
        
    payload = {
        "model": "openrouter/meta-llama/Llama-3-70b-chat-hf",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
    with TestClient(app) as client:
        client.app.state.provider_router.routing['model_prefix_map'] = {'openrouter/': 'openrouter'}
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        if r.status_code != 200:
            print(f"[TEST DEBUG] Unexpected status: {r.status_code}, body: {r.text}")
        assert r.status_code == 200
        assert r.json()["result"] == "ok"
        assert r.json()["model"] == "openrouter/meta-llama/Llama-3-70b-chat-hf"
    return
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    class DummyClient:
        async def chat_completions(self, payload, model, **kwargs):
            assert model == "openrouter/meta-llama/Llama-3-70b-chat-hf"
            return type("Resp", (), {"content": {"result": "ok", "model": model}, "status_code": 200})()
    monkeypatch.setitem(
        __import__("router.provider_clients", fromlist=["PROVIDER_CLIENTS"]).PROVIDER_CLIENTS,
        "openrouter", DummyClient()
    )
    payload = {
        "model": "openrouter/meta-llama/Llama-3-70b-chat-hf",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
    with TestClient(app) as client:
        # Patch the routing map so openrouter/ is routed to openrouter
        client.app.state.provider_router.routing['model_prefix_map'] = {'openrouter/': 'openrouter'}
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        assert r.status_code == 200
        assert r.json()["model"] == "openrouter/meta-llama/Llama-3-70b-chat-hf"

def test_chat_completions_invalid_model(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"model": "invalidmodel", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        assert r.status_code == 400
        assert "Model name must be in <provider>/<model> format." in str(r.content)

def test_chat_completions_unknown_provider(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {
        "model": "unknown/foobar",
        "messages": [{"role": "user", "content": "hi"}]
    }
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        assert r.status_code == 400
        assert "Unknown remote provider for model" in r.text

def test_chat_completions_missing_auth():
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"model": "openai/gpt-4.1", "messages": [{"role": "user", "content": "test"}]}
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions", json=payload)
        assert r.status_code == 401

def test_chat_completions_missing_model(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"messages": [{"role": "user", "content": "test"}]}
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        assert r.status_code == 400
    assert "model" in str(r.content)
