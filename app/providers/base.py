from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel


Role = Literal["system", "user", "assistant"]
StopReason = Literal["stop", "length"]


class ChatMessage(BaseModel):
    role: Role
    content: str


class GenerationResult(BaseModel):
    text: str
    prompt_tokens: int
    completion_tokens: int
    stop_reason: StopReason


class TokenChunk(BaseModel):
    delta: str
    done: bool = False
    stop_reason: StopReason | None = None


@runtime_checkable
class LLMProvider(Protocol):
    name: str
    model_id: str
    quantization: str

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> GenerationResult: ...

    def stream(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> AsyncIterator[TokenChunk]: ...
