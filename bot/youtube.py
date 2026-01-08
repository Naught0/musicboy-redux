import asyncio
from collections.abc import Mapping
from typing import Any, TypedDict
from urllib import parse

import discord
import yt_dlp


class SongNotFound(Exception):
    pass


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "options": "-vn",
}


async def get_playlist_urls(url: str, *, loop: asyncio.AbstractEventLoop | None = None):
    """Retrieves a list of all URLs from a playlist without downloading/processing audio yet."""
    loop = loop or asyncio.get_event_loop()

    # Use specific options for quick metadata extraction
    meta_opts = YTDL_OPTIONS.copy()
    meta_opts["extract_flat"] = True

    with yt_dlp.YoutubeDL(meta_opts) as ydl:  # type: ignore
        data: Mapping[str, Any] = await loop.run_in_executor(
            None, lambda: ydl.extract_info(url, download=False)
        )

    if not data:
        raise SongNotFound(f"Couldn't find playlist data for {url}")

    if "entries" in data:
        # Return list of video URLs
        return [
            f"https://www.youtube.com/watch?v={entry['id']}"
            for entry in data["entries"]
            if entry
        ]

    return [url]  # Return as single-item list if it's just one video


class VideoInfo(TypedDict):
    title: str
    audio_url: str
    url: str


def parse_yt_url(url: str):
    res = parse.urlparse(url.strip("<>"))
    qs = parse.parse_qs(res.query)
    try:
        playlist_id = qs["list"][0]
        return f"https://www.youtube.com/playlist?list={playlist_id}"
    except (KeyError, IndexError):
        v = qs["v"][0]
        return f"https://www.youtube.com/watch?v={v}"


def get_video_info(url: str):
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:  # type: ignore
        data = ydl.extract_info(url, download=False)

    if not data:
        raise SongNotFound(f"Couldn't find data for {url}")
    if not (title := data.get("title")):
        raise SongNotFound(f"Couldn't find title for {url}")
    if not (ytdl_url := data.get("url")):
        raise SongNotFound(f"Couldn't find url for {url}")

    return VideoInfo(title=title, url=parse_yt_url(url), audio_url=ytdl_url)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source: discord.AudioSource, *, info: VideoInfo, volume=0.5):
        super().__init__(source, volume)
        self.title = info["title"]
        self.url = info["url"]

    @classmethod
    def from_video_info(cls, info: VideoInfo):
        return cls(
            discord.FFmpegPCMAudio(
                info["audio_url"],
                options=FFMPEG_OPTIONS["options"],
            ),
            info=info,
        )
