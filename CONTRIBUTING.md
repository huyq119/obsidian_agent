# Contributing

Thanks for helping improve Obsidian Agent. This project is a local, read-only
CLI agent for Obsidian vaults, so contributions should keep user notes, local
indexes, and API keys private by default.

## Development Setup

Create a virtual environment and install the package with development
dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Check that the CLI imports correctly:

```bash
PYTHONPATH=src .venv/bin/python -m obsidian_agent.cli --help
```

## Running Tests

Run the full local test suite before opening a pull request:

```bash
PYTHONPATH=src .venv/bin/python -m pytest
```

For provider-related tests, prefer fake providers:

```bash
obsidian-agent scan --embedding-provider fake
obsidian-agent ask "agent project" --embedding-provider fake --llm-provider fake
```

Do not add tests that require real API keys unless they are explicitly isolated
and skipped by default.

## Privacy and Local Data

Never commit:

- Real API keys or `.env` files.
- Obsidian vault contents.
- `.obsidian-agent/` local state.
- SQLite databases, Chroma vector indexes, or generated reports.
- Local absolute paths that reveal a user's machine or vault name.
- Generated output directories such as `outputs/` or `hatch_runs/`.

Before committing, run a privacy scan from the repository root:

```bash
rg -n --hidden --glob '!.git/**' --glob '!.venv/**' --glob '!.pytest_cache/**' --glob '!.obsidian-agent/**' --glob '!**/__pycache__/**' --glob '!hatch_runs/**' '<your-username>|<your-vault-name>|<api-key-prefix>|<private-key-marker>' .
```

A no-match result is expected for a clean public change.

## Change Guidelines

- Keep the vault read-only unless the feature explicitly introduces a reviewed
  write path.
- Match the existing CLI patterns in `src/obsidian_agent/cli.py`.
- Add focused tests for behavior changes.
- Keep provider calls behind explicit configuration and avoid network calls in
  default tests.
- Update README or `docs/project-overview.md` when user-facing commands,
  configuration, or setup steps change.

## Pull Request Checklist

Before publishing a change:

```bash
git status --short
git diff --check
PYTHONPATH=src .venv/bin/python -m pytest
```

Confirm the status output only contains intended source, tests, docs, or CI
files. GitHub Actions will also run the test suite on Python 3.11 and 3.12 for
pushes and pull requests targeting `main`.
