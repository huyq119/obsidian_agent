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
