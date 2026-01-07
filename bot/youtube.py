import asyncio

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

    with yt_dlp.YoutubeDL(meta_opts) as ydl:
        data = await loop.run_in_executor(
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


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            data = await loop.run_in_executor(
                None, lambda: ydl.extract_info(url, download=not stream)
            )

        if data is None:
            raise SongNotFound(f"Couldn't find data for {url}")

        if "entries" in data:
            data = data["entries"][0]

        filename = data["url"] if stream else ydl.prepare_filename(data)
        return cls(
            discord.FFmpegPCMAudio(
                filename,
                options=FFMPEG_OPTIONS["options"],
            ),
            data=data,
        )
