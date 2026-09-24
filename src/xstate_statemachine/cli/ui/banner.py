# src/xstate_statemachine/cli/ui/banner.py
# -----------------------------------------------------------------------------
# 🪧 The `xsm` banner -- block-letter logo, gradient-painted when possible
# -----------------------------------------------------------------------------
"""Banner rendering with three sizes chosen by terminal width."""

from __future__ import annotations

from typing import List

from .style import INDIGO, INDIGO_DEEP, AMBER, Style, sgr
from .term import Capabilities
from .text import visible_width

# Hand-drawn block letters. Each glyph is 6 rows; rows are joined per letter.
_BIG = [
    "██╗  ██╗███████╗███╗   ███╗",
    "╚██╗██╔╝██╔════╝████╗ ████║",
    " ╚███╔╝ ███████╗██╔████╔██║",
    " ██╔██╗ ╚════██║██║╚██╔╝██║",
    "██╔╝ ██╗███████║██║ ╚═╝ ██║",
    "╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝",
]
_SMALL = [
    "▀▄▀ █▀▀ █▄ ▄█",
    "█ █ ▄▄█ █ ▀ █",
]
_ASCII = [
    " __  __ ___ __  __ ",
    " \\ \\/ // __||  \\/  |",
    "  >  < \\__ \\| |\\/| |",
    " /_/\\_\\|___/|_|  |_|",
]

TAGLINE = "statecharts for Python · XState-compatible · zero dependencies"


def _lerp(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _gradient_line(line: str, caps: Capabilities, t_row: float) -> str:
    """Paint one banner row with a left→right indigo→amber sweep."""
    if not caps.color:
        return line
    if not caps.truecolor:
        return (
            sgr(Style(fg=INDIGO, bold=True, fg16=94), caps) + line + "\x1b[0m"
        )
    out: List[str] = []
    n = max(1, len(line))
    for i, ch in enumerate(line):
        if ch == " ":
            out.append(ch)
            continue
        t = (i / n) * 0.75 + t_row * 0.25
        rgb = _lerp(
            INDIGO_DEEP if t < 0.5 else INDIGO,
            INDIGO if t < 0.5 else AMBER,
            (t % 0.5) * 2,
        )
        out.append("\x1b[38;2;%d;%d;%dm%s" % (*rgb, ch))
    out.append("\x1b[0m")
    return "".join(out)


def render(caps: Capabilities, version: str) -> List[str]:
    """Banner lines for the current terminal."""
    if not caps.unicode:
        art = _ASCII
    elif caps.width >= 60:
        art = _BIG
    else:
        art = _SMALL
    rows = len(art)
    lines = [
        _gradient_line(row, caps, i / max(1, rows - 1))
        for i, row in enumerate(art)
    ]
    ver = f"v{version}"
    tag = TAGLINE if caps.unicode else TAGLINE.replace("·", "-")
    meta = f"{ver}  {tag}"
    if caps.color:
        meta = (
            sgr(Style(fg=AMBER, bold=True, fg16=93), caps)
            + ver
            + "\x1b[0m"
            + "  "
            + sgr(Style(fg=(148, 163, 184), fg16=90), caps)
            + tag
            + "\x1b[0m"
        )
    lines.append("")
    lines.append(meta if visible_width(f"{ver}  {tag}") <= caps.width else ver)
    return lines
