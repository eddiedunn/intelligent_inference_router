import httpx
from fastapi.testclient import TestClient

import router.main as router_main
import router.registry as registry
from local_agent.main import app as agent_app
from sqlalchemy import create_engine


def test_forward_to_local_agent(monkeypatch, tmp_path) -> None:
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
    transport = httpx.ASGITransport(app=agent_app)

    def client_factory(*args, **kwargs):
        return real_async_client(transport=transport, base_url="http://testserver")

    monkeypatch.setattr(router_main.httpx, "AsyncClient", client_factory)

    with TestClient(router_main.app) as client:
        payload = {
            "model": "local_mistral",
            "messages": [{"role": "user", "content": "hi"}],
        }
        response = client.post("/v1/chat/completions", json=payload)
        assert response.status_code == 200
        assert response.json()["choices"][0]["message"]["content"] == "Echo: hi"
