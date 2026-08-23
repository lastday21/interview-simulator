import asyncio
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

BOT_HEARTBEAT_KEY = "interview-simulator:bot:heartbeat"
BOT_HEARTBEAT_INTERVAL_SECONDS = 10
BOT_HEARTBEAT_TTL_SECONDS = 30

logger = logging.getLogger(__name__)


async def refresh_bot_heartbeat(redis: Redis) -> None:
    await redis.set(
        BOT_HEARTBEAT_KEY,
        "alive",
        ex=BOT_HEARTBEAT_TTL_SECONDS,
    )


async def is_bot_heartbeat_alive(redis: Redis) -> bool:
    return bool(await redis.exists(BOT_HEARTBEAT_KEY))


async def run_bot_heartbeat(redis_url: str) -> None:
    redis = Redis.from_url(redis_url)
    try:
        while True:
            try:
                await refresh_bot_heartbeat(redis)
            except RedisError:
                logger.exception("Could not refresh bot heartbeat")
            await asyncio.sleep(BOT_HEARTBEAT_INTERVAL_SECONDS)
    finally:
        await redis.aclose()
