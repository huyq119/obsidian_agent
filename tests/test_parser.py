from pathlib import Path

from obsidian_agent.vault.parser import parse_markdown_note


def test_parse_frontmatter_tags_title_and_links():
    text = """---
tags:
  - ai
  - project
---
# Agent Project

Body with #inline and [[Loose|loose note]] plus [Doc](docs/readme.md).
"""

    note = parse_markdown_note(path=Path("Project.md"), text=text)

    assert note.title == "Agent Project"
    assert note.frontmatter["tags"] == ["ai", "project"]
    assert note.tags == ["ai", "project", "inline"]
    assert "Loose" in note.links
    assert "docs/readme.md" in note.links
    assert note.has_explicit_title is True


def test_parse_crlf_frontmatter_tags_and_title():
    text = "---\r\ntags:\r\n  - crlf\r\n---\r\n# CRLF Note\r\nBody"

    note = parse_markdown_note(path=Path("CRLF.md"), text=text)

    assert note.frontmatter["tags"] == ["crlf"]
    assert "crlf" in note.tags
    assert note.title == "CRLF Note"


def test_parse_bom_before_frontmatter():
    text = "\ufeff---\ntags:\n  - bom\n---\n# BOM Note\nBody"

    note = parse_markdown_note(path=Path("BOM.md"), text=text)

    assert note.frontmatter["tags"] == ["bom"]
    assert "bom" in note.tags
    assert note.title == "BOM Note"
