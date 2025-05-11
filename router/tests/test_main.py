import os
import yaml
import pytest
import threading
from fastapi.testclient import TestClient
from router.main import create_app
from prometheus_client import CollectorRegistry

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '../config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_health():
    app = create_app(metrics_registry=CollectorRegistry())
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("ok", "healthy")

def test_version():
    app = create_app(metrics_registry=CollectorRegistry())
    with TestClient(app) as client:
        response = client.get("/version")
        assert response.status_code == 200
        assert "version" in response.json()

def test_config_loading():
    config = load_config()
    assert "services" in config
    assert isinstance(config["services"], dict)

def test_infer_sync(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {"result": "ok", "output": "test-output"}
            @property
            def status_code(self):
                return 200
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 200
        assert response.json()["result"] == "ok"

def test_infer_async(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {"job_id": "abc123"}
            @property
            def status_code(self):
                return 202
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}, "async": True}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code in (200, 202)
        assert "job_id" in response.json()

def test_infer_missing_model(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"model": "not_a_real_model", "input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 404 or response.status_code == 400

def test_infer_missing_input(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"model": "musicgen"}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_missing_model_field(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_invalid_payload_type(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)

    payload = ["not", "a", "dict"]
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_empty_payload(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)
    with TestClient(app) as client:
        response = client.post("/infer", json={}, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_upstream_httpx_exception(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)

    def mock_post(*args, **kwargs):
        raise Exception("Upstream error")
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 502 or response.status_code == 500

def test_infer_upstream_non_200(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)

    class MockResponse:
        def __init__(self, status_code):
            self._status_code = status_code
        def json(self):
            return {"error": "bad gateway"}
        @property
        def status_code(self):
            return self._status_code
    def mock_post(*args, **kwargs):
        return MockResponse(502)
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 502 or response.status_code == 500

# Fuzz/large payload test
def test_infer_large_payload(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)

    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {"result": "ok", "output": "test-output"}
            @property
            def status_code(self):
                return 200
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "x" * 1000000}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 200
        assert response.json()["result"] == "ok"

# Concurrency/async job status simulation
def test_infer_concurrent_requests(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)

    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {"result": "ok", "output": "test-output"}
            @property
            def status_code(self):
                return 200
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    with TestClient(app) as client:
        threads = []
        results = []
        def send_request():
            resp = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
            results.append(resp.status_code)
        for _ in range(10):
            t = threading.Thread(target=send_request)
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        assert all(code == 200 for code in results)

def test_infer_valid_api_key(monkeypatch, test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    monkeypatch.setattr("transformers.pipeline", lambda *a, **kw: lambda *a, **kw: None)

    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {"result": "ok", "output": "test-output"}
            @property
            def status_code(self):
                return 200
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 200
        assert response.json()["result"] == "ok"

def test_chat_completions_missing_api_key():
    from router.main import rate_limiter_dep
    app = create_app(metrics_registry=CollectorRegistry())
    # Print all routes for debug
    print("ROUTES:", [route.path for route in app.routes])
    # Override rate limiter to no-op for test isolation
    async def no_op_rate_limiter(request):
        pass
    app.dependency_overrides[rate_limiter_dep] = no_op_rate_limiter

    payload = {"model": "openai/gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 401


def test_chat_completions_invalid_api_key(test_api_key):
    from router.main import rate_limiter_dep
    app = create_app(metrics_registry=CollectorRegistry())
    # Print all routes for debug
    print("ROUTES:", [route.path for route in app.routes])
    # Override rate limiter to no-op for test isolation
    async def no_op_rate_limiter(request):
        pass
    app.dependency_overrides[rate_limiter_dep] = no_op_rate_limiter

    headers = {"Authorization": "Bearer invalid-key"}
    payload = {"model": "openai/gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=payload, headers=headers)
        assert response.status_code in (401, 403)


def test_chat_completions_rate_limit(test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    headers = {"Authorization": f"Bearer {test_api_key}"}
    payload = {"model": "musicgen", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as client:
        # Simulate rapid requests to hit rate limit
        hit_429 = False
        for _ in range(110):
            response = client.post("/v1/chat/completions", json=payload, headers=headers)
            if response.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "Did not hit rate limit after 110 requests"

def test_infer_rate_limit(test_api_key):
    app = create_app(metrics_registry=CollectorRegistry())
    headers = {"Authorization": f"Bearer {test_api_key}"}
    payload = {"model": "musicgen", "input": {"prompt": "hi"}}
    with TestClient(app) as client:
        hit_429 = False
        for _ in range(110):
            response = client.post("/infer", json=payload, headers=headers)
            if response.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "Did not hit rate limit on /infer after 110 requests"

def test_infer_missing_api_key():
    app = create_app(metrics_registry=CollectorRegistry())
    payload = {"model": "musicgen", "input": {"prompt": "hi"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload)
        assert response.status_code == 401

def test_infer_invalid_api_key():
    app = create_app(metrics_registry=CollectorRegistry())
    headers = {"Authorization": "Bearer invalid-key"}
    payload = {"model": "musicgen", "input": {"prompt": "hi"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers=headers)
        assert response.status_code in (401, 403)
