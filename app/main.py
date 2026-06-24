import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.bot import create_dispatcher
from app.core.settings import get_settings


def build_application() -> tuple[Bot, Dispatcher]:
    """Build the top-level bot objects needed by the application."""
    settings = get_settings()
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = create_dispatcher(redis_url=settings.redis_url)
    return bot, dispatcher


async def set_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="trainer", description="Тренажер"),
            BotCommand(command="interview", description="Интервью"),
            BotCommand(command="statistic", description="Статистика"),
        ]
    )


async def main() -> None:
    bot, dispatcher = build_application()
    await set_bot_commands(bot)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
