from datetime import datetime

from sqlalchemy import (
    String,
    BigInteger,
    ForeignKey,
    Text,
    DateTime,
    Boolean,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from database.connection import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    first_name: Mapped[str] = mapped_column(
        String(100)
    )

    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    avatar_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="0"
    )

    ban_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    banned_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    violation_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)

    sender: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        index=True
    )

    reciver: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id"),
        index=True
    )

    content: Mapped[str] = mapped_column(
        Text
    )

    content_type: Mapped[str] = mapped_column(
        String(50),
        default="text",
        server_default="text"
    )

    media_file_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    reaction: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    reply_to: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id"),
        nullable=True,
        index=True
    )


class BlockedUser(Base):
    __tablename__ = "blocked_users"

    id: Mapped[int] = mapped_column(primary_key=True)

    blocker_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True
    )

    blocked_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "blocker_id",
            "blocked_id",
            name="uq_blocker_blocked"
        ),
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)

    reporter_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True
    )

    reported_id: Mapped[int] = mapped_column(
        BigInteger,
        index=True
    )

    message_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    reason: Mapped[str] = mapped_column(
        String(50)
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="open",
        server_default="open"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )
