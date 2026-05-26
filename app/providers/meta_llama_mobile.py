"""Llama 3.2 provider configured to mirror on-device constraints.

Intentionally not a multi-vendor router. Same chat template, context
window, sampling defaults, and stop tokens we will ship on the phone, so
prompts and evals transfer 1:1 to the ExecuTorch provider later.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from app.prompts.llama3_template import STOP_TOKENS, render
from app.providers.base import ChatMessage, GenerationResult, TokenChunk


class MetaLlamaMobileProvider:
    name = "meta-llama-mobile"

    def __init__(
        self,
        model_path: str | Path,
        *,
        model_id: str = "meta-llama/Llama-3.2-1B-Instruct",
        quantization: str = "Q4_K_M",
        n_ctx: int = 4096,
    ) -> None:
        self.model_id = model_id
        self.quantization = quantization
        self._model_path = Path(model_path)
        self._n_ctx = n_ctx
        self._llm: Any = None

    def _load(self) -> Any:
        if self._llm is not None:
            return self._llm
        from llama_cpp import Llama

        self._llm = Llama(
            model_path=str(self._model_path),
            n_ctx=self._n_ctx,
            verbose=False,
        )
        return self._llm

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> GenerationResult:
        prompt = render(messages)
        stop_tokens = (stop or []) + STOP_TOKENS
        llm = self._load()
        result = await asyncio.to_thread(
            llm,
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop_tokens,
        )
        choice = result["choices"][0]
        usage = result["usage"]
        return GenerationResult(
            text=choice["text"],
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            stop_reason="stop" if choice["finish_reason"] == "stop" else "length",
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        max_tokens: int = 256,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> AsyncIterator[TokenChunk]:
        prompt = render(messages)
        stop_tokens = (stop or []) + STOP_TOKENS
        llm = self._load()
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[TokenChunk | None] = asyncio.Queue()

        def produce() -> None:
            finish: str | None = None
            for chunk in llm(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop_tokens,
                stream=True,
            ):
                choice = chunk["choices"][0]
                delta = choice.get("text", "")
                finish = choice.get("finish_reason") or finish
                if delta:
                    asyncio.run_coroutine_threadsafe(
                        queue.put(TokenChunk(delta=delta)), loop
                    )
            reason = "stop" if finish == "stop" else "length"
            asyncio.run_coroutine_threadsafe(
                queue.put(TokenChunk(delta="", done=True, stop_reason=reason)), loop
            )
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

        producer = asyncio.create_task(asyncio.to_thread(produce))
        try:
            while True:
                item = await queue.get()
                if item is None:
                    return
                yield item
        finally:
            await producer
