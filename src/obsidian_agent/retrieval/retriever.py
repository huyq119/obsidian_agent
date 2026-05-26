from __future__ import annotations

from obsidian_agent.providers.base import RetrievedChunk


class Retriever:
    def __init__(self, vector_store, embedding_provider, top_k: int):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.top_k = top_k

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        query_embedding = self.embedding_provider.embed_query(question)
        raw_results = self.vector_store.query(query_embedding, top_k=self.top_k)
        return _deduplicate_results(raw_results)


def _deduplicate_results(results: list[RetrievedChunk]) -> list[RetrievedChunk]:
    best_by_key: dict[tuple[str, int], RetrievedChunk] = {}
    for chunk in results:
        key = (chunk.path, chunk.chunk_index)
        current = best_by_key.get(key)
        if current is None or chunk.score > current.score:
            best_by_key[key] = chunk

    per_note_counts: dict[str, int] = {}
    deduped: list[RetrievedChunk] = []
    for chunk in sorted(best_by_key.values(), key=lambda item: item.score, reverse=True):
        note_count = per_note_counts.get(chunk.path, 0)
        if note_count >= 3:
            continue
        per_note_counts[chunk.path] = note_count + 1
        deduped.append(chunk)
    return deduped
