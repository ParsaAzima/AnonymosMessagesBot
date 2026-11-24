from sqlalchemy import select, func, or_

from database.connection import SessionLocal
from database.models import Message


# =========================================================
# Serializer
# =========================================================

def _to_dict(message: Message) -> dict:
    """Convert a Message row into a plain dictionary."""

    return {
        "id": message.id,
        "sender": message.sender,
        "receiver": message.reciver,
        "content": message.content,
        "content_type": message.content_type,
        "media_file_id": message.media_file_id,
        "created_at": message.created_at,
        "reaction": message.reaction,
        "reply_to": message.reply_to,
    }


# =========================================================
# Write Operations
# =========================================================

def save_message(
    sender_id: int,
    receiver_id: int,
    content: str,
    content_type: str = "text",
    media_file_id: str | None = None,
) -> int:
    """Persist a message and return its database id."""

    with SessionLocal() as session:

        message = Message(
            sender=sender_id,
            reciver=receiver_id,
            content=content,
            content_type=content_type,
            media_file_id=media_file_id,
        )

        session.add(message)
        session.commit()

        return message.id


def save_reply(
    original_id: int,
    sender_id: int,
    receiver_id: int,
    content: str,
) -> int:
    """Save an anonymous reply linked to the original message."""

    with SessionLocal() as session:

        message = Message(
            sender=sender_id,
            reciver=receiver_id,
            content=content,
            content_type="text",
            reply_to=original_id,
        )

        session.add(message)
        session.commit()

        return message.id


def set_reaction(message_id: int, reaction: str | None) -> bool:
    """Set or clear a reaction. Return False if the message is gone."""

    with SessionLocal() as session:

        message = session.get(Message, message_id)

        if message is None:
            return False

        message.reaction = reaction

        session.commit()

        return True


# =========================================================
# Read Operations
# =========================================================

def get_message(message_id: int) -> dict | None:
    """Return a single message by id."""

    with SessionLocal() as session:

        message = session.get(Message, message_id)

        return _to_dict(message) if message else None


def count_inbox(user_id: int) -> int:
    """Count messages received by a user."""

    with SessionLocal() as session:

        return session.scalar(
            select(func.count()).select_from(Message).where(
                Message.reciver == user_id
            )
        ) or 0


def get_inbox(
    user_id: int,
    limit: int,
    offset: int = 0,
) -> list[dict]:
    """Return received messages, newest first."""

    with SessionLocal() as session:

        rows = session.scalars(
            select(Message)
            .where(Message.reciver == user_id)
            .order_by(
                Message.created_at.desc(),
                Message.id.desc()
            )
            .limit(limit)
            .offset(offset)
        ).all()

        return [_to_dict(row) for row in rows]


def count_history(user_id: int) -> int:
    """Count all messages a user sent or received."""

    with SessionLocal() as session:

        return session.scalar(
            select(func.count()).select_from(Message).where(
                or_(
                    Message.sender == user_id,
                    Message.reciver == user_id
                )
            )
        ) or 0


def get_history(
    user_id: int,
    limit: int,
    offset: int = 0,
) -> list[dict]:
    """Return sent and received messages, newest first."""

    with SessionLocal() as session:

        rows = session.scalars(
            select(Message)
            .where(
                or_(
                    Message.sender == user_id,
                    Message.reciver == user_id
                )
            )
            .order_by(
                Message.created_at.desc(),
                Message.id.desc()
            )
            .limit(limit)
            .offset(offset)
        ).all()

        return [_to_dict(row) for row in rows]
