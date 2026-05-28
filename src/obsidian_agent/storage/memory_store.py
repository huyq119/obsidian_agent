from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def add_memory(self, text: str) -> int:
        created_at = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO memories (text, created_at) VALUES (?, ?)",
                (text, created_at),
            )
            return int(cursor.lastrowid)

    def list_memories(self, *, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def search_memories(self, query: str, *, limit: int = 5) -> list[dict]:
        terms = _query_terms(query)
        memories = self.list_memories(limit=1000)
        if not terms:
            return memories[:limit]

        scored: list[dict] = []
        for memory in memories:
            text = str(memory["text"]).casefold()
            score = sum(text.count(term) for term in terms)
            if score <= 0:
                continue
            scored.append({**memory, "score": score})
        scored.sort(key=lambda item: (int(item["score"]), int(item["id"])), reverse=True)
        return scored[:limit]

    def delete_memory(self, memory_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)


def _query_terms(query: str) -> list[str]:
    return [term.casefold() for term in re.findall(r"\w+", query) if term.strip()]
