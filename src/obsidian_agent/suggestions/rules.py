from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path


@dataclass(frozen=True)
class Suggestion:
    kind: str
    path: str
    message: str
    severity: str = "info"


def build_suggestions(notes: list[dict], short_note_word_threshold: int = 30) -> list[Suggestion]:
    suggestions: list[Suggestion] = []
    title_counts: dict[str, list[str]] = {}

    for note in notes:
        path = str(note["path"])
        title = str(note["title"])
        frontmatter = json.loads(str(note.get("frontmatter_json", "{}")))
        tags = json.loads(str(note.get("tags_json", "[]")))
        backlinks = int(note.get("backlinks_count", 0))
        outgoing = int(note.get("outgoing_links_count", 0))
        has_explicit_title = bool(note.get("has_explicit_title", 0))
        word_count = int(note.get("word_count", 0))

        if frontmatter == {}:
            suggestions.append(
                Suggestion(
                    kind="missing_frontmatter",
                    path=path,
                    message="Add YAML frontmatter to improve organization.",
                ),
            )
        if not tags:
            suggestions.append(
                Suggestion(
                    kind="missing_tags",
                    path=path,
                    message="Add tags to improve discoverability.",
                ),
            )
        if backlinks == 0 and outgoing == 0:
            suggestions.append(
                Suggestion(
                    kind="isolated_note",
                    path=path,
                    message="This note has no inbound or outbound links.",
                ),
            )
        if not has_explicit_title:
            suggestions.append(
                Suggestion(
                    kind="missing_explicit_title",
                    path=path,
                    message="Add an explicit H1 title.",
                ),
            )
        filename_stem = Path(path).stem
        if has_explicit_title and title.casefold() != filename_stem.casefold():
            suggestions.append(
                Suggestion(
                    kind="title_filename_mismatch",
                    path=path,
                    message=f"H1 title '{title}' differs from filename stem '{filename_stem}'.",
                ),
            )
        if word_count < short_note_word_threshold:
            suggestions.append(
                Suggestion(
                    kind="short_note",
                    path=path,
                    message=f"Note has only {word_count} words.",
                ),
            )

        title_key = title.casefold()
        title_counts.setdefault(title_key, []).append(path)

    for paths in title_counts.values():
        if len(paths) > 1:
            for path in paths:
                suggestions.append(
                    Suggestion(
                        kind="duplicate_title",
                        path=path,
                        message="Another note shares the same title.",
                    ),
                )

    suggestions.extend(_similar_filename_suggestions(notes))
    return suggestions


def _similar_filename_suggestions(notes: list[dict]) -> list[Suggestion]:
    suggestions: list[Suggestion] = []
    paths = [str(note["path"]) for note in notes]
    stems = [Path(path).stem.casefold() for path in paths]
    for index, left_stem in enumerate(stems):
        for other_index, right_stem in enumerate(stems):
            if other_index <= index:
                continue
            ratio = SequenceMatcher(None, left_stem, right_stem).ratio()
            if ratio >= 0.85:
                suggestions.append(
                    Suggestion(
                        kind="similar_filename",
                        path=paths[index],
                        message=f"Filename is similar to {paths[other_index]}.",
                    ),
                )
                suggestions.append(
                    Suggestion(
                        kind="similar_filename",
                        path=paths[other_index],
                        message=f"Filename is similar to {paths[index]}.",
                    ),
                )
    return suggestions
