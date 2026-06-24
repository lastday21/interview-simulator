from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import MAIN_MENU


def back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Назад в меню",
                    callback_data=MAIN_MENU,
                )
            ]
        ]
    )
