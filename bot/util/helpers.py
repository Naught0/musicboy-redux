from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


def chunk(seq: Sequence[T], n):
    return [seq[i : i + n] for i in range(0, len(seq), n)]


def seconds_to_time_str(seconds: int | float):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    hours_str = f"{hours:02.0f}:" if hours else ""
    return f"{hours_str}{minutes:02.0f}:{seconds:02.0f}"


def draw_progress_bar(progress: float, total: int, length: int = 20):
    percent = progress / total
    return (
        "█" * max(int(length * percent), 1)
        + "▓▒"
        + "░" * (length - int(length * percent))
    )
