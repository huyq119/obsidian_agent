from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    path: str
    title: str
    heading: str
    chunk_index: int
    score: float


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("EmbeddingProvider.embed_texts")

    def embed_query(self, query: str) -> list[float]:
        raise NotImplementedError("EmbeddingProvider.embed_query")


class LLMProvider(Protocol):
    def answer(self, question: str, contexts: list[RetrievedChunk]) -> str:
        raise NotImplementedError("LLMProvider.answer")
