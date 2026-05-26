from __future__ import annotations

import hashlib
import re

from obsidian_agent.vault.models import NoteChunk, ParsedNote

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


def chunk_note(note: ParsedNote, target_tokens: int, max_tokens: int) -> list[NoteChunk]:
    """Split one parsed note into heading-aware chunks with stable chunk ids."""
    chunks: list[NoteChunk] = []
    chunk_index = 0

    for heading, section_text in _sections(note):
        for text in _split_section(section_text, target_tokens, max_tokens):
            token_count = _count_tokens(text)
            chunks.append(
                NoteChunk(
                    id=_chunk_id(note.path, chunk_index, text),
                    note_path=note.path,
                    chunk_index=chunk_index,
                    text=text,
                    heading=heading,
                    token_count=token_count,
                    content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                )
            )
            chunk_index += 1

    return chunks


def _sections(note: ParsedNote) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = note.title
    current_lines: list[str] = []

    for line in note.content.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = match.group(2).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    return [(heading, "\n".join(lines).strip()) for heading, lines in sections if "\n".join(lines).strip()]


def _split_section(section_text: str, target_tokens: int, max_tokens: int) -> list[str]:
    token_limit = max(1, min(target_tokens, max_tokens))
    if _count_tokens(section_text) <= max_tokens:
        return [section_text]

    words = section_text.split()
    return [" ".join(words[index : index + token_limit]) for index in range(0, len(words), token_limit)]


def _count_tokens(text: str) -> int:
    return len(text.split())


def _chunk_id(note_path: str, chunk_index: int, text: str) -> str:
    return hashlib.sha256(f"{note_path}:{chunk_index}:{text}".encode("utf-8")).hexdigest()
