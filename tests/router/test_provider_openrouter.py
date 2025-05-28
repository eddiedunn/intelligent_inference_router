import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine

openrouter_app = FastAPI()


@openrouter_app.post("/api/v1/chat/completions")
async def _completions(payload: router_main.ChatCompletionRequest):
    user_msg = payload.messages[-1].content if payload.messages else ""
    content = f"OpenRouter: {user_msg}"
    return {
        "id": "or-1",
        "object": "chat.completion",
        "created": 0,
        "model": payload.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def test_forward_to_openrouter(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(router_main, "OPENROUTER_BASE_URL", "http://testserver")
    monkeypatch.setattr(router_main, "EXTERNAL_OPENROUTER_KEY", "dummy")

    db_path = tmp_path / "models.db"
    monkeypatch.setattr(router_main, "SQLITE_DB_PATH", str(db_path))
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    with registry.get_session() as session:
        registry.upsert_model(session, "mixtral-8x7b", "openrouter", "unused")

    real_async_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=openrouter_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    client = TestClient(router_main.app)
    payload = {
        "model": "mixtral-8x7b",
        "messages": [{"role": "user", "content": "hi"}],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "OpenRouter: hi"
