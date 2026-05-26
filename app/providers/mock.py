from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.providers.base import ChatMessage, GenerationResult, TokenChunk


class MockProvider:
    name = "mock"
    model_id = "mock-1"
    quantization = "none"

    def __init__(self, reply: str = "ok") -> None:
        self._reply = reply

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> GenerationResult:
        text = self._reply[:max_tokens]
        return GenerationResult(
            text=text,
            prompt_tokens=sum(len(m.content) for m in messages),
            completion_tokens=len(text),
            stop_reason="length" if len(self._reply) > max_tokens else "stop",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> AsyncIterator[TokenChunk]:
        budget = min(max_tokens, len(self._reply))
        for ch in self._reply[:budget]:
            yield TokenChunk(delta=ch)
            await asyncio.sleep(0)
        yield TokenChunk(
            delta="",
            done=True,
            stop_reason="length" if len(self._reply) > budget else "stop",
        )
