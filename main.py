import importlib

from core.config import bot, logger
from database.connection import init_db

# Importing handler modules registers all @bot.message_handler
# and @bot.callback_query_handler decorators on the TeleBot instance.
# importlib is used so the name `bot` is never shadowed by the local package.
for _module in (
    "bot.handlers",
    "bot.profile_handlers",
    "bot.social_handlers",
    "bot.moderation_handlers",
    "bot.menu",
):
    importlib.import_module(_module)


def main():

    init_db()

    logger.info("Bot is running...")

    bot.infinity_polling(
        skip_pending=True
    )


if __name__ == "__main__":
    main()
