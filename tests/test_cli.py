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


def test_init_without_vault_is_clear(tmp_path):
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(app, ["init", "--data-dir", str(data_dir)])

    assert result.exit_code == 1
    assert "Missing required option: --vault" in result.stdout


def test_init_with_missing_vault_is_clear_and_does_not_create_config(tmp_path):
    vault = tmp_path / "missing-vault"
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])

    assert result.exit_code == 1
    assert "Vault path does not exist or is not a directory" in result.stdout
    assert not (data_dir / "config.toml").exists()


def test_status_before_init_is_clear(tmp_path):
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(app, ["status", "--data-dir", str(data_dir)])

    assert result.exit_code == 1
    assert "Run `obsidian-agent init` first" in result.stdout


def test_status_after_init_prints_config_defaults(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    result = runner.invoke(app, ["status", "--data-dir", str(data_dir)])

    assert init_result.exit_code == 0
    assert result.exit_code == 0
    assert f"Vault: {vault.resolve()}" in result.stdout
    assert "Notes: 0" in result.stdout
    assert "Chunks: 0" in result.stdout
    assert "Last scan: never" in result.stdout
    assert "LLM: deepseek/deepseek-v4-pro" in result.stdout
    assert "Embedding: openai/text-embedding-3-small" in result.stdout
    assert "Readonly: true" in result.stdout


def test_status_with_stale_vault_path_is_clear(tmp_path):
    vault = tmp_path / "vault"
    moved_vault = tmp_path / "moved-vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    vault.rename(moved_vault)
    result = runner.invoke(app, ["status", "--data-dir", str(data_dir)])

    assert init_result.exit_code == 0
    assert result.exit_code == 1
    assert "Vault path does not exist or is not a directory" in result.stdout
