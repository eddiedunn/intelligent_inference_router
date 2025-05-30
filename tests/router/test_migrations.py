from sqlalchemy import create_engine, text

import router.migrations as migrations


def test_add_kind_column(tmp_path):
    db_path = tmp_path / "models.db"
    engine = create_engine(f"sqlite:///{db_path}")
    # create initial table without 'kind'
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE models (id INTEGER PRIMARY KEY, name TEXT, type TEXT, endpoint TEXT)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO models (name, type, endpoint) VALUES ('foo', 'openai', 'http://x')"
            )
        )
    # run migration
    migrations.run_all(engine)
    # verify column exists and default value applied
    with engine.begin() as conn:
        result = conn.execute(text("PRAGMA table_info(models)")).fetchall()
        names = [row[1] for row in result]
        assert "kind" in names
        row = conn.execute(text("SELECT kind FROM models WHERE name='foo'")).one()
        assert row[0] == "api"
