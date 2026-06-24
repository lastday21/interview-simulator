from collections.abc import Sequence
from typing import Protocol

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    MAIN_MENU,
    TRAINER_TOPICS,
    TrainerSubtopicCallback,
    TrainerTopicCallback,
)


class TitledItem(Protocol):
    @property
    def id(self) -> int: ...

    @property
    def title(self) -> str: ...


def trainer_topics_keyboard(topics: Sequence[TitledItem]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=topic.title,
                callback_data=TrainerTopicCallback(topic_id=topic.id).pack(),
            )
        ]
        for topic in topics
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад в меню",
                callback_data=MAIN_MENU,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trainer_subtopics_keyboard(
    subtopics: Sequence[TitledItem],
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=subtopic.title,
                callback_data=TrainerSubtopicCallback(
                    subtopic_id=subtopic.id,
                ).pack(),
            )
        ]
        for subtopic in subtopics
    ]
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад к темам",
                callback_data=TRAINER_TOPICS,
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="Назад в меню",
                callback_data=MAIN_MENU,
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trainer_selected_subtopic_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Назад к темам",
                    callback_data=TRAINER_TOPICS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад в меню",
                    callback_data=MAIN_MENU,
                )
            ],
        ]
    )
