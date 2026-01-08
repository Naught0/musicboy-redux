import asyncio
import random
from collections.abc import Iterable

from bot.util.cache import VideoInfoCache
from bot.youtube import VideoInfo, get_video_info


class PlayerState:
    """Manages the playlist state for a single guild."""

    def __init__(self, cache: VideoInfoCache):
        self.cache = cache
        self.playlist: list[VideoInfo] = []
        self.queue: list[VideoInfo] = []
        self.current_index: int = -1
        self.is_shuffled: bool = False
        self.loop: asyncio.AbstractEventLoop | None = None

    @property
    def current_track(self):
        return self.queue[self.current_index]

    async def add_tracks(self, urls: Iterable[str]):
        for url in urls:
            await self.add_track(url)

    async def add_track(self, url: str):
        if not self.loop:
            self.loop = asyncio.get_event_loop()

        track = await self.cache.get(url)
        if track is None:
            track = await self.loop.run_in_executor(None, get_video_info, url)
            await self.cache.set(track)

        self.playlist.append(track)
        self.queue.append(track)

    def get_next(self):
        if self.current_index + 1 < len(self.queue):
            self.current_index += 1
            return self.current_track
        return None

    def get_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            return self.current_track
        return None

    def skip_to(self, index: int):
        idx = index % len(self.queue)
        self.current_index = idx

    def move(self, idx: int, to_idx: int):
        if to_idx == 0:
            to_idx = 1
        if idx == 0:
            raise ValueError("Cannot move current track")

        self.queue.insert(to_idx, self.queue.pop(idx))

    def shuffle_toggle(self):
        self.is_shuffled = not self.is_shuffled
        if self.is_shuffled:
            current = (
                [self.queue[self.current_index]] if self.current_index != -1 else []
            )
            current = self.queue.pop(self.current_index)
            others = [t for t in self.queue]
            random.shuffle(others)
            self.queue = [current, *others]
            self.current_index = 0 if current else -1
        else:
            # Revert to original playlist order
            current_track = (
                self.queue[self.current_index] if self.current_index != -1 else None
            )
            self.queue = self.playlist.copy()
            if current_track:
                self.current_index = self.queue.index(current_track)
