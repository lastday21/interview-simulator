from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import (
    INTERVIEW_KEEP_ACTIVE,
    INTERVIEW_MENU,
    INTERVIEW_NEW_SELECTION,
    INTERVIEW_RESET_ACTIVE,
    INTERVIEW_SELECT_ALL_TOPICS,
    INTERVIEW_START,
    INTERVIEW_SUBTOPICS,
    INTERVIEW_TOPICS,
    InterviewAnswerCallback,
    InterviewSubtopicCallback,
    InterviewTopicCallback,
)
from app.bot.fsm import InterviewStates
from app.bot.keyboards import (
    interview_active_keyboard,
    interview_question_keyboard,
    interview_reset_active_keyboard,
    interview_subtopics_keyboard,
    interview_topics_keyboard,
)
from app.bot.keyboards.navigation import back_to_main_menu_keyboard
from app.bot.messages import answer_split
from app.bot.routers.common import ensure_user
from app.repositories import ContentRepository, InterviewRepository, ProgressRepository

router = Router(name="interview")

INTERVIEW_QUESTIONS_COUNT = 15


def _status_label(status: int) -> str:
    if status == 1:
        return "Знаю"
    if status == 0:
        return "Не знаю"
    return "Сложно"


def _format_completion_result(
    *,
    total_questions: int,
    know_count: int,
    unknown_count: int,
    difficult_count: int,
    passed: bool,
) -> str:
    verdict = "Пройдено" if passed else "Не пройдено"
    return (
        "Собеседование завершено.\n\n"
        f"Знаю: {know_count}/{total_questions}\n"
        f"Не знаю: {unknown_count}/{total_questions}\n"
        f"Сложно: {difficult_count}/{total_questions}\n\n"
        f"Вердикт: {verdict}"
    )


async def finish_active_interview(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    user_id: int,
) -> None:
    completion = await InterviewRepository(session).finish_interview(user_id=user_id)
    if completion is None:
        await message.answer("Собеседование еще не завершено.")
        return

    progress_repository = ProgressRepository(session)
    for question_id, status in completion.question_statuses:
        await progress_repository.upsert_question_status(
            user_id=user_id,
            question_id=question_id,
            status=status,
        )

    unknown_count = sum(1 for _, status in completion.question_statuses if status == 0)
    difficult_count = sum(
        1 for _, status in completion.question_statuses if status == -1
    )

    await state.clear()
    await answer_split(
        message,
        _format_completion_result(
            total_questions=completion.total_questions,
            know_count=completion.know_count,
            unknown_count=unknown_count,
            difficult_count=difficult_count,
            passed=completion.passed,
        ),
        reply_markup=back_to_main_menu_keyboard(),
    )


def _int_set_from_state(data: dict[str, object], key: str) -> set[int]:
    value = data.get(key)
    if not isinstance(value, list):
        return set()

    return {item for item in value if isinstance(item, int)}


def _sorted_ids(ids: set[int]) -> list[int]:
    return sorted(ids)


async def _resolve_interview_selection(
    state: FSMContext,
    session: AsyncSession,
) -> tuple[list[int], int]:
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
    await state.update_data(
        selected_topic_ids=_sorted_ids(selected_topic_ids),
        excluded_subtopic_ids=_sorted_ids(excluded_subtopic_ids),
        selected_subtopic_ids=selected_subtopic_ids,
        selected_questions_count=questions_count,
    )
    return selected_subtopic_ids, questions_count


async def _selected_topic_ids_from_state(
    state: FSMContext,
    session: AsyncSession,
) -> set[int]:
    data = await state.get_data()
    selected_topic_ids_value = data.get("selected_topic_ids")
    if isinstance(selected_topic_ids_value, list):
        return {
            topic_id
            for topic_id in selected_topic_ids_value
            if isinstance(topic_id, int)
        }

    topics = await ContentRepository(session).list_topics()
    selected_topic_ids = {topic.id for topic in topics}
    await state.update_data(selected_topic_ids=_sorted_ids(selected_topic_ids))
    return selected_topic_ids


async def open_interview_selection(
    message: Message, state: FSMContext, session: AsyncSession
) -> None:
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

    await answer_split(
        message,
        "Собеседование: выбери темы. По умолчанию включены все темы.",
        reply_markup=interview_topics_keyboard(
            topics,
            selected_topic_ids={topic.id for topic in topics},
        ),
    )


async def open_interview(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    user_id: int,
) -> None:
    if await InterviewRepository(session).has_active_interview(user_id):
        await state.set_state(InterviewStates.active)
        await state.update_data(pending_interview_question_ids=[])
        await message.answer(
            "У тебя есть незавершённое собеседование. Продолжить его или выбрать новый набор вопросов?",
            reply_markup=interview_active_keyboard(),
        )
        return

    await open_interview_selection(message, state, session)


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
    selected_topic_ids = await _selected_topic_ids_from_state(state, session)
    state_data = await state.get_data()
    excluded_subtopic_ids = _int_set_from_state(state_data, "excluded_subtopic_ids")

    content_repository = ContentRepository(session)
    subtopics = await content_repository.list_subtopics_by_topic_ids(
        _sorted_ids(selected_topic_ids)
    )
    selected_subtopic_ids, questions_count = await _resolve_interview_selection(
        state,
        session,
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


async def open_current_interview_question(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    user_id: int,
) -> None:
    current_question = await InterviewRepository(session).get_current_question(user_id)
    await state.set_state(InterviewStates.active)

    if current_question is None:
        await state.update_data(current_interview_question_id=None)
        await finish_active_interview(message, state, session, user_id=user_id)
        return

    await state.update_data(current_interview_question_id=current_question.question_id)
    await answer_split(
        message,
        f"Вопрос {current_question.position}/{current_question.total_questions}\n"
        f"{current_question.topic_title} / {current_question.subtopic_title}\n\n"
        f"{current_question.question_text}",
        reply_markup=interview_question_keyboard(current_question.question_id),
    )


@router.message(Command("interview"))
async def handle_interview_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    user = await ensure_user(message.from_user, session)
    if user is None:
        await message.answer("Не удалось определить пользователя.")
        return
    await open_interview(message, state, session, user_id=user.id)


@router.callback_query(F.data == INTERVIEW_MENU)
async def handle_interview_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    if user is None:
        if isinstance(callback.message, Message):
            await callback.message.answer("Не удалось определить пользователя.")
        return
    if isinstance(callback.message, Message):
        await open_interview(callback.message, state, session, user_id=user.id)


@router.callback_query(F.data == INTERVIEW_NEW_SELECTION)
async def handle_interview_new_selection_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_interview_selection(callback.message, state, session)


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

    user = await ensure_user(callback.from_user, session)
    if user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    selected_subtopic_ids, questions_count = await _resolve_interview_selection(
        state,
        session,
    )
    if questions_count < INTERVIEW_QUESTIONS_COUNT:
        await callback.message.answer(
            f"Нельзя начать собеседование: нужно минимум "
            f"{INTERVIEW_QUESTIONS_COUNT} вопросов. Сейчас доступно: "
            f"{questions_count}."
        )
        return

    content_repository = ContentRepository(session)
    question_ids = await content_repository.select_interview_question_ids(
        subtopic_ids=selected_subtopic_ids,
        limit=INTERVIEW_QUESTIONS_COUNT,
    )
    if len(question_ids) < INTERVIEW_QUESTIONS_COUNT:
        await callback.message.answer(
            f"Не удалось собрать {INTERVIEW_QUESTIONS_COUNT} уникальных вопросов."
        )
        return

    interview_repository = InterviewRepository(session)
    if await interview_repository.has_active_interview(user.id):
        await state.update_data(pending_interview_question_ids=question_ids)
        await callback.message.answer(
            "У тебя уже есть незавершенное собеседование. Сбросить его и начать новое?",
            reply_markup=interview_reset_active_keyboard(),
        )
        return

    await interview_repository.start_interview(
        user_id=user.id,
        question_ids=question_ids,
    )
    await state.set_state(InterviewStates.active)
    await state.update_data(active_interview_question_ids=question_ids)
    await callback.message.answer(
        f"Собеседование начато: {INTERVIEW_QUESTIONS_COUNT} вопросов."
    )
    await open_current_interview_question(
        callback.message,
        state,
        session,
        user_id=user.id,
    )


@router.callback_query(F.data == INTERVIEW_RESET_ACTIVE)
async def handle_interview_reset_active_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    user = await ensure_user(callback.from_user, session)
    if user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    state_data = await state.get_data()
    question_ids = _int_set_from_state(state_data, "pending_interview_question_ids")
    if len(question_ids) < INTERVIEW_QUESTIONS_COUNT:
        selected_subtopic_ids, questions_count = await _resolve_interview_selection(
            state,
            session,
        )
        if questions_count < INTERVIEW_QUESTIONS_COUNT:
            await callback.message.answer(
                f"Нельзя начать собеседование: нужно минимум "
                f"{INTERVIEW_QUESTIONS_COUNT} вопросов."
            )
            return
        question_ids = set(
            await ContentRepository(session).select_interview_question_ids(
                subtopic_ids=selected_subtopic_ids,
                limit=INTERVIEW_QUESTIONS_COUNT,
            )
        )

    ordered_question_ids = _sorted_ids(question_ids)
    if len(ordered_question_ids) < INTERVIEW_QUESTIONS_COUNT:
        await callback.message.answer(
            f"Не удалось собрать {INTERVIEW_QUESTIONS_COUNT} уникальных вопросов."
        )
        return

    await InterviewRepository(session).start_interview(
        user_id=user.id,
        question_ids=ordered_question_ids[:INTERVIEW_QUESTIONS_COUNT],
        reset_existing=True,
    )
    await state.set_state(InterviewStates.active)
    await state.update_data(
        active_interview_question_ids=ordered_question_ids[:INTERVIEW_QUESTIONS_COUNT],
        pending_interview_question_ids=[],
    )
    await callback.message.answer(
        f"Старое собеседование сброшено. Новое начато: "
        f"{INTERVIEW_QUESTIONS_COUNT} вопросов."
    )
    await open_current_interview_question(
        callback.message,
        state,
        session,
        user_id=user.id,
    )


@router.callback_query(F.data == INTERVIEW_KEEP_ACTIVE)
async def handle_interview_keep_active_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    user = await ensure_user(callback.from_user, session)
    if user is None:
        if isinstance(callback.message, Message):
            await callback.message.answer("Не удалось определить пользователя.")
        return

    await state.set_state(InterviewStates.active)
    await state.update_data(pending_interview_question_ids=[])
    if isinstance(callback.message, Message):
        await callback.message.answer("Текущее собеседование сохранено.")
        await open_current_interview_question(
            callback.message,
            state,
            session,
            user_id=user.id,
        )


@router.callback_query(InterviewAnswerCallback.filter())
async def handle_interview_answer_callback(
    callback: CallbackQuery,
    callback_data: InterviewAnswerCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    if callback_data.status not in {-1, 0, 1}:
        await callback.message.answer("Некорректный статус ответа.")
        return

    user = await ensure_user(callback.from_user, session)
    if user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    result = await InterviewRepository(session).answer_question(
        user_id=user.id,
        question_id=callback_data.question_id,
        status=callback_data.status,
    )
    if result.already_answered:
        await callback.message.answer("Этот вопрос уже был отвечен.")
        return
    if not result.is_current_question:
        await callback.message.answer("Это не текущий вопрос собеседования.")
        return
    if not result.accepted:
        await callback.message.answer("Не удалось сохранить ответ.")
        return

    await callback.message.answer(
        f"Ответ сохранен: {_status_label(callback_data.status)}."
    )
    if result.completed:
        await state.update_data(current_interview_question_id=None)
        await finish_active_interview(
            callback.message,
            state,
            session,
            user_id=user.id,
        )
        return

    await open_current_interview_question(
        callback.message,
        state,
        session,
        user_id=user.id,
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
