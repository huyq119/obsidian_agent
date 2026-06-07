from typer.testing import CliRunner

from obsidian_agent.cli import app
from obsidian_agent.config import load_config


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


def test_init_with_deepseek_bigmodel_preset_writes_provider_config(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(
        app,
        ["init", "--vault", str(vault), "--data-dir", str(data_dir), "--preset", "deepseek-bigmodel"],
    )

    config = load_config(data_dir / "config.toml")
    assert result.exit_code == 0
    assert config.llm.provider == "deepseek"
    assert config.embedding.provider == "openai_compatible"
    assert config.embedding.base_url == "https://open.bigmodel.cn/api/paas/v4/embeddings"
    assert config.embedding.api_key_env == "EMBEDDING_API_KEY"
    assert config.embedding.embedding_model == "embedding-3"


def test_init_with_unknown_preset_is_clear(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir), "--preset", "missing"])

    assert result.exit_code == 1
    assert "Unknown config preset" in result.stdout
    assert not (data_dir / "config.toml").exists()


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


def test_configure_updates_retrieval_top_k(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    result = runner.invoke(app, ["configure", "--data-dir", str(data_dir), "--top-k", "10"])

    config = load_config(data_dir / "config.toml")
    assert init_result.exit_code == 0
    assert result.exit_code == 0
    assert config.retrieval.top_k == 10
    assert "Updated retrieval.top_k: 10" in result.stdout


def test_configure_updates_chunking_options(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    result = runner.invoke(
        app,
        [
            "configure",
            "--data-dir",
            str(data_dir),
            "--target-tokens",
            "800",
            "--max-tokens",
            "1000",
        ],
    )

    config = load_config(data_dir / "config.toml")
    assert init_result.exit_code == 0
    assert result.exit_code == 0
    assert config.chunking.target_tokens == 800
    assert config.chunking.max_tokens == 1000
    assert "Updated chunking.target_tokens: 800" in result.stdout
    assert "Updated chunking.max_tokens: 1000" in result.stdout


def test_configure_rejects_invalid_chunking_bounds(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    result = runner.invoke(
        app,
        ["configure", "--data-dir", str(data_dir), "--target-tokens", "1200", "--max-tokens", "800"],
    )

    assert init_result.exit_code == 0
    assert result.exit_code == 1
    assert "chunking.target_tokens cannot exceed chunking.max_tokens" in result.stdout


def test_configure_updates_provider_preset(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    result = runner.invoke(app, ["configure", "--data-dir", str(data_dir), "--preset", "deepseek-bigmodel"])

    config = load_config(data_dir / "config.toml")
    assert init_result.exit_code == 0
    assert result.exit_code == 0
    assert config.llm.provider == "deepseek"
    assert config.embedding.provider == "openai_compatible"
    assert config.embedding.api_key_env == "EMBEDDING_API_KEY"
    assert config.embedding.embedding_model == "embedding-3"
    assert "Updated provider preset: deepseek-bigmodel" in result.stdout


def test_configure_without_options_prints_current_values(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    result = runner.invoke(app, ["configure", "--data-dir", str(data_dir)])

    assert init_result.exit_code == 0
    assert result.exit_code == 0
    assert "retrieval.top_k: 6" in result.stdout
    assert "chunking.target_tokens: 1000" in result.stdout
    assert "chunking.max_tokens: 1200" in result.stdout


def test_doctor_reports_missing_env_without_network(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)

    init_result = runner.invoke(
        app,
        ["init", "--vault", str(vault), "--data-dir", str(data_dir), "--preset", "deepseek-bigmodel"],
    )
    result = runner.invoke(app, ["doctor", "--data-dir", str(data_dir)])

    assert init_result.exit_code == 0
    assert result.exit_code == 1
    assert "OK Config:" in result.stdout
    assert "OK Vault:" in result.stdout
    assert "FAIL LLM env: DEEPSEEK_API_KEY is not set" in result.stdout
    assert "FAIL Embedding env: EMBEDDING_API_KEY is not set" in result.stdout
    assert "SKIP Network: use --network to test provider connectivity" in result.stdout


def test_doctor_passes_local_checks_with_env(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embedding-key")

    init_result = runner.invoke(
        app,
        ["init", "--vault", str(vault), "--data-dir", str(data_dir), "--preset", "deepseek-bigmodel"],
    )
    result = runner.invoke(app, ["doctor", "--data-dir", str(data_dir)])

    assert init_result.exit_code == 0
    assert result.exit_code == 0
    assert "OK LLM env: DEEPSEEK_API_KEY" in result.stdout
    assert "OK Embedding env: EMBEDDING_API_KEY" in result.stdout
    assert "SKIP Network: use --network to test provider connectivity" in result.stdout


def test_doctor_network_checks_use_configured_providers(tmp_path, monkeypatch):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"
    calls = []

    class FakeEmbedding:
        def embed_query(self, query):
            calls.append(("embedding", query))
            return [0.1, 0.2]

    class FakeLLM:
        def answer(self, question, contexts):
            calls.append(("llm", question, contexts))
            return "OK"

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-embedding-key")
    monkeypatch.setattr("obsidian_agent.cli._build_embedding_provider", lambda config, override: FakeEmbedding())
    monkeypatch.setattr("obsidian_agent.cli._build_llm_provider", lambda config, override: FakeLLM())

    init_result = runner.invoke(
        app,
        ["init", "--vault", str(vault), "--data-dir", str(data_dir), "--preset", "deepseek-bigmodel"],
    )
    result = runner.invoke(app, ["doctor", "--data-dir", str(data_dir), "--network"])

    assert init_result.exit_code == 0
    assert result.exit_code == 0
    assert "OK Embedding connectivity:" in result.stdout
    assert "OK LLM connectivity:" in result.stdout
    assert calls == [
        ("embedding", "obsidian-agent doctor embedding test"),
        ("llm", "Reply with OK.", []),
    ]
