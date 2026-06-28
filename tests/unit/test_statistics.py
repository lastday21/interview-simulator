from app.bot.routers.statistics import format_interview_stats, format_topic_stats
from app.repositories import InterviewStats, TopicStats


def test_format_topic_stats_shows_required_metrics() -> None:
    text = format_topic_stats(
        [
            TopicStats(
                topic_id=1,
                title="Python",
                total_questions=10,
                answered_questions=4,
                known_questions=2,
                unknown_questions=1,
                difficult_questions=1,
                score=1,
            )
        ]
    )

    assert text == (
        "Темы:\n- Python: всего 10, оценено 4, знаю 2, не знаю 1, сложно 1, score 1"
    )


def test_format_topic_stats_handles_empty_data() -> None:
    assert format_topic_stats([]) == "По темам пока нет данных."


def test_format_interview_stats_shows_completed_summary() -> None:
    text = format_interview_stats(
        InterviewStats(
            completed_count=3,
            average_know_count=12.666,
            passed_percent=66.6,
        )
    )

    assert text == (
        "Собеседования:\n- завершено: 3\n- среднее Знаю: 12.7/15\n- пройдено: 67%"
    )


def test_format_interview_stats_handles_empty_history() -> None:
    assert (
        format_interview_stats(
            InterviewStats(
                completed_count=0,
                average_know_count=0,
                passed_percent=0,
            )
        )
        == "Собеседования: завершенных пока нет."
    )
