from typing import Iterable, Iterator


def stream_chunks(items: Iterable[str]) -> Iterator[str]:
    for item in items:
        yield item
