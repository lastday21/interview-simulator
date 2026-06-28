from dataclasses import dataclass

from aiogram import Dispatcher

from app.bot.callbacks import (
    INTERVIEW_MENU,
    INTERVIEW_KEEP_ACTIVE,
    INTERVIEW_RESET_ACTIVE,
    INTERVIEW_SELECT_ALL_TOPICS,
    INTERVIEW_START,
    INTERVIEW_SUBTOPICS,
    INTERVIEW_TOPICS,
    MAIN_MENU,
    STATISTICS_MENU,
    TRAINER_MENU,
    TRAINER_SELECT_NUMBER,
    TRAINER_START_BEGIN,
    TRAINER_TOPICS,
    InterviewAnswerCallback,
    InterviewSubtopicCallback,
    InterviewTopicCallback,
    TrainerQuestionAnswerCallback,
    TrainerQuestionAnswerTextCallback,
    TrainerSubtopicCallback,
    TrainerTopicCallback,
)
from app.bot.dispatcher import create_dispatcher
from app.bot.keyboards import (
    interview_question_keyboard,
    interview_reset_active_keyboard,
    interview_subtopics_keyboard,
    interview_topics_keyboard,
    main_menu_keyboard,
    trainer_question_keyboard,
    trainer_selected_subtopic_keyboard,
    trainer_subtopics_keyboard,
    trainer_topics_keyboard,
)


@dataclass(slots=True, frozen=True)
class KeyboardItem:
    id: int
    title: str


def test_main_menu_keyboard_has_expected_callbacks() -> None:
    keyboard = main_menu_keyboard()

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert callback_data == [TRAINER_MENU, INTERVIEW_MENU, STATISTICS_MENU]


def test_create_dispatcher_registers_routers() -> None:
    dispatcher = create_dispatcher()

    assert isinstance(dispatcher, Dispatcher)
    assert {router.name for router in dispatcher.sub_routers} == {
        "common",
        "trainer",
        "interview",
        "statistics",
    }


def test_trainer_topics_keyboard_uses_topic_callbacks() -> None:
    keyboard = trainer_topics_keyboard(
        [
            KeyboardItem(id=1, title="Python"),
            KeyboardItem(id=2, title="SQL"),
        ]
    )

    callback_data = [row[0].callback_data for row in keyboard.inline_keyboard]

    assert callback_data == [
        TrainerTopicCallback(topic_id=1).pack(),
        TrainerTopicCallback(topic_id=2).pack(),
        MAIN_MENU,
    ]


def test_trainer_subtopics_keyboard_uses_subtopic_callbacks() -> None:
    keyboard = trainer_subtopics_keyboard(
        [
            KeyboardItem(id=10, title="Asyncio"),
            KeyboardItem(id=11, title="Typing"),
        ]
    )

    callback_data = [row[0].callback_data for row in keyboard.inline_keyboard]

    assert callback_data == [
        TrainerSubtopicCallback(subtopic_id=10).pack(),
        TrainerSubtopicCallback(subtopic_id=11).pack(),
        TRAINER_TOPICS,
        MAIN_MENU,
    ]


def test_trainer_selected_subtopic_keyboard_has_start_options() -> None:
    keyboard = trainer_selected_subtopic_keyboard()

    callback_data = [row[0].callback_data for row in keyboard.inline_keyboard]

    assert callback_data == [
        TRAINER_START_BEGIN,
        TRAINER_SELECT_NUMBER,
        TRAINER_TOPICS,
        MAIN_MENU,
    ]


def test_trainer_question_keyboard_has_answer_actions() -> None:
    keyboard = trainer_question_keyboard(question_id=42)

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert callback_data == [
        TrainerQuestionAnswerCallback(question_id=42, status=1).pack(),
        TrainerQuestionAnswerCallback(question_id=42, status=0).pack(),
        TrainerQuestionAnswerCallback(question_id=42, status=-1).pack(),
        TrainerQuestionAnswerTextCallback(question_id=42).pack(),
        TRAINER_SELECT_NUMBER,
        TRAINER_TOPICS,
        MAIN_MENU,
    ]


def test_interview_topics_keyboard_toggles_topics() -> None:
    keyboard = interview_topics_keyboard(
        [
            KeyboardItem(id=1, title="Python"),
            KeyboardItem(id=2, title="SQL"),
        ],
        selected_topic_ids={1},
    )

    buttons = [row[0] for row in keyboard.inline_keyboard]

    assert buttons[0].text == "[x] Python"
    assert buttons[0].callback_data == InterviewTopicCallback(topic_id=1).pack()
    assert buttons[1].text == "[ ] SQL"
    assert buttons[1].callback_data == InterviewTopicCallback(topic_id=2).pack()
    assert [button.callback_data for button in buttons[2:]] == [
        INTERVIEW_SELECT_ALL_TOPICS,
        INTERVIEW_SUBTOPICS,
        MAIN_MENU,
    ]


def test_interview_subtopics_keyboard_shows_start_when_enough_questions() -> None:
    keyboard = interview_subtopics_keyboard(
        [
            KeyboardItem(id=10, title="Asyncio"),
            KeyboardItem(id=11, title="Typing"),
        ],
        excluded_subtopic_ids={11},
        questions_count=15,
        minimum_questions=15,
    )

    buttons = [row[0] for row in keyboard.inline_keyboard]

    assert buttons[0].text == "[x] Asyncio"
    assert buttons[0].callback_data == InterviewSubtopicCallback(subtopic_id=10).pack()
    assert buttons[1].text == "[ ] Typing"
    assert buttons[1].callback_data == InterviewSubtopicCallback(subtopic_id=11).pack()
    assert buttons[2].text == "Начать интервью (15 вопросов)"
    assert buttons[2].callback_data == INTERVIEW_START
    assert [button.callback_data for button in buttons[3:]] == [
        INTERVIEW_TOPICS,
        MAIN_MENU,
    ]


def test_interview_subtopics_keyboard_blocks_start_when_not_enough_questions() -> None:
    keyboard = interview_subtopics_keyboard(
        [KeyboardItem(id=10, title="Asyncio")],
        excluded_subtopic_ids=set(),
        questions_count=8,
        minimum_questions=15,
    )

    start_button = keyboard.inline_keyboard[1][0]

    assert start_button.text == "Недостаточно вопросов: 8/15"
    assert start_button.callback_data == INTERVIEW_START


def test_interview_reset_active_keyboard_requires_explicit_choice() -> None:
    keyboard = interview_reset_active_keyboard()

    callback_data = [row[0].callback_data for row in keyboard.inline_keyboard]

    assert callback_data == [
        INTERVIEW_RESET_ACTIVE,
        INTERVIEW_KEEP_ACTIVE,
        INTERVIEW_SUBTOPICS,
    ]


def test_interview_question_keyboard_has_only_status_actions() -> None:
    keyboard = interview_question_keyboard(question_id=77)

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert callback_data == [
        InterviewAnswerCallback(question_id=77, status=1).pack(),
        InterviewAnswerCallback(question_id=77, status=0).pack(),
        InterviewAnswerCallback(question_id=77, status=-1).pack(),
    ]
