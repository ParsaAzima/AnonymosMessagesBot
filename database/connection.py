from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = "sqlite:///bot.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables and add any missing columns to existing tables."""

    # Ensure every model is registered on Base.metadata before create_all
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)

    # Columns that may be missing on databases created by earlier versions
    migrations = {
        "users": {
            "bio": "TEXT",
            "avatar_file_id": "VARCHAR(255)",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "is_banned": "BOOLEAN DEFAULT 0",
            "ban_reason": "TEXT",
            "banned_at": "DATETIME",
            "violation_count": "INTEGER DEFAULT 0",
        },
        "messages": {
            "content_type": "VARCHAR(50) DEFAULT 'text'",
            "media_file_id": "VARCHAR(255)",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
            "reaction": "VARCHAR(50)",
            "reply_to": "INTEGER",
        },
    }

    with engine.begin() as connection:

        for table, columns in migrations.items():

            if table not in inspector.get_table_names():
                continue

            existing = {
                col["name"]
                for col in inspector.get_columns(table)
            }

            for column, definition in columns.items():

                if column not in existing:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table} "
                            f"ADD COLUMN {column} {definition}"
                        )
                    )