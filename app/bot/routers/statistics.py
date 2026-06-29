from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import STATISTICS_MENU
from app.bot.fsm import StatisticsStates
from app.bot.keyboards.navigation import back_to_main_menu_keyboard
from app.bot.messages import answer_split
from app.bot.routers.common import ensure_user
from app.repositories import (
    ContentRepository,
    InterviewRepository,
    InterviewStats,
    TopicStats,
)

router = Router(name="statistics")


def format_topic_stats(topic_stats: list[TopicStats]) -> str:
    if not topic_stats:
        return "По темам пока нет данных."

    lines = ["Темы:"]
    for item in topic_stats:
        lines.append(
            f"- {item.title}: всего {item.total_questions}, "
            f"оценено {item.answered_questions}, "
            f"знаю {item.known_questions}, "
            f"не знаю {item.unknown_questions}, "
            f"сложно {item.difficult_questions}, "
            f"score {item.score}"
        )
    return "\n".join(lines)


def format_interview_stats(interview_stats: InterviewStats) -> str:
    if interview_stats.completed_count == 0:
        return "Собеседования: завершенных пока нет."

    return (
        "Собеседования:\n"
        f"- завершено: {interview_stats.completed_count}\n"
        f"- среднее Знаю: {interview_stats.average_know_count:.1f}/15\n"
        f"- пройдено: {interview_stats.passed_percent:.0f}%"
    )


async def open_statistics(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    *,
    user_id: int,
) -> None:
    await state.set_state(StatisticsStates.menu)

    topic_stats = await ContentRepository(session).get_topic_stats(user_id)
    interview_stats = await InterviewRepository(session).get_completed_stats(user_id)
    await answer_split(
        message,
        f"{format_topic_stats(topic_stats)}\n\n{format_interview_stats(interview_stats)}",
        reply_markup=back_to_main_menu_keyboard(),
    )


@router.message(Command("statistic"))
async def handle_statistics_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    user = await ensure_user(message.from_user, session)
    if user is None:
        await message.answer("Не удалось определить пользователя.")
        return
    await open_statistics(message, state, session, user_id=user.id)


@router.callback_query(F.data == STATISTICS_MENU)
async def handle_statistics_callback(
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
        await open_statistics(callback.message, state, session, user_id=user.id)
