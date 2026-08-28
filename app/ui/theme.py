"""Theme definitions mapping color schemes to explicit PyQt6 QColors."""

from dataclasses import dataclass
from PyQt6.QtGui import QColor

@dataclass
class Theme:
    bg: QColor
    bg_soft: QColor
    accent: QColor
    text: QColor
    dim: QColor
    line: QColor
    ink: QColor

THEMES: dict[str, Theme] = {
    "green": Theme(
        bg=QColor("#000200"),
        bg_soft=QColor("#030b05"),
        accent=QColor("#35ff6a"),
        text=QColor("#21d954"),
        dim=QColor("#12813a"),
        line=QColor("#0b5227"),
        ink=QColor("#000600"),
    ),
    "amber": Theme(
        bg=QColor("#020100"),
        bg_soft=QColor("#0b0503"),
        accent=QColor("#ffb435"),
        text=QColor("#d99621"),
        dim=QColor("#815812"),
        line=QColor("#52360b"),
        ink=QColor("#060300"),
    ),
    "blue": Theme(
        bg=QColor("#000102"),
        bg_soft=QColor("#03070b"),
        accent=QColor("#3584ff"),
        text=QColor("#2161d9"),
        dim=QColor("#123881"),
        line=QColor("#0b2252"),
        ink=QColor("#000206"),
    ),
}

ACTIVE_SCHEME = "green"

def set_active_scheme(scheme_name: str) -> None:
    global ACTIVE_SCHEME
    ACTIVE_SCHEME = scheme_name

def get_active_theme() -> Theme:
    return THEMES.get(ACTIVE_SCHEME.lower(), THEMES["green"])

def get_theme(scheme_name: str) -> Theme:
    """Return the Theme matching the scheme_name, falling back to green."""
    return THEMES.get(scheme_name.lower(), THEMES["green"])
