from sqlalchemy import select

from database.connection import SessionLocal
from database.models import User


def get_or_create_user(telegram_user) -> None:
    """
    Find a user by their Telegram ID.
    Create the user if it doesn't exist,
    otherwise update their username and first_name.
    """

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_user.id
            )
        )

        if user is None:

            user = User(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name or "Unknown"
            )

            session.add(user)

        else:

            user.username = telegram_user.username
            user.first_name = telegram_user.first_name or "Unknown"

        session.commit()


def get_user(telegram_id: int) -> bool:
    """Return True if a user with the given Telegram ID exists."""

    with SessionLocal() as session:

        return session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        ) is not None


def get_or_create_user_by_id(telegram_id: int) -> None:
    """Create a placeholder user record if one doesn't exist yet."""

    with SessionLocal() as session:

        user = session.scalar(
            select(User).where(
                User.telegram_id == telegram_id
            )
        )

        if user is None:

            session.add(
                User(
                    telegram_id=telegram_id,
                    username=None,
                    first_name="Unknown"
                )
            )

            session.commit()
