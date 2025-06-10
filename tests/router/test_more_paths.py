import httpx
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.testclient import TestClient

import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine


def test_dummy_response_has_id_prefix() -> None:
    with TestClient(router_main.app) as client:
        payload = {
            "model": "dummy-model",
            "messages": [{"role": "user", "content": "hi"}],
        }
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["id"].startswith("cmpl-")
        assert data["choices"][0]["message"]["content"] == "Hello world"


error_app = FastAPI()


@error_app.post("/infer")
async def _error(_: router_main.ChatCompletionRequest) -> Response:
    return Response(status_code=500)


def test_forward_to_local_agent_error(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("LOCAL_AGENT_URL", "http://testserver")
    router_main.settings = router_main.Settings()

    db_path = tmp_path / "models.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    router_main.settings = router_main.Settings()
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    with registry.get_session() as session:
        registry.upsert_model(
            session, "local_mistral", "local", "http://testserver", "weight"
        )

    real_async_client = httpx.AsyncClient
    transport = httpx.ASGITransport(app=error_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    with TestClient(router_main.app) as client:
        payload = {
            "model": "local_mistral",
            "messages": [{"role": "user", "content": "hi"}],
        }
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 502
        assert response.json()["detail"] == "Local agent error"


def test_forward_to_openai_missing_key(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("EXTERNAL_OPENAI_KEY", raising=False)
    router_main.settings = router_main.Settings()

    db_path = tmp_path / "models.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    router_main.settings = router_main.Settings()
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    with registry.get_session() as session:
        registry.upsert_model(session, "gpt-3.5-turbo", "openai", "unused", "api")

    with TestClient(router_main.app) as client:
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": "hi"}],
        }
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 500
        assert response.json()["detail"] == "OpenAI key not configured"
