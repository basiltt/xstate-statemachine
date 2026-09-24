# src/xstate_statemachine/cli/ui/animate.py
# -----------------------------------------------------------------------------
# ✨ One-shot animations
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: animation is a garnish with a hard time budget.
#    Every effect here completes in well under half a second and is skipped
#    entirely when `caps.animate` is False, so a script piping `xsm` never
#    pays for it and a user on a slow link can turn it off (`--no-anim`,
#    `XSM_NO_ANIM`). Nothing is ever conveyed ONLY by an animation.
# -----------------------------------------------------------------------------
"""Banner wipe-in, typewriter and a brief highlight pulse."""

from __future__ import annotations

import sys
import time
from typing import Optional, Sequence, TextIO

from .style import paint
from .term import Capabilities

_HIDE, _SHOW, _CLEAR = "\x1b[?25l", "\x1b[?25h", "\x1b[2K\r"


def wipe_in(
    caps: Capabilities,
    lines: Sequence[str],
    *,
    total_ms: int = 320,
    stream: Optional[TextIO] = None,
) -> None:
    """Reveal *lines* top-to-bottom with a short delay between rows."""
    out = stream or sys.stdout
    if not caps.animate or not lines:
        out.write("\n".join(lines) + "\n")
        out.flush()
        return
    step = min(0.06, total_ms / 1000 / max(1, len(lines)))
    out.write(_HIDE)
    try:
        for line in lines:
            out.write(line + "\n")
            out.flush()
            time.sleep(step)
    finally:
        out.write(_SHOW)
        out.flush()


def typewriter(
    caps: Capabilities,
    text: str,
    *,
    role: Optional[str] = None,
    total_ms: int = 240,
    stream: Optional[TextIO] = None,
) -> None:
    """Type *text* character by character (whole line at once when plain)."""
    out = stream or sys.stdout
    if not caps.animate or not text:
        out.write((paint(text, role, caps) if role else text) + "\n")
        out.flush()
        return
    step = total_ms / 1000 / max(1, len(text))
    out.write(_HIDE)
    try:
        for i in range(1, len(text) + 1):
            chunk = text[:i]
            out.write(_CLEAR + (paint(chunk, role, caps) if role else chunk))
            out.flush()
            time.sleep(step)
        out.write("\n")
    finally:
        out.write(_SHOW)
        out.flush()


def pulse(
    caps: Capabilities,
    line: str,
    *,
    frames: int = 3,
    total_ms: int = 180,
    stream: Optional[TextIO] = None,
) -> None:
    """Flash *line* between accent and normal, ending on the normal form.

    Used by the simulator when the active state changes so the eye is
    drawn to the new configuration.
    """
    out = stream or sys.stdout
    if not caps.animate:
        out.write(line + "\n")
        out.flush()
        return
    step = total_ms / 1000 / max(1, frames * 2)
    out.write(_HIDE)
    try:
        for _ in range(frames):
            out.write(_CLEAR + paint(line, "accent", caps))
            out.flush()
            time.sleep(step)
            out.write(_CLEAR + line)
            out.flush()
            time.sleep(step)
        out.write("\n")
    finally:
        out.write(_SHOW)
        out.flush()
