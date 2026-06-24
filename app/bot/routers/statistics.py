from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import STATISTICS_MENU
from app.bot.fsm import StatisticsStates
from app.bot.keyboards.navigation import back_to_main_menu_keyboard
from app.bot.routers.common import ensure_user

router = Router(name="statistics")


async def open_statistics(message: Message, state: FSMContext) -> None:
    await state.set_state(StatisticsStates.menu)
    await message.answer(
        "Статистика пока в разработке.",
        reply_markup=back_to_main_menu_keyboard(),
    )


@router.message(Command("statistic"))
async def handle_statistics_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(message.from_user, session)
    await open_statistics(message, state)


@router.callback_query(F.data == STATISTICS_MENU)
async def handle_statistics_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(callback.from_user, session)
    await callback.answer()
    if isinstance(callback.message, Message):
        await open_statistics(callback.message, state)
