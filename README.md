# Anonymous Messages Bot

A Telegram bot that lets people send each other anonymous messages through personal links. The sender's identity is never revealed to the recipient.

## Features

- Personal deep links for receiving anonymous messages (text, photo, video, voice, documents)
- Inbox with per-message reply and six reactions
- Anonymous replies back to the original sender
- Message history with pagination
- User profiles with bio, avatar, and message statistics
- Moderation: per-user block list, message reporting, admin review panel
- Rate limiting, spam detection, and automatic restrictions for repeat offenders
- Button-only interface (reply keyboard and inline buttons); no commands except `/start`, which Telegram requires for deep links

## Requirements

- Python 3.10 or newer
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Setup

```bash
git clone https://github.com/ParsaAzima/AnonymosMessagesBot.git
cd anonymosbot
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set your bot token:

```
BOT_TOKEN=your_token_here
```

Optionally add comma-separated Telegram user IDs to `ADMIN_IDS` to enable the admin panel.

Run the bot:

```bash
python main.py
```

The SQLite database (`bot.db`) is created automatically on first run. Existing databases are migrated in place when new columns are added.

## Configuration

All settings live in `core/config.py`:

| Setting | Default | Description |
|---|---|---|
| `FONT_STYLE` | `small_caps` | Text font applied to bot messages |
| `ADMIN_IDS` | empty | Telegram IDs with admin access |
| `RATE_LIMIT_MAX` | `5` | Messages allowed per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate-limit window in seconds |
| `SPAM_LINK_LIMIT` | `3` | Links allowed in one message |
| `SPAM_DUPLICATE_LIMIT` | `3` | Repeated messages before flagging |
| `AUTO_BAN_THRESHOLD` | `5` | Violations before automatic restriction |

Sensitive values are read from the environment and are never committed. See `.env.example`.

## Project structure

```
main.py              Entry point and handler registration
core/                Configuration, guards, typography, text builders
database/            SQLAlchemy models, engine, and migrations
services/            Business logic for users, messages, profiles, moderation
bot/                 Handlers, keyboards, menu dispatcher, reply helpers
```

## Security notes

- The bot token is loaded from `BOT_TOKEN` and is excluded from version control by `.gitignore`.
- Blocking and reporting work from stored sender IDs; recipient-facing messages never expose identity.
- Reaction emojis are the only emojis rendered by the bot; all other text is cleaned before sending.

## License

GNU General Public License v2.0. See [LICENSE](LICENSE).
