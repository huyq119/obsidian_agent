from pathlib import Path
import shutil

from typer.testing import CliRunner

from obsidian_agent.cli import app


runner = CliRunner()


def test_full_offline_cli_flow(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"
    report = tmp_path / "suggestions.md"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    ask_result = runner.invoke(
        app,
        ["ask", "agent project", "--data-dir", str(data_dir), "--embedding-provider", "fake", "--llm-provider", "fake"],
    )
    assert ask_result.exit_code == 0
    assert "Sources:" in ask_result.stdout

    suggest_result = runner.invoke(app, ["suggest", "--data-dir", str(data_dir), "--output", str(report)])
    assert suggest_result.exit_code == 0
    assert report.exists()

    status_result = runner.invoke(app, ["status", "--data-dir", str(data_dir)])
    assert status_result.exit_code == 0
    assert "Readonly: true" in status_result.stdout
