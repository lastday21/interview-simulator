from pathlib import Path

from app.services import load_question_rows, plan_question_rows


CATALOG_PATH = Path("data/questions.json")


def test_question_catalog_is_ready_for_training() -> None:
    rows = load_question_rows(CATALOG_PATH)
    planned, duplicates_skipped = plan_question_rows(rows)

    assert len(rows) == 224
    assert len(planned) == 224
    assert duplicates_skipped == 0
    assert len({row.external_id for row in rows}) == len(rows)
    assert all(row.question_text.endswith(("?", ".")) for row in rows)
    assert all(120 <= len(row.answer_text) <= 1800 for row in rows)
    assert {row.source_id for row in rows} == {
        "project-original",
        "yakimka-python-interview-questions",
    }


def test_obsolete_and_duplicate_questions_are_removed() -> None:
    rows = load_question_rows(CATALOG_PATH)
    question_ids = {row.external_id for row in rows}

    assert "q-0063" not in question_ids
    assert "q-0083" not in question_ids
