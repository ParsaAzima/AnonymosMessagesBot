from telebot import types

from core.config import bot
from core.guards import restricted
from core.ui_text import (
    heading,
    field,
    plain_field,
    hint,
    warning,
    success,
    card,
    divider,
    THIN_DIVIDER,
)
from bot.helpers import reply, get_bot_link
from bot.keyboards import cancel_keyboard, is_cancel
from services.user import get_or_create_user, get_or_create_user_by_id
from services.profile import get_profile, update_bio, update_avatar


# =========================================================
# Profile Keyboard
# =========================================================

def profile_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Build the inline keyboard shown under a profile card."""

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            text="Set Bio",
            callback_data=f"profile_setbio_{user_id}"
        ),
        types.InlineKeyboardButton(
            text="Set Avatar",
            callback_data=f"profile_setavatar_{user_id}"
        ),
    )

    kb.add(
        types.InlineKeyboardButton(
            text="My Link",
            callback_data=f"profile_link_{user_id}"
        ),
        types.InlineKeyboardButton(
            text="Close",
            callback_data="profile_close"
        ),
    )

    return kb


# =========================================================
# Profile Command
# =========================================================

@restricted
def profile_command(message):

    get_or_create_user(message.from_user)

    user_id = message.from_user.id

    _send_profile(message.chat.id, user_id)


# =========================================================
# Profile Card Sender
# =========================================================

def _send_profile(chat_id: int, user_id: int) -> bool:
    """Send the profile card to a chat. Return False if user not found."""

    get_or_create_user_by_id(user_id)

    profile = get_profile(user_id)

    if profile is None:

        reply(
            chat_id,
            card(
warning("Could not load your profile"),
        [hint("Please press Profile again.")],
            )
        )

        return False

    # Send avatar as photo if available, otherwise plain text
    if profile["avatar_file_id"]:

        bot.send_photo(
            chat_id=chat_id,
            photo=profile["avatar_file_id"],
            caption=_profile_text(user_id, profile),
            reply_markup=profile_keyboard(user_id)
        )

    else:

        bot.send_message(
            chat_id=chat_id,
            text=_profile_text(user_id, profile),
            reply_markup=profile_keyboard(user_id)
        )

    return True


# =========================================================
# Profile Text Builder
# =========================================================

def _profile_text(user_id: int, profile: dict) -> str:
    """Build the profile card text."""

    rows = [
        field("", "Name", profile["first_name"]),
    ]

    if profile["username"]:
        rows.append(
            field("", "Username", f"@{profile['username']}")
        )

    bio_display = (
        profile["bio"] if profile["bio"] else "Not set"
    )
    rows.append(field("", "Bio", bio_display))

    created = profile["created_at"]
    if created:
        rows.append(
            field(
                "",
                "Member since",
                created.strftime("%Y-%m-%d"),
            )
        )

    rows.extend([
        "",
        divider(),
        "",
        field("", "Messages sent", profile["messages_sent"]),
        field("", "Messages received", profile["messages_received"]),
        "",
        field("", "Your link", get_bot_link(user_id)),
    ])

    return card(
        heading("", "Personal Profile"),
        rows,
        footer="Use the buttons below to edit your profile.",
    )


# =========================================================
# Callback Handler
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (c.data or "").startswith("profile_")
)
@restricted
def profile_callback(call):

    user_id = call.from_user.id

    # --- Close ---
    if call.data == "profile_close":

        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        bot.answer_callback_query(call.id)

        return

    # --- Extract target user_id from callback data ---
    parts = call.data.split("_")

    # profile_setbio_12345  -> ["profile", "setbio", "12345"]
    if len(parts) < 3:
        bot.answer_callback_query(call.id)
        return

    action = parts[1]

    try:
        target_id = int(parts[2])
    except ValueError:
        bot.answer_callback_query(call.id)
        return

    # Only the profile owner can view or modify
    if target_id != user_id:
        bot.answer_callback_query(
            call.id,
            text=warning("This is not your profile!")
        )
        return

    # --- Open Profile (from /start button) ---
    if action == "open":

        bot.answer_callback_query(call.id)

        bot.delete_message(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )

        _send_profile(call.message.chat.id, user_id)

        return

    # --- Set Bio ---
    if action == "setbio":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            chat_id=call.message.chat.id,
            text=card(
heading("", "Set Your Bio"),
                [
hint("Send your new bio as a text message."),
plain_field("Limit", "200 characters max"),
                ],
        footer="Press Cancel to abort.",
            ),
            reply_markup=cancel_keyboard()
        )

        bot.register_next_step_handler(
            msg,
            restricted(_receive_bio),
            user_id
        )

        return

    # --- Set Avatar ---
    if action == "setavatar":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            chat_id=call.message.chat.id,
            text=card(
heading("", "Set Your Avatar"),
                [hint("Send a photo to use as your avatar.")],
        footer="Press Cancel to abort.",
            ),
            reply_markup=cancel_keyboard()
        )

        bot.register_next_step_handler(
            msg,
            restricted(_receive_avatar),
            user_id
        )

        return

    # --- My Link ---
    if action == "link":

        bot.answer_callback_query(call.id)

        bot.send_message(
            chat_id=call.message.chat.id,
            text=(
                "Your personal link:\n"
                f"{get_bot_link(user_id)}\n\n"
                "Share it with anyone to receive "
                "anonymous messages."
            )
        )

        return

    bot.answer_callback_query(call.id)


# =========================================================
# Bio Input Handler
# =========================================================

def _receive_bio(message, user_id: int):

    if is_cancel(message):

        reply(
            message.chat.id,
hint("Bio update cancelled.")
        )

        return

    bio = (message.text or "").strip()

    if not bio:

        reply(
            message.chat.id,
warning("Bio cannot be empty.")
        )

        return

    if len(bio) > 200:

        reply(
            message.chat.id,
warning("Bio is too long (max 200 characters).")
        )

        return

    if update_bio(user_id, bio):

        reply(
            message.chat.id,
            card(
success("Your bio has been updated!"),
        [hint("Press Profile to view your profile.")],
            )
        )

    else:

        reply(
            message.chat.id,
warning("Something went wrong. Please press Profile again.")
        )


# =========================================================
# Avatar Input Handler
# =========================================================

def _receive_avatar(message, user_id: int):

    if is_cancel(message):

        reply(
            message.chat.id,
hint("Avatar update cancelled.")
        )

        return

    if message.content_type != "photo":

        reply(
            message.chat.id,
            card(
warning("Please send a photo, not text."),
        [hint("Try again from Profile.")],
            )
        )

        return

    file_id = message.photo[-1].file_id

    if update_avatar(user_id, file_id):

        reply(
            message.chat.id,
            card(
success("Your avatar has been updated!"),
        [hint("Press Profile to view your profile.")],
            )
        )

    else:

        reply(
            message.chat.id,
warning("Something went wrong. Please press Profile again.")
        )
