# src/xstate_statemachine/cli/ui/progress.py
# -----------------------------------------------------------------------------
# ⏳ Spinners, progress bars and step lists -- in-place when the terminal
#    allows, one plain line per event when it does not
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: every live widget has a `plain` rendering that
#    prints ONE line per meaningful change and never rewrites. Scripts, CI
#    logs and the tests therefore see the same information as a human --
#    "◐ Generating…" becomes "Generating..." followed by "✓ Generated".
#    Animation is a presentation detail, never the only record of an event.
# -----------------------------------------------------------------------------
"""Spinner, ProgressBar and StepList."""

from __future__ import annotations

import sys
import threading
import time
from typing import List, Optional, Sequence, TextIO

from .style import paint
from .term import Capabilities
from .text import pad, visible_width

SPINNER_FRAMES = {
    "braille": "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    "dots": "⣾⣽⣻⢿⡿⣟⣯⣷",
    "bounce": "▖▘▝▗",
    "arc": "◜◠◝◞◡◟",
    "ascii": "|/-\\",
}

_HIDE = "\x1b[?25l"
_SHOW = "\x1b[?25h"
_CLEAR_LINE = "\x1b[2K\r"


class Spinner:
    """A single-line spinner with a message; a context manager.

    ::

        with Spinner(caps, "Parsing machines") as sp:
            ...
            sp.update("Parsing 3 machines")
        # prints "✓ Parsing 3 machines" on exit (or ✗ on exception)
    """

    def __init__(
        self,
        caps: Capabilities,
        message: str,
        *,
        frames: str = "braille",
        interval: float = 0.08,
        stream: Optional[TextIO] = None,
    ) -> None:
        self.caps = caps
        self.message = message
        self.frames = SPINNER_FRAMES[frames if caps.unicode else "ascii"]
        self.interval = interval
        self.out = stream or sys.stdout
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._final: Optional[str] = None

    # ---------------------------------------------------------------- api
    def update(self, message: str) -> None:
        self.message = message

    def succeed(self, message: Optional[str] = None) -> None:
        self._final = paint(
            "✓" if self.caps.unicode else "OK", "ok", self.caps
        )
        if message:
            self.message = message

    def fail(self, message: Optional[str] = None) -> None:
        self._final = paint(
            "✗" if self.caps.unicode else "X", "err", self.caps
        )
        if message:
            self.message = message

    # ---------------------------------------------------------------- ctx
    def __enter__(self) -> "Spinner":
        if self.caps.animate:
            self.out.write(_HIDE)
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()
        else:
            self.out.write(f"{self.message}...\n")
            self.out.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._final is None:
            if exc_type is None:
                self.succeed()
            else:
                self.fail()
        if self.caps.animate:
            self._stop.set()
            if self._thread:
                self._thread.join()
            self.out.write(
                _CLEAR_LINE + f"{self._final} {self.message}\n" + _SHOW
            )
        else:
            self.out.write(f"{self._final} {self.message}\n")
        self.out.flush()

    def _spin(self) -> None:
        i = 0
        while not self._stop.is_set():
            frame = paint(
                self.frames[i % len(self.frames)], "accent", self.caps
            )
            self.out.write(_CLEAR_LINE + f"{frame} {self.message}")
            self.out.flush()
            i += 1
            self._stop.wait(self.interval)


class ProgressBar:
    """A determinate bar: ``[████████░░░░░░] 8/14 files``."""

    BLOCKS = " ▏▎▍▌▋▊▉█"

    def __init__(
        self,
        caps: Capabilities,
        total: int,
        *,
        label: str = "",
        width: int = 30,
        stream: Optional[TextIO] = None,
    ) -> None:
        self.caps, self.total, self.label, self.width = (
            caps,
            total,
            label,
            width,
        )
        self.out = stream or sys.stdout
        self.current = 0
        self._started = time.monotonic()

    def _render(self) -> str:
        frac = 0 if self.total == 0 else self.current / self.total
        if self.caps.unicode:
            cells = frac * self.width
            full = int(cells)
            part = (
                self.BLOCKS[int((cells - full) * 8)]
                if full < self.width
                else ""
            )
            bar = "█" * full + part + " " * (self.width - full - len(part))
        else:
            full = int(frac * self.width)
            bar = "#" * full + "-" * (self.width - full)
        pct = f"{frac * 100:3.0f}%"
        return (
            paint("[", "muted", self.caps)
            + paint(bar, "brand", self.caps)
            + paint("]", "muted", self.caps)
            + f" {pct}  {self.current}/{self.total} {self.label}"
        )

    def advance(self, n: int = 1, label: Optional[str] = None) -> None:
        self.current = min(self.total, self.current + n)
        if label is not None:
            self.label = label
        if self.caps.animate:
            self.out.write(_CLEAR_LINE + self._render())
            if self.current >= self.total:
                self.out.write("\n")
            self.out.flush()
        else:
            self.out.write(f"[{self.current}/{self.total}] {self.label}\n")
            self.out.flush()


class StepList:
    """A checklist that fills in as steps complete.

    Animated: the block is redrawn in place. Plain: one line per step
    completion. Steps are ``pending`` → ``running`` → ``done`` | ``failed``
    | ``skipped``.
    """

    ICONS = {
        "pending": ("○", "muted", "."),
        "running": ("◐", "accent", ">"),
        "done": ("✓", "ok", "OK"),
        "failed": ("✗", "err", "X"),
        "skipped": ("–", "dim", "-"),
    }

    def __init__(
        self,
        caps: Capabilities,
        steps: Sequence[str],
        *,
        stream: Optional[TextIO] = None,
    ) -> None:
        self.caps = caps
        self.steps = list(steps)
        self.state = ["pending"] * len(self.steps)
        self.detail = [""] * len(self.steps)
        self.out = stream or sys.stdout
        self._drawn = 0

    def _icon(self, state: str) -> str:
        glyph, role, ascii_ = self.ICONS[state]
        return paint(glyph if self.caps.unicode else ascii_, role, self.caps)

    def _lines(self) -> List[str]:
        w = max(visible_width(s) for s in self.steps) if self.steps else 0
        return [
            f"  {self._icon(st)} {pad(name, w)}"
            + (paint(f"  {d}", "muted", self.caps) if d else "")
            for name, st, d in zip(self.steps, self.state, self.detail)
        ]

    def _redraw(self) -> None:
        if self._drawn:
            self.out.write(f"\x1b[{self._drawn}A")
        for line in self._lines():
            self.out.write(_CLEAR_LINE + line + "\n")
        self._drawn = len(self.steps)
        self.out.flush()

    def start(self, i: int, detail: str = "") -> None:
        self.state[i] = "running"
        self.detail[i] = detail
        if self.caps.animate:
            self._redraw()

    def finish(self, i: int, detail: str = "", *, state: str = "done") -> None:
        self.state[i] = state
        if detail:
            self.detail[i] = detail
        if self.caps.animate:
            self._redraw()
        else:
            _, _, ascii_ = self.ICONS[state]
            tail = f" -- {self.detail[i]}" if self.detail[i] else ""
            self.out.write(f"{self._icon(state)} {self.steps[i]}{tail}\n")
            self.out.flush()

    def begin(self) -> None:
        """Draw the initial pending list (animated mode only)."""
        if self.caps.animate:
            self._redraw()
