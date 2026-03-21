from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session_factory


class DbSessionMiddleware(BaseMiddleware):
    """Create one DB session per update and finalize its transaction."""

    async def __call__(
        self,
        handler: Callable[[dict[str, Any], dict[str, Any]], Awaitable[Any]],
        event: dict[str, Any],
        data: dict[str, Any],
    ) -> Any:
        async with get_session_factory()() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise


def get_session_from_data(data: dict[str, Any]) -> AsyncSession:
    return data["session"]
