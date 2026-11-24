import re
from datetime import datetime, timedelta

from sqlalchemy import select, func

from core.config import (
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW,
    SPAM_LINK_LIMIT,
    SPAM_DUPLICATE_LIMIT,
    SPAM_DUPLICATE_WINDOW,
    AUTO_BAN_THRESHOLD,
)
from database.connection import SessionLocal
from database.models import (
    User,
    Message,
    BlockedUser,
    Report,
)


# =========================================================
# Ban Management
# =========================================================

def get_user_record(telegram_id: int) -> User | None:
    """Return the raw User row for a Telegram ID."""

    with SessionLocal() as session:
        return session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )


def is_banned(telegram_id: int) -> bool:
    """Return True if the account is restricted."""

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        return bool(user and user.is_banned)


def ban_user(telegram_id: int, reason: str = "No reason given") -> bool:
    """Restrict an account. Returns False if the user doesn't exist."""

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        if user is None:
            return False

        user.is_banned = True
        user.ban_reason = reason
        user.banned_at = datetime.now()

        session.commit()

        return True


def unban_user(telegram_id: int) -> bool:
    """Lift a restriction. Returns False if the user doesn't exist."""

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        if user is None:
            return False

        user.is_banned = False
        user.ban_reason = None
        user.banned_at = None
        user.violation_count = 0

        session.commit()

        return True


def get_banned_users() -> list[dict]:
    """Return all restricted accounts."""

    with SessionLocal() as session:

        rows = session.scalars(
            select(User)
            .where(User.is_banned.is_(True))
            .order_by(User.banned_at.desc())
        ).all()

        return [
            {
                "telegram_id": row.telegram_id,
                "first_name": row.first_name,
                "reason": row.ban_reason,
                "banned_at": row.banned_at,
            }
            for row in rows
        ]


# =========================================================
# Block Management
# =========================================================

def is_blocked(blocker_id: int, blocked_id: int) -> bool:
    """Return True if blocker_id has blocked blocked_id."""

    with SessionLocal() as session:

        return session.scalar(
            select(BlockedUser).where(
                BlockedUser.blocker_id == blocker_id,
                BlockedUser.blocked_id == blocked_id
            )
        ) is not None


def block_user(blocker_id: int, blocked_id: int) -> bool:
    """Block a user. Returns False if already blocked."""

    if blocker_id == blocked_id:
        return False

    with SessionLocal() as session:

        existing = session.scalar(
            select(BlockedUser).where(
                BlockedUser.blocker_id == blocker_id,
                BlockedUser.blocked_id == blocked_id
            )
        )

        if existing is not None:
            return False

        session.add(
            BlockedUser(
                blocker_id=blocker_id,
                blocked_id=blocked_id
            )
        )

        session.commit()

        return True


def unblock_user(blocker_id: int, blocked_id: int) -> bool:
    """Remove a block. Returns True if a block was removed."""

    with SessionLocal() as session:

        row = session.scalar(
            select(BlockedUser).where(
                BlockedUser.blocker_id == blocker_id,
                BlockedUser.blocked_id == blocked_id
            )
        )

        if row is None:
            return False

        session.delete(row)
        session.commit()

        return True


def get_blocked_users(blocker_id: int) -> list[int]:
    """Return the IDs blocked by a user."""

    with SessionLocal() as session:

        rows = session.scalars(
            select(BlockedUser.blocked_id)
            .where(BlockedUser.blocker_id == blocker_id)
            .order_by(BlockedUser.created_at.desc())
        ).all()

        return list(rows)


# =========================================================
# Reports
# =========================================================

def create_report(
    reporter_id: int,
    reported_id: int,
    reason: str,
    message_id: int | None = None,
    details: str | None = None,
) -> bool:
    """Store a new user report."""

    with SessionLocal() as session:

        session.add(
            Report(
                reporter_id=reporter_id,
                reported_id=reported_id,
                message_id=message_id,
                reason=reason,
                details=details,
                status="open",
            )
        )

        session.commit()

        return True


def get_report(report_id: int) -> dict | None:
    """Return one report by id."""

    with SessionLocal() as session:

        row = session.get(Report, report_id)

        if row is None:
            return None

        return {
            "id": row.id,
            "reporter_id": row.reporter_id,
            "reported_id": row.reported_id,
            "message_id": row.message_id,
            "reason": row.reason,
            "details": row.details,
            "status": row.status,
            "created_at": row.created_at,
        }


def get_reports(status: str = "open") -> list[dict]:
    """Return reports with the given status, oldest first."""

    with SessionLocal() as session:

        rows = session.scalars(
            select(Report)
            .where(Report.status == status)
            .order_by(Report.created_at.asc())
        ).all()

        return [
            {
                "id": row.id,
                "reporter_id": row.reporter_id,
                "reported_id": row.reported_id,
                "reason": row.reason,
                "details": row.details,
                "created_at": row.created_at,
            }
            for row in rows
        ]


def update_report_status(report_id: int, status: str) -> bool:
    """Mark a report as reviewed, actioned or dismissed."""

    with SessionLocal() as session:

        row = session.get(Report, report_id)

        if row is None:
            return False

        row.status = status

        session.commit()

        return True


# =========================================================
# Rate Limiting
# =========================================================

def is_rate_limited(user_id: int) -> bool:
    """Return True if the user exceeded the sending rate."""

    cutoff = datetime.now() - timedelta(
        seconds=RATE_LIMIT_WINDOW
    )

    with SessionLocal() as session:

        count = session.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.sender == user_id,
                Message.created_at >= cutoff
            )
        ) or 0

        return count >= RATE_LIMIT_MAX


# =========================================================
# Anti-Spam
# =========================================================

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
REPEAT_PATTERN = re.compile(r"(.)\1{15,}")


def detect_spam(user_id: int, content: str) -> tuple[bool, str]:
    """
    Check content for spam patterns.
    Returns (is_spam, reason).
    """

    # Link flood
    if len(URL_PATTERN.findall(content)) > SPAM_LINK_LIMIT:
        return True, "Too many links in one message."

    # Excessive repeated characters
    if REPEAT_PATTERN.search(content):
        return True, "Suspicious repetitive text."

    # Repeated identical content in a short window
    cutoff = datetime.now() - timedelta(
        seconds=SPAM_DUPLICATE_WINDOW
    )

    with SessionLocal() as session:

        count = session.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.sender == user_id,
                Message.content == content,
                Message.created_at >= cutoff
            )
        ) or 0

        if count >= SPAM_DUPLICATE_LIMIT:
            return True, "Duplicate message detected."

    return False, ""


# =========================================================
# Violations & Auto-Restriction
# =========================================================

def record_violation(
    telegram_id: int,
    reason: str,
) -> tuple[int, bool]:
    """
    Record a policy violation.
    Returns (new_count, was_auto_banned).
    """

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        if user is None:
            return 0, False

        user.violation_count += 1

        auto_banned = (
            user.violation_count >= AUTO_BAN_THRESHOLD
            and not user.is_banned
        )

        if auto_banned:
            user.is_banned = True
            user.ban_reason = (
                f"Auto-restricted after "
                f"{user.violation_count} violations. "
                f"Last: {reason}"
            )
            user.banned_at = datetime.now()

        session.commit()

        return user.violation_count, auto_banned


def check_message_allowed(
    user_id: int,
    content: str,
) -> tuple[bool, str]:
    """
    Combined pre-send check.
    Returns (allowed, rejection_reason).
    """

    if is_rate_limited(user_id):
        return False, "rate_limit"

    is_spam, reason = detect_spam(user_id, content)

    if is_spam:
        return False, reason

    return True, ""
