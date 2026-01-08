import orjson
from redis.asyncio import Redis

from bot.youtube import VideoInfo


class VideoInfoCache:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> VideoInfo | None:
        data = await self.redis.get(key)
        if data is None:
            return None
        print("Hit cache for ", key)
        return VideoInfo(**orjson.loads(data))

    async def set(self, info: VideoInfo):
        return await self.redis.set(
            info.url,
            orjson.dumps(info),
        )
