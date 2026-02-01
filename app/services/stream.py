import json
from typing import Iterable, Iterator


def stream_chunks(items: Iterable[str]) -> Iterator[str]:
    for item in items:
        yield item


def sse_chat_chunks(content: str, model: str) -> Iterator[str]:
    header = {
        "id": "chatcmpl-stream",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(header)}\n\n"
    for token in stream_chunks([content]):
        chunk = {
            "id": "chatcmpl-stream",
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}],
        }
        yield f"data: {json.dumps(chunk)}\n\n"
    tail = {
        "id": "chatcmpl-stream",
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(tail)}\n\n"
    yield "data: [DONE]\n\n"
