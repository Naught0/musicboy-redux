from collections import defaultdict

import discord
from discord.ext import commands

from bot.bot import MusicBotRedux
from bot.player import PlayerState
from bot.util.const import DELETE_AFTER
from bot.util.embed import (
    EmbedPaginator,
    make_np_embed,
    make_queue_embeds,
    make_simple_embed,
)
from bot.youtube import YTDLSource, get_playlist_urls, parse_yt_url


class MusicPlayer(commands.Cog):
    def __init__(self, bot: MusicBotRedux):
        self.bot = bot
        self._states: dict[int, PlayerState] = defaultdict(
            lambda: PlayerState(bot.cache)
        )
        self._volume = defaultdict(lambda: 0.5)
        self._tasks = set()

    def get_state(self, guild_id: int) -> PlayerState:
        return self._states[guild_id]

    async def play_next(self, ctx: commands.Context):
        if ctx.guild is None:
            return

        state = self.get_state(ctx.guild.id)
        info = state.get_next()
        if not isinstance(ctx.voice_client, discord.VoiceClient):
            return await ctx.message.add_reaction("❌")

        if info:
            ctx.voice_client.play(
                YTDLSource.from_video_info(info, volume=self._volume[ctx.guild.id]),
                after=lambda _: self.bot.loop.create_task(self.play_next(ctx)),
            )
            if isinstance(ctx.voice_client.source, YTDLSource):
                await ctx.send(
                    embed=make_np_embed(state, ctx.voice_client.source.progress_seconds)
                )
            else:
                print("Not YTDLSource, got", type(ctx.voice_client.source))

        else:
            await ctx.send(
                embed=make_simple_embed("⏹️ Queue Finished"), delete_after=DELETE_AFTER
            )
            await ctx.voice_client.disconnect()

    @commands.command(aliases=["np"])
    async def now_playing(self, ctx):
        state = self.get_state(ctx.guild.id)
        if state.playlist:
            await ctx.send(
                embed=make_np_embed(state, ctx.voice_client.source.progress_seconds)
            )
        else:
            await ctx.send(
                embed=make_simple_embed("⏹️ Queue Empty"), delete_after=DELETE_AFTER
            )

    @commands.command(aliases=["leave"])
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            await ctx.message.add_reaction("❌")

    @commands.command(aliases=["p", "resume"])
    async def play(self, ctx, *, url: str | None = None):
        if not ctx.guild:
            return
        if not ctx.voice_client:
            await self.join(ctx)

        state = self.get_state(ctx.guild.id)
        if url is None:
            if not state.playlist:
                await ctx.send(
                    embed=make_simple_embed("⏹️ Queue Empty"), delete_after=DELETE_AFTER
                )
                return await ctx.message.add_reaction("❌")

            if ctx.voice_client.is_paused():
                ctx.voice_client.resume()
            elif not ctx.voice_client.is_playing():
                await self.play_next(ctx)
            else:
                print("Client is neither paused nor playing")
            return

        url = parse_yt_url(url)
        await ctx.message.add_reaction("🔄")
        first, *rest = await get_playlist_urls(url)
        await state.add_track(first)

        if rest:
            task = self.bot.loop.create_task(state.add_tracks(rest))
            task.add_done_callback(self._tasks.discard)
            self._tasks.add(task)

        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

        await ctx.message.clear_reactions()
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.message.add_reaction("⏸️")

    @commands.command(aliases=["next"])
    async def skip(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()
            await ctx.message.add_reaction("✅")

    @commands.command()
    async def shuffle(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.shuffle_toggle()
        if state.is_shuffled:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("↩️")

    @commands.command(aliases=["q"])
    async def queue(self, ctx, *, url: str | None = None):
        state = self.get_state(ctx.guild.id)
        if not state.playlist:
            return await ctx.message.add_reaction("❌")

        if url:
            return await self.play(ctx, url=url)

        embeds = make_queue_embeds(state)
        message = await ctx.send(embed=embeds[0])
        if len(embeds) > 1:
            paginator = EmbedPaginator(embeds=embeds, message=message)
            await paginator.start()

    @commands.command(aliases=["v", "vol"])
    async def volume(self, ctx: commands.Context, volume: int | None = None):
        if not ctx.guild:
            return

        if volume is None:
            return await ctx.send(
                embed=make_simple_embed(f"🔊 {self._volume[ctx.guild.id] * 100:.0f}%")
            )

        if volume < 0 or volume > 100:
            await ctx.message.add_reaction("❌")
            return await ctx.send(
                embed=make_simple_embed("Invalid Volume (must be 0 - 100)"),
                delete_after=DELETE_AFTER,
            )

        if isinstance(ctx.voice_client, discord.VoiceClient):
            if isinstance(ctx.voice_client.source, YTDLSource):
                ctx.voice_client.source.volume = volume / 100

        self._volume[ctx.guild.id] = volume / 100
        await ctx.message.add_reaction("✅")

    @commands.command(aliases=["mv"])
    async def move(self, ctx, idx: int, to_idx: int):
        state = self.get_state(ctx.guild.id)
        try:
            state.move(idx, to_idx)
        except ValueError:
            await ctx.message.add_reaction("❌")
        else:
            await ctx.message.add_reaction("✅")


async def setup(bot):
    await bot.add_cog(MusicPlayer(bot))
