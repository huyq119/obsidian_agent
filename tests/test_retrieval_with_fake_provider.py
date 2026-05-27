from pathlib import Path

from obsidian_agent.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from obsidian_agent.providers.openai_compatible_embedding import (
    OpenAICompatibleEmbeddingProvider,
    _embeddings_endpoint,
    _normalize_base_url,
)
from obsidian_agent.storage.vector_store import InMemoryVectorStore


def test_fake_embedding_is_deterministic():
    provider = FakeEmbeddingProvider(dimensions=8)

    assert provider.embed_query("agent") == provider.embed_query("agent")
    assert len(provider.embed_query("agent")) == 8


def test_in_memory_vector_store_returns_sources():
    embeddings = FakeEmbeddingProvider(dimensions=8)
    store = InMemoryVectorStore()
    store.upsert_chunks(
        [
            {
                "id": "c1",
                "text": "AI agent planning notes",
                "metadata": {"path": "Project.md", "title": "Project", "heading": "Plan", "chunk_index": 0},
            }
        ],
        embeddings.embed_texts(["AI agent planning notes"]),
    )

    results = store.query(embeddings.embed_query("agent planning"), top_k=1)

    assert results[0].text == "AI agent planning notes"
    assert results[0].path == "Project.md"


def test_fake_llm_mentions_context_sources():
    llm = FakeLLMProvider()
    answer = llm.answer("What about agents?", [])

    assert "Fake answer" in answer


def test_openai_compatible_embedding_accepts_embeddings_endpoint():
    base_url = _normalize_base_url("https://open.bigmodel.cn/api/paas/v4/embeddings")

    assert base_url == "https://open.bigmodel.cn/api/paas/v4"


def test_openai_compatible_embedding_builds_bigmodel_endpoint():
    endpoint = _embeddings_endpoint("https://open.bigmodel.cn/api/paas/v4")

    assert endpoint == "https://open.bigmodel.cn/api/paas/v4/embeddings"


def test_bigmodel_embedding_provider_uses_httpx_endpoint(monkeypatch):
    requests = []

    class FakeResponse:
        text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {"index": 1, "embedding": [0.3, 0.4]},
                    {"index": 0, "embedding": [0.1, 0.2]},
                ]
            }

    def fake_post(endpoint, *, headers, json, timeout):
        requests.append(
            {
                "endpoint": endpoint,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse()

    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")
    monkeypatch.setattr("obsidian_agent.providers.openai_compatible_embedding.httpx.post", fake_post)

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://open.bigmodel.cn/api/paas/v4/embeddings",
        api_key_env="EMBEDDING_API_KEY",
        embedding_model="embedding-3",
        dimensions=2048,
    )

    embeddings = provider.embed_texts(["alpha", "beta"])

    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert requests == [
        {
            "endpoint": "https://open.bigmodel.cn/api/paas/v4/embeddings",
            "headers": {
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
            },
            "json": {
                "model": "embedding-3",
                "input": ["alpha", "beta"],
                "dimensions": 2048,
            },
            "timeout": 60.0,
        }
    ]
