from pathlib import Path

from obsidian_agent.vault.chunker import chunk_note
from obsidian_agent.vault.parser import parse_markdown_note


def test_chunk_note_preserves_heading_metadata():
    text = "# Title\n\nIntro\n\n## Plan\n\n" + "word " * 1400
    note = parse_markdown_note(Path("Note.md"), text)

    chunks = chunk_note(note, target_tokens=100, max_tokens=120)

    assert len(chunks) > 1
    assert chunks[0].heading == "Title"
    assert any(chunk.heading == "Plan" for chunk in chunks)
    assert chunks[0].note_path == "Note.md"
