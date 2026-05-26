from __future__ import annotations

import os

from openai import OpenAI


class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key_env: str,
        embedding_model: str,
        dimensions: int = 1536,
    ):
        self.embedding_model = embedding_model
        self.dimensions = dimensions
        self.client = OpenAI(
            api_key=_require_api_key(api_key_env),
            base_url=base_url,
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def _require_api_key(env_name: str) -> str:
    api_key = os.environ.get(env_name)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {env_name}")
    return api_key
