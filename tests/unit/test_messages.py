import pytest

from app.bot.messages import split_message_text


def test_split_message_text_keeps_chunks_under_limit() -> None:
    chunks = split_message_text("first\nsecond\nthird", limit=12)

    assert chunks == ["first\nsecond", "third"]


def test_split_message_text_splits_long_single_line() -> None:
    chunks = split_message_text("abcdef", limit=2)

    assert chunks == ["ab", "cd", "ef"]


def test_split_message_text_rejects_invalid_limit() -> None:
    with pytest.raises(ValueError):
        split_message_text("text", limit=0)
