import discord
from discord.ext import commands

from bot.player import PlayerState
from bot.youtube import YTDLSource, get_playlist_urls


class MusicPlayer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states: dict[int, PlayerState] = {}

    def get_state(self, guild_id: int) -> PlayerState:
        if guild_id not in self.states:
            self.states[guild_id] = PlayerState()
        return self.states[guild_id]

    async def play_next(self, ctx):
        state = self.get_state(ctx.guild.id)
        url = state.get_next()

        if url:
            player = await YTDLSource.from_url(url, loop=self.bot.loop)
            ctx.voice_client.play(
                player, after=lambda e: self.bot.loop.create_task(self.play_next(ctx))
            )
            await ctx.send(f"Now playing: **{player.title}**")
        else:
            await ctx.send("End of playlist.")

    @commands.command()
    async def stop(self, ctx):
        await ctx.voice_client.disconnect()

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            await channel.connect()
        else:
            await ctx.send("You are not in a voice channel.")

    @commands.command()
    async def play(self, ctx, *, url: str):
        if not ctx.voice_client:
            await self.join(ctx)

        state = self.get_state(ctx.guild.id)
        if "list=" in url:
            urls = await get_playlist_urls(url)
            state.add_tracks(urls)
        else:
            state.add_track(url)

        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)
        else:
            await ctx.send(f"Added to queue: {url}")

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Paused.")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resumed.")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client:
            ctx.voice_client.stop()  # Trigger 'after' callback to play_next
            await ctx.send("Skipped.")

    @commands.command()
    async def shuffle(self, ctx):
        state = self.get_state(ctx.guild.id)
        state.shuffle_toggle()
        status = "enabled" if state.is_shuffled else "disabled"
        await ctx.send(f"Shuffle {status}.")

    @commands.command(aliases=["q"])
    async def queue(self, ctx):
        state = self.get_state(ctx.guild.id)
        await ctx.send(
                "\n".join(f"{i + 1}. <{url}>" for i, url in enumerate(state.queue[:10]))
        )

    @commands.command(aliases=['v', 'vol'])
    async def volume(self, ctx, volume: int| None=None):
        if not isinstance(ctx.voice_client, discord.VoiceClient):
            return await ctx.message.add_reaction("❌")
        if not isinstance(ctx.voice_client.source, discord.PCMVolumeTransformer):
            return await ctx.message.add_reaction("❌")

        if volume is None:
            return await ctx.send(f"Current volume: {ctx.voice_client.source.volume * 100}")

        if volume < 0 or volume > 100:
            return await ctx.message.add_reaction("❌")

        ctx.voice_client.source.volume = volume / 100
