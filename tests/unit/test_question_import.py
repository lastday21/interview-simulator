import json
from pathlib import Path

import pytest

from app.services.question_import import (
    QuestionRow,
    load_question_rows,
    plan_question_rows,
)


def _question_row(
    external_id: str,
    *,
    topic: str = "Python",
    subtopic: str = "Asyncio",
    question: str = "Что такое event loop?",
    answer: str = "Цикл событий.",
    is_active: bool = True,
) -> QuestionRow:
    return QuestionRow(
        external_id=external_id,
        source_id="original",
        topic_title=topic,
        subtopic_title=subtopic,
        question_text=question,
        answer_text=answer,
        is_active=is_active,
    )


def _write_catalog(path: Path, questions: list[dict[str, object]]) -> None:
    payload = {
        "schema_version": 1,
        "sources": {
            "original": {
                "title": "Original questions",
                "url": "https://example.com/questions",
                "license": "Proprietary",
                "copyright": "Copyright 2026",
            }
        },
        "questions": questions,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_load_question_rows_validates_catalog(tmp_path: Path) -> None:
    catalog_path = tmp_path / "questions.json"
    _write_catalog(
        catalog_path,
        [
            {
                "id": "python-asyncio-001",
                "источник": "original",
                "тема": " Python ",
                "подтема": " Asyncio ",
                "вопрос": " Что такое event loop? ",
                "ответ": " Цикл событий. ",
            }
        ],
    )

    assert load_question_rows(catalog_path) == [_question_row("python-asyncio-001")]


def test_load_question_rows_rejects_duplicate_id(tmp_path: Path) -> None:
    catalog_path = tmp_path / "questions.json"
    question: dict[str, object] = {
        "id": "python-001",
        "источник": "original",
        "тема": "Python",
        "подтема": "Основы",
        "вопрос": "Вопрос",
        "ответ": "Ответ",
    }
    _write_catalog(catalog_path, [question, question])

    with pytest.raises(ValueError, match="duplicate question id"):
        load_question_rows(catalog_path)


def test_load_question_rows_rejects_unknown_source(tmp_path: Path) -> None:
    catalog_path = tmp_path / "questions.json"
    _write_catalog(
        catalog_path,
        [
            {
                "id": "python-001",
                "источник": "unknown",
                "тема": "Python",
                "подтема": "Основы",
                "вопрос": "Вопрос",
                "ответ": "Ответ",
            }
        ],
    )

    with pytest.raises(ValueError, match="unknown source id"):
        load_question_rows(catalog_path)


def test_load_question_rows_rejects_legacy_list(tmp_path: Path) -> None:
    catalog_path = tmp_path / "questions.json"
    catalog_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="top-level object"):
        load_question_rows(catalog_path)


def test_plan_question_rows_preserves_order_and_skips_duplicates() -> None:
    rows = [
        _question_row("python-asyncio-001"),
        _question_row(
            "python-asyncio-002",
            question="Что такое coroutine?",
            answer="Корутина.",
            is_active=False,
        ),
        _question_row("python-asyncio-003", answer="Повтор."),
        _question_row(
            "python-typing-001",
            subtopic="Typing",
            question="Что такое Protocol?",
            answer="Протокол.",
        ),
        _question_row(
            "sql-join-001",
            topic="SQL",
            subtopic="JOIN",
            question="Что такое LEFT JOIN?",
            answer="Соединение.",
        ),
    ]

    planned, duplicates_skipped = plan_question_rows(rows)

    assert duplicates_skipped == 1
    assert [
        (row.topic_title, row.subtopic_title, row.subtopic_position) for row in planned
    ] == [
        ("Python", "Asyncio", 1),
        ("Python", "Asyncio", 1),
        ("Python", "Typing", 2),
        ("SQL", "JOIN", 1),
    ]
    assert [row.question_position for row in planned] == [1, 2, 1, 1]
    assert [row.is_active for row in planned] == [True, False, True, True]
