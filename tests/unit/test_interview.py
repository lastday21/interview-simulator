from sqlalchemy.dialects import postgresql

from app.bot.routers.interview import _format_completion_result
from app.repositories.interview import _completed_stats_query


def test_format_completion_result_passed() -> None:
    assert _format_completion_result(
        total_questions=15,
        know_count=13,
        unknown_count=1,
        difficult_count=1,
        passed=True,
    ) == (
        "Собеседование завершено.\n\n"
        "Знаю: 13/15\n"
        "Не знаю: 1/15\n"
        "Сложно: 1/15\n\n"
        "Вердикт: Пройдено"
    )


def test_format_completion_result_failed() -> None:
    assert "Вердикт: Не пройдено" in _format_completion_result(
        total_questions=15,
        know_count=12,
        unknown_count=2,
        difficult_count=1,
        passed=False,
    )


def test_completed_stats_query_uses_postgresql_safe_boolean_average() -> None:
    compiled = str(_completed_stats_query(1).compile(dialect=postgresql.dialect()))

    assert "CASE WHEN" in compiled
    assert "CAST(interview_sessions.passed AS FLOAT" not in compiled
