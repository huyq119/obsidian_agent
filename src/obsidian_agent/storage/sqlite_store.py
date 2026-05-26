from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from obsidian_agent.vault.models import NoteChunk, ParsedNote

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
  path TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  frontmatter_json TEXT NOT NULL,
  tags_json TEXT NOT NULL,
  links_json TEXT NOT NULL,
  backlinks_count INTEGER NOT NULL DEFAULT 0,
  outgoing_links_count INTEGER NOT NULL DEFAULT 0,
  has_explicit_title INTEGER NOT NULL,
  word_count INTEGER NOT NULL DEFAULT 0,
  content_hash TEXT NOT NULL,
  modified_at REAL,
  indexed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
  id TEXT PRIMARY KEY,
  note_path TEXT NOT NULL REFERENCES notes(path) ON DELETE CASCADE,
  chunk_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  heading TEXT NOT NULL,
  token_count INTEGER NOT NULL,
  content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL
);
"""


class SQLiteStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def get_note_hash(self, path: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT content_hash FROM notes WHERE path = ?",
                (path,),
            ).fetchone()
        return None if row is None else str(row[0])

    def upsert_note_with_chunks(self, note: ParsedNote, chunks: list[NoteChunk]) -> None:
        indexed_at = datetime.now(UTC).isoformat()
        word_count = len(note.content.split())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO notes (
                  path, title, frontmatter_json, tags_json, links_json,
                  backlinks_count, outgoing_links_count, has_explicit_title,
                  word_count, content_hash, modified_at, indexed_at
                ) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                  title = excluded.title,
                  frontmatter_json = excluded.frontmatter_json,
                  tags_json = excluded.tags_json,
                  links_json = excluded.links_json,
                  has_explicit_title = excluded.has_explicit_title,
                  word_count = excluded.word_count,
                  content_hash = excluded.content_hash,
                  modified_at = excluded.modified_at,
                  indexed_at = excluded.indexed_at
                """,
                (
                    note.path,
                    note.title,
                    json.dumps(note.frontmatter, ensure_ascii=False),
                    json.dumps(note.tags, ensure_ascii=False),
                    json.dumps(note.links, ensure_ascii=False),
                    len(note.links),
                    int(note.has_explicit_title),
                    word_count,
                    note.content_hash,
                    note.modified_at,
                    indexed_at,
                ),
            )
            conn.execute("DELETE FROM chunks WHERE note_path = ?", (note.path,))
            if chunks:
                chunk_ids = [chunk.id for chunk in chunks]
                placeholders = ",".join("?" for _ in chunk_ids)
                conn.execute(f"DELETE FROM chunks WHERE id IN ({placeholders})", chunk_ids)
            conn.executemany(
                """
                INSERT INTO chunks (id, note_path, chunk_index, text, heading, token_count, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.id,
                        chunk.note_path,
                        chunk.chunk_index,
                        chunk.text,
                        chunk.heading,
                        chunk.token_count,
                        chunk.content_hash,
                    )
                    for chunk in chunks
                ],
            )

    def delete_notes_not_in(self, current_paths: set[str]) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT path FROM notes").fetchall()
            existing = {str(row[0]) for row in rows}
            to_delete = sorted(existing - current_paths)
            if to_delete:
                placeholders = ",".join("?" for _ in to_delete)
                conn.execute(f"DELETE FROM notes WHERE path IN ({placeholders})", to_delete)
        return to_delete

    def recompute_backlinks(self) -> None:
        notes = self.list_notes()
        title_index: dict[str, str] = {}
        stem_index: dict[str, str] = {}
        for note in notes:
            path = str(note["path"])
            title_key = _normalize_link_target(str(note["title"]))
            stem_key = _normalize_link_target(Path(path).stem)
            title_index[title_key] = path
            stem_index[stem_key] = path

        backlink_counts = {str(note["path"]): 0 for note in notes}
        for note in notes:
            source_path = str(note["path"])
            links = json.loads(str(note["links_json"]))
            for link in links:
                target = _resolve_link_target(str(link), title_index, stem_index)
                if target is None or target == source_path:
                    continue
                backlink_counts[target] = backlink_counts.get(target, 0) + 1

        with self._connect() as conn:
            for path, count in backlink_counts.items():
                conn.execute(
                    "UPDATE notes SET backlinks_count = ? WHERE path = ?",
                    (count, path),
                )

    def count_notes(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM notes").fetchone()
        return int(row[0])

    def count_chunks(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()
        return int(row[0])

    def get_note(self, path: str) -> dict:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM notes WHERE path = ?", (path,)).fetchone()
        if row is None:
            raise KeyError(path)
        return dict(row)

    def list_notes(self) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM notes ORDER BY path").fetchall()
        return [dict(row) for row in rows]

    def list_chunks_for_paths(self, paths: list[str]) -> list[dict]:
        if not paths:
            return []
        placeholders = ",".join("?" for _ in paths)
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM chunks WHERE note_path IN ({placeholders}) ORDER BY note_path, chunk_index",
                paths,
            ).fetchall()
        return [dict(row) for row in rows]

    def list_all_chunks(self) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT c.*, n.title
                FROM chunks c
                JOIN notes n ON n.path = c.note_path
                ORDER BY c.note_path, c.chunk_index
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_chunk_ids_for_paths(self, paths: list[str]) -> list[str]:
        chunks = self.list_chunks_for_paths(paths)
        return [str(chunk["id"]) for chunk in chunks]

    def set_last_scan_summary(self, summary: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO meta (key, value_json) VALUES ('last_scan_summary', ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json
                """,
                (json.dumps(summary),),
            )

    def get_last_scan_summary(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value_json FROM meta WHERE key = 'last_scan_summary'",
            ).fetchone()
        if row is None:
            return None
        return json.loads(str(row[0]))

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def _normalize_link_target(value: str) -> str:
    stem = Path(value).stem
    return stem.casefold()


def _resolve_link_target(
    link: str,
    title_index: dict[str, str],
    stem_index: dict[str, str],
) -> str | None:
    normalized = _normalize_link_target(link)
    if normalized in title_index:
        return title_index[normalized]
    if normalized in stem_index:
        return stem_index[normalized]
    return None
