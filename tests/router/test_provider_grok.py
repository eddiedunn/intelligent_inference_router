import json
import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine


grok_app = FastAPI()


@grok_app.post("/openai/v1/chat/completions")
async def _completion(payload: router_main.ChatCompletionRequest):
    user_msg = payload.messages[-1].content if payload.messages else ""
    if payload.stream:

        async def gen():
            chunk = json.dumps(
                {"choices": [{"delta": {"content": f"Grok: {user_msg}"}, "index": 0}]}
            )
            yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")
    return {
        "id": "grok-1",
        "object": "chat.completion",
        "created": 0,
        "model": payload.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": f"Grok: {user_msg}"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def setup_registry(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "models.db"
    monkeypatch.setattr(router_main, "SQLITE_DB_PATH", str(db_path))
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    with registry.get_session() as session:
        registry.upsert_model(session, "grok-model", "grok", "unused")


def patch_http_client(monkeypatch):
    real_async_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=grok_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)


def test_forward_to_grok(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(router_main, "GROK_BASE_URL", "http://testserver")
    monkeypatch.setattr(router_main, "EXTERNAL_GROK_KEY", "dummy")

    setup_registry(monkeypatch, tmp_path)
    patch_http_client(monkeypatch)

    client = TestClient(router_main.app)
    payload = {
        "model": "grok-model",
        "messages": [{"role": "user", "content": "hi"}],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Grok: hi"


def test_forward_to_grok_stream(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(router_main, "GROK_BASE_URL", "http://testserver")
    monkeypatch.setattr(router_main, "EXTERNAL_GROK_KEY", "dummy")

    setup_registry(monkeypatch, tmp_path)
    patch_http_client(monkeypatch)

    client = TestClient(router_main.app)
    payload = {
        "model": "grok-model",
        "messages": [{"role": "user", "content": "hi"}],
        "stream": True,
    }
    with client.stream("POST", "/v1/chat/completions", json=payload) as resp:
        assert resp.status_code == 200
        lines = list(resp.iter_lines())
    decoded = [
        line.decode() if isinstance(line, bytes) else line for line in lines if line
    ]
    assert any("Grok: hi" in line for line in decoded)
    assert decoded[-1] == "data: [DONE]"
