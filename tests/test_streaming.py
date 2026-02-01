from app.services.stream import stream_chunks


def test_stream_chunks():
    chunks = list(stream_chunks(["a", "b"]))
    assert chunks == ["a", "b"]
