import asyncio

import pytest
from sqlalchemy import select

from app.db import get_session_factory
from app.db.engine import get_engine
from app.db.models import Question
from app.repositories import ContentRepository

pytestmark = pytest.mark.integration


def test_trainer_question_context_comes_from_postgresql() -> None:
    async def scenario() -> None:
        async with get_session_factory()() as session:
            question = await session.scalar(
                select(Question)
                .where(Question.is_active.is_(True))
                .order_by(Question.id)
                .limit(1)
            )
            assert question is not None

            context = await ContentRepository(session).get_trainer_question_context(
                question.id
            )

            assert context is not None
            assert context.topic_title
            assert context.subtopic_title
            assert context.total_questions >= 1

        await get_engine().dispose()

    asyncio.run(scenario())
