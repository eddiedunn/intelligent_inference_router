import router.main as router_main
import router.registry as registry
from sqlalchemy import create_engine


def init_db(tmp_path):
    db_path = tmp_path / "models.db"
    router_main.SQLITE_DB_PATH = str(db_path)
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    router_main.load_registry()
    return db_path


def test_select_backend_registry(monkeypatch, tmp_path):
    init_db(tmp_path)
    with registry.get_session() as session:
        registry.upsert_model(session, "gpt-test", "openai", "unused")
    router_main.load_registry()
    payload = router_main.ChatCompletionRequest(model="gpt-test", messages=[])
    assert router_main.select_backend(payload) == "openai"


def test_select_backend_prefix():
    payload = router_main.ChatCompletionRequest(model="local_dummy", messages=[])
    assert router_main.select_backend(payload) == "local"


def test_select_backend_cost_threshold(monkeypatch):
    monkeypatch.setattr(router_main, "ROUTER_COST_THRESHOLD", 5)
    payload = router_main.ChatCompletionRequest(
        model="gpt-any",
        messages=[router_main.Message(role="user", content="x" * 10)],
    )
    router_main.BACKEND_METRICS.clear()
    assert router_main.select_backend(payload) == "local"


def test_select_backend_latency(monkeypatch):
    monkeypatch.setattr(router_main, "ROUTER_COST_THRESHOLD", 100)
    router_main.BACKEND_METRICS["local"] = {"latency": 2.0, "count": 1}
    router_main.BACKEND_METRICS["openai"] = {"latency": 0.1, "count": 1}
    payload = router_main.ChatCompletionRequest(
        model="gpt-fast",
        messages=[router_main.Message(role="user", content="hi")],
    )
    assert router_main.select_backend(payload) == "openai"
