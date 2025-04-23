import pytest
from fastapi.testclient import TestClient
from router.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200

def test_models_auth():
    r = client.get("/v1/models", headers={"Authorization": "Bearer changeme"})
    assert r.status_code == 200
    assert "llama" in str(r.json())
