from fastapi.testclient import TestClient
import pytest

import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine

pytestmark = pytest.mark.integration


def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "models.db"
    monkeypatch.setattr(router_main, "SQLITE_DB_PATH", str(db_path))
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    router_main.load_registry()


def test_fallback_to_local_cache(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)
    router_main.CACHE_STORE.clear()
    monkeypatch.setattr(router_main, "CACHE_ENDPOINT", "http://localhost:9999")

    async def backend(_: router_main.ChatCompletionRequest):
        return {"res": 1}

    monkeypatch.setattr(router_main, "forward_to_local_agent", backend)

    payload = {
        "model": "local-any",
        "messages": [{"role": "user", "content": "hi"}],
    }

    with TestClient(router_main.app) as client:
        resp1 = client.post("/v1/chat/completions", json=payload)
        assert resp1.json() == {"res": 1}

        async def fail(_: router_main.ChatCompletionRequest):
            raise AssertionError("backend called twice")

        monkeypatch.setattr(router_main, "forward_to_local_agent", fail)
        resp2 = client.post("/v1/chat/completions", json=payload)
        assert resp2.json() == {"res": 1}
