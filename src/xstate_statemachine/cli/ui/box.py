# src/xstate_statemachine/cli/ui/box.py
# -----------------------------------------------------------------------------
# 🧱 Panels, rules and card grids
# -----------------------------------------------------------------------------
"""Boxed panels and horizontal rules, with ASCII fallback glyph sets."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .style import paint
from .term import Capabilities
from .text import pad, truncate, visible_width, wrap


@dataclass(frozen=True)
class Glyphs:
    """One border glyph set."""

    tl: str
    tr: str
    bl: str
    br: str
    h: str
    v: str
    lt: str  # left tee (├)
    rt: str  # right tee (┤)


ROUNDED = Glyphs("╭", "╮", "╰", "╯", "─", "│", "├", "┤")
HEAVY = Glyphs("┏", "┓", "┗", "┛", "━", "┃", "┣", "┫")
DOUBLE = Glyphs("╔", "╗", "╚", "╝", "═", "║", "╠", "╣")
ASCII = Glyphs("+", "+", "+", "+", "-", "|", "+", "+")


def glyphs_for(caps: Capabilities, kind: str = "rounded") -> Glyphs:
    """Pick a glyph set the terminal can draw."""
    if not caps.unicode:
        return ASCII
    return {"rounded": ROUNDED, "heavy": HEAVY, "double": DOUBLE}.get(
        kind, ROUNDED
    )


def rule(
    caps: Capabilities,
    title: str = "",
    *,
    role: str = "muted",
    width: Optional[int] = None,
) -> str:
    """A horizontal rule, optionally with a centred title."""
    w = width or caps.width
    g = glyphs_for(caps)
    if not title:
        return paint(g.h * w, role, caps)
    label = f" {title} "
    side = max(0, (w - visible_width(label)) // 2)
    line = g.h * side + label + g.h * max(0, w - side - visible_width(label))
    return paint(line, role, caps)


def panel(
    caps: Capabilities,
    body: Sequence[str],
    *,
    title: str = "",
    subtitle: str = "",
    role: str = "brand",
    kind: str = "rounded",
    width: Optional[int] = None,
    padding: int = 1,
) -> List[str]:
    """Render *body* lines inside a bordered box; returns the lines.

    Lines wider than the box are truncated (with a styled-span-safe
    ellipsis) rather than wrapped, because callers pass pre-formatted
    tables and trees whose alignment wrapping would destroy. Wrap prose
    yourself with `text.wrap` first.
    """
    g = glyphs_for(caps, kind)
    outer = min(width or caps.width, caps.width)
    inner = outer - 2 - 2 * padding
    pad_s = " " * padding
    border = lambda s: paint(s, role, caps)  # noqa: E731

    top_label = f" {title} " if title else ""
    top = (
        g.tl
        + top_label
        + g.h * max(0, outer - 2 - visible_width(top_label))
        + g.tr
    )
    lines = [border(top)]
    if subtitle:
        lines.append(
            border(g.v)
            + pad_s
            + pad(paint(truncate(subtitle, inner), "muted", caps), inner)
            + pad_s
            + border(g.v)
        )
        lines.append(border(g.lt + g.h * (outer - 2) + g.rt))
    for raw in body:
        for line in (raw.split("\n") if "\n" in raw else [raw]):
            cell = pad(truncate(line, inner), inner)
            lines.append(border(g.v) + pad_s + cell + pad_s + border(g.v))
    lines.append(border(g.bl + g.h * (outer - 2) + g.br))
    return lines


def cards(
    caps: Capabilities,
    items: Sequence[Sequence[str]],
    *,
    columns: int = 0,
    role: str = "brand.deep",
    min_width: int = 28,
) -> List[str]:
    """Lay small panels out in a grid; each item is (title, *body lines)."""
    if not items:
        return []
    cols = columns or max(1, min(len(items), caps.width // (min_width + 2)))
    card_w = (caps.width - (cols - 1) * 2) // cols
    inner = card_w - 4
    rendered: List[List[str]] = []
    for item in items:
        title, *body = item
        body_lines: List[str] = []
        for b in body:
            body_lines.extend(
                wrap(b, inner) if visible_width(b) > inner else [b]
            )
        rendered.append(
            panel(caps, body_lines, title=title, role=role, width=card_w)
        )
    out: List[str] = []
    for i in range(0, len(rendered), cols):
        row = rendered[i : i + cols]
        height = max(len(c) for c in row)
        for r in range(height):
            parts = [
                c[r] if r < len(c) else " " * visible_width(c[0]) for c in row
            ]
            out.append("  ".join(parts))
    return out
