from __future__ import annotations

from obsidian_agent.providers.base import LLMProvider, RetrievedChunk

SYSTEM_PROMPT = """你是一个本地 Obsidian 知识库助手。
只能根据给定的笔记片段回答。
如果上下文不足，请明确说明无法从当前知识库判断。
回答后列出使用到的来源文件路径。"""


def answer_question(
    question: str,
    contexts: list[RetrievedChunk],
    llm_provider: LLMProvider,
) -> tuple[str, list[str]]:
    answer = llm_provider.answer(question, contexts)
    sources = sorted({chunk.path for chunk in contexts})
    return answer, sources
