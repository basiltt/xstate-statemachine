# src/xstate_statemachine/cli/ui/style.py
# -----------------------------------------------------------------------------
# 🎨 Styles and the xsm theme
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: callers never write escape codes. They ask for a
#    NAMED role -- `accent`, `ok`, `warn`, `err`, `muted`, `title`, `kind.final`
#    -- and the theme maps roles to colours per capability tier (truecolor →
#    256 → 16 → none). One palette, chosen deliberately: a deep indigo brand,
#    an amber accent, slate for secondary text, and the conventional
#    green/yellow/red for status, so the CLI reads as one product rather
#    than a rainbow of defaults.
# -----------------------------------------------------------------------------
"""Named styles rendered against the detected terminal tier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .term import Capabilities

RGB = Tuple[int, int, int]

_RESET = "\x1b[0m"


@dataclass(frozen=True)
class Style:
    """One text style: an optional foreground and text attributes.

    Attributes:
        fg: 24-bit colour; downgraded per tier when rendering.
        bold / dim / italic / underline: SGR attributes.
        fg16: the 16-colour SGR code (30-37 / 90-97) to use when the
            terminal cannot do 256 or truecolor. Chosen per role so the
            fallback is still legible on dark AND light backgrounds.
    """

    fg: Optional[RGB] = None
    bold: bool = False
    dim: bool = False
    italic: bool = False
    underline: bool = False
    fg16: Optional[int] = None


# ---- the palette -----------------------------------------------------------
INDIGO: RGB = (99, 102, 241)
INDIGO_DEEP: RGB = (67, 56, 202)
AMBER: RGB = (245, 158, 11)
SLATE: RGB = (148, 163, 184)
SLATE_DIM: RGB = (100, 116, 139)
GREEN: RGB = (34, 197, 94)
YELLOW: RGB = (234, 179, 8)
RED: RGB = (239, 68, 68)
CYAN: RGB = (34, 211, 238)
PINK: RGB = (236, 72, 153)
WHITE: RGB = (241, 245, 249)

#: Role → Style. The keys are the whole vocabulary the rest of the CLI uses.
THEME: Dict[str, Style] = {
    "reset": Style(),
    "brand": Style(fg=INDIGO, bold=True, fg16=94),
    "brand.deep": Style(fg=INDIGO_DEEP, fg16=34),
    "accent": Style(fg=AMBER, bold=True, fg16=93),
    "title": Style(fg=WHITE, bold=True, fg16=97),
    "text": Style(),
    "muted": Style(fg=SLATE, fg16=90),
    "dim": Style(dim=True, fg16=90),
    "ok": Style(fg=GREEN, bold=True, fg16=92),
    "warn": Style(fg=YELLOW, bold=True, fg16=93),
    "err": Style(fg=RED, bold=True, fg16=91),
    "info": Style(fg=CYAN, fg16=96),
    "key": Style(fg=AMBER, fg16=33),
    "path": Style(fg=CYAN, underline=True, fg16=36),
    "code": Style(fg=SLATE, fg16=37),
    "diff.add": Style(fg=GREEN, fg16=32),
    "diff.del": Style(fg=RED, fg16=31),
    "diff.hunk": Style(fg=CYAN, fg16=36),
    # state kinds, for trees and diagrams
    "kind.atomic": Style(fg=WHITE, fg16=97),
    "kind.compound": Style(fg=INDIGO, bold=True, fg16=94),
    "kind.parallel": Style(fg=PINK, bold=True, fg16=95),
    "kind.final": Style(fg=GREEN, bold=True, fg16=92),
    "kind.history": Style(fg=AMBER, italic=True, fg16=33),
    "kind.active": Style(fg=AMBER, bold=True, fg16=93),
    "event": Style(fg=CYAN, bold=True, fg16=96),
    "guard": Style(fg=YELLOW, fg16=33),
    "action": Style(fg=PINK, fg16=95),
    "service": Style(fg=INDIGO, fg16=94),
}


def _rgb_to_256(rgb: RGB) -> int:
    """Nearest xterm-256 cube colour for an RGB triple."""
    r, g, b = (round(c / 255 * 5) for c in rgb)
    return 16 + 36 * r + 6 * g + b


def sgr(style: Style, caps: Capabilities) -> str:
    """The SGR prefix for *style* on this terminal ('' when colour is off)."""
    if not caps.color:
        return ""
    codes = []
    if style.bold:
        codes.append("1")
    if style.dim:
        codes.append("2")
    if style.italic:
        codes.append("3")
    if style.underline:
        codes.append("4")
    if style.fg is not None:
        if caps.truecolor:
            codes.append("38;2;%d;%d;%d" % style.fg)
        elif style.fg16 is not None and not caps.truecolor and caps.tty:
            # 🎯 256-colour is honoured by every modern terminal that is a
            #    tty; prefer the cube, keep fg16 for the dumbest hosts.
            codes.append("38;5;%d" % _rgb_to_256(style.fg))
        elif style.fg16 is not None:
            codes.append(str(style.fg16))
    return "\x1b[" + ";".join(codes) + "m" if codes else ""


def paint(text: str, role: str, caps: Capabilities) -> str:
    """Wrap *text* in the escapes for *role*; identity when colour is off."""
    if not caps.color or not text:
        return text
    style = THEME.get(role)
    if style is None:
        raise KeyError(f"unknown style role {role!r}")
    prefix = sgr(style, caps)
    return f"{prefix}{text}{_RESET}" if prefix else text
