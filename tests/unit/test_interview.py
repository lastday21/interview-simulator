from app.bot.routers.interview import _format_completion_result


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
