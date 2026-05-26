from pathlib import Path
import shutil

from typer.testing import CliRunner

from obsidian_agent.cli import app


runner = CliRunner()


def test_scan_indexes_fixture_vault_without_network(tmp_path, monkeypatch):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    assert init_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"])

    assert scan_result.exit_code == 0
    assert "Scanned: 2" in scan_result.stdout
    assert "Notes: 2" in scan_result.stdout
    assert (data_dir / "agent.db").exists()


def test_status_after_scan_reports_counts(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    status_result = runner.invoke(app, ["status", "--data-dir", str(data_dir)])

    assert status_result.exit_code == 0
    assert "Notes: 2" in status_result.stdout
    assert "Chunks:" in status_result.stdout
