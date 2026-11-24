from core.config import bot, logger, ADMIN_IDS
from core.guards import restricted
from core.ui_text import (
    heading,
    field,
    hint,
    warning,
    error,
    success,
    card,
)
from bot.helpers import reply
from bot.keyboards import (
    BTN_INBOX,
    BTN_HISTORY,
    BTN_PROFILE,
    BTN_BLOCKED,
    BTN_ADMIN,
    BTN_BACK,
    MAIN_BUTTONS,
    main_keyboard,
    cancel_keyboard,
    admin_keyboard,
    is_cancel,
)
from services.moderation import ban_user, unban_user

from bot import profile_handlers
from bot import social_handlers
from bot import moderation_handlers


# =========================================================
# Main Menu Dispatcher
# =========================================================

@bot.message_handler(
    func=lambda m: m.text in MAIN_BUTTONS,
    content_types=["text"]
)
@restricted
def menu_dispatcher(message):

    choice = message.text
    user_id = message.from_user.id
    chat_id = message.chat.id

    # --- Inbox ---
    if choice == BTN_INBOX:
        social_handlers.inbox_command(message)
        return

    # --- History ---
    if choice == BTN_HISTORY:
        social_handlers.history_command(message)
        return

    # --- Profile ---
    if choice == BTN_PROFILE:
        profile_handlers.profile_command(message)
        return

    # --- Blocked list ---
    if choice == BTN_BLOCKED:
        moderation_handlers.blocked_command(message)
        return

    # --- Admin panel ---
    if choice == BTN_ADMIN:

        if user_id not in ADMIN_IDS:

            reply(
                chat_id,
        "This section is for administrators only."
            )

            return

        bot.send_message(
            chat_id,
        "Admin Panel\n\n"
            "Choose an action:",
            reply_markup=admin_keyboard()
        )

        return


# =========================================================
# Admin Panel Callbacks
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (c.data or "").startswith("admin_")
)
@restricted
def admin_callback(call):

    data = call.data or ""
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if user_id not in ADMIN_IDS:

        bot.answer_callback_query(
            call.id,
            text="Admins only"
        )

        return

    # --- Ban User ---
    if data == "admin_ban":

        bot.answer_callback_query(call.id)

        prompt = bot.send_message(
            chat_id,
            "Send the user ID and an optional reason.\n\n"
            "Example: 123456789 spam\n\n"
        "Press Cancel to abort.",
            reply_markup=cancel_keyboard()
        )

        bot.register_next_step_handler(
            prompt,
            restricted(_admin_ban_input)
        )

        return

    # --- Unban User ---
    if data == "admin_unban":

        bot.answer_callback_query(call.id)

        prompt = bot.send_message(
            chat_id,
            "Send the user ID to unrestrict.\n\n"
        "Press Cancel to abort.",
            reply_markup=cancel_keyboard()
        )

        bot.register_next_step_handler(
            prompt,
            restricted(_admin_unban_input)
        )

        return

    # --- Banned list ---
    if data == "admin_banned":

        bot.answer_callback_query(call.id)

        _delete_card(call)
        moderation_handlers._send_banned(chat_id, 0)

        return

    # --- Reports ---
    if data == "admin_reports":

        bot.answer_callback_query(call.id)

        _delete_card(call)
        moderation_handlers._send_reports(chat_id, 0)

        return

    # --- Back to main menu ---
    if data == "admin_back":

        bot.answer_callback_query(call.id)

        _delete_card(call)

        bot.send_message(
            chat_id,
            "Main menu — choose an option below.",
            reply_markup=main_keyboard(user_id)
        )

        return

    bot.answer_callback_query(call.id)


# =========================================================
# Admin Input Handlers
# =========================================================

def _admin_ban_input(message):

    if is_cancel(message):

        reply(
            message.chat.id,
            "Ban cancelled."
        )

        return

    parts = (message.text or "").split(maxsplit=1)

    if not parts:

        reply(
            message.chat.id,
            "Please send a user ID."
        )

        return

    try:
        target_id = int(parts[0])
    except ValueError:

        reply(
            message.chat.id,
            "Invalid user ID. Send only numbers."
        )

        return

    reason = (
        parts[1].strip()
        if len(parts) == 2 and parts[1].strip()
        else "No reason given"
    )

    if ban_user(target_id, reason):

        reply(
            message.chat.id,
        f"User {target_id} has been restricted.\n"
            f"Reason: {reason}"
        )

        try:
            bot.send_message(
                target_id,
        "Your account has been restricted "
                "by an administrator.\n\n"
                f"Reason: {reason}"
            )
        except Exception as error:
            logger.debug("Ban notice failed: %s", error)

    else:

        reply(
            message.chat.id,
            "User not found. They must open the bot "
            "via their personal link first."
        )


def _admin_unban_input(message):

    if is_cancel(message):

        reply(
            message.chat.id,
            "Unban cancelled."
        )

        return

    value = (message.text or "").strip()

    try:
        target_id = int(value)
    except ValueError:

        reply(
            message.chat.id,
            "Invalid user ID. Send only numbers."
        )

        return

    if unban_user(target_id):

        reply(
            message.chat.id,
        f"User {target_id} has been unrestricted."
        )

        try:
            bot.send_message(
                target_id,
        "Your account has been unrestricted. "
                "You may use the bot again."
            )
        except Exception as error:
            logger.debug("Unban notice failed: %s", error)

    else:

        reply(
            message.chat.id,
            "User not found."
        )


# =========================================================
# Utility
# =========================================================

def _delete_card(call) -> None:

    try:
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except Exception as error:
        logger.debug("Could not delete card: %s", error)
