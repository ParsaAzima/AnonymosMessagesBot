from sqlalchemy import select, func

from database.connection import SessionLocal
from database.models import User, Message


def get_profile(telegram_id: int) -> dict | None:
    """
    Return a profile dictionary for a user:
        first_name, username, bio, avatar_file_id, created_at,
        messages_sent, messages_received
    Returns None if the user doesn't exist.
    """

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        if user is None:
            return None

        sent_count = session.scalar(
            select(func.count()).select_from(Message).where(
                Message.sender == telegram_id
            )
        )

        received_count = session.scalar(
            select(func.count()).select_from(Message).where(
                Message.reciver == telegram_id
            )
        )

        return {
            "first_name": user.first_name,
            "username": user.username,
            "bio": user.bio,
            "avatar_file_id": user.avatar_file_id,
            "created_at": user.created_at,
            "messages_sent": sent_count or 0,
            "messages_received": received_count or 0,
        }


def update_bio(telegram_id: int, bio: str) -> bool:
    """Set the user's bio. Return True on success, False if user not found."""

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        if user is None:
            return False

        user.bio = bio

        session.commit()

        return True


def update_avatar(telegram_id: int, file_id: str) -> bool:
    """Set the user's avatar file_id. Return True on success, False if user not found."""

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        if user is None:
            return False

        user.avatar_file_id = file_id

        session.commit()

        return True
