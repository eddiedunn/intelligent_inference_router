from fastapi.testclient import TestClient
from router.main import app

client = TestClient(app)

def test_health_no_auth():
    r = client.get("/health")
    assert r.status_code == 200

def test_models_requires_auth():
    r = client.get("/v1/models")
    assert r.status_code in (401, 403)
