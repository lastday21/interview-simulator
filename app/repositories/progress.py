from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
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

        statement = (
            insert(UserQuestionStatus)
            .values(
                user_id=user_id,
                question_id=question_id,
                status=status,
            )
            .on_conflict_do_update(
                index_elements=[
                    UserQuestionStatus.user_id,
                    UserQuestionStatus.question_id,
                ],
                set_={
                    "status": status,
                    "updated_at": func.now(),
                },
            )
            .returning(UserQuestionStatus)
        )

        record = await self._session.scalar(statement)
        if record is None:
            raise RuntimeError("Could not save question status")
        return record

    async def set_trainer_question_status_once(
        self,
        *,
        user_id: int,
        question_id: int,
        status: int,
        message_id: int,
    ) -> bool:
        if status not in {-1, 0, 1}:
            raise ValueError("Status must be one of -1, 0, 1")

        statement = (
            insert(UserQuestionStatus)
            .values(
                user_id=user_id,
                question_id=question_id,
                status=status,
                last_trainer_message_id=message_id,
            )
            .on_conflict_do_update(
                index_elements=[
                    UserQuestionStatus.user_id,
                    UserQuestionStatus.question_id,
                ],
                set_={
                    "status": status,
                    "last_trainer_message_id": message_id,
                    "updated_at": func.now(),
                },
                where=or_(
                    UserQuestionStatus.last_trainer_message_id.is_(None),
                    UserQuestionStatus.last_trainer_message_id != message_id,
                ),
            )
            .returning(UserQuestionStatus.user_id)
        )

        return await self._session.scalar(statement) is not None
