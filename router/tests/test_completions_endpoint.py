import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import sys
print('[DEBUG] IMPORT: test_completions_endpoint.py loaded'); sys.stdout.flush()
import pytest
from fastapi.testclient import TestClient
from fastapi import Request
from router.main import create_app
from prometheus_client import CollectorRegistry

app = create_app(metrics_registry=CollectorRegistry())

def auth_header():
    # Use 'changeme' for test mode to always pass authentication
    return {"Authorization": "Bearer changeme"}

def patch_rate_limiter(monkeypatch):
    async def dummy_rate_limiter_dep(request: Request):
        return None
    monkeypatch.setattr("router.main.rate_limiter_dep", dummy_rate_limiter_dep)

def patch_scrubber(monkeypatch):
    monkeypatch.setattr("router.main.hybrid_scrub_and_log", lambda body, direction=None: body)

def test_completions_valid_multi_slash(monkeypatch):
    # Patch all dependencies BEFORE app/client creation
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    monkeypatch.setattr(
        "router.main.load_config",
        lambda: {
            "services": {"openrouter/meta-llama/Llama-3-70b-chat-hf": "http://dummy"},
            "model_prefix_map": {"openrouter/": "openrouter"}
        }
    )
    monkeypatch.setattr(
        "router.model_registry.list_models",
        lambda: {'data': [{'id': 'openrouter/meta-llama/Llama-3-70b-chat-hf', 'endpoint_url': None}]}
    )
    class DummyClient:
        async def completions(self, payload, model, **kwargs):
            assert model == "meta-llama/Llama-3-70b-chat-hf"
            return type("Resp", (), {"content": {"result": "ok", "model": model}, "status_code": 200})()
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
    # Now create app and client after all monkeypatches
    app = create_app(metrics_registry=CollectorRegistry())
    with TestClient(app) as client:
        client.app.state.provider_router.routing['model_prefix_map'] = {'openrouter/': 'openrouter'}
        # Use FastAPI dependency override for get_provider_router
        from router.openai_routes import get_provider_router
        class DummyRouter:
            async def classify_prompt(self, messages):
                print('[DEBUG TEST] DummyRouter.classify_prompt CALLED')
                return "local"
            def select_provider(self, payload, user_id):
                # Provide the minimal interface needed for the test
                return (
                    "http://dummy",  # provider_url
                    {},              # headers
                    "openrouter"    # provider_name
                )
            async def cache_set(self, *a, **kw):
                pass
            def record_usage(self, *a, **kw):
                pass
        app.dependency_overrides[get_provider_router] = lambda: DummyRouter()
        # Patch httpx.AsyncClient.post to return a dummy response
        import httpx
        from unittest.mock import AsyncMock, patch
        class DummyHTTPXResponse:
            def __init__(self):
                self.status_code = 200
            async def json(self):
                return {"result": "ok", "model": payload["model"]}
            @property
            def content(self):
                return {"result": "ok", "model": payload["model"]}
        async def dummy_post(*args, **kwargs):
            return DummyHTTPXResponse()
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=dummy_post)):
            r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
            assert r.status_code == 200
            assert r.json()["result"] == "ok"
            assert r.json()["model"] == "openrouter/meta-llama/Llama-3-70b-chat-hf"

def test_completions_invalid_model(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    payload = {"model": "invalidmodel", "messages": [{"role": "user", "content": "test"}]}
    app = create_app(metrics_registry=CollectorRegistry())
    from router.openai_routes import get_provider_router
    class DummyRouter:
        async def classify_prompt(self, messages):
            return "local"
        def select_provider(self, payload, user_id):
            return ("http://dummy", {"Authorization": "Bearer test-secret-key-robust"}, "openrouter")
        async def cache_set(self, *a, **kw):
            pass
        def record_usage(self, *a, **kw):
            pass
    with TestClient(app) as client:
        app.dependency_overrides[get_provider_router] = lambda: DummyRouter()
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        assert r.status_code == 400
        assert "Model name must be in <provider>/<model> format." in str(r.content)

def test_completions_unknown_provider(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    payload = {"model": "unknownprovider/modelname", "messages": [{"role": "user", "content": "test"}]}
    app = create_app(metrics_registry=CollectorRegistry())
    from router.openai_routes import get_provider_router
    class DummyRouter:
        async def classify_prompt(self, messages):
            return "local"
        def select_provider(self, payload, user_id):
            return ("http://dummy", {"Authorization": "Bearer test-secret-key-robust"}, "unknownprovider")
        async def cache_set(self, *a, **kw):
            pass
        def record_usage(self, *a, **kw):
            pass
    with TestClient(app) as client:
        app.dependency_overrides[get_provider_router] = lambda: DummyRouter()
        r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
        assert r.status_code == 400
        assert "Unknown remote provider for model" in str(r.content)

def test_completions_missing_auth():
    # No need to patch rate limiter or scrubber, as this fails before either is called
    payload = {"model": "openai/gpt-4.1", "messages": [{"role": "user", "content": "test"}]}
    app = create_app(metrics_registry=CollectorRegistry())
    from router.openai_routes import get_provider_router
    class DummyRouter:
        async def classify_prompt(self, messages):
            return "local"
        def select_provider(self, payload, user_id):
            return ("http://dummy", {}, "openai")
        async def cache_set(self, *a, **kw):
            pass
        def record_usage(self, *a, **kw):
            pass
    with TestClient(app) as client:
        r = client.post("/v1/chat/completions", json=payload)  # No auth header
        assert r.status_code == 401

def test_completions_missing_model(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    payload = {"messages": [{"role": "user", "content": "test"}]}
    app = create_app(metrics_registry=CollectorRegistry())
    from router.openai_routes import get_provider_router
    class DummyRouter:
        async def classify_prompt(self, messages):
            return "local"
        def select_provider(self, payload, user_id):
            return ("http://dummy", {"Authorization": "Bearer test-secret-key-robust"}, "openai")
        async def cache_set(self, *a, **kw):
            pass
        def record_usage(self, *a, **kw):
            pass
    import httpx
    from unittest.mock import AsyncMock, patch
    class DummyHTTPXResponse:
        def __init__(self):
            self.status_code = 200
        async def json(self):
            return {"result": "ok", "model": payload.get("model", "")}
        @property
        def content(self):
            return {"result": "ok", "model": payload.get("model", "")}
    async def dummy_post(*args, **kwargs):
        return DummyHTTPXResponse()
    with TestClient(app) as client:
        app.dependency_overrides[get_provider_router] = lambda: DummyRouter()
        with patch.object(httpx.AsyncClient, "post", new=AsyncMock(side_effect=dummy_post)):
            r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
            assert r.status_code == 400
            assert "model" in str(r.content)
