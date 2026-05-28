from __future__ import annotations

import os
import shutil
from dataclasses import replace
from pathlib import Path

import typer
from rich.console import Console

from obsidian_agent.config import (
    AgentConfig,
    RetrievalConfig,
    config_path_for,
    create_config,
    default_data_dir,
    load_config,
    save_config,
)
from obsidian_agent.providers.deepseek_llm import DeepSeekLLMProvider
from obsidian_agent.providers.base import RetrievedChunk
from obsidian_agent.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from obsidian_agent.providers.openai_compatible_embedding import OpenAICompatibleEmbeddingProvider
from obsidian_agent.providers.openai_embedding import OpenAIEmbeddingProvider
from obsidian_agent.retrieval.qa import answer_question
from obsidian_agent.retrieval.retriever import Retriever
from obsidian_agent.storage.memory_store import MemoryStore
from obsidian_agent.storage.sqlite_store import SQLiteStore
from obsidian_agent.storage.vector_store import ChromaVectorStore, InMemoryVectorStore
from obsidian_agent.suggestions.reporter import render_json_report, render_markdown_report
from obsidian_agent.suggestions.rules import build_suggestions
from obsidian_agent.vault.models import NoteChunk
from obsidian_agent.vault.scanner import scan_vault_files


app = typer.Typer(help="Read-only CLI agent for Obsidian knowledge bases.")
memory_app = typer.Typer(help="Manage local explicit memories.")
console = Console()
app.add_typer(memory_app, name="memory")


def _data_dir(value: Path | None) -> Path:
    return (value or default_data_dir()).expanduser().resolve()


def _load_agent_config(target: Path) -> AgentConfig:
    try:
        return load_config(config_path_for(target))
    except FileNotFoundError as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc
    except ValueError as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc


def _db_path(target: Path) -> Path:
    return target / "agent.db"


def _memory_db_path(target: Path) -> Path:
    return target / "memory.db"


def _memory_store(target: Path) -> MemoryStore:
    store = MemoryStore(_memory_db_path(target))
    store.initialize()
    return store


def _build_embedding_provider(config: AgentConfig, override: str | None):
    provider_name = (override or config.embedding.provider).lower()
    if provider_name == "fake":
        return FakeEmbeddingProvider(dimensions=8)
    if provider_name == "openai":
        return OpenAIEmbeddingProvider(config.embedding)
    if provider_name == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(
            base_url=config.embedding.base_url,
            api_key_env=config.embedding.api_key_env,
            embedding_model=config.embedding.embedding_model,
            dimensions=config.embedding.dimensions,
        )
    console.print(f"Unknown embedding provider: {provider_name}")
    raise typer.Exit(1)


def _build_llm_provider(config: AgentConfig, override: str | None):
    provider_name = (override or config.llm.provider).lower()
    if provider_name == "fake":
        return FakeLLMProvider()
    if provider_name == "deepseek":
        return DeepSeekLLMProvider(config.llm)
    console.print(f"Unknown LLM provider: {provider_name}")
    raise typer.Exit(1)


def _chunk_payload(chunk: dict, note: dict | None = None) -> dict:
    title = str(note["title"]) if note else str(chunk.get("title", ""))
    return {
        "id": str(chunk["id"]),
        "text": str(chunk["text"]),
        "metadata": {
            "path": str(chunk["note_path"]),
            "title": title,
            "heading": str(chunk["heading"]),
            "chunk_index": int(chunk["chunk_index"]),
        },
    }


def _build_vector_store_from_sqlite(
    store: SQLiteStore,
    embedding_provider,
    *,
    use_chroma: bool,
    data_dir: Path,
):
    if use_chroma:
        vector_store = ChromaVectorStore(data_dir / "vectors")
    else:
        vector_store = InMemoryVectorStore()

    chunks = store.list_all_chunks()
    if not chunks:
        return vector_store

    note_cache: dict[str, dict] = {}
    payloads = []
    texts = []
    for chunk in chunks:
        note_path = str(chunk["note_path"])
        if note_path not in note_cache:
            note_cache[note_path] = store.get_note(note_path)
        payloads.append(_chunk_payload(chunk, note_cache[note_path]))
        texts.append(str(chunk["text"]))

    embeddings = embedding_provider.embed_texts(texts)
    vector_store.upsert_chunks(payloads, embeddings)
    return vector_store


@app.command()
def init(
    vault: Path | None = typer.Option(None, "--vault", help="Path to the Obsidian vault."),
    data_dir: Path | None = typer.Option(None, "--data-dir", help="Agent data directory."),
    preset: str = typer.Option("default", "--preset", help="Configuration preset: default or deepseek-bigmodel."),
) -> None:
    if vault is None:
        console.print("Missing required option: --vault")
        raise typer.Exit(1)
    target = _data_dir(data_dir)
    try:
        config = create_config(vault, preset=preset)
    except ValueError as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc
    save_config(config, config_path_for(target))
    (target / "vectors").mkdir(parents=True, exist_ok=True)
    (target / "reports").mkdir(parents=True, exist_ok=True)
    console.print(f"Initialized obsidian-agent at {target}")


@memory_app.command("add")
def memory_add(
    text: str,
    data_dir: Path | None = typer.Option(None, "--data-dir"),
) -> None:
    target = _data_dir(data_dir)
    memory_id = _memory_store(target).add_memory(text)
    console.print(f"Added memory: {memory_id}")


@memory_app.command("list")
def memory_list(
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    limit: int = typer.Option(20, "--limit", min=1),
) -> None:
    target = _data_dir(data_dir)
    memories = _memory_store(target).list_memories(limit=limit)
    if not memories:
        console.print("No memories")
        return
    for memory in memories:
        console.print(f"{memory['id']}. {memory['text']}", soft_wrap=True)


@memory_app.command("search")
def memory_search(
    query: str,
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    limit: int = typer.Option(5, "--limit", min=1),
) -> None:
    target = _data_dir(data_dir)
    memories = _memory_store(target).search_memories(query, limit=limit)
    if not memories:
        console.print("No matching memories")
        return
    for memory in memories:
        score = int(memory.get("score", 0))
        console.print(f"{memory['id']}. score={score} {memory['text']}", soft_wrap=True)


@memory_app.command("delete")
def memory_delete(
    memory_id: int,
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    force: bool = typer.Option(False, "--force", help="Delete without confirmation."),
) -> None:
    if not force:
        confirmed = typer.confirm(f"Delete memory {memory_id}?")
        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(1)

    target = _data_dir(data_dir)
    deleted = _memory_store(target).delete_memory(memory_id)
    if not deleted:
        console.print(f"Memory not found: {memory_id}")
        raise typer.Exit(1)
    console.print(f"Deleted memory: {memory_id}")


@app.command()
def configure(
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    top_k: int | None = typer.Option(None, "--top-k", min=1, help="Persist the default retrieval result count."),
) -> None:
    target = _data_dir(data_dir)
    config = _load_agent_config(target)
    if top_k is None:
        console.print(f"retrieval.top_k: {config.retrieval.top_k}")
        return

    updated = replace(
        config,
        retrieval=RetrievalConfig(top_k=top_k),
    )
    save_config(updated, config_path_for(target))
    console.print(f"Updated retrieval.top_k: {top_k}")


@app.command()
def scan(
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    rebuild: bool = typer.Option(False, "--rebuild"),
    embedding_provider: str | None = typer.Option(None, "--embedding-provider"),
) -> None:
    target = _data_dir(data_dir)
    config = _load_agent_config(target)
    db_path = _db_path(target)

    if rebuild:
        if db_path.exists():
            db_path.unlink()
        vectors_dir = target / "vectors"
        if vectors_dir.exists():
            shutil.rmtree(vectors_dir, ignore_errors=True)
        vectors_dir.mkdir(parents=True, exist_ok=True)

    store = SQLiteStore(db_path)
    store.initialize()

    use_fake = (embedding_provider or config.embedding.provider).lower() == "fake"
    embedder = _build_embedding_provider(config, embedding_provider)
    vector_store = None if use_fake else ChromaVectorStore(target / "vectors")

    scan_result = scan_vault_files(
        config.vault_path,
        config.scan,
        target_tokens=config.chunking.target_tokens,
        max_tokens=config.chunking.max_tokens,
    )

    current_paths = {note.path for note in scan_result.notes}
    updated_paths: list[str] = []
    skipped_count = 0

    for note in scan_result.notes:
        existing_hash = store.get_note_hash(note.path)
        if not rebuild and existing_hash == note.content_hash:
            skipped_count += 1
            continue

        note_chunks = [chunk for chunk in scan_result.chunks if chunk.note_path == note.path]
        old_chunk_ids = store.get_chunk_ids_for_paths([note.path])
        store.upsert_note_with_chunks(note, note_chunks)
        updated_paths.append(note.path)

        if vector_store is not None and note_chunks:
            if old_chunk_ids:
                vector_store.delete_chunk_ids(old_chunk_ids)
            payloads = [_chunk_payload_from_model(chunk, note) for chunk in note_chunks]
            embeddings = embedder.embed_texts([chunk.text for chunk in note_chunks])
            vector_store.upsert_chunks(payloads, embeddings)

    deleted_paths = sorted(
        {note["path"] for note in store.list_notes()} - current_paths,
    )
    deleted_chunk_ids: list[str] = []
    if deleted_paths:
        deleted_chunk_ids = store.get_chunk_ids_for_paths(deleted_paths)
        store.delete_notes_not_in(current_paths)
        if vector_store is not None and deleted_chunk_ids:
            vector_store.delete_chunk_ids(deleted_chunk_ids)
    else:
        store.delete_notes_not_in(current_paths)

    store.recompute_backlinks()

    summary = {
        "scanned": scan_result.scanned_files,
        "skipped": skipped_count,
        "updated": len(updated_paths),
        "deleted": len(deleted_paths),
        "warnings": len(scan_result.warnings),
        "notes": store.count_notes(),
        "chunks": store.count_chunks(),
    }
    store.set_last_scan_summary(summary)

    for warning in scan_result.warnings:
        console.print(f"Warning: {warning}")

    console.print(f"Scanned: {scan_result.scanned_files}")
    console.print(f"Updated: {len(updated_paths)}")
    console.print(f"Deleted: {len(deleted_paths)}")
    console.print(f"Warnings: {len(scan_result.warnings)}")
    console.print(f"Notes: {store.count_notes()}")
    console.print(f"Chunks: {store.count_chunks()}")


@app.command()
def doctor(
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    network: bool = typer.Option(False, "--network", help="Test live embedding and LLM provider connectivity."),
) -> None:
    target = _data_dir(data_dir)
    try:
        config = load_config(config_path_for(target))
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"FAIL Config: {exc}")
        raise typer.Exit(1) from exc

    failures = 0
    console.print(f"OK Config: {config_path_for(target)}")
    console.print(f"OK Vault: {config.vault_path}", soft_wrap=True)

    if _env_is_available(config.llm.provider, config.llm.api_key_env):
        console.print(f"OK LLM env: {config.llm.api_key_env}")
    else:
        failures += 1
        console.print(f"FAIL LLM env: {config.llm.api_key_env} is not set")

    if _env_is_available(config.embedding.provider, config.embedding.api_key_env):
        console.print(f"OK Embedding env: {config.embedding.api_key_env}")
    else:
        failures += 1
        console.print(f"FAIL Embedding env: {config.embedding.api_key_env} is not set")

    if network:
        failures += _run_network_doctor_checks(config)
    else:
        console.print("SKIP Network: use --network to test provider connectivity")

    if failures:
        raise typer.Exit(1)


def _env_is_available(provider: str, api_key_env: str) -> bool:
    if provider.lower() == "fake":
        return True
    return bool(os.environ.get(api_key_env))


def _run_network_doctor_checks(config: AgentConfig) -> int:
    failures = 0
    try:
        embedding = _build_embedding_provider(config, None)
        vector = embedding.embed_query("obsidian-agent doctor embedding test")
        if not vector:
            raise RuntimeError("empty embedding")
        console.print(f"OK Embedding connectivity: {len(vector)} dimensions")
    except Exception as exc:
        failures += 1
        console.print(f"FAIL Embedding connectivity: {exc}")

    try:
        llm = _build_llm_provider(config, None)
        answer = llm.answer("Reply with OK.", [])
        if not answer:
            raise RuntimeError("empty response")
        console.print("OK LLM connectivity: received response")
    except Exception as exc:
        failures += 1
        console.print(f"FAIL LLM connectivity: {exc}")
    return failures


@app.command()
def ask(
    question: str,
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    embedding_provider: str | None = typer.Option(None, "--embedding-provider"),
    llm_provider: str | None = typer.Option(None, "--llm-provider"),
    show_context: bool = typer.Option(False, "--show-context", help="Print retrieved chunks before the answer."),
    context_chars: int = typer.Option(240, "--context-chars", min=0, help="Maximum characters per retrieved chunk."),
    top_k: int | None = typer.Option(None, "--top-k", min=1, help="Override the configured retrieval result count."),
    use_memory: bool = typer.Option(False, "--use-memory", help="Include matching local memories in the answer context."),
    memory_top_k: int = typer.Option(3, "--memory-top-k", min=1, help="Maximum local memories to include."),
) -> None:
    target = _data_dir(data_dir)
    config = _load_agent_config(target)
    db_path = _db_path(target)
    if not db_path.exists():
        console.print("Run scan first")
        raise typer.Exit(1)

    store = SQLiteStore(db_path)
    store.initialize()
    if store.count_chunks() == 0:
        console.print("Run scan first")
        raise typer.Exit(1)

    embedder = _build_embedding_provider(config, embedding_provider)
    llm = _build_llm_provider(config, llm_provider)
    use_fake = (embedding_provider or config.embedding.provider).lower() == "fake"
    if use_fake:
        vector_store = _build_vector_store_from_sqlite(
            store,
            embedder,
            use_chroma=False,
            data_dir=target,
        )
    else:
        vector_store = ChromaVectorStore(target / "vectors")
        if vector_store.count() == 0:
            console.print("Run scan first")
            raise typer.Exit(1)

    retriever = Retriever(vector_store, embedder, top_k=top_k or config.retrieval.top_k)
    contexts = retriever.retrieve(question)
    if use_memory:
        contexts = _memory_contexts(target, question, limit=memory_top_k) + contexts
    if show_context:
        _print_contexts(contexts, context_chars=context_chars)
    answer, sources = answer_question(question, contexts, llm)

    console.print(answer)
    console.print("Sources:")
    for source in sources:
        console.print(source)


def _memory_contexts(target: Path, query: str, *, limit: int) -> list[RetrievedChunk]:
    memories = _memory_store(target).search_memories(query, limit=limit)
    contexts: list[RetrievedChunk] = []
    for memory in memories:
        contexts.append(
            RetrievedChunk(
                id=f"memory:{memory['id']}",
                text=str(memory["text"]),
                path="memory",
                title="Memory",
                heading="Local memory",
                chunk_index=int(memory["id"]),
                score=float(memory.get("score", 0)),
            )
        )
    return contexts


def _print_contexts(contexts: list[RetrievedChunk], *, context_chars: int) -> None:
    console.print("Contexts:")
    if not contexts:
        console.print("- none")
        return
    for index, context in enumerate(contexts, start=1):
        heading = context.heading or "(no heading)"
        console.print(
            f"{index}. {context.path} | {heading} | "
            f"chunk={context.chunk_index} | score={context.score:.4f}",
            soft_wrap=True,
        )
        snippet = _truncate_context_text(context.text, max_chars=context_chars)
        if snippet:
            console.print(snippet, soft_wrap=True)


def _truncate_context_text(text: str, *, max_chars: int) -> str:
    normalized = " ".join(text.split())
    if max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


@app.command()
def suggest(
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    output: Path | None = typer.Option(None, "--output"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    target = _data_dir(data_dir)
    config = _load_agent_config(target)
    db_path = _db_path(target)
    if not db_path.exists():
        console.print("Run scan first")
        raise typer.Exit(1)

    store = SQLiteStore(db_path)
    store.initialize()
    notes = store.list_notes()
    suggestions = build_suggestions(notes)

    if format.lower() == "json":
        report = render_json_report(suggestions)
    else:
        report = render_markdown_report(suggestions)

    if output is None:
        console.print(report.rstrip())
        return

    resolved_output = output.expanduser().resolve()
    vault_root = config.vault_path.resolve()
    try:
        resolved_output.relative_to(vault_root)
        inside_vault = True
    except ValueError:
        inside_vault = False

    if inside_vault:
        console.print("Refusing to write inside the vault")
        raise typer.Exit(1)

    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(report, encoding="utf-8")
    console.print(f"Wrote suggestions to {resolved_output}")


@app.command()
def status(data_dir: Path | None = typer.Option(None, "--data-dir", help="Agent data directory.")) -> None:
    target = _data_dir(data_dir)
    config = _load_agent_config(target)

    note_count = 0
    chunk_count = 0
    last_scan = "never"
    db_path = _db_path(target)
    if db_path.exists():
        store = SQLiteStore(db_path)
        store.initialize()
        note_count = store.count_notes()
        chunk_count = store.count_chunks()
        summary = store.get_last_scan_summary()
        if summary is not None:
            last_scan = (
                f"scanned={summary.get('scanned', 0)}, "
                f"updated={summary.get('updated', 0)}, "
                f"deleted={summary.get('deleted', 0)}"
            )

    console.print(f"Vault: {config.vault_path}", soft_wrap=True)
    console.print(f"Notes: {note_count}")
    console.print(f"Chunks: {chunk_count}")
    console.print(f"Last scan: {last_scan}")
    console.print(f"LLM: {config.llm.provider}/{config.llm.chat_model}")
    console.print(f"Embedding: {config.embedding.provider}/{config.embedding.embedding_model}")
    console.print(f"Readonly: {str(config.readonly).lower()}")


def _chunk_payload_from_model(chunk: NoteChunk, note) -> dict:
    return {
        "id": chunk.id,
        "text": chunk.text,
        "metadata": {
            "path": chunk.note_path,
            "title": note.title,
            "heading": chunk.heading,
            "chunk_index": chunk.chunk_index,
        },
    }


if __name__ == "__main__":
    app()
