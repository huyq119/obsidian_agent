from __future__ import annotations

import math
import shutil
from pathlib import Path

from obsidian_agent.providers.base import RetrievedChunk


class InMemoryVectorStore:
    def __init__(self) -> None:
        self._records: dict[str, dict] = {}

    def reset(self) -> None:
        self._records.clear()

    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._records[str(chunk["id"])] = {
                "id": str(chunk["id"]),
                "text": str(chunk["text"]),
                "metadata": dict(chunk.get("metadata", {})),
                "embedding": embedding,
            }

    def delete_chunk_ids(self, ids: list[str]) -> None:
        for chunk_id in ids:
            self._records.pop(chunk_id, None)

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        scored: list[tuple[float, dict]] = []
        for record in self._records.values():
            score = _cosine_similarity(embedding, record["embedding"])
            scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        results: list[RetrievedChunk] = []
        for score, record in scored[:top_k]:
            metadata = record["metadata"]
            results.append(
                RetrievedChunk(
                    id=str(record["id"]),
                    text=str(record["text"]),
                    path=str(metadata.get("path", "")),
                    title=str(metadata.get("title", "")),
                    heading=str(metadata.get("heading", "")),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    score=score,
                ),
            )
        return results

    def count(self) -> int:
        return len(self._records)


class ChromaVectorStore:
    def __init__(self, persist_dir: Path, collection_name: str = "obsidian_chunks"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        import chromadb

        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        import chromadb

        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        if self.persist_dir.exists():
            shutil.rmtree(self.persist_dir, ignore_errors=True)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self.persist_dir))
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        ids = [str(chunk["id"]) for chunk in chunks]
        documents = [str(chunk["text"]) for chunk in chunks]
        metadatas = [dict(chunk.get("metadata", {})) for chunk in chunks]
        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def delete_chunk_ids(self, ids: list[str]) -> None:
        if not ids:
            return
        self._collection.delete(ids=ids)

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        if self.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=min(top_k, self.count()),
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        chunks: list[RetrievedChunk] = []
        for index, chunk_id in enumerate(ids):
            metadata = metadatas[index] or {}
            distance = float(distances[index]) if distances else 0.0
            chunks.append(
                RetrievedChunk(
                    id=str(chunk_id),
                    text=str(documents[index]),
                    path=str(metadata.get("path", "")),
                    title=str(metadata.get("title", "")),
                    heading=str(metadata.get("heading", "")),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    score=1.0 - distance,
                ),
            )
        return chunks

    def count(self) -> int:
        return int(self._collection.count())


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
