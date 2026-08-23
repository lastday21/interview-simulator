from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, case, delete, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import Question, Subtopic, Topic, UserQuestionStatus


@dataclass(slots=True, frozen=True)
class QuestionWithStatus:
    question: Question
    status: int | None


@dataclass(slots=True, frozen=True)
class TrainerQuestionContext:
    topic_title: str
    subtopic_title: str
    total_questions: int


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
        has_active_questions = exists(
            select(Question.id)
            .join(Subtopic, Subtopic.id == Question.subtopic_id)
            .where(
                Subtopic.topic_id == Topic.id,
                Question.is_active.is_(True),
            )
        )
        result = await self._session.scalars(
            select(Topic).where(has_active_questions).order_by(Topic.id)
        )
        return list(result)

    async def list_subtopics(self, topic_id: int) -> list[Subtopic]:
        result = await self._session.scalars(
            select(Subtopic)
            .where(
                Subtopic.topic_id == topic_id,
                exists(
                    select(Question.id).where(
                        Question.subtopic_id == Subtopic.id,
                        Question.is_active.is_(True),
                    )
                ),
            )
            .order_by(Subtopic.position, Subtopic.id)
        )
        return list(result)

    async def get_subtopic(self, subtopic_id: int) -> Subtopic | None:
        return await self._session.get(Subtopic, subtopic_id)

    async def list_subtopics_by_topic_ids(
        self,
        topic_ids: list[int],
    ) -> list[Subtopic]:
        if not topic_ids:
            return []

        result = await self._session.scalars(
            select(Subtopic)
            .where(
                Subtopic.topic_id.in_(topic_ids),
                exists(
                    select(Question.id).where(
                        Question.subtopic_id == Subtopic.id,
                        Question.is_active.is_(True),
                    )
                ),
            )
            .order_by(Subtopic.topic_id, Subtopic.position, Subtopic.id)
        )
        return list(result)

    async def get_next_subtopic_with_questions(
        self,
        current_subtopic_id: int,
        *,
        active_only: bool = True,
    ) -> Subtopic | None:
        current_subtopic = await self._session.get(Subtopic, current_subtopic_id)
        if current_subtopic is None:
            return None

        has_questions = exists(
            select(Question.id).where(Question.subtopic_id == Subtopic.id)
        )
        if active_only:
            has_questions = exists(
                select(Question.id).where(
                    Question.subtopic_id == Subtopic.id,
                    Question.is_active.is_(True),
                )
            )

        query = (
            select(Subtopic)
            .join(Topic, Topic.id == Subtopic.topic_id)
            .where(has_questions)
            .where(
                or_(
                    Subtopic.topic_id > current_subtopic.topic_id,
                    and_(
                        Subtopic.topic_id == current_subtopic.topic_id,
                        or_(
                            Subtopic.position > current_subtopic.position,
                            and_(
                                Subtopic.position == current_subtopic.position,
                                Subtopic.id > current_subtopic.id,
                            ),
                        ),
                    ),
                )
            )
            .order_by(Topic.id, Subtopic.position, Subtopic.id)
            .limit(1)
        )
        return await self._session.scalar(query)

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

    async def get_trainer_question_context(
        self,
        question_id: int,
    ) -> TrainerQuestionContext | None:
        counted_question = aliased(Question)
        total_questions = (
            select(func.count(counted_question.id))
            .where(
                counted_question.subtopic_id == Subtopic.id,
                counted_question.is_active.is_(True),
            )
            .correlate(Subtopic)
            .scalar_subquery()
        )
        query = (
            select(Topic.title, Subtopic.title, total_questions)
            .select_from(Question)
            .join(Subtopic, Subtopic.id == Question.subtopic_id)
            .join(Topic, Topic.id == Subtopic.topic_id)
            .where(Question.id == question_id)
        )
        row = (await self._session.execute(query)).one_or_none()
        if row is None:
            return None

        return TrainerQuestionContext(
            topic_title=row[0],
            subtopic_title=row[1],
            total_questions=int(row[2]),
        )

    async def list_weak_questions(
        self,
        user_id: int,
        *,
        active_only: bool = True,
    ) -> list[QuestionWithStatus]:
        query = (
            select(Question, UserQuestionStatus.status)
            .join(
                UserQuestionStatus,
                (UserQuestionStatus.question_id == Question.id)
                & (UserQuestionStatus.user_id == user_id),
            )
            .join(Subtopic, Subtopic.id == Question.subtopic_id)
            .join(Topic, Topic.id == Subtopic.topic_id)
            .where(UserQuestionStatus.status.in_([-1, 0]))
            .order_by(Topic.id, Subtopic.position, Question.position, Question.id)
        )
        if active_only:
            query = query.where(Question.is_active.is_(True))

        result = await self._session.execute(query)
        return [
            QuestionWithStatus(question=question, status=status)
            for question, status in result.all()
        ]

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

    async def select_interview_question_ids(
        self,
        *,
        subtopic_ids: list[int],
        limit: int,
        active_only: bool = True,
    ) -> list[int]:
        if not subtopic_ids or limit <= 0:
            return []

        query = (
            select(Question.id)
            .where(Question.subtopic_id.in_(subtopic_ids))
            .order_by(func.random())
            .limit(limit)
        )
        if active_only:
            query = query.where(Question.is_active.is_(True))

        result = await self._session.scalars(query)
        return list(result)

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
        external_id: str,
        source_id: str,
        subtopic_id: int,
        position: int,
        question_text: str,
        answer_text: str,
        is_active: bool = True,
    ) -> tuple[Question, bool]:
        question = await self._session.scalar(
            select(Question).where(Question.external_id == external_id)
        )
        if question is None:
            question = await self._session.scalar(
                select(Question).where(
                    Question.external_id.is_(None),
                    Question.subtopic_id == subtopic_id,
                    Question.position == position,
                )
            )
        created = question is None
        if question is None:
            question = Question(
                external_id=external_id,
                source_id=source_id,
                subtopic_id=subtopic_id,
                position=position,
                question_text=question_text,
                answer_text=answer_text,
                is_active=is_active,
            )
            self._session.add(question)
        else:
            question.external_id = external_id
            question.source_id = source_id
            question.subtopic_id = subtopic_id
            question.position = position
            question.question_text = question_text
            question.answer_text = answer_text
            question.is_active = is_active

        await self._session.flush()
        return question, created

    async def deactivate_questions_not_in_catalog(
        self,
        external_ids: set[str],
    ) -> int:
        missing_condition: ColumnElement[bool] = Question.external_id.is_(None)
        if external_ids:
            missing_condition = or_(
                missing_condition,
                Question.external_id.not_in(external_ids),
            )

        result = await self._session.scalars(
            update(Question)
            .where(
                missing_condition,
                Question.is_active.is_(True),
            )
            .values(is_active=False)
            .returning(Question.id)
        )
        return len(list(result))

    async def delete_questions_not_in_catalog(
        self,
        external_ids: set[str],
    ) -> int:
        missing_condition: ColumnElement[bool] = Question.external_id.is_(None)
        if external_ids:
            missing_condition = or_(
                missing_condition,
                Question.external_id.not_in(external_ids),
            )

        result = await self._session.scalars(
            delete(Question).where(missing_condition).returning(Question.id)
        )
        return len(list(result))

    async def delete_empty_subtopics(self) -> int:
        has_questions = exists(
            select(Question.id).where(Question.subtopic_id == Subtopic.id)
        )
        result = await self._session.scalars(
            delete(Subtopic).where(~has_questions).returning(Subtopic.id)
        )
        return len(list(result))

    async def delete_empty_topics(self) -> int:
        has_subtopics = exists(select(Subtopic.id).where(Subtopic.topic_id == Topic.id))
        result = await self._session.scalars(
            delete(Topic).where(~has_subtopics).returning(Topic.id)
        )
        return len(list(result))
