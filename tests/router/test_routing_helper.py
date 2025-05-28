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
