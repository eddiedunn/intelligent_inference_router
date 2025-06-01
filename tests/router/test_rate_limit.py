from fastapi.testclient import TestClient
import router.main as router_main


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(router_main, "RATE_LIMIT_REQUESTS", 2)
    monkeypatch.setattr(router_main, "RATE_LIMIT_WINDOW", 60)
    router_main.RATE_LIMIT_STATE.clear()
    with TestClient(router_main.app) as client:
        payload = {"model": "dummy", "messages": [{"role": "user", "content": "hi"}]}
        assert client.post("/v1/chat/completions", json=payload).status_code == 200
        assert client.post("/v1/chat/completions", json=payload).status_code == 200
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Rate limit exceeded"
