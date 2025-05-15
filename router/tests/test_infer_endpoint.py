import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import pytest
from fastapi.testclient import TestClient
from router.main import create_app
from prometheus_client import CollectorRegistry
from fastapi import Request

def patch_rate_limiter(monkeypatch):
    async def dummy_rate_limiter_dep(request: Request):
        return None
    monkeypatch.setattr("router.main.rate_limiter_dep", dummy_rate_limiter_dep)

def patch_scrubber(monkeypatch):
    monkeypatch.setattr("router.main.hybrid_scrub_and_log", lambda body, direction=None: body)

def auth_header():
    return {"Authorization": "Bearer test-secret-key-robust"}

@pytest.fixture(autouse=True)
def patch_deps(monkeypatch):
    async def dummy_rate_limiter_dep(request: Request):
        return None
    monkeypatch.setattr("router.main.rate_limiter_dep", dummy_rate_limiter_dep)
    monkeypatch.setattr("router.main.hybrid_scrub_and_log", lambda body, direction=None: body)
from prometheus_client import CollectorRegistry

def test_infer_valid(monkeypatch):
    # Patch httpx.post and load_config before app creation
    import httpx
    monkeypatch.setattr("router.main.load_config", lambda: {"services": {"openai/gpt-4.1": "http://mockservice", "musicgen": "http://mockservice"}})
    monkeypatch.setattr(
    httpx,
    "post",
    lambda *args, **kwargs: type(
        "Resp", (),
        {"json": (lambda *a, **kw: {"model": "gpt-4.1"}), "status_code": 200}
    )()
)

    from router.main import create_app
    app = create_app(metrics_registry=CollectorRegistry())
    client = TestClient(app)
    payload = {
        "model": "openai/gpt-4.1",
        "input": {"prompt": "Hello!"}
    }
    print("[ROUTES]")
    for route in app.routes:
        print(route)
    with TestClient(app) as client:
        r = client.post("/infer", headers=auth_header(), json=payload)
        if r.status_code != 200:
            print(f"FAIL: status={r.status_code}, body={r.text}")
        assert r.status_code == 200
        assert r.json()["model"] == "gpt-4.1"

def test_infer_invalid_model(monkeypatch):
    import httpx
    monkeypatch.setattr("router.main.load_config", lambda: {"services": {}})
    monkeypatch.setattr(httpx, "post", lambda url, json: type("Resp", (), {"json": lambda: {}, "status_code": 200})())
    from router.main import create_app
    app = create_app(metrics_registry=CollectorRegistry())
    client = TestClient(app)
    payload = {"model": "invalidmodel", "input": {"prompt": "test"}}
    r = client.post("/infer", headers=auth_header(), json=payload)
    assert r.status_code == 400
    # Accept either custom or generic error message
    assert ('Model name must be in <provider>/<model> format.' in r.text) or ("Invalid request payload" in r.text)

def test_infer_unknown_provider(monkeypatch):
    import httpx
    monkeypatch.setattr("router.main.load_config", lambda: {"services": {}})
    monkeypatch.setattr(httpx, "post", lambda url, json: type("Resp", (), {"json": lambda: {}, "status_code": 200})())
    from router.main import create_app
    app = create_app(metrics_registry=CollectorRegistry())
    client = TestClient(app)
    payload = {"model": "unknownprovider/modelname", "input": {"prompt": "test"}}
    r = client.post("/infer", headers=auth_header(), json=payload)
    # Accept both 400 and 404, and check for expected error text
    assert r.status_code in (400, 404)
    assert ('Unknown remote provider for model' in r.text) or ("Invalid request payload" in r.text)

def test_infer_missing_auth():
    from unittest.mock import patch
    with patch("router.main.load_config", return_value={"services": {"openai/gpt-4.1": "http://mockservice", "musicgen": "http://mockservice"}}):
        app = create_app(metrics_registry=CollectorRegistry())
        client = TestClient(app)
        payload = {"model": "openai/gpt-4.1", "input": {"prompt": "test"}}
        r = client.post("/infer", json=payload)
        assert r.status_code == 401

def test_infer_missing_model(monkeypatch):
    monkeypatch.setattr("router.main.load_config", lambda: {"services": {}})
    app = create_app(metrics_registry=CollectorRegistry())
    client = TestClient(app)
    payload = {"input": {"prompt": "test"}}
    r = client.post("/infer", headers=auth_header(), json=payload)
    assert r.status_code == 422 or r.status_code == 400
    assert "model" in r.text or "field required" in r.text
