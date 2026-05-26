from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from obsidian_agent.config import (
    config_path_for,
    create_default_config,
    default_data_dir,
    load_config,
    save_config,
)


app = typer.Typer(help="Read-only CLI agent for Obsidian knowledge bases.")
console = Console()


def _data_dir(value: Path | None) -> Path:
    return (value or default_data_dir()).expanduser().resolve()


@app.command()
def init(
    vault: Path | None = typer.Option(None, "--vault", help="Path to the Obsidian vault."),
    data_dir: Path | None = typer.Option(None, "--data-dir", help="Agent data directory."),
) -> None:
    if vault is None:
        console.print("Missing required option: --vault")
        raise typer.Exit(1)
    target = _data_dir(data_dir)
    try:
        config = create_default_config(vault)
    except ValueError as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc
    save_config(config, config_path_for(target))
    (target / "vectors").mkdir(parents=True, exist_ok=True)
    (target / "reports").mkdir(parents=True, exist_ok=True)
    console.print(f"Initialized obsidian-agent at {target}")


@app.command()
def status(data_dir: Path | None = typer.Option(None, "--data-dir", help="Agent data directory.")) -> None:
    target = _data_dir(data_dir)
    try:
        config = load_config(config_path_for(target))
    except (FileNotFoundError, ValueError) as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc

    console.print(f"Vault: {config.vault_path}", soft_wrap=True)
    console.print("Notes: 0")
    console.print("Chunks: 0")
    console.print("Last scan: never")
    console.print(f"LLM: {config.llm.provider}/{config.llm.chat_model}")
    console.print(f"Embedding: {config.embedding.provider}/{config.embedding.embedding_model}")
    console.print(f"Readonly: {str(config.readonly).lower()}")
