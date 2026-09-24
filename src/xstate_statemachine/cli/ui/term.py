# src/xstate_statemachine/cli/ui/term.py
# -----------------------------------------------------------------------------
# 🖥️ Terminal capability detection -- the ONE place the CLI asks "what can
#    this console do?"
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: every rendering primitive (colour, box glyphs,
#    spinners, key reads) consults `Capabilities` instead of probing the
#    environment itself, so the fallback story is decided once and tested
#    once. The contract for scripts and CI: when stdout is not a TTY, or the
#    user asks (`--plain`, `NO_COLOR`, `XSM_NO_COLOR`, `TERM=dumb`), output is
#    deterministic plain text -- no ANSI, no cursor movement, no animation --
#    and the same words appear in the same order as the styled rendering.
#
# 🪟 Windows: modern consoles (Windows Terminal, VS Code) honour VT escapes
#    once `ENABLE_VIRTUAL_TERMINAL_PROCESSING` is set on the output handle;
#    legacy conhost with a non-UTF-8 code page cannot draw box glyphs. We
#    enable VT via ctypes (stdlib) and degrade glyphs by probing
#    encodability, the same check `_safe_print` has always made (#cli).
# -----------------------------------------------------------------------------
"""Terminal capability detection for the `xsm` CLI (zero dependencies)."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from typing import Optional, TextIO

#: Environment variables that force plain output. `NO_COLOR` is the
#: cross-tool convention (https://no-color.org); `XSM_*` are ours.
_PLAIN_ENV = ("NO_COLOR", "XSM_NO_COLOR", "XSM_PLAIN")
_NO_ANIM_ENV = ("XSM_NO_ANIM", "CI")
_FORCE_COLOR_ENV = ("FORCE_COLOR", "XSM_FORCE_COLOR")


@dataclass(frozen=True)
class Capabilities:
    """What the current console can render.

    Attributes:
        tty: stdout is an interactive terminal.
        color: ANSI colour/bold/dim escapes are honoured.
        truecolor: 24-bit colour is honoured (else 256 / 16 fallback).
        unicode: box-drawing, block and braille glyphs are encodable.
        animate: spinners / progress / transitions may redraw in place.
        width: usable columns for layout.
        height: rows, for scrolling panels.
    """

    tty: bool
    color: bool
    truecolor: bool
    unicode: bool
    animate: bool
    width: int
    height: int

    @property
    def plain(self) -> bool:
        """``True`` when output must be deterministic plain text."""
        return not self.color and not self.animate


def _env_set(names: tuple) -> bool:
    return any(os.environ.get(n, "") not in ("", "0", "false") for n in names)


def _enable_windows_vt(stream: TextIO) -> bool:
    """Turn on VT processing for a Windows console handle; ``True`` if on.

    No-op (returns ``True``) off Windows. Returns ``False`` when the console
    refuses -- legacy conhost on old builds -- so the caller falls back to
    plain output rather than printing raw escape bytes.
    """
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        import msvcrt

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = msvcrt.get_osfhandle(stream.fileno())
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        enable_vt = 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if mode.value & enable_vt:
            return True
        return bool(kernel32.SetConsoleMode(handle, mode.value | enable_vt))
    except Exception:  # pragma: no cover -- exotic console hosts
        return False


def _unicode_ok(stream: TextIO) -> bool:
    """Can this stream encode the glyphs the UI uses?"""
    encoding = getattr(stream, "encoding", None) or "utf-8"
    probe = "╭─╮│╰╯├└─┘█▉▊▋▌▍▎▏⠋⠙✓✗●◆→"
    try:
        probe.encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def detect(
    stream: Optional[TextIO] = None,
    *,
    plain: bool = False,
    no_color: bool = False,
    no_anim: bool = False,
) -> Capabilities:
    """Probe *stream* (default ``sys.stdout``) and the environment.

    Args:
        stream: The output stream to probe.
        plain: Force plain text (the ``--plain`` flag).
        no_color: Disable colour but keep glyphs/animation (``--no-color``).
        no_anim: Disable in-place redraws (``--no-anim``).
    """
    out = stream if stream is not None else sys.stdout
    try:
        tty = bool(out.isatty())
    except Exception:
        tty = False
    size = shutil.get_terminal_size(fallback=(100, 30))
    width = max(40, min(size.columns, 160))
    height = max(10, size.lines)

    forced = _env_set(_FORCE_COLOR_ENV)
    dumb = os.environ.get("TERM", "") == "dumb"
    color = (tty or forced) and not plain and not no_color
    color = color and not _env_set(_PLAIN_ENV) and not dumb
    if color and not _enable_windows_vt(out):
        color = False
    # 🧭 Plain output is DETERMINISTIC: box glyphs only when we are styling a
    #    terminal. A pipe or a file gets ASCII regardless of its encoding.
    unicode = _unicode_ok(out) and not plain and (tty or forced)
    animate = tty and color and not no_anim and not _env_set(_NO_ANIM_ENV)
    colorterm = os.environ.get("COLORTERM", "").lower()
    truecolor = color and (
        colorterm in ("truecolor", "24bit")
        or os.environ.get("WT_SESSION") is not None  # Windows Terminal
        or os.environ.get("TERM_PROGRAM") in ("vscode", "iTerm.app")
    )
    return Capabilities(
        tty=tty,
        color=color,
        truecolor=truecolor,
        unicode=unicode,
        animate=animate,
        width=width,
        height=height,
    )


#: ⚡ A fully-plain capability set, for tests and for `--plain`.
PLAIN = Capabilities(
    tty=False,
    color=False,
    truecolor=False,
    unicode=False,
    animate=False,
    width=100,
    height=30,
)
