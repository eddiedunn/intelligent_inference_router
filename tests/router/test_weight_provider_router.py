from fastapi.testclient import TestClient

import router.main as router_main
import router.registry as registry
from router.providers import huggingface
from sqlalchemy import create_engine


class DummyPipe:
    def __call__(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        return_full_text: bool,
    ):
        return [{"generated_text": f"HF: {prompt}"}]


def test_forward_to_weight_provider(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "models.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    router_main.settings = router_main.Settings()
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    with registry.get_session() as session:
        registry.upsert_model(session, "hf-model", "huggingface", "unused", "weight")
    provider = huggingface.HuggingFaceProvider()
    monkeypatch.setattr(provider, "_get_pipeline", lambda m: DummyPipe())
    router_main.WEIGHT_PROVIDERS.clear()
    router_main.WEIGHT_PROVIDERS["huggingface"] = provider
    with TestClient(router_main.app) as client:
        payload = {
            "model": "hf-model",
            "messages": [{"role": "user", "content": "hi"}],
        }
        resp = client.post("/v1/chat/completions", json=payload)
        assert resp.status_code == 200
        assert resp.json()["choices"][0]["message"]["content"] == "HF: hi"
