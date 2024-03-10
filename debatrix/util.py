from collections.abc import Iterator
from typing import TypeVar

from tiktoken import Encoding, get_encoding

T = TypeVar("T")


def tokenize(text: str, /, *, batch_size: int = 1) -> Iterator[str]:
    enc: Encoding = get_encoding("gpt2")
    tokens: list[int] = enc.encode(text)
    start: int = 0

    for end in range(1, len(tokens) + 1):
        try:
            if start + batch_size <= end:
                current: str = enc.decode(tokens[start:end], errors="strict")
                yield current
                start = end
        except UnicodeDecodeError:
            pass

    if start != len(tokens):
        yield enc.decode(tokens[start:], errors="strict")


def sanitize(raw: T | None, default: T) -> T:
    return default if raw is None else raw
