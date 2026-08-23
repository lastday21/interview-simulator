from collections.abc import Sequence
from typing import Protocol

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    INTERVIEW_KEEP_ACTIVE,
    INTERVIEW_NEW_SELECTION,
    INTERVIEW_RESET_ACTIVE,
    INTERVIEW_SELECT_ALL_TOPICS,
    INTERVIEW_START,
    INTERVIEW_SUBTOPICS,
    INTERVIEW_TOPICS,
    MAIN_MENU,
    InterviewAnswerCallback,
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


def interview_reset_active_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Сбросить и начать новое",
                    callback_data=INTERVIEW_RESET_ACTIVE,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Оставить текущее",
                    callback_data=INTERVIEW_KEEP_ACTIVE,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад к подтемам",
                    callback_data=INTERVIEW_SUBTOPICS,
                )
            ],
        ]
    )


def interview_active_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Продолжить текущее",
                    callback_data=INTERVIEW_KEEP_ACTIVE,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Выбрать новое",
                    callback_data=INTERVIEW_NEW_SELECTION,
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


def interview_question_keyboard(question_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Знаю",
                    callback_data=InterviewAnswerCallback(
                        question_id=question_id,
                        status=1,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Не знаю",
                    callback_data=InterviewAnswerCallback(
                        question_id=question_id,
                        status=0,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Сложно",
                    callback_data=InterviewAnswerCallback(
                        question_id=question_id,
                        status=-1,
                    ).pack(),
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
