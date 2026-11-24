from telebot import types

from core.config import bot, logger, ADMIN_IDS
from core.guards import restricted, admin_only
from core.ui_text import (
    heading,
    field,
    hint,
    warning,
    success,
    info,
    card,
    divider,
)
from bot.helpers import reply
from bot.keyboards import cancel_keyboard, is_cancel
from services.moderation import (
    block_user,
    unblock_user,
    is_blocked,
    get_blocked_users,
    create_report,
    get_report,
    get_reports,
    update_report_status,
    ban_user,
    unban_user,
    get_banned_users,
)
from services.message import get_message
from services.user import get_or_create_user


PAGE_SIZE = 1

REPORT_REASONS = [
    ("spam", "Spam"),
    ("harassment", "Harassment"),
    ("inappropriate", "Inappropriate"),
    ("other", "Other"),
]


# =========================================================
# Keyboard Helpers
# =========================================================

def _nav_keyboard(
    keyboard: types.InlineKeyboardMarkup,
    page: int,
    total: int,
    prefix: str,
) -> types.InlineKeyboardMarkup:

    nav = []

    if page > 0:
        nav.append(
            types.InlineKeyboardButton(
                text="Prev",
                callback_data=f"{prefix}_{page - 1}"
            )
        )

    if page < total - 1:
        nav.append(
            types.InlineKeyboardButton(
                text="Next",
                callback_data=f"{prefix}_{page + 1}"
            )
        )

    nav.append(
        types.InlineKeyboardButton(
            text="Close",
            callback_data="social_close"
        )
    )

    keyboard.add(*nav)

    return keyboard


# =========================================================
# Blocked List
# =========================================================

@restricted
def blocked_command(message):

    get_or_create_user(message.from_user)

    _send_blocked(message.chat.id, message.from_user.id, 0)


def _send_blocked(chat_id: int, user_id: int, page: int) -> None:

    blocked = get_blocked_users(user_id)

    if not blocked:

        bot.send_message(
            chat_id,
            card(
            heading("", "Block List is Empty"),
                [
            hint(
                        "Use the Block button on an inbox "
                        "message to block its sender."
                    )
                ],
            )
        )

        return

    total = len(blocked)
    page = max(0, min(page, total - 1))
    target = blocked[page]

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            text="Unblock",
            callback_data=f"unblock_{target}"
        )
    )

    _nav_keyboard(kb, page, total, "blocklist")

    bot.send_message(
        chat_id,
        card(
            heading("", f"Block List ({page + 1} / {total})"),
            [
            field("", "Blocked user", target),
            ],
        ),
        reply_markup=kb
    )


# =========================================================
# Admin: Banned Users
# =========================================================

@restricted
@admin_only
def banned_command(message):

    _send_banned(message.chat.id, 0)


def _send_banned(chat_id: int, page: int) -> None:

    banned = get_banned_users()

    if not banned:
        bot.send_message(
            chat_id,
            success("No restricted users.")
        )
        return

    total = len(banned)
    page = max(0, min(page, total - 1))
    entry = banned[page]

    kb = types.InlineKeyboardMarkup()

    kb.add(
        types.InlineKeyboardButton(
            text="Unrestrict",
            callback_data=f"unban_{entry['telegram_id']}"
        )
    )

    _nav_keyboard(kb, page, total, "banlist")

    reason = entry["reason"] or "No reason given"

    bot.send_message(
        chat_id,
        card(
            heading(
        "",
                f"Restricted Users ({page + 1} / {total})"
            ),
            [
            field("", "ID", entry["telegram_id"]),
            field("", "Name", entry["first_name"]),
            field("", "Reason", reason),
            ],
        ),
        reply_markup=kb
    )


# =========================================================
# Admin: Reports
# =========================================================

@restricted
@admin_only
def reports_command(message):

    _send_reports(message.chat.id, 0)


def _send_reports(chat_id: int, page: int) -> None:

    reports = get_reports("open")

    if not reports:
        bot.send_message(
            chat_id,
            success("No open reports.")
        )
        return

    total = len(reports)
    page = max(0, min(page, total - 1))
    report = reports[page]

    kb = types.InlineKeyboardMarkup(row_width=2)

    kb.add(
        types.InlineKeyboardButton(
            text="Ban User",
            callback_data=(
                f"reportban_{report['id']}_"
                f"{report['reported_id']}"
            )
        ),
        types.InlineKeyboardButton(
            text="Dismiss",
            callback_data=f"reportdismiss_{report['id']}"
        )
    )

    _nav_keyboard(kb, page, total, "reportlist")

    rows = [
            field("", "Report ID", report["id"]),
            field("", "Reporter", report["reporter_id"]),
            field("", "Reported user", report["reported_id"]),
            field("", "Reason", report["reason"]),
    ]

    if report["details"]:
        rows.append(
            field("", "Details", report["details"])
        )

    bot.send_message(
        chat_id,
        card(
            heading(
        "",
                f"Open Report ({page + 1} / {total})"
            ),
            rows,
        ),
        reply_markup=kb
    )


# =========================================================
# Callback Router
# =========================================================

@bot.callback_query_handler(
    func=lambda c: (c.data or "").startswith(
        (
            "blockuser_",
            "reportuser_",
            "reportreason_",
            "reportban_",
            "reportdismiss_",
            "unblock_",
            "unban_",
            "blocklist_",
            "reportlist_",
            "banlist_",
        )
    )
)
@restricted
def moderation_callback(call):

    data = call.data or ""
    user_id = call.from_user.id
    parts = data.split("_")

    # --- Block sender from an inbox message ---
    if len(parts) == 2 and parts[0] == "blockuser":

        try:
            message_id = int(parts[1])
        except ValueError:
            bot.answer_callback_query(call.id)
            return

        message = get_message(message_id)

        if message is None or message["receiver"] != user_id:

            bot.answer_callback_query(
                call.id,
                text="This is not your message!"
            )

            return

        if is_blocked(user_id, message["sender"]):

            bot.answer_callback_query(
                call.id,
                text="Already blocked"
            )

            return

        if block_user(user_id, message["sender"]):

            bot.answer_callback_query(
                call.id,
                text="Sender blocked"
            )

            _delete_card(call)

        else:

            bot.answer_callback_query(
                call.id,
                text="Could not block this user"
            )

        return

    # --- Report: choose reason ---
    if len(parts) == 2 and parts[0] == "reportuser":

        try:
            message_id = int(parts[1])
        except ValueError:
            bot.answer_callback_query(call.id)
            return

        message = get_message(message_id)

        if message is None or message["receiver"] != user_id:

            bot.answer_callback_query(
                call.id,
                text="This is not your message!"
            )

            return

        bot.answer_callback_query(call.id)

        kb = types.InlineKeyboardMarkup(row_width=2)

        kb.add(
            *[
                types.InlineKeyboardButton(
                    text=label,
                    callback_data=(
                        f"reportreason_{message_id}_{code}"
                    )
                )
                for code, label in REPORT_REASONS
            ]
        )

        bot.send_message(
            chat_id=call.message.chat.id,
        text=heading("", "Why report this message?"),
            reply_markup=kb
        )

        return

    # --- Report: reason selected ---
    if len(parts) == 3 and parts[0] == "reportreason":

        try:
            message_id = int(parts[1])
        except ValueError:
            bot.answer_callback_query(call.id)
            return

        code = parts[2]
        labels = dict(REPORT_REASONS)

        if code not in labels:
            bot.answer_callback_query(call.id)
            return

        message = get_message(message_id)

        if message is None or message["receiver"] != user_id:

            bot.answer_callback_query(
                call.id,
                text="This is not your message!"
            )

            return

        if code == "other":

            bot.answer_callback_query(call.id)

            prompt = bot.send_message(
                chat_id=call.message.chat.id,
                text=card(
            heading("", "Report Reason"),
                    [hint("Type a short reason for this report.")],
        footer="Press Cancel to abort.",
                ),
                reply_markup=cancel_keyboard()
            )

            bot.register_next_step_handler(
                prompt,
                restricted(_receive_report_details),
                message_id
            )

            return

        create_report(
            reporter_id=user_id,
            reported_id=message["sender"],
            reason=labels[code],
            message_id=message_id,
        )

        bot.answer_callback_query(
            call.id,
            text="Report submitted"
        )

        bot.send_message(
            chat_id=call.message.chat.id,
            text=(
            card(
            success("Report submitted"),
                [hint("Thank you. Moderators will review it.")],
            )
            )
        )

        return

    # --- Unblock ---
    if len(parts) == 2 and parts[0] == "unblock":

        try:
            target = int(parts[1])
        except ValueError:
            bot.answer_callback_query(call.id)
            return

        if unblock_user(user_id, target):

            bot.answer_callback_query(
                call.id,
                text="User unblocked"
            )

            _delete_card(call)
            _send_blocked(call.message.chat.id, user_id, 0)

        else:

            bot.answer_callback_query(
                call.id,
                text="Could not unblock"
            )

        return

    # --- Admin actions ---
    if len(parts) >= 2 and parts[0] in (
        "reportban",
        "reportdismiss",
        "unban",
    ):

        if user_id not in ADMIN_IDS:

            bot.answer_callback_query(
                call.id,
                text="Admins only"
            )

            return

        # Ban from report
        if parts[0] == "reportban"and len(parts) == 3:

            try:
                report_id = int(parts[1])
                target_id = int(parts[2])
            except ValueError:
                bot.answer_callback_query(call.id)
                return

            report = get_report(report_id)

            reason = (
                f"Report: {report['reason']}"
                if report
                else "Reported by user"
            )

            ban_user(target_id, reason)
            update_report_status(report_id, "actioned")

            bot.answer_callback_query(
                call.id,
                text="User banned"
            )

            _delete_card(call)
            _send_reports(call.message.chat.id, 0)

            try:
                bot.send_message(
                    target_id,
        "Your account has been restricted "
                    "by a moderator.\n\n"
                    f"Reason: {reason}"
                )
            except Exception as error:
                logger.debug("Ban notice failed: %s", error)

            return

        # Dismiss report
        if parts[0] == "reportdismiss"and len(parts) == 2:

            try:
                report_id = int(parts[1])
            except ValueError:
                bot.answer_callback_query(call.id)
                return

            update_report_status(report_id, "dismissed")

            bot.answer_callback_query(
                call.id,
                text="Report dismissed"
            )

            _delete_card(call)
            _send_reports(call.message.chat.id, 0)

            return

        # Unban
        if parts[0] == "unban"and len(parts) == 2:

            try:
                target_id = int(parts[1])
            except ValueError:
                bot.answer_callback_query(call.id)
                return

            if unban_user(target_id):
                bot.answer_callback_query(
                    call.id,
                    text="User unrestricted"
                )
            else:
                bot.answer_callback_query(
                    call.id,
                    text="User not found"
                )

            _delete_card(call)
            _send_banned(call.message.chat.id, 0)

            return

    # --- Pagination ---
    if len(parts) == 2:

        try:
            page = int(parts[1])
        except ValueError:
            bot.answer_callback_query(call.id)
            return

        action = parts[0]
        chat_id = call.message.chat.id

        bot.answer_callback_query(call.id)

        if action == "blocklist":
            _delete_card(call)
            _send_blocked(chat_id, user_id, page)

        elif action == "reportlist":
            _delete_card(call)
            _send_reports(chat_id, page)

        elif action == "banlist":
            _delete_card(call)
            _send_banned(chat_id, page)

        return

    bot.answer_callback_query(call.id)


# =========================================================
# Report Details Input
# =========================================================

def _receive_report_details(message, message_id: int):

    if is_cancel(message):

        reply(
            message.chat.id,
            hint("Report cancelled.")
        )

        return

    details = (message.text or "").strip()

    if not details:
        reply(
            message.chat.id,
            warning("Report reason cannot be empty.")
        )

        return

    report_message = get_message(message_id)

    if report_message is None:
        reply(
            message.chat.id,
            "That message is no longer available."
        )

        return

    create_report(
        reporter_id=message.from_user.id,
        reported_id=report_message["sender"],
        reason="Other",
        message_id=message_id,
        details=details,
    )

    reply(
        message.chat.id,
        "Thank you. Your report has been "
        "sent to the moderators."
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
