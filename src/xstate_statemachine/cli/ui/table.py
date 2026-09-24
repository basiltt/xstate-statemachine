# src/xstate_statemachine/cli/ui/table.py
# -----------------------------------------------------------------------------
# 📊 Tables that fit the terminal
# -----------------------------------------------------------------------------
"""A width-aware table renderer with auto-fit and ASCII fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .box import glyphs_for
from .style import paint
from .term import Capabilities
from .text import pad, truncate, visible_width


@dataclass
class Column:
    """One table column.

    Attributes:
        header: Column title.
        align: ``left`` / ``right`` / ``center``.
        role: Style role applied to every cell (headers use ``title``).
        min_width / max_width: Bounds for auto-fit. ``max_width=0`` means
            "no cap"; the widest column is shrunk first when the table is
            wider than the terminal.
        shrink: Whether auto-fit may narrow this column.
    """

    header: str
    align: str = "left"
    role: Optional[str] = None
    min_width: int = 3
    max_width: int = 0
    shrink: bool = True


@dataclass
class Table:
    columns: List[Column]
    rows: List[List[str]] = field(default_factory=list)
    zebra: bool = False
    border: bool = True

    def add(self, *cells: object) -> "Table":
        self.rows.append([str(c) if c is not None else "" for c in cells])
        return self

    # ---------------------------------------------------------------- layout
    def _widths(self, caps: Capabilities) -> List[int]:
        n = len(self.columns)
        widths = [
            max(
                visible_width(c.header),
                *(visible_width(r[i]) if i < len(r) else 0 for r in self.rows),
                c.min_width,
            )
            for i, c in enumerate(self.columns)
        ]
        for i, c in enumerate(self.columns):
            if c.max_width:
                widths[i] = min(widths[i], c.max_width)
        # 3 chars per separator ("│ x │"), 1 extra for the outer borders
        chrome = (3 * (n - 1)) + (4 if self.border else 0)
        budget = caps.width - chrome
        # shrink the widest shrinkable column until it fits
        while sum(widths) > budget:
            candidates = [
                i
                for i, c in enumerate(self.columns)
                if c.shrink and widths[i] > c.min_width
            ]
            if not candidates:
                break
            i = max(candidates, key=lambda k: widths[k])
            widths[i] -= 1
        return widths

    # ---------------------------------------------------------------- render
    def render(self, caps: Capabilities) -> List[str]:
        g = glyphs_for(caps)
        widths = self._widths(caps)
        sep_mid = paint(f" {g.v} ", "muted", caps)
        v = paint(g.v, "muted", caps)

        def row_line(cells: Sequence[str], header: bool, idx: int) -> str:
            parts = []
            for i, col in enumerate(self.columns):
                raw = cells[i] if i < len(cells) else ""
                cell = truncate(raw, widths[i])
                if header:
                    cell = paint(cell, "title", caps)
                elif col.role:
                    cell = paint(cell, col.role, caps)
                elif self.zebra and idx % 2 == 1:
                    cell = paint(cell, "muted", caps)
                parts.append(pad(cell, widths[i], col.align))
            line = sep_mid.join(parts)
            return f"{v} {line} {v}" if self.border else line

        def hline(left: str, mid: str, right: str) -> str:
            segs = [g.h * (w + 2) for w in widths]
            return paint(left + mid.join(segs) + right, "muted", caps)

        out: List[str] = []
        if self.border:
            out.append(hline(g.tl, "┬" if caps.unicode else "+", g.tr))
        out.append(row_line([c.header for c in self.columns], True, 0))
        out.append(
            hline(g.lt, "┼" if caps.unicode else "+", g.rt)
            if self.border
            else paint((" " * 3).join(g.h * w for w in widths), "muted", caps)
        )
        for idx, r in enumerate(self.rows):
            out.append(row_line(r, False, idx))
        if self.border:
            out.append(hline(g.bl, "┴" if caps.unicode else "+", g.br))
        return out
