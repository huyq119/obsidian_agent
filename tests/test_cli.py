from typer.testing import CliRunner

from obsidian_agent.cli import app


runner = CliRunner()


def test_init_creates_config_and_data_dirs(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])

    assert result.exit_code == 0
    assert (data_dir / "config.toml").exists()
    assert (data_dir / "vectors").is_dir()
    assert (data_dir / "reports").is_dir()
    assert "Initialized" in result.stdout


def test_status_before_init_is_clear(tmp_path):
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(app, ["status", "--data-dir", str(data_dir)])

    assert result.exit_code == 1
    assert "Run `obsidian-agent init` first" in result.stdout
