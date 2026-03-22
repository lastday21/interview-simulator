from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Question, Subtopic, Topic, UserQuestionStatus


@dataclass(slots=True, frozen=True)
class QuestionWithStatus:
    question: Question
    status: int | None


@dataclass(slots=True, frozen=True)
class TopicStats:
    topic_id: int
    title: str
    total_questions: int
    answered_questions: int
    known_questions: int
    unknown_questions: int
    difficult_questions: int
    score: int


class ContentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_topics(self) -> list[Topic]:
        result = await self._session.scalars(select(Topic).order_by(Topic.id))
        return list(result)

    async def list_subtopics(self, topic_id: int) -> list[Subtopic]:
        result = await self._session.scalars(
            select(Subtopic)
            .where(Subtopic.topic_id == topic_id)
            .order_by(Subtopic.position, Subtopic.id)
        )
        return list(result)

    async def list_questions(
        self,
        subtopic_id: int,
        *,
        user_id: int | None = None,
        active_only: bool = True,
    ) -> list[QuestionWithStatus]:
        if user_id is None:
            question_query = (
                select(Question)
                .where(Question.subtopic_id == subtopic_id)
                .order_by(Question.position, Question.id)
            )
            if active_only:
                question_query = question_query.where(Question.is_active.is_(True))

            questions = list(await self._session.scalars(question_query))
            return [
                QuestionWithStatus(question=question, status=None)
                for question in questions
            ]

        question_with_status_query = (
            select(Question, UserQuestionStatus.status)
            .outerjoin(
                UserQuestionStatus,
                (UserQuestionStatus.question_id == Question.id)
                & (UserQuestionStatus.user_id == user_id),
            )
            .where(Question.subtopic_id == subtopic_id)
            .order_by(Question.position, Question.id)
        )
        if active_only:
            question_with_status_query = question_with_status_query.where(
                Question.is_active.is_(True)
            )

        result = await self._session.execute(question_with_status_query)
        return [
            QuestionWithStatus(question=question, status=status)
            for question, status in result.all()
        ]

    async def get_question(self, question_id: int) -> Question | None:
        return await self._session.get(Question, question_id)

    async def get_question_by_position(
        self,
        *,
        subtopic_id: int,
        position: int,
        active_only: bool = True,
    ) -> Question | None:
        query = select(Question).where(
            Question.subtopic_id == subtopic_id,
            Question.position == position,
        )
        if active_only:
            query = query.where(Question.is_active.is_(True))
        return await self._session.scalar(query)

    async def get_next_question(
        self,
        *,
        subtopic_id: int,
        current_position: int,
        active_only: bool = True,
    ) -> Question | None:
        query = (
            select(Question)
            .where(
                Question.subtopic_id == subtopic_id,
                Question.position > current_position,
            )
            .order_by(Question.position, Question.id)
            .limit(1)
        )
        if active_only:
            query = query.where(Question.is_active.is_(True))
        return await self._session.scalar(query)

    async def count_questions(
        self,
        *,
        topic_ids: list[int] | None = None,
        subtopic_ids: list[int] | None = None,
        active_only: bool = True,
    ) -> int:
        query = select(func.count(Question.id)).select_from(Question)
        if topic_ids is not None:
            query = query.join(Subtopic, Subtopic.id == Question.subtopic_id).where(
                Subtopic.topic_id.in_(topic_ids)
            )
        if subtopic_ids is not None:
            query = query.where(Question.subtopic_id.in_(subtopic_ids))
        if active_only:
            query = query.where(Question.is_active.is_(True))

        result = await self._session.scalar(query)
        return int(result or 0)

    async def get_topic_stats(self, user_id: int) -> list[TopicStats]:
        query = (
            select(
                Topic.id,
                Topic.title,
                func.count(Question.id).label("total_questions"),
                func.count(UserQuestionStatus.question_id).label("answered_questions"),
                func.coalesce(
                    func.sum(case((UserQuestionStatus.status == 1, 1), else_=0)), 0
                ).label("known_questions"),
                func.coalesce(
                    func.sum(case((UserQuestionStatus.status == 0, 1), else_=0)), 0
                ).label("unknown_questions"),
                func.coalesce(
                    func.sum(case((UserQuestionStatus.status == -1, 1), else_=0)), 0
                ).label("difficult_questions"),
                func.coalesce(func.sum(UserQuestionStatus.status), 0).label("score"),
            )
            .join(Subtopic, Subtopic.topic_id == Topic.id)
            .join(Question, Question.subtopic_id == Subtopic.id)
            .outerjoin(
                UserQuestionStatus,
                (UserQuestionStatus.question_id == Question.id)
                & (UserQuestionStatus.user_id == user_id),
            )
            .where(Question.is_active.is_(True))
            .group_by(Topic.id, Topic.title)
            .order_by(Topic.id)
        )
        result = await self._session.execute(query)
        return [TopicStats(*row) for row in result.all()]

    async def upsert_topic(self, title: str) -> tuple[Topic, bool]:
        topic = await self._session.scalar(select(Topic).where(Topic.title == title))
        created = topic is None
        if topic is None:
            topic = Topic(title=title)
            self._session.add(topic)
            await self._session.flush()
        return topic, created

    async def upsert_subtopic(
        self,
        *,
        topic_id: int,
        title: str,
        position: int,
    ) -> tuple[Subtopic, bool]:
        subtopic = await self._session.scalar(
            select(Subtopic).where(
                Subtopic.topic_id == topic_id,
                Subtopic.title == title,
            )
        )
        created = subtopic is None
        if subtopic is None:
            subtopic = Subtopic(topic_id=topic_id, title=title, position=position)
            self._session.add(subtopic)
        else:
            subtopic.position = position

        await self._session.flush()
        return subtopic, created

    async def upsert_question(
        self,
        *,
        subtopic_id: int,
        position: int,
        question_text: str,
        answer_text: str,
        is_active: bool = True,
    ) -> tuple[Question, bool]:
        question = await self._session.scalar(
            select(Question).where(
                Question.subtopic_id == subtopic_id,
                Question.position == position,
            )
        )
        created = question is None
        if question is None:
            question = Question(
                subtopic_id=subtopic_id,
                position=position,
                question_text=question_text,
                answer_text=answer_text,
                is_active=is_active,
            )
            self._session.add(question)
        else:
            question.question_text = question_text
            question.answer_text = answer_text
            question.is_active = is_active

        await self._session.flush()
        return question, created
