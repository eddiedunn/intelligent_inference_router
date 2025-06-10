import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine

anthropic_app = FastAPI()


@anthropic_app.post("/v1/messages")
async def _messages(payload: router_main.ChatCompletionRequest):
    user_msg = payload.messages[-1].content if payload.messages else ""
    content = f"Anthropic: {user_msg}"
    return {
        "id": "anth-1",
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


def test_forward_to_anthropic(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://testserver")
    monkeypatch.setenv("EXTERNAL_ANTHROPIC_KEY", "dummy")
    router_main.settings = router_main.Settings()

    db_path = tmp_path / "models.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    router_main.settings = router_main.Settings()
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    with registry.get_session() as session:
        registry.upsert_model(session, "claude-3", "anthropic", "unused", "api")

    real_async_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=anthropic_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    with TestClient(router_main.app) as client:
        payload = {
            "model": "claude-3",
            "messages": [{"role": "user", "content": "hi"}],
        }
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        assert response.json()["choices"][0]["message"]["content"] == "Anthropic: hi"
