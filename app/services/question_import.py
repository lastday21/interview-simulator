from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ContentRepository


@dataclass(slots=True, frozen=True)
class QuestionRow:
    topic_title: str
    subtopic_title: str
    question_text: str
    answer_text: str
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class PlannedQuestionRow:
    topic_title: str
    subtopic_title: str
    subtopic_position: int
    question_text: str
    answer_text: str
    question_position: int
    is_active: bool = True


@dataclass(slots=True)
class ImportStats:
    topics_created: int = 0
    subtopics_created: int = 0
    questions_created: int = 0
    questions_updated: int = 0
    duplicates_skipped: int = 0


REQUIRED_FIELDS = {
    "тема": "topic_title",
    "подтема": "subtopic_title",
    "вопрос": "question_text",
    "ответ": "answer_text",
}


def _normalize_value(value: Any, *, field_name: str, index: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Row {index}: field '{field_name}' must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"Row {index}: field '{field_name}' must not be empty")
    return normalized


def _normalize_is_active(value: Any, *, index: int) -> bool:
    if value is None:
        return True
    if isinstance(value, bool):
        return value
    raise ValueError(f"Row {index}: field 'is_active' must be a boolean when provided")


def load_question_rows(path: Path) -> list[QuestionRow]:
    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, list):
        raise ValueError("Questions JSON must contain a top-level list")

    rows: list[QuestionRow] = []
    for index, item in enumerate(raw_payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Row {index}: expected an object")

        normalized: dict[str, Any] = {}
        for source_field, target_field in REQUIRED_FIELDS.items():
            if source_field not in item:
                raise ValueError(
                    f"Row {index}: missing required field '{source_field}'"
                )
            normalized[target_field] = _normalize_value(
                item[source_field],
                field_name=source_field,
                index=index,
            )

        normalized["is_active"] = _normalize_is_active(
            item.get("is_active"),
            index=index,
        )
        rows.append(QuestionRow(**normalized))

    return rows


def plan_question_rows(rows: list[QuestionRow]) -> tuple[list[PlannedQuestionRow], int]:
    planned: list[PlannedQuestionRow] = []
    duplicates_skipped = 0

    subtopic_positions: dict[str, int] = {}
    subtopic_order: dict[tuple[str, str], int] = {}
    question_positions: dict[tuple[str, str], int] = {}
    seen_questions: set[tuple[str, str, str]] = set()

    for row in rows:
        duplicate_key = (row.topic_title, row.subtopic_title, row.question_text)
        if duplicate_key in seen_questions:
            duplicates_skipped += 1
            continue
        seen_questions.add(duplicate_key)

        subtopic_key = (row.topic_title, row.subtopic_title)
        if subtopic_key not in subtopic_order:
            next_subtopic_position = subtopic_positions.get(row.topic_title, 0) + 1
            subtopic_positions[row.topic_title] = next_subtopic_position
            subtopic_order[subtopic_key] = next_subtopic_position

        next_question_position = question_positions.get(subtopic_key, 0) + 1
        question_positions[subtopic_key] = next_question_position

        planned.append(
            PlannedQuestionRow(
                topic_title=row.topic_title,
                subtopic_title=row.subtopic_title,
                subtopic_position=subtopic_order[subtopic_key],
                question_text=row.question_text,
                answer_text=row.answer_text,
                question_position=next_question_position,
                is_active=row.is_active,
            )
        )

    return planned, duplicates_skipped


class QuestionImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ContentRepository(session)

    async def import_rows(self, rows: list[PlannedQuestionRow]) -> ImportStats:
        stats = ImportStats()
        topic_ids: dict[str, int] = {}
        subtopic_ids: dict[tuple[str, str], int] = {}

        for row in rows:
            topic_id = topic_ids.get(row.topic_title)
            if topic_id is None:
                topic, created = await self._repository.upsert_topic(row.topic_title)
                topic_id = topic.id
                topic_ids[row.topic_title] = topic_id
                if created:
                    stats.topics_created += 1

            subtopic_key = (row.topic_title, row.subtopic_title)
            subtopic_id = subtopic_ids.get(subtopic_key)
            if subtopic_id is None:
                subtopic, created = await self._repository.upsert_subtopic(
                    topic_id=topic_id,
                    title=row.subtopic_title,
                    position=row.subtopic_position,
                )
                subtopic_id = subtopic.id
                subtopic_ids[subtopic_key] = subtopic_id
                if created:
                    stats.subtopics_created += 1

            _, created = await self._repository.upsert_question(
                subtopic_id=subtopic_id,
                position=row.question_position,
                question_text=row.question_text,
                answer_text=row.answer_text,
                is_active=row.is_active,
            )
            if created:
                stats.questions_created += 1
            else:
                stats.questions_updated += 1

        return stats
