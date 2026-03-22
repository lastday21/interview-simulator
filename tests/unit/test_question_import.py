from app.services.question_import import QuestionRow, plan_question_rows


def test_plan_question_rows_preserves_order_and_skips_duplicates() -> None:
    rows = [
        QuestionRow(
            topic_title="Python",
            subtopic_title="Asyncio",
            question_text="Что такое event loop?",
            answer_text="loop",
        ),
        QuestionRow(
            topic_title="Python",
            subtopic_title="Asyncio",
            question_text="Что такое coroutine?",
            answer_text="coroutine",
            is_active=False,
        ),
        QuestionRow(
            topic_title="Python",
            subtopic_title="Asyncio",
            question_text="Что такое event loop?",
            answer_text="duplicate",
        ),
        QuestionRow(
            topic_title="Python",
            subtopic_title="Typing",
            question_text="Что такое Protocol?",
            answer_text="protocol",
        ),
        QuestionRow(
            topic_title="SQL",
            subtopic_title="JOIN",
            question_text="Что такое LEFT JOIN?",
            answer_text="join",
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
