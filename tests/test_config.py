from pathlib import Path

from obsidian_agent.config import AgentConfig, create_default_config, load_config, save_config


def test_default_config_uses_deepseek_and_openai_embedding(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()

    config = create_default_config(vault_path=vault)

    assert config.vault_path == vault.resolve()
    assert config.readonly is True
    assert config.llm.provider == "deepseek"
    assert config.llm.base_url == "https://api.deepseek.com"
    assert config.llm.chat_model == "deepseek-v4-pro"
    assert config.llm.api_key_env == "DEEPSEEK_API_KEY"
    assert config.llm.thinking is True
    assert config.llm.reasoning_effort == "high"
    assert config.embedding.provider == "openai"
    assert config.embedding.base_url == "https://api.openai.com/v1"
    assert config.embedding.embedding_model == "text-embedding-3-small"
    assert config.embedding.api_key_env == "OPENAI_API_KEY"
    assert config.embedding.dimensions == 1536
    assert config.scan.max_file_size_bytes == 1_048_576
    assert config.scan.skip_hidden_dirs is True
    assert config.scan.skip_dirs == [".obsidian", ".git", "node_modules"]
    assert config.chunking.target_tokens == 1000
    assert config.chunking.max_tokens == 1200
    assert config.retrieval.top_k == 6


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
