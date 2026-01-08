import os

import discord
from discord.ext import commands
from redis.asyncio import Redis

from bot.util.cache import VideoInfoCache

ENABLED_COGS = ("music_player",)


class MusicBotRedux(commands.Bot):
    cache: VideoInfoCache
    redis: Redis

    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(*args, intents=intents, command_prefix=["-", "!!"], **kwargs)

    async def setup_hook(self):
        self.redis = Redis.from_url(os.getenv("REDIS_URL") or "redis://localhost:6379")
        self.cache = VideoInfoCache(self.redis)
        print("✅ Cache initialized")

        for cog in ENABLED_COGS:
            await self.load_extension(f"bot.cogs.{cog}")
            print("✅ Loaded cog", cog)

    async def on_ready(self):
        print(
            f"ℹ️ Logged in as {self.user} (ID:{self.application_id}) 🕐 {discord.utils.utcnow()}"
        )
