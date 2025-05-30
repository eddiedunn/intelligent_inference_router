from typer.testing import CliRunner
from sqlalchemy import create_engine

import router.cli as cli
import router.registry as registry


def init_db(tmp_path):
    db_path = tmp_path / "models.db"
    registry.SQLITE_DB_PATH = str(db_path)
    registry.engine = create_engine(f"sqlite:///{db_path}")
    registry.SessionLocal = registry.sessionmaker(bind=registry.engine)
    registry.create_tables()


def test_refresh_openai(monkeypatch, tmp_path):
    init_db(tmp_path)

    def fake_get(url, headers=None, timeout=30):
        class Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return {"data": [{"id": "gpt-test"}]}

        return Resp()

    monkeypatch.setattr(cli.httpx, "get", fake_get)
    monkeypatch.setenv("EXTERNAL_OPENAI_KEY", "dummy")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com")

    runner = CliRunner()
    result = runner.invoke(cli.app, ["refresh-openai"])
    assert result.exit_code == 0

    with registry.get_session() as session:
        models = registry.list_models(session)
        assert len(models) == 1
        assert models[0].name == "gpt-test"
        assert models[0].kind == "api"
