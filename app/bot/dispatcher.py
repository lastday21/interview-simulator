from aiogram import Dispatcher

from app.bot.middlewares import DbSessionMiddleware
from app.bot.storage import create_storage


def create_dispatcher(redis_url: str | None = None) -> Dispatcher:
    dispatcher = Dispatcher(storage=create_storage(redis_url))
    dispatcher.update.outer_middleware(DbSessionMiddleware())
    return dispatcher
