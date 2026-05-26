from __future__ import annotations

import os

from openai import OpenAI

from obsidian_agent.config import LLMConfig
from obsidian_agent.providers.base import RetrievedChunk
from obsidian_agent.retrieval.qa import SYSTEM_PROMPT


class DeepSeekLLMProvider:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = OpenAI(
            api_key=_require_api_key(config.api_key_env),
            base_url=config.base_url,
        )

    def answer(self, question: str, contexts: list[RetrievedChunk]) -> str:
        context_text = _format_contexts(contexts)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"问题:\n{question}\n\n笔记片段:\n{context_text}",
            },
        ]
        kwargs: dict = {
            "model": self.config.chat_model,
            "messages": messages,
        }
        if self.config.thinking:
            kwargs["extra_body"] = {"thinking": {"type": "enabled"}}
            kwargs["reasoning_effort"] = self.config.reasoning_effort
        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def _format_contexts(contexts: list[RetrievedChunk]) -> str:
    blocks: list[str] = []
    for chunk in contexts:
        blocks.append(
            f"[{chunk.path} | {chunk.heading}]\n{chunk.text}",
        )
    return "\n\n".join(blocks)


def _require_api_key(env_name: str) -> str:
    api_key = os.environ.get(env_name)
    if not api_key:
        raise RuntimeError(f"Missing API key environment variable: {env_name}")
    return api_key
