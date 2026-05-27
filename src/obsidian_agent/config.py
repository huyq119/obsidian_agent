from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w
import tomllib


@dataclass(frozen=True)
class ScanConfig:
    max_file_size_bytes: int = 1_048_576
    skip_hidden_dirs: bool = True
    skip_dirs: list[str] = field(default_factory=lambda: [".obsidian", ".git", "node_modules"])


@dataclass(frozen=True)
class ChunkingConfig:
    target_tokens: int = 1000
    max_tokens: int = 1200


@dataclass(frozen=True)
class RetrievalConfig:
    top_k: int = 6


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    api_key_env: str = "DEEPSEEK_API_KEY"
    chat_model: str = "deepseek-v4-pro"
    thinking: bool = True
    reasoning_effort: str = "high"


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = "openai"
    base_url: str = "https://api.openai.com/v1"
    api_key_env: str = "OPENAI_API_KEY"
    embedding_model: str = "text-embedding-3-small"
    dimensions: int = 1536


@dataclass(frozen=True)
class AgentConfig:
    vault_path: Path
    readonly: bool = True
    scan: ScanConfig = field(default_factory=ScanConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)


SUPPORTED_CONFIG_PRESETS = ("default", "deepseek-bigmodel")


def default_data_dir() -> Path:
    return Path.cwd() / ".obsidian-agent"


def config_path_for(data_dir: Path) -> Path:
    return data_dir / "config.toml"


def _validate_vault_path(vault_path: Path) -> Path:
    resolved = vault_path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"Vault path does not exist or is not a directory: {resolved}")
    return resolved


def create_default_config(vault_path: Path) -> AgentConfig:
    return create_config(vault_path=vault_path, preset="default")


def create_config(vault_path: Path, *, preset: str = "default") -> AgentConfig:
    resolved = _validate_vault_path(vault_path)
    if preset == "default":
        return AgentConfig(vault_path=resolved)
    if preset == "deepseek-bigmodel":
        return AgentConfig(
            vault_path=resolved,
            embedding=EmbeddingConfig(
                provider="openai_compatible",
                base_url="https://open.bigmodel.cn/api/paas/v4/embeddings",
                api_key_env="EMBEDDING_API_KEY",
                embedding_model="embedding-3",
                dimensions=1536,
            ),
        )
    supported = ", ".join(SUPPORTED_CONFIG_PRESETS)
    raise ValueError(f"Unknown config preset: {preset}. Supported presets: {supported}")


def _to_dict(config: AgentConfig) -> dict[str, Any]:
    return {
        "vault_path": str(config.vault_path),
        "readonly": config.readonly,
        "scan": config.scan.__dict__,
        "chunking": config.chunking.__dict__,
        "retrieval": config.retrieval.__dict__,
        "llm": config.llm.__dict__,
        "embedding": config.embedding.__dict__,
    }


def save_config(config: AgentConfig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tomli_w.dumps(_to_dict(config)), encoding="utf-8")


def load_config(path: Path) -> AgentConfig:
    if not path.exists():
        raise FileNotFoundError(f"Run `obsidian-agent init` first. Missing config: {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    vault_path = _validate_vault_path(Path(data["vault_path"]))
    return AgentConfig(
        vault_path=vault_path,
        readonly=bool(data.get("readonly", True)),
        scan=ScanConfig(**data.get("scan", {})),
        chunking=ChunkingConfig(**data.get("chunking", {})),
        retrieval=RetrievalConfig(**data.get("retrieval", {})),
        llm=LLMConfig(**data.get("llm", {})),
        embedding=EmbeddingConfig(**data.get("embedding", {})),
    )
