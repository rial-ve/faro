from app.providers.base import ChatMessage

EOT = "<|eot_id|>"
STOP_TOKENS = [EOT, "<|end_of_text|>"]


def render(messages: list[ChatMessage]) -> str:
    # No leading <|begin_of_text|>: the runtime tokenizer (llama.cpp and
    # ExecuTorch both) adds BOS itself. Including it here duplicates it.
    parts: list[str] = []
    for m in messages:
        parts.append(
            f"<|start_header_id|>{m.role}<|end_header_id|>\n\n{m.content}{EOT}"
        )
    parts.append("<|start_header_id|>assistant<|end_header_id|>\n\n")
    return "".join(parts)
