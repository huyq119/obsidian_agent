from pathlib import Path

from obsidian_agent.config import AgentConfig, create_default_config, load_config, save_config


def test_default_config_uses_deepseek_and_openai_embedding(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()

    config = create_default_config(vault_path=vault)

    assert config.vault_path == vault.resolve()
    assert config.readonly is True
    assert config.llm.provider == "deepseek"
    assert config.llm.chat_model == "deepseek-v4-pro"
    assert config.llm.api_key_env == "DEEPSEEK_API_KEY"
    assert config.embedding.provider == "openai"
    assert config.embedding.embedding_model == "text-embedding-3-small"
    assert config.embedding.api_key_env == "OPENAI_API_KEY"


def test_save_and_load_config_round_trip(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    data_dir = tmp_path / ".obsidian-agent"
    config_path = data_dir / "config.toml"
    config = create_default_config(vault_path=vault)

    save_config(config, config_path)
    loaded = load_config(config_path)

    assert loaded == config
    assert config_path.exists()
