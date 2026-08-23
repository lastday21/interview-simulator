from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from redis.asyncio import Redis
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.health import is_bot_heartbeat_alive
from app.core.settings import get_settings
from app.db.engine import create_engine


async def check_database() -> None:
    engine = create_engine()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


async def check_bot_heartbeat(redis_url: str) -> None:
    redis = Redis.from_url(redis_url)
    try:
        if not await redis.ping():
            raise RuntimeError("Redis ping did not return PONG")
        if not await is_bot_heartbeat_alive(redis):
            raise RuntimeError("Bot heartbeat is missing")
    finally:
        await redis.aclose()


async def main() -> None:
    settings = get_settings()
    await check_database()
    await check_bot_heartbeat(settings.redis_url)
    print("healthcheck=ok")


if __name__ == "__main__":
    asyncio.run(main())
