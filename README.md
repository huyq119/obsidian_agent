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
