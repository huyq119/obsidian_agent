# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project uses semantic
versioning for release labels.

## [0.1.0] - 2026-06-07

### Added

- Initial read-only Obsidian vault CLI workflow with `init`, `scan`, `ask`,
  `suggest`, `status`, `doctor`, and `configure` commands.
- Markdown parsing, chunking, backlink extraction, SQLite metadata storage, and
  Chroma-backed local vector indexing.
- Retrieval QA flow with source reporting, context debugging, top-k tuning, and
  fake providers for offline tests.
- DeepSeek chat provider and OpenAI/OpenAI-compatible embedding providers,
  including the `deepseek-bigmodel` preset.
- Explicit local memory commands for adding, listing, searching, deleting, and
  opt-in use during answers.
- Project documentation for quick start, installation, architecture, deployment,
  memory usage, environment variables, and contribution workflow.
- GitHub Actions CI for Python 3.11 and 3.12.

### Changed

- Expanded `configure` to persist retrieval count, chunk token limits, and
  provider presets.
- Normalized OpenAI-compatible embedding endpoint handling.
- Improved scan resilience for parse errors and CRLF frontmatter.

### Security

- Documented privacy rules for local vault data, API keys, generated outputs,
  SQLite databases, and vector indexes.
- Added ignore rules for local state and generated artifacts.
