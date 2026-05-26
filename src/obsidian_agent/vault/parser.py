from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import yaml

from obsidian_agent.vault.models import ParsedNote

_HEADING_RE = re.compile(r"^#\s+(.+?)\s*#*\s*$", re.MULTILINE)
_INLINE_TAG_RE = re.compile(r"(?<![\w/#])#([A-Za-z0-9_/-]+)")
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def parse_markdown_note(path: Path, text: str, modified_at: float | None = None) -> ParsedNote:
    """Return parsed metadata, links, tags, content hash, and title for one Markdown note."""
    frontmatter, content = _split_frontmatter(text)
    title_match = _HEADING_RE.search(content)
    has_explicit_title = title_match is not None
    title = title_match.group(1).strip() if title_match else path.stem

    return ParsedNote(
        path=path.as_posix(),
        title=title,
        content=content,
        frontmatter=frontmatter,
        tags=_unique(_frontmatter_tags(frontmatter) + _inline_tags(content)),
        links=_unique(_wikilinks(content) + _markdown_links(content)),
        has_explicit_title=has_explicit_title,
        content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        modified_at=modified_at,
    )


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    start_match = re.match(r"^\ufeff?---\r?\n", text)
    if start_match is None:
        return {}, text

    closing = re.search(r"^---[ \t]*(?:\r?\n|$)", text[start_match.end() :], re.MULTILINE)
    if closing is None:
        return {}, text

    end = start_match.end() + closing.start()
    content_start = start_match.end() + closing.end()
    raw_frontmatter = text[start_match.end() : end]
    parsed = yaml.safe_load(raw_frontmatter) or {}
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed, text[content_start:].lstrip("\r\n")


def _frontmatter_tags(frontmatter: dict[str, Any]) -> list[str]:
    tags = frontmatter.get("tags", [])
    if isinstance(tags, str):
        return [tag.strip().lstrip("#") for tag in re.split(r"[\s,]+", tags) if tag.strip()]
    if isinstance(tags, list):
        return [str(tag).strip().lstrip("#") for tag in tags if str(tag).strip()]
    return []


def _inline_tags(content: str) -> list[str]:
    return [match.group(1) for match in _INLINE_TAG_RE.finditer(content)]


def _wikilinks(content: str) -> list[str]:
    return [match.group(1).strip() for match in _WIKILINK_RE.finditer(content)]


def _markdown_links(content: str) -> list[str]:
    return [match.group(1).strip() for match in _MARKDOWN_LINK_RE.finditer(content)]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_values: list[str] = []
    for value in values:
        if value and value not in seen:
            unique_values.append(value)
            seen.add(value)
    return unique_values
