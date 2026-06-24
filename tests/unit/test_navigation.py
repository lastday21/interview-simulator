from aiogram import Dispatcher

from app.bot.callbacks import INTERVIEW_MENU, STATISTICS_MENU, TRAINER_MENU
from app.bot.dispatcher import create_dispatcher
from app.bot.keyboards import main_menu_keyboard


def test_main_menu_keyboard_has_expected_callbacks() -> None:
    keyboard = main_menu_keyboard()

    callback_data = [
        button.callback_data for row in keyboard.inline_keyboard for button in row
    ]

    assert callback_data == [TRAINER_MENU, INTERVIEW_MENU, STATISTICS_MENU]


def test_create_dispatcher_registers_routers() -> None:
    dispatcher = create_dispatcher()

    assert isinstance(dispatcher, Dispatcher)
    assert {router.name for router in dispatcher.sub_routers} == {
        "common",
        "trainer",
        "interview",
        "statistics",
    }
