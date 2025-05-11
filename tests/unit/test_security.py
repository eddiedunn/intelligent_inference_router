from fastapi.testclient import TestClient
from router.main import create_app
from prometheus_client import CollectorRegistry

app = create_app(metrics_registry=CollectorRegistry())
client = TestClient(app)

def test_health_no_auth():
    r = client.get("/health")
    assert r.status_code == 200

def test_models_requires_auth():
    r = client.get("/v1/models")
    assert r.status_code in (401, 403)
