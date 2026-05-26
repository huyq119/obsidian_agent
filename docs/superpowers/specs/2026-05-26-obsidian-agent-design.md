# Obsidian Knowledge Base Agent Design

Date: 2026-05-26
Status: Approved for implementation planning

## Goal

Build a local, read-only CLI agent for managing an Obsidian knowledge base. The first version scans an Obsidian vault, indexes Markdown notes into a local data directory, answers questions using retrieval-augmented generation, and produces deterministic organization suggestions without modifying any vault files.

## Product Scope

The MVP includes:

- Initialize a local agent data directory for one Obsidian vault.
- Scan Markdown notes from the vault.
- Parse frontmatter, headings, tags, wikilinks, Markdown links, and note text.
- Store structured note and chunk metadata in SQLite.
- Store chunk embeddings in a local persistent vector store.
- Answer user questions from retrieved note chunks and cite source note paths.
- Generate read-only organization suggestions from deterministic metadata rules.
- Support DeepSeek V4 Pro as the default chat model provider.
- Support OpenAI and OpenAI-compatible embedding providers.
- Use fake providers in tests so default tests do not call external APIs.

The MVP does not include:

- Editing, moving, renaming, or deleting files inside the Obsidian vault.
- Applying organization suggestions automatically.
- Obsidian plugin integration.
- Web UI.
- Reading or indexing non-Markdown attachments such as PDFs, images, audio, or video.
- Saving API keys in project config.
- LLM-generated organization suggestions.

## User Workflow

The CLI is named `obsidian-agent`.

The main workflow is:

```bash
obsidian-agent init --vault ~/Documents/Notes
obsidian-agent scan
obsidian-agent ask "我最近关于项目管理的想法有哪些？"
obsidian-agent suggest --output suggestions.md
obsidian-agent status
```

`init` creates the local data directory and config. By default, the data directory is `.obsidian-agent/` in the current project, with an optional `--data-dir` override.

`scan` reads Markdown files, updates SQLite metadata, and updates the vector store. It supports incremental updates by hashing file contents and skipping unchanged notes.

`ask` embeds the query, retrieves relevant chunks, calls the configured LLM, and prints an answer with source file paths.

`suggest` prints deterministic organization suggestions or writes them to Markdown or JSON outside the vault.

`status` prints the configured vault path, note count, chunk count, last scan time, provider configuration, and read-only state.

## Architecture

The system is split into focused modules:

- `cli`: command definitions, argument parsing, terminal output.
- `config`: config loading, validation, default values, and environment variable names.
- `vault`: scanning, Markdown parsing, metadata extraction, and chunking.
- `storage`: SQLite persistence and vector store persistence.
- `providers`: interfaces and implementations for chat and embedding providers.
- `retrieval`: vector search, chunk de-duplication, prompt assembly, and QA orchestration.
- `suggestions`: deterministic rules and report rendering.

Recommended project structure:

```text
obsidian-agent/
  pyproject.toml
  README.md
  src/obsidian_agent/
    cli.py
    config.py
    vault/
      scanner.py
      parser.py
      chunker.py
    storage/
      sqlite_store.py
      vector_store.py
    providers/
      base.py
      deepseek_llm.py
      openai_embedding.py
      openai_compatible_embedding.py
      fake.py
    retrieval/
      retriever.py
      qa.py
    suggestions/
      rules.py
      reporter.py
  tests/
    fixtures/vault_basic/
    test_config.py
    test_scanner.py
    test_parser.py
    test_chunker.py
    test_suggestions.py
    test_retrieval_with_fake_provider.py
```

## Data Directory

Default local state:

```text
.obsidian-agent/
  config.toml
  agent.db
  vectors/
  reports/
```

The agent may write inside its own data directory and to explicit report output paths. It must not write inside the Obsidian vault in the MVP.

## Configuration

The config separates chat and embedding providers so the final answer model can differ from the retrieval model.

Default config:

```toml
vault_path = "/absolute/path/to/vault"
readonly = true

[scan]
max_file_size_bytes = 1048576
skip_hidden_dirs = true
skip_dirs = [".obsidian", ".git", "node_modules"]

[chunking]
target_tokens = 1000
max_tokens = 1200

[retrieval]
top_k = 6

[llm]
provider = "deepseek"
base_url = "https://api.deepseek.com"
api_key_env = "DEEPSEEK_API_KEY"
chat_model = "deepseek-v4-pro"
thinking = true
reasoning_effort = "high"

[embedding]
provider = "openai"
base_url = "https://api.openai.com/v1"
api_key_env = "OPENAI_API_KEY"
embedding_model = "text-embedding-3-small"
dimensions = 1536
```

OpenAI-compatible embedding config:

```toml
[embedding]
provider = "openai_compatible"
base_url = "https://your-provider.example.com/v1"
api_key_env = "EMBEDDING_API_KEY"
embedding_model = "your-embedding-model"
dimensions = 1536
```

API keys are read from environment variables only. Config stores environment variable names, provider names, model names, base URLs, and non-secret settings.

## Provider Interfaces

The provider layer exposes two independent interfaces:

```python
class EmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, query: str) -> list[float]:
        ...


class LLMProvider:
    def answer(self, question: str, contexts: list["RetrievedChunk"]) -> str:
        ...
```

MVP provider implementations:

- `DeepSeekLLMProvider`: OpenAI-compatible chat client with `base_url = "https://api.deepseek.com"` and default model `deepseek-v4-pro`.
- `OpenAIEmbeddingProvider`: OpenAI embeddings with default model `text-embedding-3-small`.
- `OpenAICompatibleEmbeddingProvider`: configurable OpenAI-compatible `/embeddings` client.
- `FakeEmbeddingProvider` and `FakeLLMProvider`: deterministic test providers.

DeepSeek is used for chat completion in the MVP, not embeddings. The design keeps embeddings separate because the DeepSeek API documentation consulted during planning focuses on chat/completions compatibility and does not define a default embedding model for this project.

## SQLite Data Model

SQLite stores structured metadata and chunk records.

`notes`:

- `id`: stable internal note id.
- `path`: vault-relative note path.
- `title`: parsed title, preferably first H1, falling back to filename stem.
- `frontmatter_json`: parsed YAML frontmatter as JSON.
- `tags_json`: parsed tags as JSON array.
- `links_json`: outgoing wikilinks and Markdown links as JSON array.
- `backlinks_count`: number of inbound note links.
- `outgoing_links_count`: number of outgoing note links.
- `content_hash`: hash of raw Markdown content.
- `modified_at`: filesystem modified time.
- `indexed_at`: scan time.

`chunks`:

- `id`: stable chunk id.
- `note_id`: parent note id.
- `chunk_index`: chunk order within note.
- `text`: chunk text.
- `heading`: nearest Markdown heading.
- `token_count`: estimated token count.
- `content_hash`: hash of chunk text.

Additional housekeeping tables may track schema version and last scan metadata.

## Vector Store

Use Chroma for the first implementation because it provides local persistence and metadata support with less custom index management than direct FAISS use.

Each vector record stores:

- `id`: chunk id matching SQLite.
- `document`: chunk text.
- `embedding`: provider-generated vector.
- `metadata.note_id`.
- `metadata.path`.
- `metadata.title`.
- `metadata.heading`.
- `metadata.chunk_index`.

The vector store must be rebuilt or repaired by `scan --rebuild` if persistent index files become inconsistent.

## Scan And Index Flow

`scan` performs:

1. Load config and validate vault path.
2. Walk the vault recursively.
3. Include `.md` files only.
4. Skip `.obsidian/`, hidden directories, configured skip directories, and files above the size limit.
5. Compute raw Markdown content hash.
6. Skip unchanged files by comparing path and hash against SQLite.
7. Parse changed or new notes.
8. Chunk changed or new notes.
9. Upsert note and chunk metadata in SQLite.
10. Embed changed chunks and upsert them in Chroma.
11. Detect deleted notes and remove their SQLite rows and vector records.
12. Recompute backlink counts after parsing all current links.
13. Print a summary with scanned, skipped, updated, deleted, warning, note, and chunk counts.

Single-file parse failures produce warnings and do not abort the whole scan.

## Markdown Parsing

Parser responsibilities:

- Extract YAML frontmatter when present.
- Extract H1 title when present.
- Fall back to filename stem as title when H1 is missing.
- Extract inline and frontmatter tags.
- Extract wikilinks such as `[[Project Note]]` and `[[Project Note|alias]]`.
- Extract Markdown links such as `[label](target.md)`.
- Preserve enough source text for chunking and retrieval.

The parser does not need to support every Obsidian extension in the MVP. Unsupported syntax remains as plain text.

## Chunking Strategy

The chunker should:

- Prefer Markdown heading boundaries.
- Target about 800 to 1200 tokens per chunk.
- Split very long heading sections by paragraph.
- Attach the nearest heading to each chunk.
- Avoid merging content across files.

Token count may be estimated in the MVP. The implementation should keep the chunking interface isolated so a tokenizer can be added later.

## RAG Ask Flow

`ask` performs:

1. Load config and local indexes.
2. Validate that scan has run and that the vector store has records.
3. Embed the user question with the configured embedding provider.
4. Retrieve top-k chunks from Chroma, default `top_k = 6`.
5. De-duplicate near-identical chunks and avoid over-representing one note.
6. Build a prompt with the question and retrieved context.
7. Call DeepSeek V4 Pro through `DeepSeekLLMProvider`.
8. Print the answer and source paths.

The prompt instructs the model:

```text
你是一个本地 Obsidian 知识库助手。
只能根据给定的笔记片段回答。
如果上下文不足，请明确说明无法从当前知识库判断。
回答后列出使用到的来源文件路径。
```

The source list is generated from retrieved chunk metadata, not trusted solely from model output.

## Organization Suggestions

`suggest` uses deterministic metadata rules in the MVP:

- Missing frontmatter.
- Missing tags.
- Isolated note with no inbound or outbound links.
- Missing explicit H1 title.
- H1 title differs substantially from filename stem.
- Very short note below a configured word-count threshold.
- Duplicate exact titles.
- Highly similar filenames.

The command outputs a readable report by default. It can also write Markdown or JSON:

```bash
obsidian-agent suggest --output suggestions.md
obsidian-agent suggest --format json --output suggestions.json
```

Reports must be written outside the vault. If the user provides an explicit output path that resolves inside the vault, the MVP should warn and refuse to write the report.

## Error Handling

Expected user-facing errors:

- Running `scan`, `ask`, `suggest`, or `status` before `init`: show a message that `init` is required.
- Vault path does not exist: show the configured path and ask the user to fix config or rerun `init`.
- Missing provider API key: show the required environment variable name.
- Empty or missing index during `ask`: show that `scan` must run first.
- Vector index inconsistency: show `scan --rebuild`.
- Parse failure in one note: show a warning and continue scanning.
- Provider API error: show provider name, operation, and a concise retryable/non-retryable message without exposing secrets.

## Safety Requirements

- The MVP is read-only with respect to the Obsidian vault.
- No command may alter vault Markdown files.
- No command may write reports inside the vault.
- API keys are never written to `config.toml`.
- Logs must not print full API keys.
- `scan` reads Markdown only and skips attachments.
- `.obsidian/` is skipped by default.
- Any future write-capable feature must be designed as a separate `apply` workflow with explicit user confirmation.

## Testing Strategy

Default tests must run without real network calls.

Use fixture vaults under `tests/fixtures/` to cover:

- Config creation and loading.
- Vault scanning with skipped directories and size limits.
- Frontmatter, title, tag, wikilink, and Markdown link parsing.
- Heading-aware chunking.
- Incremental scan for added, modified, unchanged, and deleted files.
- Suggestion rules for missing tags, missing frontmatter, isolated notes, short notes, duplicate titles, and similar filenames.
- Retrieval and QA orchestration with fake embedding and fake LLM providers.
- CLI command behavior for `init`, `scan`, `ask`, `suggest`, and `status`.

Optional smoke tests may use real provider credentials when `DEEPSEEK_API_KEY` or `OPENAI_API_KEY` is present, but these tests must not run by default.

## Milestones

1. Project skeleton and config.
2. Vault scanning, parsing, and chunking.
3. SQLite persistence and incremental scan.
4. Embedding providers and Chroma vector store.
5. Retrieval and DeepSeek V4 Pro QA flow.
6. Deterministic organization suggestions.
7. End-to-end CLI verification with fixture vault.

## Success Criteria

The MVP is successful when:

- A user can initialize the agent for a real Obsidian vault.
- `scan` builds or updates local SQLite and vector indexes without modifying the vault.
- `ask` answers questions from retrieved note chunks and prints source paths.
- `suggest` produces useful read-only organization suggestions.
- `status` accurately reports vault and index state.
- Default tests pass without external API credentials.
