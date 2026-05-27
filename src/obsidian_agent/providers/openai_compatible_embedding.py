from __future__ import annotations

import os
from urllib.parse import urlparse

import httpx
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
        self._api_key = _require_api_key(api_key_env)
        self._base_url = base_url
        self._endpoint = _embeddings_endpoint(base_url)
        self.client = None if _is_bigmodel_url(base_url) else OpenAI(
            api_key=self._api_key,
            base_url=_normalize_base_url(base_url),
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.client is None:
            return _bigmodel_embed(
                endpoint=self._endpoint,
                api_key=self._api_key,
                model=self.embedding_model,
                input_texts=texts,
                dimensions=self.dimensions,
            )
        response = self.client.embeddings.create(model=self.embedding_model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def _require_api_key(env_name: str) -> str:
    api_key = os.environ.get(env_name)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {env_name}")
    return api_key


def _normalize_base_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/embeddings"):
        return normalized[: -len("/embeddings")]
    return normalized


def _embeddings_endpoint(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/embeddings"):
        return normalized
    return normalized + "/embeddings"


def _is_bigmodel_url(base_url: str) -> bool:
    try:
        parsed = urlparse(base_url)
    except Exception:
        return False
    return parsed.hostname == "open.bigmodel.cn"


def _bigmodel_embed(
    *,
    endpoint: str,
    api_key: str,
    model: str,
    input_texts: list[str],
    dimensions: int,
) -> list[list[float]]:
    payload: dict = {"model": model, "input": input_texts}
    if dimensions:
        payload["dimensions"] = dimensions

    response = httpx.post(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60.0,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = response.text
        raise RuntimeError(f"BigModel embeddings request failed: {exc} body={body}") from exc
    data = response.json()
    items = data.get("data") or []
    if not isinstance(items, list):
        raise RuntimeError("Invalid embeddings response: missing data list")
    items_sorted = sorted(items, key=lambda item: int(item.get("index", 0)))
    embeddings: list[list[float]] = []
    for item in items_sorted:
        embedding = item.get("embedding")
        if not isinstance(embedding, list):
            raise RuntimeError("Invalid embeddings response: embedding is not a list")
        embeddings.append([float(x) for x in embedding])
    return embeddings
