from obsidian_agent.storage.memory_store import MemoryStore


def test_memory_store_add_list_and_search(tmp_path):
    store = MemoryStore(tmp_path / "memory.db")
    store.initialize()

    memory_id = store.add_memory("User prefers concise AI agent answers.")
    store.add_memory("Vault contains article drafts.")

    memories = store.list_memories()
    results = store.search_memories("concise answers", limit=5)

    assert memory_id == 1
    assert len(memories) == 2
    assert memories[0]["text"] == "Vault contains article drafts."
    assert results[0]["text"] == "User prefers concise AI agent answers."
    assert results[0]["score"] > 0
