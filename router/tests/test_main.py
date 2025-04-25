import os
import secrets
import pytest
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi.testclient import TestClient
from router.main import app
import yaml
import random
import string
import threading
import time
import asyncio
import pytest_asyncio

API_KEY = "test-key"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

TEST_IIR_API_KEY = "test-" + secrets.token_urlsafe(16)
os.environ["IIR_API_KEY"] = TEST_IIR_API_KEY

@pytest.fixture(scope="session")
def test_api_key():
    return TEST_IIR_API_KEY

# Helper to mock config.yaml loading if needed
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '../config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] in ("ok", "healthy")

def test_version():
    with TestClient(app) as client:
        response = client.get("/version")
        assert response.status_code == 200
        assert "version" in response.json()

def test_config_loading():
    config = load_config()
    assert "services" in config
    assert isinstance(config["services"], dict)

def test_infer_sync(monkeypatch, test_api_key):
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
    payload = {"model": "not_a_real_model", "input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 404 or response.status_code == 400

def test_infer_missing_input(monkeypatch, test_api_key):
    payload = {"model": "musicgen"}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_missing_model_field(monkeypatch, test_api_key):
    payload = {"input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_invalid_payload_type(monkeypatch, test_api_key):
    payload = ["not", "a", "dict"]
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_empty_payload(monkeypatch, test_api_key):
    with TestClient(app) as client:
        response = client.post("/infer", json={}, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 422 or response.status_code == 400

def test_infer_upstream_httpx_exception(monkeypatch, test_api_key):
    def mock_post(*args, **kwargs):
        raise Exception("Upstream error")
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    with TestClient(app) as client:
        response = client.post("/infer", json=payload, headers={"Authorization": f"Bearer {test_api_key}"})
        assert response.status_code == 502 or response.status_code == 500

def test_infer_upstream_non_200(monkeypatch, test_api_key):
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
    payload = {"model": "musicgen", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 401

def test_chat_completions_invalid_api_key(test_api_key):
    headers = {"Authorization": "Bearer invalid-key"}
    payload = {"model": "musicgen", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as client:
        response = client.post("/v1/chat/completions", json=payload, headers=headers)
        assert response.status_code in (401, 403)

def test_chat_completions_rate_limit(test_api_key):
    headers = {"Authorization": f"Bearer {test_api_key}"}
    payload = {"model": "musicgen", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as client:
        # Simulate rapid requests to hit rate limit
        for _ in range(105):
            response = client.post("/v1/chat/completions", json=payload, headers=headers)
        # Should get 429 at some point
        assert any(
            client.post("/v1/chat/completions", json=payload, headers=headers).status_code == 429
            for _ in range(5)
        )
