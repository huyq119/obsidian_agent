from __future__ import annotations

import json

from obsidian_agent.suggestions.rules import Suggestion


def render_markdown_report(suggestions: list[Suggestion | dict]) -> str:
    lines = ["# Obsidian Agent Suggestions", ""]
    if not suggestions:
        lines.append("No suggestions found.")
        return "\n".join(lines)

    for item in suggestions:
        suggestion = _coerce_suggestion(item)
        lines.append(f"## {suggestion.kind}")
        lines.append(f"- Path: `{suggestion.path}`")
        lines.append(f"- Message: {suggestion.message}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_json_report(suggestions: list[Suggestion | dict]) -> str:
    payload = [_coerce_suggestion(item).__dict__ for item in suggestions]
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _coerce_suggestion(item: Suggestion | dict) -> Suggestion:
    if isinstance(item, Suggestion):
        return item
    return Suggestion(
        kind=str(item["kind"]),
        path=str(item["path"]),
        message=str(item["message"]),
        severity=str(item.get("severity", "info")),
    )
