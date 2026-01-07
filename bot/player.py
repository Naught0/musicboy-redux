import random
from collections.abc import Iterable
from typing import Optional


class PlayerState:
    """Manages the playlist state for a single guild."""

    def __init__(self):
        self.playlist: list[str] = []
        self._queue: list[str] = []
        self.current_index: int = -1
        self.is_shuffled: bool = False

    @property
    def queue(self):
        return self._queue.copy()

    def add_tracks(self, urls: Iterable[str]):
        for url in urls:
            self.add_track(url)

    def add_track(self, url: str):
        self.playlist.append(url)
        self._queue.append(url)

    def get_next(self) -> Optional[str]:
        print("Advancing index from ", self.current_index, "to", self.current_index + 1)
        if self.current_index + 1 < len(self._queue):
            self.current_index += 1
            return self._queue[self.current_index]
        return None

    def get_previous(self) -> Optional[str]:
        if self.current_index > 0:
            self.current_index -= 1
            return self._queue[self.current_index]
        return None

    def shuffle_toggle(self):
        self.is_shuffled = not self.is_shuffled
        if self.is_shuffled:
            # Keep current song at index 0, shuffle the rest
            current = (
                [self._queue[self.current_index]] if self.current_index != -1 else []
            )
            others = [t for i, t in enumerate(self._queue) if i != self.current_index]
            random.shuffle(others)
            self._queue = current + others
            self.current_index = 0 if current else -1
        else:
            # Revert to original playlist order
            current_track = (
                self._queue[self.current_index] if self.current_index != -1 else None
            )
            self._queue = self.playlist.copy()
            if current_track:
                self.current_index = self._queue.index(current_track)
