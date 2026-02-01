from app.services.stream import sse_chat_chunks, stream_chunks


def test_stream_chunks():
    chunks = list(stream_chunks(["a", "b"]))
    assert chunks == ["a", "b"]


def test_sse_chat_chunks_contains_done():
    chunks = list(sse_chat_chunks("hi", "gemini-2.5-pro"))
    assert chunks[-1] == "data: [DONE]\n\n"
