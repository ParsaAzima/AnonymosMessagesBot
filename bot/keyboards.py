from telebot import types

from core.config import ADMIN_IDS


# =========================================================
# Button Labels
# =========================================================

BTN_INBOX = "Inbox"
BTN_HISTORY = "History"
BTN_PROFILE = "Profile"
BTN_BLOCKED = "Blocked"
BTN_ADMIN = "Admin"
BTN_CANCEL = "Cancel"
BTN_BACK = "Back"

MAIN_BUTTONS = (
    BTN_INBOX,
    BTN_HISTORY,
    BTN_PROFILE,
    BTN_BLOCKED,
    BTN_ADMIN,
)


def is_cancel(message) -> bool:
    """Accept the Cancel button (and /cancel for older clients)."""

    value = (message.text or "").strip()

    return value in (BTN_CANCEL, "/cancel")


# =========================================================
# Reply Keyboards
# =========================================================

def main_keyboard(user_id: int) -> types.ReplyKeyboardMarkup:
    """Persistent keyboard shown at the bottom of the chat."""

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        is_persistent=True
    )

    kb.row(BTN_INBOX, BTN_HISTORY)
    kb.row(BTN_PROFILE, BTN_BLOCKED)

    if user_id in ADMIN_IDS:
        kb.row(BTN_ADMIN)

    return kb


def cancel_keyboard() -> types.ReplyKeyboardMarkup:
    """One-time keyboard for flows waiting for text input."""

    kb = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True
    )

    kb.row(BTN_CANCEL)

    return kb


def remove_keyboard() -> types.ReplyKeyboardRemove:
    return types.ReplyKeyboardRemove()


# =========================================================
# Inline Keyboards
# =========================================================

def admin_keyboard() -> types.InlineKeyboardMarkup:
    """Admin panel shown after pressing the Admin button."""

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            text="Ban User",
            callback_data="admin_ban"
        ),
        types.InlineKeyboardButton(
            text="Unban User",
            callback_data="admin_unban"
        ),
    )

    kb.add(
        types.InlineKeyboardButton(
            text="Banned List",
            callback_data="admin_banned"
        ),
        types.InlineKeyboardButton(
            text="Reports",
            callback_data="admin_reports"
        ),
    )

    kb.add(
        types.InlineKeyboardButton(
            text=BTN_BACK,
            callback_data="admin_back"
        )
    )

    return kb
