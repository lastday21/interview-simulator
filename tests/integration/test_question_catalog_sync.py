import asyncio

import pytest
from sqlalchemy import func, select

from app.db import get_session_factory
from app.db.engine import get_engine
from app.db.models import Question
from app.services import PlannedQuestionRow, QuestionImportService

pytestmark = pytest.mark.integration


def test_catalog_sync_deactivates_and_explicitly_deletes_missing_questions() -> None:
    async def scenario() -> None:
        async with get_session_factory()() as session:
            original_count = await session.scalar(select(func.count(Question.id)))
            assert original_count is not None
            assert original_count > 0

            rows = [
                PlannedQuestionRow(
                    external_id="catalog-sync-test-001",
                    source_id="integration-test",
                    topic_title="Проверка каталога",
                    subtopic_title="Синхронизация",
                    subtopic_position=1,
                    question_text="Проверочный вопрос",
                    answer_text="Проверочный ответ",
                    question_position=1,
                )
            ]
            service = QuestionImportService(session)

            stats = await service.import_rows(rows)
            assert stats.questions_created == 1
            assert stats.questions_deactivated == original_count

            active_count = await session.scalar(
                select(func.count(Question.id)).where(Question.is_active.is_(True))
            )
            assert active_count == 1

            purge_stats = await service.import_rows(rows, purge_missing=True)
            assert purge_stats.questions_deleted == original_count
            assert purge_stats.subtopics_deleted > 0
            assert purge_stats.topics_deleted > 0

            total_count = await session.scalar(select(func.count(Question.id)))
            assert total_count == 1

            await session.rollback()

        await get_engine().dispose()

    asyncio.run(scenario())
