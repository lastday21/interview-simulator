from dataclasses import dataclass

from aiogram import Dispatcher

from app.bot.callbacks import (
    INTERVIEW_MENU,
    MAIN_MENU,
    STATISTICS_MENU,
    TRAINER_MENU,
    TRAINER_TOPICS,
    TrainerSubtopicCallback,
    TrainerTopicCallback,
)
from app.bot.dispatcher import create_dispatcher
from app.bot.keyboards import (
    main_menu_keyboard,
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
