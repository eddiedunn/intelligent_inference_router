import pytest
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter
from fastapi.testclient import TestClient
from router.main import app
import yaml
import os
import random
import string
import threading
import time
import asyncio
import pytest_asyncio

client = TestClient(app)
API_KEY = "test-key"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Removed setup_fastapi_limiter fixture; FastAPILimiter is now initialized in app startup event.

# Helper to mock config.yaml loading if needed
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), '../config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] in ("ok", "healthy")

def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert "version" in response.json()

def test_config_loading():
    config = load_config()
    assert "services" in config
    assert isinstance(config["services"], dict)

def test_infer_sync(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
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
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["result"] == "ok"

def test_infer_async(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
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
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code in (200, 202)
    assert "job_id" in response.json()

def test_infer_missing_model(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    payload = {"model": "not_a_real_model", "input": {"prompt": "test"}}
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code == 404 or response.status_code == 400

def test_infer_missing_input(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    payload = {"model": "musicgen"}
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code == 422
    assert "detail" in response.json()

def test_infer_missing_model_field(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    payload = {"input": {"prompt": "test"}}
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code == 422
    assert "detail" in response.json()

def test_infer_invalid_payload_type(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    payload = "not a dict"
    response = client.post("/infer", data=payload, headers={"Content-Type": "application/json", **HEADERS})
    assert response.status_code in (400, 422)
    assert "detail" in response.json()

def test_infer_empty_payload(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    response = client.post("/infer", data="{}", headers={"Content-Type": "application/json", **HEADERS})
    assert response.status_code == 422
    assert "detail" in response.json()

def test_infer_upstream_httpx_exception(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    def mock_post(*args, **kwargs):
        raise Exception("Simulated upstream failure")
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code == 502
    assert "Upstream error" in response.json().get("detail", "")

def test_infer_upstream_non_200(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    class MockResponse:
        def json(self):
            return {"error": "fail"}
        @property
        def status_code(self):
            return 500
    monkeypatch.setattr("httpx.post", lambda *a, **kw: MockResponse())
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code == 500

# Fuzz/large payload test
def test_infer_large_payload(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {"result": "ok", "output": "large"}
            @property
            def status_code(self):
                return 200
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    big_prompt = ''.join(random.choices(string.ascii_letters + string.digits, k=100_000))
    payload = {"model": "musicgen", "input": {"prompt": big_prompt}}
    response = client.post("/infer", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["result"] == "ok"

# Concurrency/async job status simulation
def test_infer_concurrent_requests(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    def mock_post(*args, **kwargs):
        class MockResponse:
            def json(self):
                return {"result": "ok", "output": "concurrent"}
            @property
            def status_code(self):
                return 200
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    results = []
    def worker():
        response = client.post("/infer", json=payload, headers=HEADERS)
        results.append(response.status_code)
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert all(code == 200 for code in results)

def test_infer_valid_api_key(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    payload = {"model": "musicgen", "input": {"prompt": "test"}}
    response = client.post("/infer", json=payload, headers=HEADERS)
    # Should succeed or fail upstream, but not due to auth
    assert response.status_code in (200, 404, 502)

def test_chat_completions_missing_api_key(monkeypatch):
    monkeypatch.delenv("IIR_API_KEY", raising=False)
    payload = {"model": "musicgen", "messages": [{"role": "user", "content": "hi"}]}
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code in (401, 403)

def test_chat_completions_invalid_api_key(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", "correct-key")
    payload = {"model": "musicgen", "messages": [{"role": "user", "content": "hi"}]}
    response = client.post("/v1/chat/completions", json=payload, headers={"Authorization": "Bearer wrong-key"})
    assert response.status_code == 403

def test_chat_completions_rate_limit(monkeypatch):
    monkeypatch.setenv("IIR_API_KEY", API_KEY)
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {"model": "musicgen", "messages": [{"role": "user", "content": "hi"}]}
    # Simulate rapid requests to hit rate limit
    for _ in range(105):
        response = client.post("/v1/chat/completions", json=payload, headers=headers)
    # Last response should be 429 or similar (rate limited)
    assert response.status_code in (429, 503)
