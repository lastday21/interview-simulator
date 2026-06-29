from app.bot.routers.common import router as common_router
from app.bot.routers.errors import router as errors_router
from app.bot.routers.interview import router as interview_router
from app.bot.routers.statistics import router as statistics_router
from app.bot.routers.trainer import router as trainer_router

__all__ = [
    "common_router",
    "errors_router",
    "interview_router",
    "statistics_router",
    "trainer_router",
]
