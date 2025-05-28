import json

from fastapi.testclient import TestClient
import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine


class FakeRedis:
    def __init__(self) -> None:
        self.db: dict[str, str] = {}

    async def get(self, key: str):
        return self.db.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.db[key] = value


def setup_db(monkeypatch, tmp_path):
    db_path = tmp_path / "models.db"
    monkeypatch.setattr(router_main, "SQLITE_DB_PATH", str(db_path))
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    router_main.load_registry()


def test_cache_hit_skips_backend(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)

    fake = FakeRedis()
    monkeypatch.setattr(router_main, "redis_client", fake)

    payload = router_main.ChatCompletionRequest(
        model="local-test",
        messages=[router_main.Message(role="user", content="hi")],
    )

    cache_key = router_main.make_cache_key(payload)
    fake.db[cache_key] = json.dumps({"cached": True})

    async def fail(_: router_main.ChatCompletionRequest):
        raise AssertionError("backend called")

    monkeypatch.setattr(router_main, "forward_to_local_agent", fail)

    client = TestClient(router_main.app)
    resp = client.post("/v1/chat/completions", json=payload.dict())
    assert resp.status_code == 200
    assert resp.json() == {"cached": True}


def test_cache_store_and_hit(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)

    fake = FakeRedis()
    monkeypatch.setattr(router_main, "redis_client", fake)

    async def backend(_: router_main.ChatCompletionRequest):
        return {"data": 1}

    monkeypatch.setattr(router_main, "forward_to_local_agent", backend)

    payload = {
        "model": "local-any",
        "messages": [{"role": "user", "content": "hi"}],
    }

    client = TestClient(router_main.app)
    resp1 = client.post("/v1/chat/completions", json=payload)
    assert resp1.json() == {"data": 1}

    async def fail(_: router_main.ChatCompletionRequest):
        raise AssertionError("called twice")

    monkeypatch.setattr(router_main, "forward_to_local_agent", fail)
    resp2 = client.post("/v1/chat/completions", json=payload)
    assert resp2.json() == {"data": 1}
