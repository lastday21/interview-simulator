from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from aiogram import Bot
from redis.asyncio import Redis
from sqlalchemy import text

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings
from app.db.engine import create_engine


async def check_database() -> None:
    engine = create_engine()
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    finally:
        await engine.dispose()


async def check_redis(redis_url: str) -> None:
    redis = Redis.from_url(redis_url)
    try:
        pong = await redis.ping()
        if pong is not True:
            raise RuntimeError("Redis ping did not return PONG")
    finally:
        await redis.aclose()


async def check_telegram(bot_token: str) -> str | None:
    bot = Bot(bot_token)
    try:
        me = await bot.get_me()
        return me.username
    finally:
        await bot.session.close()


async def main() -> None:
    settings = get_settings()

    await check_database()
    await check_redis(settings.redis_url)
    username = await check_telegram(settings.bot_token)

    print(f"runtime_smoke=ok telegram_username={username}")


if __name__ == "__main__":
    asyncio.run(main())
