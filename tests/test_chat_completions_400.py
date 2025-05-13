import os
os.environ["IIR_API_KEY"] = "test"
os.environ["REDIS_URL"] = "redis://:b71d1246cacd953070e92f8b@192.168.11.253:6379/0"
import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from router.main import create_app

@pytest.fixture
def client():
    app = create_app(metrics_registry=CollectorRegistry())
    with TestClient(app) as client:
        yield client

DUMMY_API_KEY = "test"
HEADERS = {
    "Authorization": f"Bearer {DUMMY_API_KEY}",
    "Content-Type": "application/json"
}

def test_no_body(client):
    resp = client.post("/v1/chat/completions", headers=HEADERS)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "error" in resp.text.lower() or "detail" in resp.text.lower()

def test_invalid_json(client):
    resp = client.post("/v1/chat/completions", headers=HEADERS, data="not a json")
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "error" in resp.text.lower() or "detail" in resp.text.lower()

def test_missing_model(client):
    body = {"messages": [{"role": "user", "content": "hi"}]}
    resp = client.post("/v1/chat/completions", headers=HEADERS, json=body)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "model" in resp.text.lower() or "missing" in resp.text.lower()

def test_missing_messages(client):
    body = {"model": "openai/gpt-4.1"}
    resp = client.post("/v1/chat/completions", headers=HEADERS, json=body)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "messages" in resp.text.lower() or "missing" in resp.text.lower()

def test_wrong_type_messages(client):
    body = {"model": "openai/gpt-4.1", "messages": "notalist"}
    resp = client.post("/v1/chat/completions", headers=HEADERS, json=body)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    assert "messages" in resp.text.lower() or "list" in resp.text.lower() or "type" in resp.text.lower()
