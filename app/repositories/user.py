from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
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
        statement = (
            insert(User)
            .values(
                telegram_user_id=telegram_user_id,
                username=username,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_user_id],
                set_={"username": username},
            )
            .returning(User)
        )
        user = await self._session.scalar(statement)
        if user is None:
            raise RuntimeError("Failed to upsert user")

        return user
