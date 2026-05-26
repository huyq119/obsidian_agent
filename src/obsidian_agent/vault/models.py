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
