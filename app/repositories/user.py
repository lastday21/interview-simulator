from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_user_id(self, telegram_user_id: int) -> User | None:
        return await self._session.scalar(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )

    async def upsert_user(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
    ) -> User:
        user = await self.get_by_telegram_user_id(telegram_user_id)
        if user is None:
            user = User(
                telegram_user_id=telegram_user_id,
                username=username,
            )
            self._session.add(user)
        else:
            user.username = username

        await self._session.flush()
        return user
