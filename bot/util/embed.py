import discord

from bot.player import PlayerState
from bot.youtube import VideoInfo


def make_simple_embed(title: str, url: str = ""):
    return discord.Embed(
        title=title,
        url=url,
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
    )


def make_np_embed(info: VideoInfo):
    return discord.Embed(
        title=f"▶️ {info['title']}",
        color=discord.Color.blurple(),
        timestamp=discord.utils.utcnow(),
        url=info["url"],
    )


def make_queue_embed(state: PlayerState):
    has_playlist = bool(state.playlist)
    np, *rest = state.queue[state.current_index : state.current_index + 11]
    if not has_playlist:
        return discord.Embed(
            title="❌ Nothing Queued",
            color=discord.Color.brand_red(),
            timestamp=discord.utils.utcnow(),
            url=np["url"],
        )

    em = make_np_embed(state.current_track)
    if rest:
        em.add_field(
            name="Up Next",
            value="\n".join(
                f"{i + 1}. {source['title']}" for i, source in enumerate(rest)
            ),
        )

    return em
