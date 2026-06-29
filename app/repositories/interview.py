from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import InterviewItem, InterviewSession, Question, Subtopic, Topic

PASS_THRESHOLD = 13


@dataclass(slots=True, frozen=True)
class InterviewQuestionView:
    item_id: int
    position: int
    total_questions: int
    question_id: int
    question_text: str
    topic_id: int
    topic_title: str
    subtopic_id: int
    subtopic_title: str


@dataclass(slots=True, frozen=True)
class InterviewAnswerResult:
    item: InterviewItem | None
    accepted: bool
    already_answered: bool
    is_current_question: bool
    completed: bool


@dataclass(slots=True, frozen=True)
class InterviewCompletionResult:
    session: InterviewSession
    total_questions: int
    know_count: int
    passed: bool
    question_statuses: list[tuple[int, int]]


@dataclass(slots=True, frozen=True)
class InterviewStats:
    completed_count: int
    average_know_count: float
    passed_percent: float


def _completed_stats_query(user_id: int):
    passed_score = case((InterviewSession.passed.is_(True), 1.0), else_=0.0)
    return select(
        func.count(InterviewSession.id),
        func.coalesce(func.avg(InterviewSession.correct_count), 0),
        func.coalesce(func.avg(passed_score), 0),
    ).where(InterviewSession.user_id == user_id)


class InterviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def has_active_interview(self, user_id: int) -> bool:
        return (await self.get_total_questions(user_id)) > 0

    async def get_total_questions(self, user_id: int) -> int:
        result = await self._session.execute(
            select(InterviewItem.id).where(InterviewItem.user_id == user_id)
        )
        return len(result.all())

    async def get_completed_stats(self, user_id: int) -> InterviewStats:
        row = await self._session.execute(_completed_stats_query(user_id))
        completed_count, average_know_count, passed_ratio = row.one()
        return InterviewStats(
            completed_count=int(completed_count or 0),
            average_know_count=float(average_know_count or 0),
            passed_percent=float(passed_ratio or 0) * 100,
        )

    async def clear_active_interview(self, user_id: int) -> None:
        await self._session.execute(
            delete(InterviewItem).where(InterviewItem.user_id == user_id)
        )

    async def start_interview(
        self,
        *,
        user_id: int,
        question_ids: list[int],
        reset_existing: bool = False,
    ) -> list[InterviewItem]:
        if not question_ids:
            raise ValueError("question_ids must not be empty")
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("question_ids must be unique")
        if await self.has_active_interview(user_id):
            if not reset_existing:
                raise ValueError("User already has an active interview")
            await self.clear_active_interview(user_id)

        items = [
            InterviewItem(user_id=user_id, position=index, question_id=question_id)
            for index, question_id in enumerate(question_ids, start=1)
        ]
        self._session.add_all(items)
        await self._session.flush()
        return items

    async def get_current_question(self, user_id: int) -> InterviewQuestionView | None:
        total_questions = await self.get_total_questions(user_id)
        if total_questions == 0:
            return None

        row = await self._session.execute(
            select(
                InterviewItem.id,
                InterviewItem.position,
                Question.id,
                Question.question_text,
                Topic.id,
                Topic.title,
                Subtopic.id,
                Subtopic.title,
            )
            .join(Question, Question.id == InterviewItem.question_id)
            .join(Subtopic, Subtopic.id == Question.subtopic_id)
            .join(Topic, Topic.id == Subtopic.topic_id)
            .where(
                InterviewItem.user_id == user_id,
                InterviewItem.answer_status.is_(None),
            )
            .order_by(InterviewItem.position)
            .limit(1)
        )
        current = row.first()
        if current is None:
            return None

        return InterviewQuestionView(
            item_id=current[0],
            position=current[1],
            total_questions=total_questions,
            question_id=current[2],
            question_text=current[3],
            topic_id=current[4],
            topic_title=current[5],
            subtopic_id=current[6],
            subtopic_title=current[7],
        )

    async def answer_question(
        self,
        *,
        user_id: int,
        question_id: int,
        status: int,
    ) -> InterviewAnswerResult:
        if status not in {-1, 0, 1}:
            raise ValueError("Status must be one of -1, 0, 1")

        item = await self._session.scalar(
            select(InterviewItem).where(
                InterviewItem.user_id == user_id,
                InterviewItem.question_id == question_id,
            )
        )
        if item is None:
            return InterviewAnswerResult(
                item=None,
                accepted=False,
                already_answered=False,
                is_current_question=False,
                completed=False,
            )

        if item.answer_status is not None:
            return InterviewAnswerResult(
                item=item,
                accepted=False,
                already_answered=True,
                is_current_question=False,
                completed=False,
            )

        current = await self._session.scalar(
            select(InterviewItem)
            .where(
                InterviewItem.user_id == user_id,
                InterviewItem.answer_status.is_(None),
            )
            .order_by(InterviewItem.position)
            .limit(1)
        )
        if current is None or current.id != item.id:
            return InterviewAnswerResult(
                item=item,
                accepted=False,
                already_answered=False,
                is_current_question=False,
                completed=False,
            )

        item.answer_status = status
        item.answered_at = datetime.now(timezone.utc)
        await self._session.flush()

        has_unanswered = await self._session.scalar(
            select(InterviewItem.id)
            .where(
                InterviewItem.user_id == user_id,
                InterviewItem.answer_status.is_(None),
            )
            .order_by(InterviewItem.position)
            .limit(1)
        )

        return InterviewAnswerResult(
            item=item,
            accepted=True,
            already_answered=False,
            is_current_question=True,
            completed=has_unanswered is None,
        )

    async def finish_interview(
        self,
        *,
        user_id: int,
    ) -> InterviewCompletionResult | None:
        items = list(
            await self._session.scalars(
                select(InterviewItem)
                .where(InterviewItem.user_id == user_id)
                .order_by(InterviewItem.position)
            )
        )
        if not items or any(item.answer_status is None for item in items):
            return None

        question_statuses = [
            (item.question_id, item.answer_status)
            for item in items
            if item.answer_status is not None
        ]
        know_count = sum(1 for _, status in question_statuses if status == 1)
        passed = know_count >= PASS_THRESHOLD

        session = InterviewSession(
            user_id=user_id,
            correct_count=know_count,
            passed=passed,
        )
        self._session.add(session)
        await self._session.flush()
        await self.clear_active_interview(user_id)

        return InterviewCompletionResult(
            session=session,
            total_questions=len(items),
            know_count=know_count,
            passed=passed,
            question_statuses=question_statuses,
        )
