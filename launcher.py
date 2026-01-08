import asyncio
import logging
import os

import discord
from dotenv import load_dotenv

from bot.bot import MusicBotRedux

logging.basicConfig(
    level=logging.ERROR if os.getenv("ENV") == "production" else logging.INFO
)


async def main():
    load_dotenv()

    if not discord.opus.is_loaded():
        discord.opus.load_opus(os.environ["OPUS_PATH"])

    if not discord.opus.is_loaded():
        raise Exception("Failed to load opus")

    bot = MusicBotRedux()

    await bot.start(os.environ["BOT_TOKEN"])


if __name__ == "__main__":
    asyncio.run(main())
