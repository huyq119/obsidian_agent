from pathlib import Path
import shutil

from typer.testing import CliRunner

from obsidian_agent.cli import app


runner = CliRunner()


def test_ask_uses_fake_providers_and_prints_sources(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    result = runner.invoke(
        app,
        ["ask", "What does the project say?", "--data-dir", str(data_dir), "--embedding-provider", "fake", "--llm-provider", "fake"],
    )

    assert result.exit_code == 0
    assert "Fake answer" in result.stdout
    assert "Sources:" in result.stdout
    assert "Project.md" in result.stdout
