import re


# =========================================================
# Emoji Removal
# =========================================================

# Matches emoji, pictographs, variation selectors and arrows.
# Reaction emojis never pass through here: they are stored
# separately in bot.social_handlers.REACTIONS.
_EMOJI = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\u2600-\u27BF"
    "\u2B00-\u2BFF"
    "\uFE0F"
    "\u2190-\u21FF"
    "]"
)


def clean(value) -> str:
    """Strip emojis from any outgoing text."""

    if value is None:
        return ""

    return re.sub(r" {2,}", " ", _EMOJI.sub("", str(value))).strip()


# =========================================================
# Visual Constants
# =========================================================

DIVIDER = "━━━━━━━━━━━━━━━━━━━━"
THIN_DIVIDER = "────────────────────"


# =========================================================
# Building Blocks
# =========================================================

def heading(_icon: str, title: str) -> str:
    """A title line followed by a divider.

    The first argument is kept for call-site compatibility
    but is intentionally ignored: no icons are rendered.
    """

    return f"{clean(title)}\n{DIVIDER}"


def divider() -> str:
    return DIVIDER


def field(_icon: str, label: str, value) -> str:
    """A labeled row, e.g. 'Name: Parsa'."""

    return f"{clean(label)}: {clean(value)}"


def plain_field(label: str, value) -> str:
    return f"{clean(label)}: {clean(value)}"


def hint(value: str) -> str:
    return clean(value)


def success(value: str) -> str:
    return clean(value)


def warning(value: str) -> str:
    return clean(value)


def error(value: str) -> str:
    return clean(value)


def info(value: str) -> str:
    return clean(value)


def card(title: str, rows: list[str], footer: str = None) -> str:
    """Assemble a titled card out of prepared rows."""

    parts = [clean(title)] + [clean(row) for row in rows]

    if footer:
        parts.extend(["", THIN_DIVIDER, clean(footer)])

    return "\n".join(parts)


def numbered(items: list[str]) -> str:
    return "\n".join(
        f"{index}. {value}"
        for index, value in enumerate(items, 1)
    )
