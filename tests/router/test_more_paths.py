import asyncio
import httpx
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient

import router.main as router_main


def test_dummy_response_has_id_prefix() -> None:
    client = TestClient(router_main.app)
    payload = {"model": "dummy-model", "messages": [{"role": "user", "content": "hi"}]}
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"].startswith("cmpl-")
    assert data["choices"][0]["message"]["content"] == "Hello world"


error_app = FastAPI()


@error_app.post("/infer")
async def _error(_: router_main.ChatCompletionRequest) -> Response:
    return Response(status_code=500)


def test_forward_to_local_agent_error(monkeypatch) -> None:
    monkeypatch.setattr(router_main, "LOCAL_AGENT_URL", "http://testserver")

    real_async_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=error_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    client = TestClient(router_main.app)
    payload = {
        "model": "local_mistral",
        "messages": [{"role": "user", "content": "hi"}],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 502
    assert response.json()["detail"] == "Local agent error"


def test_forward_to_openai_missing_key(monkeypatch) -> None:
    monkeypatch.setattr(router_main, "EXTERNAL_OPENAI_KEY", None)
    client = TestClient(router_main.app)
    payload = {"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 500
    assert response.json()["detail"] == "OpenAI key not configured"
