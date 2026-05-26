import pytest

from app.prompts.llama3_template import render
from app.providers.base import ChatMessage
from app.providers.mock import MockProvider


async def test_mock_generate_returns_reply():
    p = MockProvider(reply="hello")
    out = await p.generate([ChatMessage(role="user", content="hi")])
    assert out.text == "hello"
    assert out.stop_reason == "stop"
    assert out.completion_tokens == 5


async def test_mock_generate_truncates_at_max_tokens():
    p = MockProvider(reply="hello world")
    out = await p.generate([ChatMessage(role="user", content="hi")], max_tokens=5)
    assert out.text == "hello"
    assert out.stop_reason == "length"


async def test_mock_stream_emits_characters_then_done():
    p = MockProvider(reply="hi")
    chunks = [c async for c in p.stream([ChatMessage(role="user", content="hi")])]
    assert "".join(c.delta for c in chunks) == "hi"
    assert chunks[-1].done is True
    assert chunks[-1].stop_reason == "stop"


def test_llama3_template_round_trip():
    rendered = render(
        [
            ChatMessage(role="system", content="be brief"),
            ChatMessage(role="user", content="hi"),
        ]
    )
    assert rendered.startswith("<|start_header_id|>system<|end_header_id|>")
    assert "<|begin_of_text|>" not in rendered
    assert "<|start_header_id|>system<|end_header_id|>\n\nbe brief<|eot_id|>" in rendered
    assert "<|start_header_id|>user<|end_header_id|>\n\nhi<|eot_id|>" in rendered
    assert rendered.endswith("<|start_header_id|>assistant<|end_header_id|>\n\n")
