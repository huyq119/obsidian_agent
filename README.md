# Obsidian Agent

[![CI](https://github.com/huyq119/obsidian_agent/actions/workflows/ci.yml/badge.svg)](https://github.com/huyq119/obsidian_agent/actions/workflows/ci.yml)

A local read-only CLI agent for Obsidian knowledge bases.

See [Project Overview](docs/project-overview.md) for the project introduction, architecture, installation, and deployment guide.
See [Contributing](CONTRIBUTING.md) for local development, testing, and privacy checks.

## Quick Start

Initialize the agent with your Obsidian vault path.

```bash
obsidian-agent init --vault "/path/to/your/Obsidian vault" --preset deepseek-bigmodel
```

Check that the config, vault path, and required environment variables are ready.

```bash
obsidian-agent doctor
```

Scan the vault and build the local index.

```bash
obsidian-agent scan --rebuild
```

Ask your first question.

```bash
obsidian-agent ask "Summarize the main themes in this vault."
```

## MVP Commands

```bash
obsidian-agent init --vault ~/Documents/Notes
obsidian-agent configure --top-k 10
obsidian-agent scan
obsidian-agent ask "What does my vault say about AI agents?"
obsidian-agent ask "What does my vault say about AI agents?" --show-context --top-k 10
obsidian-agent memory add "User prefers concise answers."
obsidian-agent ask "What does my vault say about AI agents?" --use-memory
obsidian-agent suggest --output suggestions.md
obsidian-agent status
obsidian-agent doctor
```

The agent stores local state in `.obsidian-agent/` and does not modify vault files.

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

### DeepSeek + BigModel Embeddings

For a local Obsidian vault with DeepSeek answers and BigModel embeddings:

```bash
export DEEPSEEK_API_KEY="<your-deepseek-api-key>"
export EMBEDDING_API_KEY="<your-bigmodel-api-key>"
```

Initialize a data directory:

```bash
obsidian-agent init --vault "/path/to/your/Obsidian vault" --preset deepseek-bigmodel
```

Run a smoke test:

```bash
obsidian-agent scan --rebuild
obsidian-agent ask "Summarize the main themes in this vault."
```

Inspect retrieval context when tuning embeddings, chunking, or `top_k`:

```bash
obsidian-agent configure --top-k 10
obsidian-agent configure --target-tokens 800 --max-tokens 1000
obsidian-agent configure --preset deepseek-bigmodel
obsidian-agent ask "Summarize the main themes in this vault." --show-context
obsidian-agent ask "Summarize the main themes in this vault." --show-context --top-k 10 --context-chars 120
```

`configure` persists retrieval, chunking, and provider preset settings in `.obsidian-agent/config.toml`.
`ask --top-k` only overrides it for one question.

## Memory Usage

The memory feature is explicit and local-first. It does not automatically record
conversations, and memories are not used unless you pass `--use-memory`.

Add a memory:

```bash
obsidian-agent memory add "User prefers concise answers."
```

List and search memories:

```bash
obsidian-agent memory list
obsidian-agent memory search "concise answers"
```

Delete a memory:

```bash
obsidian-agent memory delete 1
obsidian-agent memory delete 1 --force
```

Use matching memories during one answer:

```bash
obsidian-agent ask "Answer with my preferences in mind." --use-memory
obsidian-agent ask "Answer with my preferences in mind." --use-memory --memory-top-k 5
```

Memories are stored locally in `.obsidian-agent/memory.db`. They are only included
in answers when `ask --use-memory` is set. When enabled, matching memories are sent
to the configured LLM together with the retrieved vault context.

Troubleshoot configuration and providers:

```bash
obsidian-agent doctor
obsidian-agent doctor --network
```

`doctor` checks the local config, vault path, and required environment variables.
`doctor --network` also sends minimal test requests to the configured embedding and
LLM providers.

## Offline Development

Use fake providers for local tests:

```bash
obsidian-agent scan --embedding-provider fake
obsidian-agent ask "agent project" --embedding-provider fake --llm-provider fake
```

The MVP does not modify vault files.

## Development and Testing

Install the package with development dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the local test suite:

```bash
PYTHONPATH=src .venv/bin/python -m pytest
```

GitHub Actions runs the same test suite on Python 3.11 and 3.12 for pushes and
pull requests targeting `main`.
