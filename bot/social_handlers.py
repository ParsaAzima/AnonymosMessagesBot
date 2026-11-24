from telebot import types

from core.config import bot, logger
from core.guards import restricted
from core.ui_text import (
    heading,
    field,
    hint,
    warning,
    error,
    success,
    info,
    card,
    divider,
    THIN_DIVIDER,
)
from bot.helpers import reply
from bot.keyboards import cancel_keyboard, is_cancel
from services.user import get_or_create_user
from services.moderation import (
    is_blocked,
    check_message_allowed,
    record_violation,
)
from services.message import (
    count_inbox,
    get_inbox,
    count_history,
    get_history,
    get_message,
    set_reaction,
    save_reply,
)


INBOX_PAGE_SIZE = 1
HISTORY_PAGE_SIZE = 5

REACTIONS = [
    ("like", "👍"),
    ("love", "❤️"),
    ("haha", "😂"),
    ("wow", "😮"),
    ("sad", "😢"),
    ("fire", "🔥"),
]

REACTION_BY_CODE = dict(REACTIONS)

MEDIA_TYPES = ("photo", "video", "document", "voice", "audio")


# =========================================================
# Formatting Helpers
# =========================================================

def _format_date(value) -> str:
    if value is None:
        return "unknown"

    try:
        return value.strftime("%Y-%m-%d %H:%M")
    except AttributeError:
        return str(value)


def _inbox_card(message: dict, page: int, total: int) -> str:
    rows = []

    if message["reply_to"]:
        rows.append(info("This is an anonymous reply"))

    content = (
        message["content"]
        or f"[{message['content_type']}]"
    )

    rows.extend([
        "",
        content,
        "",
            divider(),
            field("", "Received", _format_date(message["created_at"])),
    ])

    if message["reaction"]:
        rows.append(
            field(
        "",
                "Your reaction",
                message["reaction"]
            )
        )

    return card(
            heading(
        "",
            f"Inbox ({page + 1} / {total})"
        ),
        rows,
        footer="Reply, react, block or report below.",
    )


def _history_text(
    rows: list[dict],
    user_id: int,
    page: int,
    total_pages: int,
) -> str:
    lines = [
            heading(
        "",
            f"Message History ({page + 1} / {total_pages})"
        ),
        "",
    ]

    for message in rows:

        direction = (
        "Received"
            if message["receiver"] == user_id
        else "Sent"
        )

        snippet = (
            message["content"]
            or f"[{message['content_type']}]"
        ).replace("\n", "")

        if len(snippet) > 60:
            snippet = snippet[:60] + "…"

        reaction = (
            f"{message['reaction']}"
            if message["reaction"]
            else ""
        )

        lines.append(
            f"{direction} | "
            f"{_format_date(message['created_at'])}"
            f"{reaction}"
        )
        lines.append(f"{snippet}")
        lines.append("")

    return "\n".join(lines)


# =========================================================
# Keyboards
# =========================================================

def _inbox_keyboard(
    message_id: int,
    page: int,
    total: int,
) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=3)

    kb.add(
        types.InlineKeyboardButton(
            text="Reply",
            callback_data=f"inbox_reply_{message_id}"
        )
    )

    kb.add(
        *[
            types.InlineKeyboardButton(
                text=emoji,
                callback_data=(
                    f"inbox_react_{message_id}_{code}_{page}"
                )
            )
            for code, emoji in REACTIONS
        ]
    )

    kb.add(
        types.InlineKeyboardButton(
            text="Block",
            callback_data=f"blockuser_{message_id}"
        ),
        types.InlineKeyboardButton(
            text="Report",
            callback_data=f"reportuser_{message_id}"
        ),
    )

    nav = []

    if page > 0:
        nav.append(
            types.InlineKeyboardButton(
                text="Prev",
                callback_data=f"inbox_page_{page - 1}"
            )
        )

    if page < total - 1:
        nav.append(
            types.InlineKeyboardButton(
                text="Next",
                callback_data=f"inbox_page_{page + 1}"
            )
        )

    nav.append(
        types.InlineKeyboardButton(
            text="Close",
            callback_data="social_close"
        )
    )

    kb.add(*nav)

    return kb


def _history_keyboard(
    page: int,
    total_pages: int,
) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)

    nav = []

    if page > 0:
        nav.append(
            types.InlineKeyboardButton(
                text="Prev",
                callback_data=f"hist_page_{page - 1}"
            )
        )

    if page < total_pages - 1:
        nav.append(
            types.InlineKeyboardButton(
                text="Next",
                callback_data=f"hist_page_{page + 1}"
            )
        )

    nav.append(
        types.InlineKeyboardButton(
            text="Close",
            callback_data="social_close"
        )
    )

    kb.add(*nav)

    return kb


def _empty_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="Close",
            callback_data="social_close"
        )
    )
    return kb


# =========================================================
# Rendering
# =========================================================

def _send_inbox_card(
    chat_id: int,
    message: dict,
    page: int,
    total: int,
) -> None:
    """Send one inbox card, rendering media when available."""

    caption = _inbox_card(message, page, total)
    keyboard = _inbox_keyboard(message["id"], page, total)

    content_type = message["content_type"]
    file_id = message["media_file_id"]

    if content_type == "photo"and file_id:
        bot.send_photo(
            chat_id,
            file_id,
            caption=caption,
            reply_markup=keyboard
        )

    elif content_type == "video"and file_id:
        bot.send_video(
            chat_id,
            file_id,
            caption=caption,
            reply_markup=keyboard
        )

    elif content_type == "document"and file_id:
        bot.send_document(
            chat_id,
            file_id,
            caption=caption,
            reply_markup=keyboard
        )

    elif content_type == "voice"and file_id:
        bot.send_voice(
            chat_id,
            file_id,
            caption=caption,
            reply_markup=keyboard
        )

    elif content_type == "audio"and file_id:
        bot.send_audio(
            chat_id,
            file_id,
            caption=caption,
            reply_markup=keyboard
        )

    else:
        bot.send_message(
            chat_id,
            caption,
            reply_markup=keyboard
        )


def _edit_inbox_card(
    call,
    message: dict,
    page: int,
    total: int,
) -> None:
    """Update an existing inbox card in place."""

    caption = _inbox_card(message, page, total)
    keyboard = _inbox_keyboard(message["id"], page, total)

    content_type = message["content_type"]
    file_id = message["media_file_id"]

    try:

        if content_type in MEDIA_TYPES and file_id \
                and call.message.caption is not None:

            bot.edit_message_caption(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                caption=caption,
                reply_markup=keyboard
            )

        else:

            bot.edit_message_text(
                text=caption,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )

    except Exception as error:

        # Telegram raises when nothing actually changed
        logger.debug("Inbox card not modified: %s", error)


# =========================================================
# Commands
# =========================================================

@restricted
def inbox_command(message):

    get_or_create_user(message.from_user)

    _send_inbox(message.chat.id, message.from_user.id, 0)


@restricted
def history_command(message):

    get_or_create_user(message.from_user)

    _send_history(message.chat.id, message.from_user.id, 0)


# =========================================================
# Senders
# =========================================================

def _send_inbox(chat_id: int, user_id: int, page: int) -> None:

    total = count_inbox(user_id)

    if total == 0:

        bot.send_message(
            chat_id,
            card(
            heading("", "Inbox is Empty"),
                [
            hint(
                        "Share your personal link to receive "
                        "anonymous messages."
                    )
                ],
            ),
            reply_markup=_empty_keyboard()
        )

        return

    max_page = (total - 1) // INBOX_PAGE_SIZE
    page = max(0, min(page, max_page))

    rows = get_inbox(
        user_id,
        limit=INBOX_PAGE_SIZE,
        offset=page * INBOX_PAGE_SIZE
    )

    if not rows:
        return

    _send_inbox_card(chat_id, rows[0], page, total)


def _send_history(chat_id: int, user_id: int, page: int) -> None:

    total = count_history(user_id)

    if total == 0:

        bot.send_message(
            chat_id,
            card(
            heading("", "No History Yet"),
                [
            hint(
                        "Send or receive an anonymous "
                        "message first."
                    )
                ],
            ),
            reply_markup=_empty_keyboard()
        )

        return

    total_pages = (
        (total + HISTORY_PAGE_SIZE - 1) // HISTORY_PAGE_SIZE
    )

    page = max(0, min(page, total_pages - 1))

    rows = get_history(
        user_id,
        limit=HISTORY_PAGE_SIZE,
        offset=page * HISTORY_PAGE_SIZE
    )

    bot.send_message(
        chat_id,
        _history_text(rows, user_id, page, total_pages),
        reply_markup=_history_keyboard(page, total_pages)
    )


# =========================================================
# Callback Router
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (c.data or "").startswith(
        ("inbox_", "hist_", "social_")
    )
)
@restricted
def social_callback(call):

    data = call.data or ""
    user_id = call.from_user.id
    parts = data.split("_")

    # --- Close ---
    if data == "social_close":

        bot.answer_callback_query(call.id)

        _delete_card(call)

        return

    # --- Open inbox from /start button ---
    if data == "social_open_inbox":

        bot.answer_callback_query(call.id)

        _delete_card(call)
        _send_inbox(call.message.chat.id, user_id, 0)

        return

    # --- Inbox pagination ---
    if len(parts) == 3 and parts[:2] == ["inbox", "page"]:

        bot.answer_callback_query(call.id)

        try:
            page = int(parts[2])
        except ValueError:
            return

        _delete_card(call)
        _send_inbox(call.message.chat.id, user_id, page)

        return

    # --- History pagination ---
    if len(parts) == 3 and parts[:2] == ["hist", "page"]:

        bot.answer_callback_query(call.id)

        try:
            page = int(parts[2])
        except ValueError:
            return

        _delete_card(call)
        _send_history(call.message.chat.id, user_id, page)

        return

    # --- Reactions ---
    # inbox_react_{message_id}_{code}_{page}
    if len(parts) == 5 and parts[:2] == ["inbox", "react"]:

        try:
            message_id = int(parts[2])
            page = int(parts[4])
        except ValueError:
            bot.answer_callback_query(call.id)
            return

        code = parts[3]
        emoji = REACTION_BY_CODE.get(code)

        if emoji is None:
            bot.answer_callback_query(call.id)
            return

        message = get_message(message_id)

        # Only the recipient may react
        if message is None or message["receiver"] != user_id:

            bot.answer_callback_query(
                call.id,
                text="This is not your message!"
            )

            return

        new_reaction = (
            None if message["reaction"] == emoji else emoji
        )

        set_reaction(message_id, new_reaction)

        bot.answer_callback_query(
            call.id,
            text=(
                f"Reaction removed"
                if new_reaction is None
                else f"Reacted with {new_reaction}"
            )
        )

        if new_reaction is not None:
            _notify_sender(
                message["sender"],
                card(
            heading("", "New Reaction"),
                    [
            field(
                            new_reaction,
                            "Someone reacted to your message",
                            "Anonymous"
                        )
                    ],
                )
            )

        updated = get_message(message_id)

        if updated is not None:
            _edit_inbox_card(
                call,
                updated,
                page,
                count_inbox(user_id)
            )

        return

    # --- Anonymous reply ---
    if len(parts) == 3 and parts[:2] == ["inbox", "reply"]:

        try:
            message_id = int(parts[2])
        except ValueError:
            bot.answer_callback_query(call.id)
            return

        message = get_message(message_id)

        # Only the recipient may reply
        if message is None or message["receiver"] != user_id:

            bot.answer_callback_query(
                call.id,
                text="This is not your message!"
            )

            return

        bot.answer_callback_query(call.id)

        prompt = bot.send_message(
            chat_id=call.message.chat.id,
            text=card(
            heading("", "Write a Reply"),
                [hint("Your reply stays anonymous.")],
        footer="Press Cancel to abort.",
            ),
            reply_markup=cancel_keyboard()
        )

        bot.register_next_step_handler(
            prompt,
            restricted(_receive_reply),
            message_id
        )

        return

    bot.answer_callback_query(call.id)


# =========================================================
# Reply Input
# =========================================================

def _receive_reply(message, message_id: int):

    if is_cancel(message):

        reply(
            message.chat.id,
            hint("Reply cancelled.")
        )

        return

    content = (message.text or "").strip()

    if not content:

        reply(
            message.chat.id,
            card(
            warning("Reply cannot be empty."),
        [hint("Press Inbox and try again.")],
            )
        )

        return

    original = get_message(message_id)

    if original is None:

        reply(
            message.chat.id,
            warning("That message is no longer available.")
        )

        return

    sender_id = message.from_user.id

    # The original sender may have blocked this user
    if is_blocked(original["sender"], sender_id):

        reply(
            message.chat.id,
            warning(
                "This user has blocked you. "
                "Your reply was not delivered."
            )
        )

        return

    # Apply rate limiting and spam checks to replies too
    allowed, reason = check_message_allowed(
        sender_id,
        content
    )

    if not allowed:

        count, auto_banned = record_violation(
            sender_id,
            reason
        )

        if auto_banned:
            text = error(
                "Your account has been restricted "
                "after repeated violations."
            )
        elif reason == "rate_limit":
            text = warning(
                "You are sending messages too fast. "
                "Please wait a moment."
            )
        else:
            text = warning(f"Reply blocked: {reason}")

        reply(message.chat.id, text)

        return

    save_reply(
        original_id=message_id,
        sender_id=sender_id,
        receiver_id=original["sender"],
        content=content,
    )

    # Deliver the reply anonymously to the original sender
    try:

        bot.send_message(
            original["sender"],
            card(
            heading("", "Anonymous Reply"),
                [f"“{content}”"],
            )
        )

    except Exception as error:

        logger.exception(
            "Anonymous reply delivery failed: %s",
            error
        )

        reply(
            message.chat.id,
            card(
            warning("Reply saved, but delivery failed"),
                [hint("The recipient may have blocked the bot.")],
            )
        )

        return

    reply(
        message.chat.id,
            success("Your anonymous reply has been sent!")
    )


# =========================================================
# Utilities
# =========================================================

def _notify_sender(telegram_id: int, text: str) -> None:
    """Send an anonymous notification to a message's original sender."""

    try:
        bot.send_message(telegram_id, text)
    except Exception as error:
        logger.debug(
            "Could not notify sender %s: %s",
            telegram_id,
            error
        )


def _delete_card(call) -> None:
    """Remove a card message, ignoring Telegram errors."""

    try:
        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except Exception as error:
        logger.debug("Could not delete card: %s", error)
