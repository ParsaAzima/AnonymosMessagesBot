import re

from core.config import FONT_STYLE


# =========================================================
# Font Definition (small_caps only)
# =========================================================

LOWER = "abcdefghijklmnopqrstuvwxyz"
UPPER = LOWER.upper()

# Each entry: (lowercase glyphs, uppercase glyphs).
# Only one font is supported; other styles were removed intentionally.
FONTS = {
    "small_caps": (
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
        "ᴀʙᴄᴅᴇꜰɢʜɪᴊᴋʟᴍɴᴏᴘǫʀꜱᴛᴜᴠᴡxʏᴢ",
    ),
}

FONT_MAPS = {
    name: str.maketrans(LOWER + UPPER, low + up)
    for name, (low, up) in FONTS.items()
}


# =========================================================
# Protected Tokens
# =========================================================

# URLs and HTML tags/entities must never be translated.
# The capturing group is required: re.split() keeps matched tokens only
# when the pattern has a group, otherwise the URL is consumed and lost.
PROTECTED = re.compile(
    r"(https?://\S+|<[^>]+>|&[#a-zA-Z0-9]+;)"
)


# =========================================================
# Styling Functions
# =========================================================

def stylize(value: str, style: str = None) -> str:
    """Apply the small_caps font while leaving protected tokens intact."""

    style = style or FONT_STYLE

    font_map = FONT_MAPS.get(style)

    if font_map is None:
        return value

    return "".join(
        part if PROTECTED.fullmatch(part) or part.startswith(
            ("http://", "https://")
        )
        else part.translate(font_map)
        for part in PROTECTED.split(value)
    )


def text(value: str) -> str:
    """Default styling entry point."""

    return stylize(value)
