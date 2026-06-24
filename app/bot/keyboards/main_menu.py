from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import INTERVIEW_MENU, STATISTICS_MENU, TRAINER_MENU


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Тренажер",
                    callback_data=TRAINER_MENU,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Интервью",
                    callback_data=INTERVIEW_MENU,
                )
            ],
            [
                InlineKeyboardButton(
                    text="Статистика",
                    callback_data=STATISTICS_MENU,
                )
            ],
        ]
    )
