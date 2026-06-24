from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import TRAINER_MENU
from app.bot.fsm import TrainerStates
from app.bot.keyboards.navigation import back_to_main_menu_keyboard
from app.bot.routers.common import ensure_user

router = Router(name="trainer")


async def open_trainer(message: Message, state: FSMContext) -> None:
    await state.set_state(TrainerStates.select_topic)
    await message.answer(
        "Тренажер пока в разработке. Следующий шаг - выбор темы.",
        reply_markup=back_to_main_menu_keyboard(),
    )


@router.message(Command("trainer"))
async def handle_trainer_command(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(message.from_user, session)
    await open_trainer(message, state)


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
        await open_trainer(callback.message, state)
