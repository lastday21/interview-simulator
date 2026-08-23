from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import ContentRepository


CATALOG_SCHEMA_VERSION = 1
QUESTION_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]*\Z")
SOURCE_REQUIRED_FIELDS = ("title", "url", "license", "copyright")


@dataclass(slots=True, frozen=True)
class QuestionRow:
    external_id: str
    source_id: str
    topic_title: str
    subtopic_title: str
    question_text: str
    answer_text: str
    is_active: bool = True


@dataclass(slots=True, frozen=True)
class PlannedQuestionRow:
    external_id: str
    source_id: str
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
    topics_deleted: int = 0
    subtopics_created: int = 0
    subtopics_deleted: int = 0
    questions_created: int = 0
    questions_updated: int = 0
    questions_deactivated: int = 0
    questions_deleted: int = 0
    duplicates_skipped: int = 0


REQUIRED_FIELDS = {
    "id": "external_id",
    "источник": "source_id",
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


def _validate_sources(value: Any) -> set[str]:
    if not isinstance(value, dict) or not value:
        raise ValueError("Questions JSON field 'sources' must be a non-empty object")

    source_ids: set[str] = set()
    for source_id, metadata in value.items():
        if not isinstance(source_id, str) or not QUESTION_ID_PATTERN.fullmatch(
            source_id
        ):
            raise ValueError(f"Invalid source id: {source_id!r}")
        if not isinstance(metadata, dict):
            raise ValueError(f"Source '{source_id}' metadata must be an object")
        for field_name in SOURCE_REQUIRED_FIELDS:
            field_value = metadata.get(field_name)
            if not isinstance(field_value, str) or not field_value.strip():
                raise ValueError(
                    f"Source '{source_id}' field '{field_name}' must be a non-empty string"
                )
        source_ids.add(source_id)
    return source_ids


def load_question_rows(path: Path) -> list[QuestionRow]:
    raw_payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError("Questions JSON must contain a top-level object")
    if raw_payload.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ValueError(
            f"Questions JSON schema_version must be {CATALOG_SCHEMA_VERSION}"
        )

    source_ids = _validate_sources(raw_payload.get("sources"))
    raw_questions = raw_payload.get("questions")
    if not isinstance(raw_questions, list):
        raise ValueError("Questions JSON field 'questions' must be a list")

    rows: list[QuestionRow] = []
    seen_external_ids: set[str] = set()
    for index, item in enumerate(raw_questions, start=1):
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

        external_id = normalized["external_id"]
        if not QUESTION_ID_PATTERN.fullmatch(external_id):
            raise ValueError(f"Row {index}: invalid question id '{external_id}'")
        if external_id in seen_external_ids:
            raise ValueError(f"Row {index}: duplicate question id '{external_id}'")
        seen_external_ids.add(external_id)

        source_id = normalized["source_id"]
        if source_id not in source_ids:
            raise ValueError(f"Row {index}: unknown source id '{source_id}'")

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
                external_id=row.external_id,
                source_id=row.source_id,
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

    async def import_rows(
        self,
        rows: list[PlannedQuestionRow],
        *,
        purge_missing: bool = False,
    ) -> ImportStats:
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
                external_id=row.external_id,
                source_id=row.source_id,
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

        external_ids = {row.external_id for row in rows}
        if purge_missing:
            stats.questions_deleted = (
                await self._repository.delete_questions_not_in_catalog(external_ids)
            )
            stats.subtopics_deleted = await self._repository.delete_empty_subtopics()
            stats.topics_deleted = await self._repository.delete_empty_topics()
        else:
            stats.questions_deactivated = (
                await self._repository.deactivate_questions_not_in_catalog(external_ids)
            )

        return stats
