from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.providers.base import ChatMessage, GenerationResult, LLMProvider


router = APIRouter()


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    max_tokens: int = Field(256, ge=1, le=4096)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    stop: list[str] | None = None


def _provider(request: Request) -> LLMProvider:
    return request.app.state.provider


@router.post("/chat/completions", response_model=GenerationResult)
async def chat_completions(body: ChatRequest, request: Request) -> GenerationResult:
    provider = _provider(request)
    return await provider.generate(
        body.messages,
        max_tokens=body.max_tokens,
        temperature=body.temperature,
        stop=body.stop,
    )


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, request: Request) -> EventSourceResponse:
    provider = _provider(request)

    async def events():
        async for chunk in provider.stream(
            body.messages,
            max_tokens=body.max_tokens,
            temperature=body.temperature,
            stop=body.stop,
        ):
            yield {"data": chunk.model_dump_json()}

    return EventSourceResponse(events())
