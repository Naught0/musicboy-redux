from dataclasses import dataclass

import discord
from discord.ext import commands

from bot.player import PlayerState
from bot.util.const import DELETE_AFTER
from bot.util.embed import make_np_embed, make_queue_embed, make_simple_embed
from bot.youtube import YTDLSource, get_playlist_urls, parse_yt_url


@dataclass
class State:
    player: PlayerState
    last_np_message: discord.Message | None


class MusicPlayer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.states: dict[int, State] = {}
        self.tasks = set()

    def get_state(self, guild_id: int) -> State:
        if guild_id not in self.states:
            self.states[guild_id] = State(PlayerState(), None)
        return self.states[guild_id]

    async def play_next(self, ctx):
        state = self.get_state(ctx.guild.id)
        video = state.player.get_next()

        if video:
            ctx.voice_client.play(
                YTDLSource.from_video_info(video),
                after=lambda e: self.bot.loop.create_task(self.play_next(ctx)),
            )
            if state.last_np_message:
                await state.last_np_message.delete()
            msg = await ctx.send(embed=make_np_embed(video))
            state.last_np_message = msg
        else:
            await ctx.send(
                embed=make_simple_embed("⏹️ Queue Finished"), delete_after=DELETE_AFTER
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
    async def play(self, ctx: commands.Context, *, url: str | None = None):
        if not ctx.guild:
            return
        if not ctx.voice_client:
            await self.join(ctx)

        voice_client: discord.VoiceClient = ctx.voice_client  # type: ignore

        state = self.get_state(ctx.guild.id)
        if url is None:
            if not state.player.playlist:
                await ctx.send(
                    embed=make_simple_embed("⏹️ Queue Empty"), delete_after=DELETE_AFTER
                )
                return await ctx.message.add_reaction("❌")
            if voice_client.is_paused():
                voice_client.resume()
            return

        url = parse_yt_url(url)
        await ctx.message.add_reaction("🔄")
        first, *rest = await get_playlist_urls(url)
        await state.player.add_track(first)

        if rest:
            task = self.bot.loop.create_task(state.player.add_tracks(rest))
            task.add_done_callback(self.tasks.discard)
            self.tasks.add(task)

        if not voice_client.is_playing():
            await self.play_next(ctx)
        else:
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
        state.player.shuffle_toggle()
        await ctx.message.add_reaction("✅")

    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        state = self.get_state(ctx.guild.id)
        if not state.player.playlist:
            return await ctx.message.add_reaction("❌")

        await ctx.send(embed=make_queue_embed(state.player))

    @commands.command(aliases=["v", "vol"])
    async def volume(self, ctx: commands.Context, volume: int | None = None):
        if not isinstance(ctx.voice_client, discord.VoiceClient):
            return await ctx.message.add_reaction("❌")
        if not isinstance(ctx.voice_client.source, discord.PCMVolumeTransformer):
            return await ctx.message.add_reaction("❌")

        if volume is None:
            return await ctx.send(
                embed=make_simple_embed(
                    f"🔊 {int(ctx.voice_client.source.volume * 100)}%"
                ),
                delete_after=DELETE_AFTER,
            )

        if volume < 0 or volume > 100:
            await ctx.message.add_reaction("❌")
            return await ctx.send(
                embed=make_simple_embed("Invalid Volume (must be 0 - 100)"),
                delete_after=DELETE_AFTER,
            )

        ctx.voice_client.source.volume = volume / 100
