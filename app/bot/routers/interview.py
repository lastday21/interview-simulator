from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import INTERVIEW_MENU
from app.bot.fsm import InterviewStates
from app.bot.keyboards.navigation import back_to_main_menu_keyboard
from app.bot.routers.common import ensure_user

router = Router(name="interview")


async def open_interview(message: Message, state: FSMContext) -> None:
    await state.set_state(InterviewStates.menu)
    await message.answer(
        "Интервью пока в разработке. Следующий шаг - выбор тем.",
        reply_markup=back_to_main_menu_keyboard(),
    )


@router.message(Command("interview"))
async def handle_interview_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(message.from_user, session)
    await open_interview(message, state)


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
        await open_interview(callback.message, state)
