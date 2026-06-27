from collections.abc import Sequence
from typing import Protocol

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    INTERVIEW_SELECT_ALL_TOPICS,
    INTERVIEW_START,
    INTERVIEW_SUBTOPICS,
    INTERVIEW_TOPICS,
    MAIN_MENU,
    InterviewSubtopicCallback,
    InterviewTopicCallback,
)


class TitledItem(Protocol):
    @property
    def id(self) -> int: ...

    @property
    def title(self) -> str: ...


def interview_topics_keyboard(
    topics: Sequence[TitledItem],
    *,
    selected_topic_ids: set[int],
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'[x]' if topic.id in selected_topic_ids else '[ ]'} "
                f"{topic.title}",
                callback_data=InterviewTopicCallback(topic_id=topic.id).pack(),
            )
        ]
        for topic in topics
    ]
    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="Выбрать все темы",
                    callback_data=INTERVIEW_SELECT_ALL_TOPICS,
                )
            ],
            [
                InlineKeyboardButton(
                    text="К подтемам",
                    callback_data=INTERVIEW_SUBTOPICS,
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
    return InlineKeyboardMarkup(inline_keyboard=rows)


def interview_subtopics_keyboard(
    subtopics: Sequence[TitledItem],
    *,
    excluded_subtopic_ids: set[int],
    questions_count: int,
    minimum_questions: int,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{'[ ]' if subtopic.id in excluded_subtopic_ids else '[x]'} "
                f"{subtopic.title}",
                callback_data=InterviewSubtopicCallback(subtopic_id=subtopic.id).pack(),
            )
        ]
        for subtopic in subtopics
    ]

    if questions_count >= minimum_questions:
        start_text = f"Начать интервью ({questions_count} вопросов)"
    else:
        start_text = f"Недостаточно вопросов: {questions_count}/{minimum_questions}"

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=start_text,
                    callback_data=INTERVIEW_START,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад к темам",
                    callback_data=INTERVIEW_TOPICS,
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
    return InlineKeyboardMarkup(inline_keyboard=rows)
