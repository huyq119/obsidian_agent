from __future__ import annotations

import hashlib
import math
import struct

from obsidian_agent.providers.base import LLMProvider, RetrievedChunk


class FakeEmbeddingProvider:
    def __init__(self, dimensions: int = 1536):
        self.dimensions = dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._embed_one(query)

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        while len(values) < self.dimensions:
            for index in range(0, len(digest), 4):
                chunk = digest[index : index + 4]
                if len(chunk) < 4:
                    chunk = chunk.ljust(4, b"\0")
                value = struct.unpack("!I", chunk)[0]
                values.append((value % 1000) / 1000.0)
                if len(values) >= self.dimensions:
                    break
            digest = hashlib.sha256(digest).digest()
        return values


class FakeLLMProvider:
    def answer(self, question: str, contexts: list[RetrievedChunk]) -> str:
        del contexts
        return f"Fake answer for: {question}"
