import asyncio
from dataclasses import dataclass
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.db import get_session_factory
from app.db.engine import get_engine
from app.db.models import InterviewItem, Question, User, UserQuestionStatus
from app.repositories import InterviewRepository, ProgressRepository

pytestmark = pytest.mark.integration


@dataclass(slots=True, frozen=True)
class CreatedUser:
    user_id: int
    question_ids: list[int]


async def create_test_user() -> CreatedUser:
    async with get_session_factory()() as session:
        question_ids = list(
            await session.scalars(
                select(Question.id)
                .where(Question.is_active.is_(True))
                .order_by(Question.id)
                .limit(15)
            )
        )
        if len(question_ids) < 15:
            raise RuntimeError("Integration test requires at least 15 questions")

        telegram_user_id = -(uuid4().int % 9_000_000_000_000_000_000)
        user = User(telegram_user_id=telegram_user_id, username="integration-test")
        session.add(user)
        await session.flush()
        await session.commit()
        return CreatedUser(user_id=user.id, question_ids=question_ids)


async def delete_test_user(user_id: int) -> None:
    async with get_session_factory()() as session:
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def save_trainer_status(
    *,
    user_id: int,
    question_id: int,
    status: int,
    message_id: int,
) -> tuple[int, bool]:
    async with get_session_factory()() as session:
        accepted = await ProgressRepository(session).set_trainer_question_status_once(
            user_id=user_id,
            question_id=question_id,
            status=status,
            message_id=message_id,
        )
        await session.commit()
        return status, accepted


async def answer_interview_question(
    *,
    user_id: int,
    question_id: int,
    status: int,
) -> tuple[int, bool, bool]:
    async with get_session_factory()() as session:
        result = await InterviewRepository(session).answer_question(
            user_id=user_id,
            question_id=question_id,
            status=status,
        )
        await session.commit()
        return status, result.accepted, result.already_answered


def test_trainer_accepts_only_one_status_from_the_same_message() -> None:
    async def scenario() -> None:
        test_user = await create_test_user()
        question_id = test_user.question_ids[0]
        try:
            results = await asyncio.gather(
                save_trainer_status(
                    user_id=test_user.user_id,
                    question_id=question_id,
                    status=1,
                    message_id=123456,
                ),
                save_trainer_status(
                    user_id=test_user.user_id,
                    question_id=question_id,
                    status=-1,
                    message_id=123456,
                ),
            )

            accepted = [status for status, is_accepted in results if is_accepted]
            assert len(accepted) == 1

            async with get_session_factory()() as session:
                saved = await session.get(
                    UserQuestionStatus,
                    (test_user.user_id, question_id),
                )
                assert saved is not None
                assert saved.status == accepted[0]
                assert saved.last_trainer_message_id == 123456

            async with get_session_factory()() as session:
                updated = await ProgressRepository(session).upsert_question_status(
                    user_id=test_user.user_id,
                    question_id=question_id,
                    status=0,
                )
                await session.commit()
                assert updated.status == 0
                assert updated.last_trainer_message_id == 123456
        finally:
            await delete_test_user(test_user.user_id)
            await get_engine().dispose()

    asyncio.run(scenario())


def test_interview_accepts_only_one_concurrent_answer() -> None:
    async def scenario() -> None:
        test_user = await create_test_user()
        question_id = test_user.question_ids[0]
        try:
            async with get_session_factory()() as session:
                await InterviewRepository(session).start_interview(
                    user_id=test_user.user_id,
                    question_ids=test_user.question_ids,
                )
                await session.commit()

            results = await asyncio.gather(
                answer_interview_question(
                    user_id=test_user.user_id,
                    question_id=question_id,
                    status=1,
                ),
                answer_interview_question(
                    user_id=test_user.user_id,
                    question_id=question_id,
                    status=0,
                ),
            )

            accepted = [status for status, is_accepted, _ in results if is_accepted]
            assert len(accepted) == 1
            assert sum(1 for _, _, duplicate in results if duplicate) == 1

            async with get_session_factory()() as session:
                saved_status = await session.scalar(
                    select(InterviewItem.answer_status).where(
                        InterviewItem.user_id == test_user.user_id,
                        InterviewItem.question_id == question_id,
                    )
                )
                assert saved_status == accepted[0]
        finally:
            await delete_test_user(test_user.user_id)
            await get_engine().dispose()

    asyncio.run(scenario())
