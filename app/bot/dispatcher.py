from aiogram import Dispatcher

from app.bot.middlewares import DbSessionMiddleware


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.update.outer_middleware(DbSessionMiddleware())
    return dispatcher
