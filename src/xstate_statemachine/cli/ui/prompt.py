# src/xstate_statemachine/cli/ui/prompt.py
# -----------------------------------------------------------------------------
# 🧭 Interactive prompts: select, multiselect, confirm, text
# -----------------------------------------------------------------------------
# Each prompt takes a `KeySource` (default: the real keyboard) and a
# `Capabilities`. In a non-interactive context callers must not reach here
# -- `Console.interactive` gates it -- but every prompt also accepts a
# `default` so a wizard can be driven from flags when stdin is not a tty.
# -----------------------------------------------------------------------------
"""Arrow-key prompts with a stdlib-only implementation."""

from __future__ import annotations

import sys
from typing import List, Optional, Sequence, TextIO, Tuple

from . import keys as K
from .style import paint
from .term import Capabilities
from .text import pad, truncate, visible_width

_HIDE, _SHOW, _CLEAR = "\x1b[?25l", "\x1b[?25h", "\x1b[2K\r"


def _up(n: int) -> str:
    return f"\x1b[{n}A" if n else ""


class _Painter:
    """Redraws a block of lines in place."""

    def __init__(self, out: TextIO) -> None:
        self.out, self.drawn = out, 0

    def draw(self, lines: Sequence[str]) -> None:
        self.out.write(_up(self.drawn))
        for line in lines:
            self.out.write(_CLEAR + line + "\n")
        self.drawn = len(lines)
        self.out.flush()

    def clear(self) -> None:
        self.out.write(_up(self.drawn))
        for _ in range(self.drawn):
            self.out.write(_CLEAR + "\n")
        self.out.write(_up(self.drawn))
        self.drawn = 0
        self.out.flush()


def select(
    caps: Capabilities,
    title: str,
    options: Sequence[Tuple[str, str]],
    *,
    default: int = 0,
    source: Optional[K.KeySource] = None,
    stream: Optional[TextIO] = None,
    hint: str = "↑↓ move · enter select · esc cancel",
) -> Optional[int]:
    """Pick one of *options* (``(label, description)``); returns the index
    or ``None`` on escape. Type a digit 1–9 to jump; ``q`` cancels."""
    out = stream or sys.stdout
    src = source or K.default_source()
    cur = max(0, min(default, len(options) - 1))
    painter = _Painter(out)
    marker = "❯" if caps.unicode else ">"
    hint_txt = (
        hint if caps.unicode else "arrows move, enter select, esc cancel"
    )
    label_w = max(visible_width(o[0]) for o in options)

    def lines() -> List[str]:
        rows = [paint(title, "title", caps)]
        for i, (label, desc) in enumerate(options):
            active = i == cur
            m = paint(marker, "accent", caps) if active else " "
            lab = paint(
                pad(label, label_w), "accent" if active else "text", caps
            )
            d = paint(truncate(desc, caps.width - label_w - 8), "muted", caps)
            rows.append(f"  {m} {lab}  {d}")
        rows.append(paint(f"  {hint_txt}", "dim", caps))
        return rows

    out.write(_HIDE)
    try:
        while True:
            painter.draw(lines())
            key = src()
            if key in (K.UP, "k"):
                cur = (cur - 1) % len(options)
            elif key in (K.DOWN, "j", K.TAB):
                cur = (cur + 1) % len(options)
            elif key == K.HOME:
                cur = 0
            elif key == K.END:
                cur = len(options) - 1
            elif key.isdigit() and 1 <= int(key) <= len(options):
                cur = int(key) - 1
            elif key == K.ENTER:
                painter.clear()
                out.write(
                    f"{paint('?', 'ok', caps)} {title}  "
                    f"{paint(options[cur][0], 'accent', caps)}\n"
                )
                return cur
            elif key in (K.ESC, "q"):
                painter.clear()
                return None
    finally:
        out.write(_SHOW)
        out.flush()


def multiselect(
    caps: Capabilities,
    title: str,
    options: Sequence[Tuple[str, str]],
    *,
    selected: Sequence[int] = (),
    source: Optional[K.KeySource] = None,
    stream: Optional[TextIO] = None,
) -> Optional[List[int]]:
    """Toggle any number of *options* with space; enter confirms."""
    out = stream or sys.stdout
    src = source or K.default_source()
    cur, chosen = 0, set(selected)
    painter = _Painter(out)
    on, off = ("◉", "○") if caps.unicode else ("[x]", "[ ]")
    marker = "❯" if caps.unicode else ">"
    label_w = max(visible_width(o[0]) for o in options)

    def lines() -> List[str]:
        rows = [paint(title, "title", caps)]
        for i, (label, desc) in enumerate(options):
            active = i == cur
            box = paint(
                on if i in chosen else off,
                "accent" if i in chosen else "muted",
                caps,
            )
            m = paint(marker, "accent", caps) if active else " "
            lab = paint(
                pad(label, label_w), "accent" if active else "text", caps
            )
            rows.append(
                f"  {m} {box} {lab}  {paint(truncate(desc, caps.width - label_w - 12), 'muted', caps)}"
            )
        rows.append(
            paint(
                "  space toggle · a all · n none · enter confirm · esc cancel",
                "dim",
                caps,
            )
        )
        return rows

    out.write(_HIDE)
    try:
        while True:
            painter.draw(lines())
            key = src()
            if key in (K.UP, "k"):
                cur = (cur - 1) % len(options)
            elif key in (K.DOWN, "j", K.TAB):
                cur = (cur + 1) % len(options)
            elif key == K.HOME:
                cur = 0
            elif key == K.END:
                cur = len(options) - 1
            elif key == K.SPACE:
                # ☑️ Toggle AND step down (Inquirer / fzf convention), so
                #    "space space enter" picks the first two rows rather
                #    than toggling the first one on and off again.
                chosen ^= {cur}
                if cur < len(options) - 1:
                    cur += 1
            elif key == "a":
                chosen = set(range(len(options)))
            elif key == "n":
                chosen = set()
            elif key == K.ENTER:
                painter.clear()
                names = (
                    ", ".join(options[i][0] for i in sorted(chosen)) or "none"
                )
                out.write(
                    f"{paint('?', 'ok', caps)} {title}  {paint(names, 'accent', caps)}\n"
                )
                return sorted(chosen)
            elif key in (K.ESC, "q"):
                painter.clear()
                return None
    finally:
        out.write(_SHOW)
        out.flush()


def confirm(
    caps: Capabilities,
    question: str,
    *,
    default: bool = True,
    source: Optional[K.KeySource] = None,
    stream: Optional[TextIO] = None,
) -> Optional[bool]:
    """Yes / no on a single key. ``None`` on escape."""
    out = stream or sys.stdout
    src = source or K.default_source()
    yn = "[Y/n]" if default else "[y/N]"
    out.write(
        f"{paint('?', 'accent', caps)} {question} {paint(yn, 'muted', caps)} "
    )
    out.flush()
    while True:
        key = src()
        if key in ("y", "Y"):
            ans: Optional[bool] = True
        elif key in ("n", "N"):
            ans = False
        elif key == K.ENTER:
            ans = default
        elif key in (K.ESC, "q"):
            ans = None
        else:
            continue
        shown = {True: "yes", False: "no", None: "cancelled"}[ans]
        out.write(paint(shown, "accent" if ans else "muted", caps) + "\n")
        out.flush()
        return ans


def text(
    caps: Capabilities,
    question: str,
    *,
    default: str = "",
    source: Optional[K.KeySource] = None,
    stream: Optional[TextIO] = None,
) -> Optional[str]:
    """Free text with a default; edits with backspace; ``None`` on escape."""
    out = stream or sys.stdout
    src = source or K.default_source()
    buf = list(default)

    def draw() -> None:
        shown = "".join(buf)
        out.write(
            _CLEAR
            + f"{paint('?', 'accent', caps)} {question} "
            + paint(shown, "accent", caps)
        )
        out.flush()

    draw()
    while True:
        key = src()
        if key == K.ENTER:
            out.write("\n")
            return "".join(buf)
        if key in (K.ESC,):
            out.write("\n")
            return None
        if key == K.BACKSPACE:
            if buf:
                buf.pop()
        elif key == K.SPACE:
            buf.append(" ")
        elif len(key) == 1:
            buf.append(key)
        draw()
