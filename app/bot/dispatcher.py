from aiogram import Dispatcher

from app.bot.middlewares import DbSessionMiddleware
from app.bot.routers import (
    common_router,
    interview_router,
    statistics_router,
    trainer_router,
)
from app.bot.storage import create_storage


def create_dispatcher(redis_url: str | None = None) -> Dispatcher:
    dispatcher = Dispatcher(storage=create_storage(redis_url))
    dispatcher.update.outer_middleware(DbSessionMiddleware())
    dispatcher.include_routers(
        common_router,
        trainer_router,
        interview_router,
        statistics_router,
    )
    return dispatcher
