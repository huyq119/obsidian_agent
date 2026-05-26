from pathlib import Path

from obsidian_agent.storage.sqlite_store import SQLiteStore
from obsidian_agent.vault.models import NoteChunk, ParsedNote


def make_note(path="Project.md", title="Project", content_hash="abc"):
    return ParsedNote(
        path=path,
        title=title,
        content="# Project\nBody",
        frontmatter={"tags": ["ai"]},
        tags=["ai"],
        links=["Loose"],
        has_explicit_title=True,
        content_hash=content_hash,
        modified_at=1.0,
    )


def make_chunk(note_path="Project.md"):
    return NoteChunk(
        id="chunk-1",
        note_path=note_path,
        chunk_index=0,
        text="Body",
        heading="Project",
        token_count=1,
        content_hash="chunk-hash",
    )


def test_upsert_notes_and_chunks_round_trip(tmp_path):
    store = SQLiteStore(tmp_path / "agent.db")
    store.initialize()

    store.upsert_note_with_chunks(make_note(), [make_chunk()])

    assert store.count_notes() == 1
    assert store.count_chunks() == 1
    assert store.get_note_hash("Project.md") == "abc"


def test_delete_missing_notes_removes_chunks(tmp_path):
    store = SQLiteStore(tmp_path / "agent.db")
    store.initialize()
    store.upsert_note_with_chunks(make_note(), [make_chunk()])

    deleted = store.delete_notes_not_in({"Other.md"})

    assert deleted == ["Project.md"]
    assert store.count_notes() == 0
    assert store.count_chunks() == 0


def test_recompute_backlinks_counts_inbound_links(tmp_path):
    store = SQLiteStore(tmp_path / "agent.db")
    store.initialize()
    store.upsert_note_with_chunks(make_note(path="Project.md", title="Agent Project"), [make_chunk("Project.md")])
    store.upsert_note_with_chunks(make_note(path="Inbox/Loose.md", title="Loose"), [make_chunk("Inbox/Loose.md")])

    store.recompute_backlinks()
    loose = store.get_note("Inbox/Loose.md")

    assert loose["backlinks_count"] == 1
