from aiogram.types import InlineKeyboardMarkup, Message

TELEGRAM_MESSAGE_LIMIT = 3900


def split_message_text(
    text: str,
    *,
    limit: int = TELEGRAM_MESSAGE_LIMIT,
) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be positive")

    chunks: list[str] = []
    current = ""

    for line in text.splitlines():
        remaining = line
        while len(remaining) > limit:
            part = remaining[:limit]
            if current:
                chunks.append(current)
                current = ""
            chunks.append(part)
            remaining = remaining[limit:]

        next_part = remaining if not current else f"{current}\n{remaining}"
        if len(next_part) <= limit:
            current = next_part
            continue

        if current:
            chunks.append(current)
        current = remaining

    if current:
        chunks.append(current)

    return chunks or [""]


async def answer_split(
    message: Message,
    text: str,
    *,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    chunks = split_message_text(text)
    for index, chunk in enumerate(chunks):
        markup = reply_markup if index == len(chunks) - 1 else None
        await message.answer(chunk, reply_markup=markup)
