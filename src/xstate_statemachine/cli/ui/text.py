# src/xstate_statemachine/cli/ui/text.py
# -----------------------------------------------------------------------------
# 📐 Width-aware text helpers
# -----------------------------------------------------------------------------
# Layout (tables, boxes, trees) must measure the VISIBLE width of a string,
# not `len()`: ANSI escapes are zero-width, and East-Asian wide characters
# and most emoji occupy two cells. Getting this wrong is why hand-rolled
# tables tear the moment a cell is coloured. Everything here is pure and
# unit-tested against fixed widths.
# -----------------------------------------------------------------------------
"""Visible-width measurement, padding, truncation and wrapping."""

from __future__ import annotations

import re
import textwrap
import unicodedata
from typing import List

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def strip_ansi(text: str) -> str:
    """Remove SGR / cursor escape sequences."""
    return _ANSI_RE.sub("", text)


def _cell_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    cat = unicodedata.category(ch)
    if cat in ("Mn", "Me", "Cf"):
        return 0
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("W", "F"):
        return 2
    # Most emoji are "N"/"A" in EAW tables but render double-width.
    cp = ord(ch)
    if (
        0x1F300 <= cp <= 0x1FAFF
        or 0x2600 <= cp <= 0x27BF
        and cp
        not in (
            0x2713,
            0x2717,
            0x2714,
            0x2718,
            0x2192,
            0x25CF,
            0x25C6,
        )
    ):
        return 2
    return 1


def visible_width(text: str) -> int:
    """Number of terminal cells *text* occupies (escapes ignored)."""
    return sum(_cell_width(ch) for ch in strip_ansi(text))


def pad(text: str, width: int, align: str = "left") -> str:
    """Pad *text* with spaces to *width* visible cells."""
    gap = width - visible_width(text)
    if gap <= 0:
        return text
    if align == "right":
        return " " * gap + text
    if align == "center":
        left = gap // 2
        return " " * left + text + " " * (gap - left)
    return text + " " * gap


def truncate(text: str, width: int, ellipsis: str = "…") -> str:
    """Cut *text* to *width* cells, ending with *ellipsis* if cut.

    Escape sequences are preserved (they are zero-width) and a reset is
    appended when anything was cut inside a styled span, so a truncated
    coloured cell never bleeds its colour into the next column.
    """
    if visible_width(text) <= width:
        return text
    ell_w = visible_width(ellipsis)
    budget = max(0, width - ell_w)
    out: List[str] = []
    used = 0
    i = 0
    styled = False
    while i < len(text):
        m = _ANSI_RE.match(text, i)
        if m:
            out.append(m.group(0))
            styled = True
            i = m.end()
            continue
        w = _cell_width(text[i])
        if used + w > budget:
            break
        out.append(text[i])
        used += w
        i += 1
    result = "".join(out) + ellipsis
    return result + "\x1b[0m" if styled else result


def wrap(text: str, width: int) -> List[str]:
    """Word-wrap plain *text* to *width* cells; keeps existing newlines."""
    lines: List[str] = []
    for para in text.splitlines() or [""]:
        if not para.strip():
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                para,
                width=max(1, width),
                break_long_words=True,
                break_on_hyphens=False,
            )
            or [""]
        )
    return lines
