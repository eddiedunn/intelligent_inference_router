from fastapi.testclient import TestClient

import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine


def test_chat_completions_dummy_response(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "models.db"
    monkeypatch.setattr(router_main, "SQLITE_DB_PATH", str(db_path))
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    router_main.load_registry()

    client = TestClient(router_main.app)
    payload = {
        "model": "dummy",
        "messages": [{"role": "user", "content": "hi"}],
    }
    response = client.post("/v1/chat/completions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["choices"][0]["message"]["content"] == "Hello world"
