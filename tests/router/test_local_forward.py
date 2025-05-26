import httpx
from fastapi.testclient import TestClient

import router.main as router_main
from local_agent.main import app as agent_app


def test_forward_to_local_agent(monkeypatch) -> None:
    monkeypatch.setattr(router_main, "LOCAL_AGENT_URL", "http://testserver")

    real_async_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=agent_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    client = TestClient(router_main.app)
    payload = {
        "model": "local_mistral",
        "messages": [{"role": "user", "content": "hi"}],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Echo: hi"
