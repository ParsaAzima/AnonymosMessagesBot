from functools import wraps

from core.config import bot, ADMIN_IDS
from services.moderation import is_banned


RESTRICTED_TEXT = (
        "Your account has been restricted due to "
    "policy violations.\n\n"
    "You can no longer use this bot."
)

ADMIN_ONLY_TEXT = (
        "This command is available to administrators only."
)


def _is_callback(update) -> bool:
    return hasattr(update, "data")


def _chat_id(update) -> int:
    if _is_callback(update):
        return update.message.chat.id
    return update.chat.id


def restricted(handler):
    """
    Block restricted users from every handler.
    Works for both Message and CallbackQuery updates.
    """

    @wraps(handler)
    def wrapper(update, *args, **kwargs):

        if not is_banned(update.from_user.id):
            return handler(update, *args, **kwargs)

        if _is_callback(update):
            bot.answer_callback_query(
                update.id,
                text="Account restricted"
            )

        bot.send_message(
            _chat_id(update),
            RESTRICTED_TEXT
        )

        return None

    return wrapper


def admin_only(handler):
    """Allow only configured administrators."""

    @wraps(handler)
    def wrapper(message, *args, **kwargs):

        if message.from_user.id not in ADMIN_IDS:

            bot.send_message(
                message.chat.id,
                ADMIN_ONLY_TEXT
            )

            return None

        return handler(message, *args, **kwargs)

    return wrapper
