import asyncio
from collections.abc import Iterable, Sequence

import discord

from bot.player import PlayerState
from bot.util.helpers import chunk, draw_progress_bar, seconds_to_time_str
from bot.youtube import VideoInfo


def make_simple_embed(title: str, url: str = ""):
    return discord.Embed(
        title=title,
        url=url,
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )


def make_np_embed(state: PlayerState, progress: float | None = None):
    info = state.current_track
    em = discord.Embed(
        title=f"▶️ {info.title}",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
        url=info.url,
    )
    if progress:
        prog_str = (
            f"{seconds_to_time_str(progress)}/{seconds_to_time_str(info.duration)}"
        )
        em.description = (
            f"```{draw_progress_bar(progress, info.duration)}\n{prog_str:>23}```"
        )

    return em


COLUMN_SIZE = 10


def queue_to_numbered_list_str(queue: Sequence[VideoInfo], offset=0):
    return "\n".join(
        f"{i + 1 + offset}. {source.title}" for i, source in enumerate(queue)
    )


def make_queue_embeds(state: PlayerState):
    has_playlist = bool(state.playlist)
    np, *rest = state.queue[state.current_index :]
    pages = chunk(rest, COLUMN_SIZE * 2)
    if not has_playlist:
        return [
            discord.Embed(
                title="❌ Nothing Queued",
                color=discord.Color.brand_red(),
                timestamp=discord.utils.utcnow(),
                url=np.url,
            )
        ]

    embeds = []
    if pages:
        for page_idx, page in enumerate(pages):
            em = make_np_embed(state)
            columns = chunk(page, COLUMN_SIZE)
            for col_idx, col in enumerate(columns):
                em.add_field(
                    name="\u200b",
                    value=queue_to_numbered_list_str(
                        col, offset=col_idx * COLUMN_SIZE + (page_idx * COLUMN_SIZE * 2)
                    ),
                )
            em.set_footer(text=f"Page {page_idx + 1}/{len(pages)}")
            embeds.append(em)
    else:
        em = make_np_embed(state)
        em.add_field(name="Up Next", value="✨ Nothing ✨")
        embeds.append(em)

    return embeds


PREV_EMOJI = "⬅️"
NEXT_EMOJI = "➡️"
NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


class EmbedPaginator:
    def __init__(
        self,
        embeds: Iterable[discord.Embed],
        message: discord.Message,
        timeout: float = 60.0,
    ):
        self.embeds = list(embeds)
        self.idx = 0
        self.msg = message
        self.timeout = timeout
        self._task: asyncio.Task | None = None

    async def _monitor_and_cleanup(self):
        """Monitor reactions then clean up"""
        await self._monitor_reactions()
        try:
            await self.msg.clear_reactions()
        except (discord.Forbidden, discord.NotFound):
            pass

    async def stop(self):
        """Manually stop the paginator early"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def start(self):
        """Add reactions and start monitoring. Returns when timeout or stopped."""
        await self.msg.add_reaction(PREV_EMOJI)
        await self.msg.add_reaction(NEXT_EMOJI)

        for i in range(min(len(self.embeds), 10)):
            await self.msg.add_reaction(NUMBER_EMOJIS[i])

        await self._monitor_and_cleanup()

    async def next(self):
        self.idx = (self.idx + 1) % len(self.embeds)
        await self.msg.edit(embed=self.embeds[self.idx])

    async def prev(self):
        self.idx = (self.idx - 1) % len(self.embeds)
        await self.msg.edit(embed=self.embeds[self.idx])

    async def goto(self, idx: int):
        self.idx = idx % len(self.embeds)
        await self.msg.edit(embed=self.embeds[self.idx])

    async def _monitor_reactions(self):
        """Monitor reactions and handle pagination"""
        bot = self.msg.channel._state._get_client()

        def check(reaction: discord.Reaction, user: discord.User):
            return (
                reaction.message.id == self.msg.id
                and not user.bot
                and str(reaction.emoji) in self._get_valid_emojis()
            )

        while True:
            try:
                reaction, user = await bot.wait_for(
                    "reaction_add", timeout=self.timeout, check=check
                )

                # Handle the reaction
                emoji = str(reaction.emoji)

                if emoji == PREV_EMOJI:
                    await self.prev()
                elif emoji == NEXT_EMOJI:
                    await self.next()
                elif emoji in NUMBER_EMOJIS:
                    page_num = NUMBER_EMOJIS.index(emoji)
                    if page_num < len(self.embeds):
                        await self.goto(page_num)

                # Remove the user's reaction
                try:
                    await reaction.remove(user)
                except (discord.Forbidden, discord.NotFound):
                    pass

            except asyncio.TimeoutError:
                # Timeout reached, stop monitoring
                break

    def _get_valid_emojis(self):
        valid = [PREV_EMOJI, NEXT_EMOJI]
        valid.extend(NUMBER_EMOJIS[: min(len(self.embeds), 10)])
        return valid
