import pytest
from fastapi.testclient import TestClient
from router.main import create_app
from prometheus_client import CollectorRegistry

app = create_app(metrics_registry=CollectorRegistry())
client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200

def test_models_auth():
    r = client.get("/v1/models", headers={"Authorization": "Bearer changeme"})
    assert r.status_code == 200
    assert "llama" in str(r.json())
