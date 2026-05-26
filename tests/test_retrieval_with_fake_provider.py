from pathlib import Path

from obsidian_agent.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from obsidian_agent.providers.openai_compatible_embedding import _normalize_base_url
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
