from typer.testing import CliRunner
import router.cli as cli


def test_show_logs(tmp_path):
    log_file = tmp_path / "router.log"
    log_file.write_text("line1\nline2\n")
    runner = CliRunner()
    result = runner.invoke(cli.app, ["show-logs", str(log_file), "--no-follow"])
    assert result.exit_code == 0
    assert "line1" in result.stdout
    assert "line2" in result.stdout


def test_export_metrics(monkeypatch):
    class Resp:
        text = "router_requests_total 1"

        def raise_for_status(self):
            pass

    monkeypatch.setattr(cli.httpx, "get", lambda url, timeout=10: Resp())
    runner = CliRunner()
    result = runner.invoke(cli.app, ["export-metrics"])
    assert result.exit_code == 0
    assert "router_requests_total" in result.stdout
