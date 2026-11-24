from core.config import bot


def reply(chat_id: int, message: str, **kwargs):
    """Send a stylized message with the main keyboard attached."""

    from core.typography import text
    from core.ui_text import clean
    from bot.keyboards import main_keyboard

    if "reply_markup" not in kwargs:
        kwargs["reply_markup"] = main_keyboard(chat_id)

    return bot.send_message(
        chat_id,
        text(clean(message)),
        **kwargs
    )


def get_bot_link(user_id: int) -> str:
    """Build a personal deep-link for a user."""

    username = bot.get_me().username

    return f"https://t.me/{username}?start=send_{user_id}"
