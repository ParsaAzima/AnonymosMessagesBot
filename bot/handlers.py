from core.config import bot, logger
from core.guards import restricted
from bot.helpers import reply, get_bot_link
from bot.keyboards import cancel_keyboard, is_cancel
from core.ui_text import (
    heading,
    field,
    hint,
    error,
    warning,
    success,
    divider,
    card,
    THIN_DIVIDER,
)
from services.user import get_or_create_user, get_user
from services.message import save_message
from services.moderation import (
    is_blocked,
    check_message_allowed,
    record_violation,
)


# =========================================================
# Start Command
# =========================================================

@bot.message_handler(commands=["start"])
@restricted
def start(message):

    get_or_create_user(message.from_user)

    args = message.text.split(maxsplit=1)

    # Normal start
    if len(args) == 1:

        link = get_bot_link(message.from_user.id)

        reply(
            message.chat.id,
            card(
                heading("", "Welcome to Anonymous Messages"),
                [
                    hint(
                        "Share your personal link with friends "
                        "to receive anonymous messages."
                    ),
                    "",
                    field("", "Your link", link),
                    "",
                    hint(
                        "Anyone with this link can message you "
                        "without revealing their identity."
                    ),
                ],
                footer="Use the buttons below to navigate.",
            )
        )

        return

    payload = args[1]

    # Anonymous message link
    if payload.startswith("send_"):

        try:
            receiver_id = int(
                payload.removeprefix("send_")
            )

        except ValueError:

            reply(
                message.chat.id,
                    warning("Invalid invitation link.")
            )

            return

        if receiver_id == message.from_user.id:

            reply(
                message.chat.id,
                    warning("You cannot send anonymous messages to yourself!")
            )

            return

        if not get_user(receiver_id):

            reply(
                message.chat.id,
                card(
                    warning("User not registered"),
                    [
                        hint(
                            "Ask them to open your link first, "
                            "then try again."
                        )
                    ],
                )
            )

            return

        reply(
            message.chat.id,
            card(
                heading("", "New Anonymous Message"),
                [
                    hint(
                        "Write anything you'd like to send. "
                        "Your identity stays hidden."
                    ),
                ],
        footer="Press Cancel to abort.",
            ),
            reply_markup=cancel_keyboard()
        )

        bot.register_next_step_handler(
            message,
            restricted(receive_anonymous_message),
            receiver_id
        )

        return

    reply(
        message.chat.id,
        card(
            warning("Unknown link"),
            [
                hint(
        "Press Profile below to get "
                    "your personal link."
                )
            ],
        )
    )


# =========================================================
# Anonymous Message Handler
# =========================================================

def receive_anonymous_message(message, receiver_id: int):

    sender_id = message.from_user.id

    # Cancel operation
    if is_cancel(message):

        reply(
            message.chat.id,
                hint("Your message has been cancelled.")
        )

        return

    # Reject unsupported message types
    if message.content_type in ("new_chat_members", "left_chat_member"):

        reply(
            message.chat.id,
                warning("This message type is not supported.")
        )

        return

    # Respect blocks
    if is_blocked(receiver_id, sender_id):

        reply(
            message.chat.id,
                warning("This user has blocked you. "
                    "Your message was not delivered.")
        )

        return

    # Rate limiting and anti-spam
    content_preview = (
        message.text
        or message.caption
        or f"[{message.content_type}]"
    )

    allowed, reason = check_message_allowed(
        sender_id,
        content_preview
    )

    if not allowed:

        count, auto_banned = record_violation(
            sender_id,
            reason
        )

        if auto_banned:

            reply(
                message.chat.id,
                    error(
                    "Your account has been restricted "
                    "after repeated violations."
                )
            )

        elif reason == "rate_limit":

            reply(
                message.chat.id,
                    warning(
                    "You are sending messages too fast.\n"
                    "Please wait a moment and try again."
                )
            )

        else:

            reply(
                message.chat.id,
                    warning(f"Message blocked by spam filter: {reason}")
            )

        return

    try:

        # Deliver anonymously
        bot.copy_message(
            chat_id=receiver_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

    except Exception as error:

        logger.exception(
            "Message delivery failed: %s",
            error
        )

        reply(
            message.chat.id,
            card(
                error("Message delivery failed"),
                [
                    hint(
                        "The recipient may have blocked the bot. "
                        "Please try again later."
                    )
                ],
            )
        )

        return

    # Save message metadata
    try:

        content = (
            message.text
            or message.caption
            or f"[{message.content_type}]"
        )

        media = getattr(
            message,
            message.content_type,
            None
        )

        if isinstance(media, list):
            # Photos arrive as a list of sizes
            media_file_id = media[-1].file_id if media else None
        else:
            media_file_id = (
                getattr(media, "file_id", None)
            )

        save_message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            content_type=message.content_type,
            media_file_id=media_file_id
        )

    except Exception as error:

        logger.exception(
            "Message database error: %s",
            error
        )

    reply(
        message.chat.id,
        card(
            success("Your anonymous message has been delivered!"),
            [hint("Thank you for using Anonymous Messages.")],
        )
    )
