from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import (
    TRAINER_MENU,
    TRAINER_TOPICS,
    TrainerSubtopicCallback,
    TrainerTopicCallback,
)
from app.bot.fsm import TrainerStates
from app.bot.keyboards import (
    trainer_selected_subtopic_keyboard,
    trainer_subtopics_keyboard,
    trainer_topics_keyboard,
)
from app.bot.routers.common import ensure_user
from app.repositories import ContentRepository

router = Router(name="trainer")


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
    subtopics = await ContentRepository(session).list_subtopics(topic_id)
    await state.set_state(TrainerStates.select_subtopic)
    await state.update_data(topic_id=topic_id)

    if not subtopics:
        await state.set_state(TrainerStates.select_topic)
        await state.set_data({})
        await message.answer(
            "В этой теме пока нет подтем.",
            reply_markup=trainer_topics_keyboard(
                await ContentRepository(session).list_topics()
            ),
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
) -> None:
    questions_count = await ContentRepository(session).count_questions(
        subtopic_ids=[subtopic_id]
    )
    await state.set_state(TrainerStates.questions_list)
    await state.update_data(subtopic_id=subtopic_id)

    await message.answer(
        f"Подтема выбрана. Вопросов: {questions_count}.\n"
        "Следующий шаг - список вопросов.",
        reply_markup=trainer_selected_subtopic_keyboard(),
    )


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


@router.callback_query(TrainerTopicCallback.filter())
async def handle_topic_callback(
    callback: CallbackQuery,
    callback_data: TrainerTopicCallback,
    state: FSMContext,
    session: AsyncSession,
) -> None:
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
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_selected_subtopic(
            callback.message,
            state,
            session,
            subtopic_id=callback_data.subtopic_id,
        )
