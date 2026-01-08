from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def chunk(seq: Sequence[T], n):
    return [seq[i : i + n] for i in range(0, len(seq), n)]
