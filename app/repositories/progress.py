from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserQuestionStatus


class ProgressRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_question_status(
        self,
        *,
        user_id: int,
        question_id: int,
    ) -> UserQuestionStatus | None:
        return await self._session.scalar(
            select(UserQuestionStatus).where(
                UserQuestionStatus.user_id == user_id,
                UserQuestionStatus.question_id == question_id,
            )
        )

    async def get_question_statuses(
        self,
        *,
        user_id: int,
        question_ids: list[int],
    ) -> dict[int, int]:
        if not question_ids:
            return {}

        result = await self._session.execute(
            select(UserQuestionStatus.question_id, UserQuestionStatus.status).where(
                UserQuestionStatus.user_id == user_id,
                UserQuestionStatus.question_id.in_(question_ids),
            )
        )
        return {question_id: status for question_id, status in result.all()}

    async def upsert_question_status(
        self,
        *,
        user_id: int,
        question_id: int,
        status: int,
    ) -> UserQuestionStatus:
        if status not in {-1, 0, 1}:
            raise ValueError("Status must be one of -1, 0, 1")

        record = await self.get_question_status(
            user_id=user_id, question_id=question_id
        )
        if record is None:
            record = UserQuestionStatus(
                user_id=user_id,
                question_id=question_id,
                status=status,
            )
            self._session.add(record)
        else:
            record.status = status

        await self._session.flush()
        return record
