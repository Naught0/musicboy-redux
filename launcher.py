import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from bot.bot import MusicPlayer

logging.basicConfig(level=logging.INFO)


async def main():
    if not discord.opus.is_loaded:
        discord.opus.load_opus(os.environ["OPUS_PATH"])

    load_dotenv()
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    bot = commands.Bot(command_prefix=["!!", "-"], intents=intents)

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user} (ID: {bot.application_id})")

    await bot.add_cog(MusicPlayer(bot))
    await bot.start(os.environ["BOT_TOKEN"])


if __name__ == "__main__":
    asyncio.run(main())
