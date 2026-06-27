from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import (
    INTERVIEW_MENU,
    INTERVIEW_SELECT_ALL_TOPICS,
    INTERVIEW_START,
    INTERVIEW_SUBTOPICS,
    INTERVIEW_TOPICS,
    InterviewSubtopicCallback,
    InterviewTopicCallback,
)
from app.bot.fsm import InterviewStates
from app.bot.keyboards import interview_subtopics_keyboard, interview_topics_keyboard
from app.bot.keyboards.navigation import back_to_main_menu_keyboard
from app.bot.routers.common import ensure_user
from app.repositories import ContentRepository

router = Router(name="interview")

INTERVIEW_QUESTIONS_COUNT = 15


def _int_set_from_state(data: dict[str, object], key: str) -> set[int]:
    value = data.get(key)
    if not isinstance(value, list):
        return set()

    return {item for item in value if isinstance(item, int)}


def _sorted_ids(ids: set[int]) -> list[int]:
    return sorted(ids)


async def _selected_topic_ids_from_state(
    state: FSMContext,
    session: AsyncSession,
) -> set[int]:
    data = await state.get_data()
    selected_topic_ids = _int_set_from_state(data, "selected_topic_ids")
    if selected_topic_ids:
        return selected_topic_ids

    topics = await ContentRepository(session).list_topics()
    selected_topic_ids = {topic.id for topic in topics}
    await state.update_data(selected_topic_ids=_sorted_ids(selected_topic_ids))
    return selected_topic_ids


async def open_interview(message: Message, state: FSMContext, session: AsyncSession) -> None:
    topics = await ContentRepository(session).list_topics()
    await state.set_state(InterviewStates.select_topics)
    await state.set_data(
        {
            "selected_topic_ids": [topic.id for topic in topics],
            "excluded_subtopic_ids": [],
        }
    )

    if not topics:
        await message.answer(
            "Пока нет тем. Сначала импортируй вопросы.",
            reply_markup=back_to_main_menu_keyboard(),
        )
        return

    await message.answer(
        "Собеседование: выбери темы. По умолчанию включены все темы.",
        reply_markup=interview_topics_keyboard(
            topics,
            selected_topic_ids={topic.id for topic in topics},
        ),
    )


async def open_interview_topics(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    topics = await ContentRepository(session).list_topics()
    selected_topic_ids = await _selected_topic_ids_from_state(state, session)
    await state.set_state(InterviewStates.select_topics)

    await message.answer(
        "Выбери темы для собеседования:",
        reply_markup=interview_topics_keyboard(
            topics,
            selected_topic_ids=selected_topic_ids,
        ),
    )


async def open_interview_subtopics(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    content_repository = ContentRepository(session)
    selected_topic_ids = await _selected_topic_ids_from_state(state, session)
    state_data = await state.get_data()
    excluded_subtopic_ids = _int_set_from_state(state_data, "excluded_subtopic_ids")

    subtopics = await content_repository.list_subtopics_by_topic_ids(
        _sorted_ids(selected_topic_ids)
    )
    selected_subtopic_ids = [
        subtopic.id
        for subtopic in subtopics
        if subtopic.id not in excluded_subtopic_ids
    ]
    questions_count = await content_repository.count_questions(
        subtopic_ids=selected_subtopic_ids
    )
    await state.set_state(InterviewStates.select_subtopics)
    await state.update_data(
        selected_topic_ids=_sorted_ids(selected_topic_ids),
        excluded_subtopic_ids=_sorted_ids(excluded_subtopic_ids),
        selected_subtopic_ids=selected_subtopic_ids,
        selected_questions_count=questions_count,
    )

    if not subtopics:
        await message.answer(
            "В выбранных темах нет подтем.",
            reply_markup=interview_subtopics_keyboard(
                [],
                excluded_subtopic_ids=set(),
                questions_count=0,
                minimum_questions=INTERVIEW_QUESTIONS_COUNT,
            ),
        )
        return

    await message.answer(
        "Выбери подтемы. По умолчанию включены все подтемы выбранных тем.\n"
        f"Доступно вопросов: {questions_count}. Нужно минимум: "
        f"{INTERVIEW_QUESTIONS_COUNT}.",
        reply_markup=interview_subtopics_keyboard(
            subtopics,
            excluded_subtopic_ids=excluded_subtopic_ids,
            questions_count=questions_count,
            minimum_questions=INTERVIEW_QUESTIONS_COUNT,
        ),
    )


@router.message(Command("interview"))
async def handle_interview_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(message.from_user, session)
    await open_interview(message, state, session)


@router.callback_query(F.data == INTERVIEW_MENU)
async def handle_interview_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(callback.from_user, session)
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_interview(callback.message, state, session)


@router.callback_query(F.data == INTERVIEW_TOPICS)
async def handle_interview_topics_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_interview_topics(callback.message, state, session)


@router.callback_query(F.data == INTERVIEW_SELECT_ALL_TOPICS)
async def handle_interview_select_all_topics_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    topics = await ContentRepository(session).list_topics()
    await state.update_data(
        selected_topic_ids=[topic.id for topic in topics],
        excluded_subtopic_ids=[],
    )
    if isinstance(callback.message, Message):
        await open_interview_topics(callback.message, state, session)


@router.callback_query(F.data == INTERVIEW_SUBTOPICS)
async def handle_interview_subtopics_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_interview_subtopics(callback.message, state, session)


@router.callback_query(F.data == INTERVIEW_START)
async def handle_interview_start_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    await open_interview_subtopics(callback.message, state, session)
    state_data = await state.get_data()
    questions_count = state_data.get("selected_questions_count")
    if not isinstance(questions_count, int) or questions_count < INTERVIEW_QUESTIONS_COUNT:
        await callback.message.answer(
            f"Нельзя начать собеседование: нужно минимум "
            f"{INTERVIEW_QUESTIONS_COUNT} вопросов."
        )
        return

    await callback.message.answer(
        "Выбор готов. Создание активной сессии будет следующим шагом."
    )


@router.callback_query(InterviewTopicCallback.filter())
async def handle_interview_topic_callback(
    callback: CallbackQuery,
    callback_data: InterviewTopicCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    state_data = await state.get_data()
    selected_topic_ids = _int_set_from_state(state_data, "selected_topic_ids")
    if callback_data.topic_id in selected_topic_ids:
        selected_topic_ids.remove(callback_data.topic_id)
    else:
        selected_topic_ids.add(callback_data.topic_id)

    topic_subtopics = await ContentRepository(session).list_subtopics(
        callback_data.topic_id
    )
    topic_subtopic_ids = {subtopic.id for subtopic in topic_subtopics}
    excluded_subtopic_ids = _int_set_from_state(state_data, "excluded_subtopic_ids")
    excluded_subtopic_ids -= topic_subtopic_ids

    await state.update_data(
        selected_topic_ids=_sorted_ids(selected_topic_ids),
        excluded_subtopic_ids=_sorted_ids(excluded_subtopic_ids),
    )
    if isinstance(callback.message, Message):
        await open_interview_topics(callback.message, state, session)


@router.callback_query(InterviewSubtopicCallback.filter())
async def handle_interview_subtopic_callback(
    callback: CallbackQuery,
    callback_data: InterviewSubtopicCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    state_data = await state.get_data()
    excluded_subtopic_ids = _int_set_from_state(state_data, "excluded_subtopic_ids")
    if callback_data.subtopic_id in excluded_subtopic_ids:
        excluded_subtopic_ids.remove(callback_data.subtopic_id)
    else:
        excluded_subtopic_ids.add(callback_data.subtopic_id)

    await state.update_data(excluded_subtopic_ids=_sorted_ids(excluded_subtopic_ids))
    if isinstance(callback.message, Message):
        await open_interview_subtopics(callback.message, state, session)
