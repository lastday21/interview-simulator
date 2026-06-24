from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage


def create_storage(redis_url: str | None = None) -> BaseStorage:
    if redis_url is None:
        return MemoryStorage()

    return RedisStorage.from_url(redis_url)
