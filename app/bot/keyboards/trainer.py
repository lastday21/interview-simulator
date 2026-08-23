from collections.abc import Sequence
from typing import Protocol

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    MAIN_MENU,
    TRAINER_REVIEW_WEAK,
    TRAINER_SELECT_NUMBER,
    TRAINER_START_BEGIN,
    TRAINER_SUBTOPICS,
    TRAINER_TOPICS,
    TrainerQuestionAnswerCallback,
    TrainerQuestionAnswerTextCallback,
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
                text="Повторить Не знаю/Сложно",
                callback_data=TRAINER_REVIEW_WEAK,
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
                    text="С начала",
                    callback_data=TRAINER_START_BEGIN,
                )
            ],
            [
                InlineKeyboardButton(
                    text="С конкретного вопроса",
                    callback_data=TRAINER_SELECT_NUMBER,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад к подтемам",
                    callback_data=TRAINER_SUBTOPICS,
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


def trainer_question_keyboard(
    question_id: int,
    *,
    show_select_number: bool = True,
    back_to_subtopics: bool = True,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="Знаю",
                callback_data=TrainerQuestionAnswerCallback(
                    question_id=question_id,
                    status=1,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Не знаю",
                callback_data=TrainerQuestionAnswerCallback(
                    question_id=question_id,
                    status=0,
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Сложно",
                callback_data=TrainerQuestionAnswerCallback(
                    question_id=question_id,
                    status=-1,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Ответ",
                callback_data=TrainerQuestionAnswerTextCallback(
                    question_id=question_id,
                ).pack(),
            ),
        ],
    ]

    if show_select_number:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Выбрать другой номер",
                    callback_data=TRAINER_SELECT_NUMBER,
                )
            ],
        )

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=("Назад к подтемам" if back_to_subtopics else "Назад к темам"),
                    callback_data=(
                        TRAINER_SUBTOPICS if back_to_subtopics else TRAINER_TOPICS
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад в меню",
                    callback_data=MAIN_MENU,
                )
            ],
        ],
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)
