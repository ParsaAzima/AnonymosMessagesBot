import logging
import os

import telebot
from dotenv import load_dotenv

# Load variables from a local .env file if present.
load_dotenv()


# =========================================================
# Bot Configuration
# =========================================================

# The bot token is never committed. Set BOT_TOKEN in the environment
# (see .env.example) before running the bot.
TOKEN = os.getenv("BOT_TOKEN", "")

# Typography style. The bot ships with a single font: small_caps.
FONT_STYLE = "small_caps"


# =========================================================
# Moderation Configuration
# =========================================================

# Comma-separated Telegram user IDs, e.g. "123456,789012"
ADMIN_IDS = {
    int(value.strip())
    for value in os.getenv("ADMIN_IDS", "").split(",")
    if value.strip().isdigit()
}

# Max messages a user may send per window
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 60  # seconds

# Spam detection thresholds
SPAM_LINK_LIMIT = 3
SPAM_DUPLICATE_LIMIT = 3
SPAM_DUPLICATE_WINDOW = 300  # seconds

# Violations before an account is auto-restricted
AUTO_BAN_THRESHOLD = 5


# =========================================================
# Bot Instance
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. "
        "Copy .env.example to .env and add your token, "
        "or export BOT_TOKEN in your shell."
    )

bot = telebot.TeleBot(TOKEN)


# =========================================================
# Logging
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)
