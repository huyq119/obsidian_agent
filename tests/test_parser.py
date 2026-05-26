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
