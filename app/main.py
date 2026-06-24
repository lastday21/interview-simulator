from app.bot import create_dispatcher
from app.core.settings import get_settings


def build_application() -> tuple:
    """Build the top-level bot objects needed by the application."""
    settings = get_settings()
    dispatcher = create_dispatcher(redis_url=settings.redis_url)
    return (dispatcher,)
