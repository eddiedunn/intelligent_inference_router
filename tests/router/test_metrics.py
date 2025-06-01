from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

import router.main as router_main


def test_request_counter_increments() -> None:
    with TestClient(router_main.app) as client:
        before = (
            REGISTRY.get_sample_value("router_requests_total", {"backend": "dummy"})
            or 0
        )
        payload = {"model": "dummy", "messages": [{"role": "user", "content": "hi"}]}
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        after = (
            REGISTRY.get_sample_value("router_requests_total", {"backend": "dummy"})
            or 0
        )
        assert after == before + 1


def test_metrics_endpoint() -> None:
    with TestClient(router_main.app) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "router_requests_total" in resp.text
