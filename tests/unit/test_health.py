import asyncio
from typing import cast
from unittest.mock import AsyncMock

from redis.asyncio import Redis

from app.core.health import (
    BOT_HEARTBEAT_KEY,
    BOT_HEARTBEAT_TTL_SECONDS,
    is_bot_heartbeat_alive,
    refresh_bot_heartbeat,
)


def test_refresh_bot_heartbeat_sets_expiring_key() -> None:
    redis = AsyncMock()

    asyncio.run(refresh_bot_heartbeat(cast(Redis, redis)))

    redis.set.assert_awaited_once_with(
        BOT_HEARTBEAT_KEY,
        "alive",
        ex=BOT_HEARTBEAT_TTL_SECONDS,
    )


def test_is_bot_heartbeat_alive_checks_key() -> None:
    redis = AsyncMock()
    redis.exists.return_value = 1

    result = asyncio.run(is_bot_heartbeat_alive(cast(Redis, redis)))

    assert result is True
    redis.exists.assert_awaited_once_with(BOT_HEARTBEAT_KEY)
