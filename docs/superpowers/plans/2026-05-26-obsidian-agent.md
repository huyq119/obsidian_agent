# Obsidian Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local read-only Python CLI agent that scans an Obsidian vault, indexes Markdown notes, answers questions with RAG using DeepSeek V4 Pro, and produces deterministic organization suggestions.

**Architecture:** The project is a Typer-based CLI with focused modules for config, vault parsing/chunking/scanning, SQLite metadata storage, Chroma vector storage, provider adapters, retrieval/QA, and suggestion reports. Tests use fixture vaults and fake providers so the default suite runs offline without API credentials.

**Tech Stack:** Python 3.11+, Typer, Rich, Pydantic, tomli-w, PyYAML, ChromaDB, OpenAI Python SDK, pytest.

---

## File Structure

Create and maintain these files:

- `pyproject.toml`: package metadata, dependencies, console script, pytest config.
- `README.md`: install, configure, and run commands.
- `src/obsidian_agent/__init__.py`: package version.
- `src/obsidian_agent/cli.py`: Typer commands `init`, `scan`, `ask`, `suggest`, `status`.
- `src/obsidian_agent/config.py`: config dataclasses, defaults, TOML load/save, path validation.
- `src/obsidian_agent/vault/models.py`: parsed note, chunk, scan result dataclasses.
- `src/obsidian_agent/vault/parser.py`: Markdown frontmatter, heading, tag, and link extraction.
- `src/obsidian_agent/vault/chunker.py`: heading-aware chunking.
- `src/obsidian_agent/vault/scanner.py`: vault file discovery and parse/chunk orchestration.
- `src/obsidian_agent/storage/sqlite_store.py`: schema, note/chunk persistence, scan stats, suggestions queries.
- `src/obsidian_agent/storage/vector_store.py`: Chroma collection wrapper and fake in-memory vector store for tests.
- `src/obsidian_agent/providers/base.py`: provider protocols and `RetrievedChunk`.
- `src/obsidian_agent/providers/deepseek_llm.py`: DeepSeek OpenAI-compatible chat adapter.
- `src/obsidian_agent/providers/openai_embedding.py`: OpenAI embedding adapter.
- `src/obsidian_agent/providers/openai_compatible_embedding.py`: configurable OpenAI-compatible embedding adapter.
- `src/obsidian_agent/providers/fake.py`: deterministic fake LLM and embedding providers.
- `src/obsidian_agent/retrieval/retriever.py`: vector retrieval and source de-duplication.
- `src/obsidian_agent/retrieval/qa.py`: prompt assembly and answer orchestration.
- `src/obsidian_agent/suggestions/rules.py`: deterministic suggestion rules.
- `src/obsidian_agent/suggestions/reporter.py`: terminal, Markdown, and JSON report rendering.
- `tests/fixtures/vault_basic/`: small Obsidian-style fixture vault.
- `tests/test_config.py`: config tests.
- `tests/test_parser.py`: parser tests.
- `tests/test_chunker.py`: chunker tests.
- `tests/test_scanner.py`: scanner tests.
- `tests/test_sqlite_store.py`: persistence tests.
- `tests/test_suggestions.py`: suggestion tests.
- `tests/test_retrieval_with_fake_provider.py`: offline retrieval/QA tests.
- `tests/test_cli.py`: CLI workflow tests.

---

### Task 1: Project Skeleton And Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/obsidian_agent/__init__.py`
- Create: package subdirectories under `src/obsidian_agent/`
- Create: `tests/fixtures/vault_basic/`

- [ ] **Step 1: Write packaging and import smoke test**

Create `tests/test_package.py`:

```python
from typer.testing import CliRunner

from obsidian_agent import __version__


def test_package_version_is_defined():
    assert __version__ == "0.1.0"
```

- [ ] **Step 2: Run smoke test to verify it fails**

Run: `pytest tests/test_package.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'obsidian_agent'`.

- [ ] **Step 3: Add package skeleton**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "obsidian-agent"
version = "0.1.0"
description = "Read-only CLI agent for Obsidian knowledge bases"
requires-python = ">=3.11"
dependencies = [
  "chromadb>=0.5.0",
  "openai>=1.0.0",
  "pydantic>=2.0.0",
  "pyyaml>=6.0.0",
  "rich>=13.0.0",
  "tomli-w>=1.0.0",
  "typer>=0.12.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0"]

[project.scripts]
obsidian-agent = "obsidian_agent.cli:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Create `src/obsidian_agent/__init__.py`:

```python
__version__ = "0.1.0"
```

Create empty `__init__.py` files in:

```text
src/obsidian_agent/providers/__init__.py
src/obsidian_agent/retrieval/__init__.py
src/obsidian_agent/storage/__init__.py
src/obsidian_agent/suggestions/__init__.py
src/obsidian_agent/vault/__init__.py
```

Create `README.md`:

````markdown
# Obsidian Agent

A local read-only CLI agent for Obsidian knowledge bases.

## MVP Commands

```bash
obsidian-agent init --vault ~/Documents/Notes
obsidian-agent scan
obsidian-agent ask "What does my vault say about AI agents?"
obsidian-agent suggest --output suggestions.md
obsidian-agent status
```

The agent stores local state in `.obsidian-agent/` and does not modify vault files.
````

- [ ] **Step 4: Run smoke test to verify it passes**

Run: `pytest tests/test_package.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src tests/test_package.py
git commit -m "chore: scaffold obsidian agent package"
```

---

### Task 2: Config Defaults, Persistence, And Init/Status CLI

**Files:**
- Create: `src/obsidian_agent/config.py`
- Create: `src/obsidian_agent/cli.py`
- Create: `tests/test_config.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write config tests**

Create `tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Write CLI init/status tests**

Create `tests/test_cli.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_config.py tests/test_cli.py -q`

Expected: FAIL because `obsidian_agent.config` and `obsidian_agent.cli` do not exist.

- [ ] **Step 4: Implement config and CLI init/status**

Create `src/obsidian_agent/config.py` with these public objects:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib
import tomli_w


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


def default_data_dir() -> Path:
    return Path.cwd() / ".obsidian-agent"


def config_path_for(data_dir: Path) -> Path:
    return data_dir / "config.toml"


def create_default_config(vault_path: Path) -> AgentConfig:
    resolved = vault_path.expanduser().resolve()
    if not resolved.exists() or not resolved.is_dir():
        raise ValueError(f"Vault path does not exist or is not a directory: {resolved}")
    return AgentConfig(vault_path=resolved)


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
    return AgentConfig(
        vault_path=Path(data["vault_path"]).expanduser().resolve(),
        readonly=bool(data.get("readonly", True)),
        scan=ScanConfig(**data.get("scan", {})),
        chunking=ChunkingConfig(**data.get("chunking", {})),
        retrieval=RetrievalConfig(**data.get("retrieval", {})),
        llm=LLMConfig(**data.get("llm", {})),
        embedding=EmbeddingConfig(**data.get("embedding", {})),
    )
```

Create `src/obsidian_agent/cli.py`:

```python
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from obsidian_agent.config import config_path_for, create_default_config, default_data_dir, load_config, save_config


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
    config = create_default_config(vault)
    save_config(config, config_path_for(target))
    (target / "vectors").mkdir(parents=True, exist_ok=True)
    (target / "reports").mkdir(parents=True, exist_ok=True)
    console.print(f"Initialized obsidian-agent at {target}")


@app.command()
def status(data_dir: Path | None = typer.Option(None, "--data-dir", help="Agent data directory.")) -> None:
    target = _data_dir(data_dir)
    try:
        config = load_config(config_path_for(target))
    except FileNotFoundError as exc:
        console.print(str(exc))
        raise typer.Exit(1) from exc

    console.print(f"Vault: {config.vault_path}")
    console.print("Notes: 0")
    console.print("Chunks: 0")
    console.print("Last scan: never")
    console.print(f"LLM: {config.llm.provider}/{config.llm.chat_model}")
    console.print(f"Embedding: {config.embedding.provider}/{config.embedding.embedding_model}")
    console.print(f"Readonly: {str(config.readonly).lower()}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config.py tests/test_cli.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_agent/config.py src/obsidian_agent/cli.py tests/test_config.py tests/test_cli.py
git commit -m "feat: add config and init status cli"
```

---

### Task 3: Markdown Models, Parser, Chunker, And Scanner

**Files:**
- Create: `src/obsidian_agent/vault/models.py`
- Create: `src/obsidian_agent/vault/parser.py`
- Create: `src/obsidian_agent/vault/chunker.py`
- Create: `src/obsidian_agent/vault/scanner.py`
- Create: `tests/fixtures/vault_basic/Project.md`
- Create: `tests/fixtures/vault_basic/Inbox/Loose.md`
- Create: `tests/fixtures/vault_basic/.obsidian/config`
- Create: `tests/test_parser.py`
- Create: `tests/test_chunker.py`
- Create: `tests/test_scanner.py`

- [ ] **Step 1: Create fixture vault files**

Create `tests/fixtures/vault_basic/Project.md`:

```markdown
---
tags:
  - ai
  - project
aliases:
  - Agent Project
---
# Agent Project

This note links to [[Loose]] and [External](https://example.com).

## Plan

Build a read-only Obsidian assistant.
```

Create `tests/fixtures/vault_basic/Inbox/Loose.md`:

```markdown
# Loose

#inbox

Short note with a link back to [[Agent Project]].
```

Create `tests/fixtures/vault_basic/.obsidian/config`:

```text
ignored
```

- [ ] **Step 2: Write parser, chunker, and scanner tests**

Create `tests/test_parser.py`:

```python
from pathlib import Path

from obsidian_agent.vault.parser import parse_markdown_note


def test_parse_frontmatter_tags_title_and_links():
    text = """---
tags:
  - ai
  - project
---
# Agent Project

Body with #inline and [[Loose|loose note]] plus [Doc](docs/readme.md).
"""

    note = parse_markdown_note(path=Path("Project.md"), text=text)

    assert note.title == "Agent Project"
    assert note.frontmatter["tags"] == ["ai", "project"]
    assert note.tags == ["ai", "project", "inline"]
    assert "Loose" in note.links
    assert "docs/readme.md" in note.links
    assert note.has_explicit_title is True
```

Create `tests/test_chunker.py`:

```python
from pathlib import Path

from obsidian_agent.vault.chunker import chunk_note
from obsidian_agent.vault.parser import parse_markdown_note


def test_chunk_note_preserves_heading_metadata():
    text = "# Title\n\nIntro\n\n## Plan\n\n" + "word " * 1400
    note = parse_markdown_note(Path("Note.md"), text)

    chunks = chunk_note(note, target_tokens=100, max_tokens=120)

    assert len(chunks) > 1
    assert chunks[0].heading == "Title"
    assert any(chunk.heading == "Plan" for chunk in chunks)
    assert chunks[0].note_path == "Note.md"
```

Create `tests/test_scanner.py`:

```python
from pathlib import Path
import shutil

from obsidian_agent.config import ScanConfig
from obsidian_agent.vault.scanner import scan_vault_files


def test_scanner_reads_markdown_and_skips_obsidian(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)

    result = scan_vault_files(vault, ScanConfig())

    assert result.warnings == []
    assert sorted(note.path for note in result.notes) == ["Inbox/Loose.md", "Project.md"]
    assert all(".obsidian" not in note.path for note in result.notes)
    assert result.scanned_files == 2
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_parser.py tests/test_chunker.py tests/test_scanner.py -q`

Expected: FAIL because vault modules do not exist.

- [ ] **Step 4: Implement vault models**

Create `src/obsidian_agent/vault/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParsedNote:
    path: str
    title: str
    content: str
    frontmatter: dict
    tags: list[str]
    links: list[str]
    has_explicit_title: bool
    content_hash: str
    modified_at: float | None = None


@dataclass(frozen=True)
class NoteChunk:
    id: str
    note_path: str
    chunk_index: int
    text: str
    heading: str
    token_count: int
    content_hash: str


@dataclass(frozen=True)
class ScanResult:
    notes: list[ParsedNote]
    chunks: list[NoteChunk]
    scanned_files: int
    skipped_files: int
    warnings: list[str] = field(default_factory=list)
```

- [ ] **Step 5: Implement parser, chunker, and scanner**

Implement `parser.py` with YAML frontmatter parsing, H1 title extraction, filename fallback, inline tag extraction, wikilink extraction, Markdown link extraction, and SHA-256 `content_hash`.

Implement `chunker.py` with `chunk_note(note, target_tokens, max_tokens)` and stable chunk ids using `sha256(f"{note.path}:{chunk_index}:{text}")`.

Implement `scanner.py` with `scan_vault_files(vault_path, scan_config, target_tokens=1000, max_tokens=1200)` that walks `.md` files, skips hidden/config directories, reads text as UTF-8, parses notes, chunks notes, records warnings for unreadable files, and returns `ScanResult`.

Core public signatures to implement:

```python
def parse_markdown_note(path: Path, text: str, modified_at: float | None = None) -> ParsedNote:
    """Return parsed metadata, links, tags, content hash, and title for one Markdown note."""

def chunk_note(note: ParsedNote, target_tokens: int, max_tokens: int) -> list[NoteChunk]:
    """Split one parsed note into heading-aware chunks with stable chunk ids."""

def scan_vault_files(
    vault_path: Path,
    scan_config: ScanConfig,
    target_tokens: int = 1000,
    max_tokens: int = 1200,
) -> ScanResult:
    """Scan Markdown files under a vault and return parsed notes, chunks, and warnings."""
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_parser.py tests/test_chunker.py tests/test_scanner.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/obsidian_agent/vault tests/fixtures tests/test_parser.py tests/test_chunker.py tests/test_scanner.py
git commit -m "feat: parse and scan obsidian markdown"
```

---

### Task 4: SQLite Metadata Store And Incremental Index State

**Files:**
- Create: `src/obsidian_agent/storage/sqlite_store.py`
- Create: `tests/test_sqlite_store.py`

- [ ] **Step 1: Write SQLite store tests**

Create `tests/test_sqlite_store.py`:

```python
from pathlib import Path

from obsidian_agent.storage.sqlite_store import SQLiteStore
from obsidian_agent.vault.models import NoteChunk, ParsedNote


def make_note(path="Project.md", title="Project", content_hash="abc"):
    return ParsedNote(
        path=path,
        title=title,
        content="# Project\nBody",
        frontmatter={"tags": ["ai"]},
        tags=["ai"],
        links=["Loose"],
        has_explicit_title=True,
        content_hash=content_hash,
        modified_at=1.0,
    )


def make_chunk(note_path="Project.md"):
    return NoteChunk(
        id="chunk-1",
        note_path=note_path,
        chunk_index=0,
        text="Body",
        heading="Project",
        token_count=1,
        content_hash="chunk-hash",
    )


def test_upsert_notes_and_chunks_round_trip(tmp_path):
    store = SQLiteStore(tmp_path / "agent.db")
    store.initialize()

    store.upsert_note_with_chunks(make_note(), [make_chunk()])

    assert store.count_notes() == 1
    assert store.count_chunks() == 1
    assert store.get_note_hash("Project.md") == "abc"


def test_delete_missing_notes_removes_chunks(tmp_path):
    store = SQLiteStore(tmp_path / "agent.db")
    store.initialize()
    store.upsert_note_with_chunks(make_note(), [make_chunk()])

    deleted = store.delete_notes_not_in({"Other.md"})

    assert deleted == ["Project.md"]
    assert store.count_notes() == 0
    assert store.count_chunks() == 0


def test_recompute_backlinks_counts_inbound_links(tmp_path):
    store = SQLiteStore(tmp_path / "agent.db")
    store.initialize()
    store.upsert_note_with_chunks(make_note(path="Project.md", title="Agent Project"), [make_chunk("Project.md")])
    store.upsert_note_with_chunks(make_note(path="Inbox/Loose.md", title="Loose"), [make_chunk("Inbox/Loose.md")])

    store.recompute_backlinks()
    loose = store.get_note("Inbox/Loose.md")

    assert loose["backlinks_count"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_sqlite_store.py -q`

Expected: FAIL because `SQLiteStore` does not exist.

- [ ] **Step 3: Implement SQLite schema and store**

Create `src/obsidian_agent/storage/sqlite_store.py` with:

```python
class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        raise NotImplementedError("SQLiteStore.initialize")

    def get_note_hash(self, path: str) -> str | None:
        raise NotImplementedError("SQLiteStore.get_note_hash")

    def upsert_note_with_chunks(self, note: ParsedNote, chunks: list[NoteChunk]) -> None:
        raise NotImplementedError("SQLiteStore.upsert_note_with_chunks")

    def delete_notes_not_in(self, current_paths: set[str]) -> list[str]:
        raise NotImplementedError("SQLiteStore.delete_notes_not_in")

    def recompute_backlinks(self) -> None:
        raise NotImplementedError("SQLiteStore.recompute_backlinks")

    def count_notes(self) -> int:
        raise NotImplementedError("SQLiteStore.count_notes")

    def count_chunks(self) -> int:
        raise NotImplementedError("SQLiteStore.count_chunks")

    def get_note(self, path: str) -> dict:
        raise NotImplementedError("SQLiteStore.get_note")

    def list_notes(self) -> list[dict]:
        raise NotImplementedError("SQLiteStore.list_notes")

    def list_chunks_for_paths(self, paths: list[str]) -> list[dict]:
        raise NotImplementedError("SQLiteStore.list_chunks_for_paths")

    def set_last_scan_summary(self, summary: dict) -> None:
        raise NotImplementedError("SQLiteStore.set_last_scan_summary")

    def get_last_scan_summary(self) -> dict | None:
        raise NotImplementedError("SQLiteStore.get_last_scan_summary")
```

Use these tables:

```sql
CREATE TABLE IF NOT EXISTS notes (
  path TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  frontmatter_json TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  links_json TEXT NOT NULL,
  backlinks_count INTEGER NOT NULL DEFAULT 0,
  outgoing_links_count INTEGER NOT NULL DEFAULT 0,
  has_explicit_title INTEGER NOT NULL,
  word_count INTEGER NOT NULL DEFAULT 0,
  content_hash TEXT NOT NULL,
  modified_at REAL,
  indexed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  note_path TEXT NOT NULL REFERENCES notes(path) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  heading TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL
);
```

Upserted notes must store `word_count` from parsed note content so `suggest` can identify short notes without reading the vault again.

Backlink matching rule for MVP: a link targets a note if the normalized link stem matches a note title or filename stem.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_sqlite_store.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_agent/storage/sqlite_store.py tests/test_sqlite_store.py
git commit -m "feat: add sqlite metadata store"
```

---

### Task 5: Embedding Providers, DeepSeek Provider, And Vector Store

**Files:**
- Create: `src/obsidian_agent/providers/base.py`
- Create: `src/obsidian_agent/providers/fake.py`
- Create: `src/obsidian_agent/providers/openai_embedding.py`
- Create: `src/obsidian_agent/providers/openai_compatible_embedding.py`
- Create: `src/obsidian_agent/providers/deepseek_llm.py`
- Create: `src/obsidian_agent/storage/vector_store.py`
- Create: `tests/test_retrieval_with_fake_provider.py`

- [ ] **Step 1: Write offline provider and vector tests**

Create `tests/test_retrieval_with_fake_provider.py`:

```python
from pathlib import Path

from obsidian_agent.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from obsidian_agent.storage.vector_store import InMemoryVectorStore


def test_fake_embedding_is_deterministic():
    provider = FakeEmbeddingProvider(dimensions=8)

    assert provider.embed_query("agent") == provider.embed_query("agent")
    assert len(provider.embed_query("agent")) == 8


def test_in_memory_vector_store_returns_sources():
    embeddings = FakeEmbeddingProvider(dimensions=8)
    store = InMemoryVectorStore()
    store.upsert_chunks(
        [
            {
                "id": "c1",
                "text": "AI agent planning notes",
                "metadata": {"path": "Project.md", "title": "Project", "heading": "Plan", "chunk_index": 0},
            }
        ],
        embeddings.embed_texts(["AI agent planning notes"]),
    )

    results = store.query(embeddings.embed_query("agent planning"), top_k=1)

    assert results[0].text == "AI agent planning notes"
    assert results[0].path == "Project.md"


def test_fake_llm_mentions_context_sources():
    llm = FakeLLMProvider()
    answer = llm.answer("What about agents?", [])

    assert "Fake answer" in answer
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retrieval_with_fake_provider.py -q`

Expected: FAIL because provider and vector modules do not exist.

- [ ] **Step 3: Implement provider protocols and fake providers**

Create `src/obsidian_agent/providers/base.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    path: str
    title: str
    heading: str
    chunk_index: int
    score: float


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("EmbeddingProvider.embed_texts")

    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError("EmbeddingProvider.embed_query")


class LLMProvider(Protocol):
    def answer(self, question: str, contexts: list[RetrievedChunk]) -> str:
        raise NotImplementedError("LLMProvider.answer")
```

Create `src/obsidian_agent/providers/fake.py` with deterministic hash-based embeddings and an LLM that returns `"Fake answer for: {question}"`.

- [ ] **Step 4: Implement OpenAI-compatible providers**

Create `openai_embedding.py`, `openai_compatible_embedding.py`, and `deepseek_llm.py`.

Provider behavior:

- Read API keys from configured environment variable names.
- Raise `RuntimeError("Missing API key environment variable: NAME")` when unset.
- Use `OpenAI(api_key=api_key, base_url=base_url)`.
- `OpenAIEmbeddingProvider.embed_texts` calls `client.embeddings.create(model=model, input=texts)`.
- `OpenAIEmbeddingProvider.embed_query` calls `embed_texts([query])[0]`.
- `OpenAICompatibleEmbeddingProvider` has the same behavior but accepts arbitrary `base_url`, `model`, `api_key_env`, and `dimensions`.
- `DeepSeekLLMProvider.answer` calls `client.chat.completions.create` with model `deepseek-v4-pro`, system prompt from the design spec, retrieved contexts, `reasoning_effort`, and `extra_body={"thinking": {"type": "enabled"}}` when thinking is enabled.

- [ ] **Step 5: Implement vector store wrappers**

Create `src/obsidian_agent/storage/vector_store.py` with:

```python
class InMemoryVectorStore:
    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        raise NotImplementedError("InMemoryVectorStore.upsert_chunks")

    def delete_chunk_ids(self, ids: list[str]) -> None:
        raise NotImplementedError("InMemoryVectorStore.delete_chunk_ids")

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError("InMemoryVectorStore.query")

    def count(self) -> int:
        raise NotImplementedError("InMemoryVectorStore.count")


class ChromaVectorStore:
    def __init__(self, persist_dir: Path, collection_name: str = "obsidian_chunks"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name

    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        raise NotImplementedError("ChromaVectorStore.upsert_chunks")

    def delete_chunk_ids(self, ids: list[str]) -> None:
        raise NotImplementedError("ChromaVectorStore.delete_chunk_ids")

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        raise NotImplementedError("ChromaVectorStore.query")

    def count(self) -> int:
        raise NotImplementedError("ChromaVectorStore.count")
```

Use cosine similarity in `InMemoryVectorStore`. Use Chroma persistent client in `ChromaVectorStore`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_retrieval_with_fake_provider.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/obsidian_agent/providers src/obsidian_agent/storage/vector_store.py tests/test_retrieval_with_fake_provider.py
git commit -m "feat: add providers and vector store"
```

---

### Task 6: Scan Command Integration

**Files:**
- Modify: `src/obsidian_agent/cli.py`
- Modify: `src/obsidian_agent/storage/sqlite_store.py`
- Modify: `src/obsidian_agent/storage/vector_store.py`
- Create: `tests/test_scan_cli.py`

- [ ] **Step 1: Write CLI scan integration test with fake embedding**

Create `tests/test_scan_cli.py`:

```python
from pathlib import Path
import shutil

from typer.testing import CliRunner

from obsidian_agent.cli import app


runner = CliRunner()


def test_scan_indexes_fixture_vault_without_network(tmp_path, monkeypatch):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    init_result = runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)])
    assert init_result.exit_code == 0

    scan_result = runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"])

    assert scan_result.exit_code == 0
    assert "Scanned: 2" in scan_result.stdout
    assert "Notes: 2" in scan_result.stdout
    assert (data_dir / "agent.db").exists()


def test_status_after_scan_reports_counts(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    status_result = runner.invoke(app, ["status", "--data-dir", str(data_dir)])

    assert status_result.exit_code == 0
    assert "Notes: 2" in status_result.stdout
    assert "Chunks:" in status_result.stdout
```

- [ ] **Step 2: Run scan CLI test to verify it fails**

Run: `pytest tests/test_scan_cli.py -q`

Expected: FAIL because `scan` command does not exist.

- [ ] **Step 3: Implement scan command**

Update `cli.py` with command:

```python
@app.command()
def scan(
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    rebuild: bool = typer.Option(False, "--rebuild"),
    embedding_provider: str | None = typer.Option(None, "--embedding-provider"),
) -> None:
    raise NotImplementedError("scan command body")
```

Behavior:

1. Load config.
2. Initialize `SQLiteStore(data_dir / "agent.db")`.
3. Scan vault with `scan_vault_files`.
4. Compare each parsed note hash with `store.get_note_hash(path)`.
5. Upsert changed notes and chunks into SQLite.
6. Embed changed chunks using fake provider when CLI override is `"fake"`, otherwise configured embedding provider.
7. Upsert changed chunks in vector store.
8. Delete removed notes and their vector chunks.
9. Recompute backlinks.
10. Save last scan summary.
11. Print `Scanned`, `Updated`, `Deleted`, `Warnings`, `Notes`, and `Chunks`.

If `--rebuild` is set, delete the existing SQLite database and vector directory before scanning, then treat every discovered note as changed. Implement `ChromaVectorStore.reset()` and `InMemoryVectorStore.reset()` so rebuild behavior is explicit and testable.

Update `status` so it reads counts and last scan metadata from `SQLiteStore` when `agent.db` exists. Before the first scan, it should keep printing `Notes: 0`, `Chunks: 0`, and `Last scan: never`.

For testability, use `InMemoryVectorStore` only when `embedding_provider == "fake"` and skip writing Chroma. For real providers, use `ChromaVectorStore(data_dir / "vectors")`.

- [ ] **Step 4: Run tests to verify scan passes**

Run: `pytest tests/test_scan_cli.py tests/test_sqlite_store.py tests/test_scanner.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/obsidian_agent/cli.py src/obsidian_agent/storage tests/test_scan_cli.py
git commit -m "feat: add scan command"
```

---

### Task 7: Retrieval, QA, And Ask Command

**Files:**
- Create: `src/obsidian_agent/retrieval/retriever.py`
- Create: `src/obsidian_agent/retrieval/qa.py`
- Modify: `src/obsidian_agent/cli.py`
- Create: `tests/test_ask_cli.py`

- [ ] **Step 1: Write ask CLI test with fake providers**

Create `tests/test_ask_cli.py`:

```python
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
```

- [ ] **Step 2: Run ask CLI test to verify it fails**

Run: `pytest tests/test_ask_cli.py -q`

Expected: FAIL because `ask` command and retrieval orchestration do not exist.

- [ ] **Step 3: Implement retriever and QA orchestration**

Create `retriever.py` with:

```python
class Retriever:
    def __init__(self, vector_store, embedding_provider, top_k: int):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.top_k = top_k

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        raise NotImplementedError("Retriever.retrieve")
```

De-duplication rule: keep the highest-scoring chunk per `(path, chunk_index)` and cap per note at 3 chunks.

Create `qa.py` with:

```python
SYSTEM_PROMPT = """你是一个本地 Obsidian 知识库助手。
只能根据给定的笔记片段回答。
如果上下文不足，请明确说明无法从当前知识库判断。
回答后列出使用到的来源文件路径。"""


def answer_question(question: str, contexts: list[RetrievedChunk], llm_provider: LLMProvider) -> tuple[str, list[str]]:
    answer = llm_provider.answer(question, contexts)
    sources = sorted({chunk.path for chunk in contexts})
    return answer, sources
```

- [ ] **Step 4: Implement ask command**

Update `cli.py` with command:

```python
@app.command()
def ask(
    question: str,
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    embedding_provider: str | None = typer.Option(None, "--embedding-provider"),
    llm_provider: str | None = typer.Option(None, "--llm-provider"),
) -> None:
    raise NotImplementedError("ask command body")
```

Behavior:

1. Load config and scan summary.
2. Exit with message `Run scan first` if there are no chunks.
3. Build fake or configured embedding provider.
4. Build fake or configured LLM provider.
5. Query vector store for top-k chunks.
6. Print answer.
7. Print `Sources:` and one source path per line.

For fake CLI tests, reconstruct an in-memory vector store from SQLite chunks and fake embeddings.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_ask_cli.py tests/test_retrieval_with_fake_provider.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_agent/retrieval src/obsidian_agent/cli.py tests/test_ask_cli.py
git commit -m "feat: add ask command with retrieval qa"
```

---

### Task 8: Organization Suggestions And Reports

**Files:**
- Create: `src/obsidian_agent/suggestions/rules.py`
- Create: `src/obsidian_agent/suggestions/reporter.py`
- Modify: `src/obsidian_agent/cli.py`
- Create: `tests/test_suggestions.py`

- [ ] **Step 1: Write suggestion tests**

Create `tests/test_suggestions.py`:

```python
from obsidian_agent.suggestions.reporter import render_markdown_report
from obsidian_agent.suggestions.rules import build_suggestions


def test_suggestions_find_missing_tags_frontmatter_and_isolated_notes():
    notes = [
        {
            "path": "Loose.md",
            "title": "Loose",
            "frontmatter_json": "{}",
            "tags_json": "[]",
            "links_json": "[]",
            "backlinks_count": 0,
            "outgoing_links_count": 0,
            "has_explicit_title": 1,
            "content": "tiny",
        }
    ]

    suggestions = build_suggestions(notes)
    kinds = {item.kind for item in suggestions}

    assert "missing_frontmatter" in kinds
    assert "missing_tags" in kinds
    assert "isolated_note" in kinds


def test_markdown_report_contains_note_paths():
    markdown = render_markdown_report([
        {"kind": "missing_tags", "path": "Loose.md", "message": "Add tags"}
    ])

    assert "# Obsidian Agent Suggestions" in markdown
    assert "Loose.md" in markdown


def test_suggest_refuses_output_inside_vault(tmp_path):
    from pathlib import Path
    import shutil
    from typer.testing import CliRunner
    from obsidian_agent.cli import app

    runner = CliRunner()
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    result = runner.invoke(app, ["suggest", "--data-dir", str(data_dir), "--output", str(vault / "suggestions.md")])

    assert result.exit_code == 1
    assert "Refusing to write inside the vault" in result.stdout
    assert not (vault / "suggestions.md").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_suggestions.py -q`

Expected: FAIL because suggestion modules do not exist.

- [ ] **Step 3: Implement suggestion rules and reports**

Create `rules.py` with:

```python
@dataclass(frozen=True)
class Suggestion:
    kind: str
    path: str
    message: str
    severity: str = "info"


def build_suggestions(notes: list[dict], short_note_word_threshold: int = 30) -> list[Suggestion]:
    raise NotImplementedError("build_suggestions")
```

Rules:

- `missing_frontmatter` when frontmatter JSON is `{}`.
- `missing_tags` when tags JSON is `[]`.
- `isolated_note` when backlinks and outgoing links are both zero.
- `missing_explicit_title` when `has_explicit_title` is false.
- `duplicate_title` when more than one note has the same lowercased title.
- `short_note` when content word count is below threshold.

Create `reporter.py` with:

```python
def render_markdown_report(suggestions: list[Suggestion | dict]) -> str:
    raise NotImplementedError("render_markdown_report")

def render_json_report(suggestions: list[Suggestion | dict]) -> str:
    raise NotImplementedError("render_json_report")
```

- [ ] **Step 4: Implement suggest command**

Update `cli.py` with:

```python
@app.command()
def suggest(
    data_dir: Path | None = typer.Option(None, "--data-dir"),
    output: Path | None = typer.Option(None, "--output"),
    format: str = typer.Option("markdown", "--format"),
) -> None:
    raise NotImplementedError("suggest command body")
```

Behavior:

1. Load config and SQLite notes.
2. Build suggestions from notes.
3. Render Markdown or JSON.
4. If output is unset, print report.
5. If output resolves inside config.vault_path, print warning and exit 1.
6. Otherwise write report to output.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_suggestions.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/obsidian_agent/suggestions src/obsidian_agent/cli.py tests/test_suggestions.py
git commit -m "feat: add read only suggestions"
```

---

### Task 9: End-To-End CLI Verification And README

**Files:**
- Modify: `README.md`
- Modify: `tests/test_cli.py`
- Create: `tests/test_e2e_cli.py`

- [ ] **Step 1: Write end-to-end CLI test**

Create `tests/test_e2e_cli.py`:

```python
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
```

- [ ] **Step 2: Run end-to-end test to verify current gaps**

Run: `pytest tests/test_e2e_cli.py -q`

Expected: PASS if previous tasks integrated cleanly, otherwise fix only the failing integration path.

- [ ] **Step 3: Update README with provider configuration**

Update `README.md` to include:

````markdown
## Provider Configuration

The default chat provider is DeepSeek V4 Pro:

```bash
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
```

The default embedding provider is OpenAI:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
```

DeepSeek is used for final answers. Embeddings are configured separately so retrieval can use OpenAI, an OpenAI-compatible endpoint, or a fake provider in tests.

## Offline Development

Use fake providers for local tests:

```bash
obsidian-agent scan --embedding-provider fake
obsidian-agent ask "agent project" --embedding-provider fake --llm-provider fake
```

The MVP does not modify vault files.
````

- [ ] **Step 4: Run full test suite**

Run: `pytest -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_e2e_cli.py tests/test_cli.py src
git commit -m "test: verify offline cli workflow"
```

---

## Final Verification

- [ ] **Step 1: Run all tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Verify no vault write behavior exists**

Run: `rg -n "write_text|unlink|rename|replace|shutil.move|remove\\(" src/obsidian_agent`

Expected:

- Allowed writes only in config save, SQLite/vector store internals, and report output code.
- No writes to paths derived from `config.vault_path`.

- [ ] **Step 3: Verify CLI help**

Run: `python -m obsidian_agent.cli --help`

Expected: command help lists `init`, `scan`, `ask`, `suggest`, and `status`.

- [ ] **Step 4: Check git status**

Run: `git status --short`

Expected: no uncommitted changes after the final commit.
