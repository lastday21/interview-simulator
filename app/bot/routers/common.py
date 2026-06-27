from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.callbacks import MAIN_MENU
from app.bot.keyboards import main_menu_keyboard
from app.db.models import User
from app.repositories import UserRepository

router = Router(name="common")


async def ensure_user(
    telegram_user: TelegramUser | None,
    session: AsyncSession,
) -> User | None:
    if telegram_user is None:
        return None

    return await UserRepository(session).upsert_user(
        telegram_user_id=telegram_user.id,
        username=telegram_user.username,
    )


async def send_main_menu(message: Message) -> None:
    await message.answer(
        "Выбери режим:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(CommandStart())
async def handle_start(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(message.from_user, session)
    await send_main_menu(message)


@router.message(Command("menu"))
async def handle_menu(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(message.from_user, session)
    await send_main_menu(message)


@router.callback_query(lambda callback: callback.data == MAIN_MENU)
async def handle_main_menu_callback(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    await state.clear()
    await ensure_user(callback.from_user, session)
    await callback.answer()
    if isinstance(callback.message, Message):
        await send_main_menu(callback.message)
