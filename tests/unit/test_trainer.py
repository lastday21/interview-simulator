from app.bot.routers.trainer import format_trainer_questions_list
from app.db.models import Question
from app.repositories import QuestionWithStatus


def test_format_trainer_questions_list_shows_statuses_and_positions() -> None:
    questions = [
        QuestionWithStatus(
            question=Question(
                id=1,
                subtopic_id=1,
                position=1,
                question_text="Что такое event loop?",
                answer_text="",
            ),
            status=1,
        ),
        QuestionWithStatus(
            question=Question(
                id=2,
                subtopic_id=1,
                position=2,
                question_text="Что такое coroutine?",
                answer_text="",
            ),
            status=None,
        ),
    ]

    text = format_trainer_questions_list(questions)

    assert "1. [Знаю] Что такое event loop?" in text
    assert "2. [Без статуса] Что такое coroutine?" in text


def test_format_trainer_questions_list_handles_empty_subtopic() -> None:
    assert format_trainer_questions_list([]) == "В этой подтеме пока нет вопросов."
