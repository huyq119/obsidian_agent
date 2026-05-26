from __future__ import annotations

from pathlib import Path

from obsidian_agent.config import ScanConfig
from obsidian_agent.vault.chunker import chunk_note
from obsidian_agent.vault.models import NoteChunk, ParsedNote, ScanResult
from obsidian_agent.vault.parser import parse_markdown_note


def scan_vault_files(
    vault_path: Path,
    scan_config: ScanConfig,
    target_tokens: int = 1000,
    max_tokens: int = 1200,
) -> ScanResult:
    """Scan Markdown files under a vault and return parsed notes, chunks, and warnings."""
    notes: list[ParsedNote] = []
    chunks: list[NoteChunk] = []
    warnings: list[str] = []
    scanned_files = 0
    skipped_files = 0

    for path in sorted(vault_path.rglob("*.md")):
        relative_path = path.relative_to(vault_path)
        if _should_skip(relative_path, scan_config):
            skipped_files += 1
            continue

        try:
            stat = path.stat()
            if stat.st_size > scan_config.max_file_size_bytes:
                skipped_files += 1
                continue
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            skipped_files += 1
            warnings.append(f"Could not read {relative_path.as_posix()}: {exc}")
            continue
        except UnicodeDecodeError as exc:
            skipped_files += 1
            warnings.append(f"Could not decode {relative_path.as_posix()}: {exc}")
            continue

        note = parse_markdown_note(relative_path, text, modified_at=stat.st_mtime)
        notes.append(note)
        chunks.extend(chunk_note(note, target_tokens=target_tokens, max_tokens=max_tokens))
        scanned_files += 1

    return ScanResult(
        notes=notes,
        chunks=chunks,
        scanned_files=scanned_files,
        skipped_files=skipped_files,
        warnings=warnings,
    )


def _should_skip(path: Path, scan_config: ScanConfig) -> bool:
    parts = path.parts[:-1]
    if any(part in scan_config.skip_dirs for part in parts):
        return True
    return scan_config.skip_hidden_dirs and any(part.startswith(".") for part in parts)
