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
    return {"Authorization": "Bearer test-secret-key-robust"}

app = create_app(metrics_registry=CollectorRegistry())
client = TestClient(app)

def test_chat_completions_valid_multi_slash(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    class DummyClient:
        async def chat_completions(self, payload, model, **kwargs):
            assert model == "meta-llama/Llama-3-70b-chat-hf"
            return type("Resp", (), {"content": {"result": "ok", "model": model}, "status_code": 200})()
    monkeypatch.setitem(
        __import__("router.provider_clients", fromlist=["PROVIDER_CLIENTS"]).PROVIDER_CLIENTS,
        "openrouter", DummyClient()
    )
    payload = {
        "model": "openrouter/meta-llama/Llama-3-70b-chat-hf",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
    r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
    assert r.status_code == 200
    assert r.json()["model"] == "meta-llama/Llama-3-70b-chat-hf"

def test_chat_completions_invalid_model(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    payload = {"model": "invalidmodel", "messages": [{"role": "user", "content": "hi"}]}
    r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
    assert r.status_code == 400
    assert "invalid_model_name" in str(r.content)

def test_chat_completions_unknown_provider(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    payload = {"model": "unknownprovider/modelname", "messages": [{"role": "user", "content": "hi"}]}
    r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
    assert r.status_code == 400
    assert "unknown_provider" in str(r.content)

def test_chat_completions_missing_auth():
    payload = {"model": "openai/gpt-4", "messages": [{"role": "user", "content": "test"}]}
    r = client.post("/v1/chat/completions", json=payload)
    assert r.status_code == 401

def test_chat_completions_missing_model(monkeypatch):
    patch_rate_limiter(monkeypatch)
    patch_scrubber(monkeypatch)
    payload = {"messages": [{"role": "user", "content": "test"}]}
    r = client.post("/v1/chat/completions", headers=auth_header(), json=payload)
    assert r.status_code == 400
    assert "model" in str(r.content)
