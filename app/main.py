from app.bot import create_dispatcher


def build_application() -> tuple:
    """Build the top-level bot objects needed by the application."""
    dispatcher = create_dispatcher()
    return (dispatcher,)
