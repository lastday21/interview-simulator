from collections.abc import Sequence

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import (
    TRAINER_MENU,
    TRAINER_SELECT_NUMBER,
    TRAINER_START_BEGIN,
    TRAINER_TOPICS,
    TrainerQuestionAnswerCallback,
    TrainerQuestionAnswerTextCallback,
    TrainerSubtopicCallback,
    TrainerTopicCallback,
)
from app.bot.fsm import TrainerStates
from app.bot.keyboards import (
    trainer_question_keyboard,
    trainer_selected_subtopic_keyboard,
    trainer_subtopics_keyboard,
    trainer_topics_keyboard,
)
from app.bot.routers.common import ensure_user
from app.db.models import Question
from app.repositories import ContentRepository, ProgressRepository, QuestionWithStatus

router = Router(name="trainer")

TELEGRAM_MESSAGE_LIMIT = 3900
QUESTION_PREVIEW_LIMIT = 100


def _status_label(status: int | None) -> str:
    if status == 1:
        return "Знаю"
    if status == 0:
        return "Не знаю"
    if status == -1:
        return "Сложно"
    return "Без статуса"


def _question_preview(text: str) -> str:
    preview = " ".join(text.split())
    if len(preview) <= QUESTION_PREVIEW_LIMIT:
        return preview
    return f"{preview[: QUESTION_PREVIEW_LIMIT - 3]}..."


def format_trainer_questions_list(
    questions: Sequence[QuestionWithStatus],
) -> str:
    if not questions:
        return "В этой подтеме пока нет вопросов."

    lines = ["Вопросы подтемы:", ""]
    lines.extend(
        f"{item.question.position}. [{_status_label(item.status)}] "
        f"{_question_preview(item.question.question_text)}"
        for item in questions
    )
    return "\n".join(lines)


def _split_message(text: str) -> list[str]:
    chunks: list[str] = []
    current = ""

    for line in text.splitlines():
        next_part = line if not current else f"{current}\n{line}"
        if len(next_part) <= TELEGRAM_MESSAGE_LIMIT:
            current = next_part
            continue

        if current:
            chunks.append(current)
        current = line

    if current:
        chunks.append(current)

    return chunks or [""]


async def _answer_split(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chunks = _split_message(text)
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        await message.answer(chunk, reply_markup=markup)


async def open_trainer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    topics = await ContentRepository(session).list_topics()
    await state.set_state(TrainerStates.select_topic)
    await state.set_data({})

    if not topics:
        await message.answer("Пока нет тем. Сначала импортируй вопросы.")
        return

    await message.answer(
        "Выбери тему:",
        reply_markup=trainer_topics_keyboard(topics),
    )


async def open_subtopics(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    topic_id: int,
) -> None:
    content_repository = ContentRepository(session)
    subtopics = await content_repository.list_subtopics(topic_id)
    await state.set_state(TrainerStates.select_subtopic)
    await state.update_data(topic_id=topic_id)

    if not subtopics:
        await state.set_state(TrainerStates.select_topic)
        await state.set_data({})
        await message.answer(
            "В этой теме пока нет подтем.",
            reply_markup=trainer_topics_keyboard(await content_repository.list_topics()),
        )
        return

    await message.answer(
        "Выбери подтему:",
        reply_markup=trainer_subtopics_keyboard(subtopics),
    )


async def open_selected_subtopic(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    subtopic_id: int,
    *,
    user_id: int | None,
) -> None:
    questions = await ContentRepository(session).list_questions(
        subtopic_id,
        user_id=user_id,
    )
    await state.set_state(TrainerStates.questions_list)
    await state.update_data(
        subtopic_id=subtopic_id,
        current_question_id=None,
        current_question_position=None,
    )

    await _answer_split(
        message,
        format_trainer_questions_list(questions),
        reply_markup=trainer_selected_subtopic_keyboard(),
    )


async def open_question(
    message: Message,
    state: FSMContext,
    question: Question,
) -> None:
    await state.set_state(TrainerStates.question)
    await state.update_data(
        current_question_id=question.id,
        current_question_position=question.position,
    )
    await _answer_split(
        message,
        f"Вопрос {question.position}\n\n{question.question_text}",
        reply_markup=trainer_question_keyboard(question.id),
    )


def _subtopic_id_from_state(data: dict[str, object]) -> int | None:
    subtopic_id = data.get("subtopic_id")
    if isinstance(subtopic_id, int):
        return subtopic_id
    return None


def _current_question_id_from_state(data: dict[str, object]) -> int | None:
    question_id = data.get("current_question_id")
    if isinstance(question_id, int):
        return question_id
    return None


@router.message(Command("trainer"))
async def handle_trainer_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(message.from_user, session)
    await open_trainer(message, state, session)


@router.callback_query(F.data == TRAINER_MENU)
async def handle_trainer_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(callback.from_user, session)
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_trainer(callback.message, state, session)


@router.callback_query(F.data == TRAINER_TOPICS)
async def handle_trainer_topics_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_trainer(callback.message, state, session)


@router.callback_query(F.data == TRAINER_START_BEGIN)
async def handle_trainer_start_begin_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    subtopic_id = _subtopic_id_from_state(await state.get_data())
    if subtopic_id is None:
        await callback.message.answer("Сначала выбери подтему.")
        await open_trainer(callback.message, state, session)
        return

    questions = await ContentRepository(session).list_questions(subtopic_id)
    if not questions:
        await callback.message.answer("В этой подтеме пока нет вопросов.")
        return

    await open_question(callback.message, state, questions[0].question)


@router.callback_query(F.data == TRAINER_SELECT_NUMBER)
async def handle_trainer_select_number_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await callback.answer()
    await state.set_state(TrainerStates.wait_question_number)
    if isinstance(callback.message, Message):
        await callback.message.answer("Введи номер вопроса из списка.")


@router.callback_query(TrainerQuestionAnswerTextCallback.filter())
async def handle_trainer_answer_text_callback(
    callback: CallbackQuery,
    callback_data: TrainerQuestionAnswerTextCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    current_question_id = _current_question_id_from_state(await state.get_data())
    if current_question_id != callback_data.question_id:
        await callback.message.answer("Этот вопрос уже не активен.")
        return

    question = await ContentRepository(session).get_question(callback_data.question_id)
    if question is None:
        await callback.message.answer("Вопрос не найден.")
        return

    await _answer_split(
        callback.message,
        f"Ответ на вопрос {question.position}\n\n{question.answer_text}",
        reply_markup=trainer_question_keyboard(question.id),
    )


@router.callback_query(TrainerQuestionAnswerCallback.filter())
async def handle_trainer_question_answer_callback(
    callback: CallbackQuery,
    callback_data: TrainerQuestionAnswerCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    state_data = await state.get_data()
    current_question_id = _current_question_id_from_state(state_data)
    if current_question_id != callback_data.question_id:
        await callback.message.answer("Этот вопрос уже обработан.")
        return

    if callback_data.status not in {-1, 0, 1}:
        await callback.message.answer("Некорректный статус ответа.")
        return

    subtopic_id = _subtopic_id_from_state(state_data)
    if subtopic_id is None:
        await callback.message.answer("Сначала выбери подтему через /trainer.")
        await open_trainer(callback.message, state, session)
        return

    user = await ensure_user(callback.from_user, session)
    if user is None:
        await callback.message.answer("Не удалось определить пользователя.")
        return

    content_repository = ContentRepository(session)
    question = await content_repository.get_question(callback_data.question_id)
    if question is None:
        await callback.message.answer("Вопрос не найден.")
        return

    await ProgressRepository(session).upsert_question_status(
        user_id=user.id,
        question_id=question.id,
        status=callback_data.status,
    )

    next_question = await content_repository.get_next_question(
        subtopic_id=subtopic_id,
        current_position=question.position,
    )
    await callback.message.answer(f"Статус сохранен: {_status_label(callback_data.status)}.")

    if next_question is None:
        await callback.message.answer("В этой подтеме вопросы закончились.")
        await open_selected_subtopic(
            callback.message,
            state,
            session,
            subtopic_id=subtopic_id,
            user_id=user.id,
        )
        return

    await open_question(callback.message, state, next_question)


@router.callback_query(TrainerTopicCallback.filter())
async def handle_topic_callback(
    callback: CallbackQuery,
    callback_data: TrainerTopicCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await ensure_user(callback.from_user, session)
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_subtopics(
            callback.message,
            state,
            session,
            topic_id=callback_data.topic_id,
        )


@router.callback_query(TrainerSubtopicCallback.filter())
async def handle_subtopic_callback(
    callback: CallbackQuery,
    callback_data: TrainerSubtopicCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user = await ensure_user(callback.from_user, session)
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_selected_subtopic(
            callback.message,
            state,
            session,
            subtopic_id=callback_data.subtopic_id,
            user_id=user.id if user is not None else None,
        )


@router.message(StateFilter(TrainerStates.wait_question_number))
async def handle_question_number_message(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    subtopic_id = _subtopic_id_from_state(await state.get_data())
    if subtopic_id is None:
        await message.answer("Сначала выбери подтему через /trainer.")
        await open_trainer(message, state, session)
        return

    raw_number = (message.text or "").strip()
    if not raw_number.isdigit():
        await message.answer("Введи номер вопроса числом.")
        return

    question = await ContentRepository(session).get_question_by_position(
        subtopic_id=subtopic_id,
        position=int(raw_number),
    )
    if question is None:
        await message.answer("В этой подтеме нет вопроса с таким номером.")
        return

    await open_question(message, state, question)
