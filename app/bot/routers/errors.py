import logging

from aiogram import Router
from aiogram.types import CallbackQuery, ErrorEvent, Message

from app.bot.keyboards.navigation import back_to_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="errors")


def _message_from_error_event(event: ErrorEvent) -> Message | None:
    message = event.update.message
    if message is not None:
        return message

    callback_query = event.update.callback_query
    if isinstance(callback_query, CallbackQuery) and isinstance(
        callback_query.message,
        Message,
    ):
        return callback_query.message

    return None


@router.errors()
async def handle_unhandled_error(event: ErrorEvent) -> bool:
    logger.exception("Unhandled bot update error", exc_info=event.exception)

    message = _message_from_error_event(event)
    if message is not None:
        await message.answer(
            "Произошла ошибка. Попробуй ещё раз или вернись в меню.",
            reply_markup=back_to_main_menu_keyboard(),
        )

    return True
