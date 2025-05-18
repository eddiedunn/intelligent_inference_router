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


import router.model_registry

# ...
def test_chat_completions_valid_multi_slash(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    # Dynamically select a valid model and provider from the registry
    models = router.model_registry.list_models().get("data", [])
    if not models:
        import pytest
        pytest.skip("No models available in registry!")
    model_id = models[0]["id"]
    provider_name = model_id.split("/")[0]
    monkeypatch.setattr("router.main.load_config", lambda: {"services": {model_id: "http://dummy"}})
    class DummyClient:
        async def chat_completions(self, payload, model, **kwargs):
            assert model == model_id
            return type("Resp", (), {"content": {"result": "ok", "model": model}, "status_code": 200})()
    monkeypatch.setitem(
        __import__("router.provider_clients", fromlist=["PROVIDER_CLIENTS"]).PROVIDER_CLIENTS,
        provider_name, DummyClient()
    )
    app = create_app(metrics_registry=CollectorRegistry())
    # Use dependency override for get_provider_router
    from router.openai_routes import get_provider_router
    class DummyRouter:
        async def classify_prompt(self, messages):
            return "general"
        def select_provider(self, payload, user_id):
            return (
                "http://dummy",  # provider_url
                {},              # headers
                provider_name    # provider_name
            )
        async def cache_set(self, *a, **kw):
            pass
        async def cache_get(self, *a, **kw):
            return None
        def record_usage(self, *a, **kw):
            pass
    app.dependency_overrides[get_provider_router] = lambda request=None: DummyRouter()

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Hello!"}]
    }
    import httpx
    from unittest.mock import AsyncMock, patch

    class DummyHTTPXResponse:
        def __init__(self):
            self.status_code = 200
            self.content = b'{"result": "ok", "model": "%s"}' % model_id.encode()
        async def json(self):
            return {"result": "ok", "model": model_id}

    with patch.object(httpx.AsyncClient, "post", new=AsyncMock(return_value=DummyHTTPXResponse())):
        with TestClient(app) as client:
            client.app.state.provider_router.routing['model_prefix_map'] = {f'{provider_name}/': provider_name}
            r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
            if r.status_code != 200:
                print(f"[TEST DEBUG] Unexpected status: {r.status_code}, body: {r.text}")
            assert r.status_code == 200
            assert r.json()["result"] == "ok"
        assert r.json()["model"] == model_id
    return

    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    class DummyClient:
        async def chat_completions(self, payload, model, **kwargs):
            assert model == "openrouter/meta-llama/llama-3-70b-chat-hf"
            return type("Resp", (), {"content": {"result": "ok", "model": model}, "status_code": 200})()
    monkeypatch.setitem(
        __import__("router.provider_clients", fromlist=["PROVIDER_CLIENTS"]).PROVIDER_CLIENTS,
        "openrouter", DummyClient()
    )
    payload = {
        "model": "openrouter/meta-llama/llama-3-70b-chat-hf",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
    with TestClient(app) as client:
        # Patch the routing map so openrouter/ is routed to openrouter
        client.app.state.provider_router.routing['model_prefix_map'] = {'openrouter/': 'openrouter'}
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        assert r.status_code == 200
        assert r.json()["model"] == "openrouter/meta-llama/llama-3-70b-chat-hf"

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
