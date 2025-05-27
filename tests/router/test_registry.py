from __future__ import annotations

from sqlalchemy import create_engine

import router.registry as registry


def init_test_db(tmp_path):
    db_path = tmp_path / "models.db"
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()
    return db_path


def test_registry_crud(tmp_path) -> None:
    init_test_db(tmp_path)

    with registry.get_session() as session:
        registry.upsert_model(session, "model-a", "local", "http://a")

    with registry.get_session() as session:
        models = registry.list_models(session)
        assert models[0].name == "model-a"
        assert models[0].endpoint == "http://a"

    with registry.get_session() as session:
        registry.upsert_model(session, "model-a", "local", "http://b")

    with registry.get_session() as session:
        model = registry.list_models(session)[0]
        assert model.endpoint == "http://b"
