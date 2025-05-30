from typer.testing import CliRunner

import router.cli as cli


class DummySession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


def test_migrate_invokes_create_tables(monkeypatch):
    called = {}

    def fake_create_tables():
        called["yes"] = True

    monkeypatch.setattr(cli, "create_tables", fake_create_tables)
    runner = CliRunner()
    result = runner.invoke(cli.app, ["migrate"])
    assert result.exit_code == 0
    assert called.get("yes")


def test_seed_reads_file(monkeypatch, tmp_path):
    data_file = tmp_path / "seed.json"
    data_file.write_text('[{"name":"a","type":"t","endpoint":"e"}]')

    calls = []

    def fake_upsert(session, name, type, endpoint, kind="api"):
        calls.append((name, type, endpoint, kind))

    monkeypatch.setattr(cli, "get_session", lambda: DummySession())
    monkeypatch.setattr(cli, "upsert_model", fake_upsert)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["seed", str(data_file)])
    assert result.exit_code == 0
    assert calls == [("a", "t", "e", "api")]


def test_add_model(monkeypatch):
    calls = []

    def fake_upsert(session, name, type, endpoint, kind="api"):
        calls.append((name, type, endpoint, kind))

    monkeypatch.setattr(cli, "get_session", lambda: DummySession())
    monkeypatch.setattr(cli, "upsert_model", fake_upsert)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["add-model", "foo", "local", "http://x", "weight"])
    assert result.exit_code == 0
    assert calls == [("foo", "local", "http://x", "weight")]


def test_add_model_invalid_type(monkeypatch):
    monkeypatch.setattr(cli, "get_session", lambda: DummySession())

    runner = CliRunner()
    result = runner.invoke(cli.app, ["add-model", "foo", "invalid", "http://x"])
    assert result.exit_code != 0
