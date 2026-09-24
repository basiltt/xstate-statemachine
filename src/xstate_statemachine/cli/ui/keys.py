# src/xstate_statemachine/cli/ui/keys.py
# -----------------------------------------------------------------------------
# ⌨️ Single-key input, POSIX and Windows, stdlib only
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `read_key` is the only function that touches the
#    real terminal, and every interactive widget takes a `KeySource`
#    callable so tests inject a scripted sequence and never need a pty.
# -----------------------------------------------------------------------------
"""Blocking single-key reader returning symbolic key names."""

from __future__ import annotations

import importlib
import sys
from typing import Any, Callable, Optional

KeySource = Callable[[], str]

# Symbolic names every widget understands.
UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"
ENTER, ESC, TAB, BACKSPACE, SPACE = "enter", "esc", "tab", "backspace", "space"
HOME, END, PGUP, PGDN = "home", "end", "pgup", "pgdn"

_POSIX_SEQ = {
    "[A": UP,
    "[B": DOWN,
    "[C": RIGHT,
    "[D": LEFT,
    "[H": HOME,
    "[F": END,
    "[5~": PGUP,
    "[6~": PGDN,
    "OA": UP,
    "OB": DOWN,
    "OC": RIGHT,
    "OD": LEFT,
}
_WIN_SEQ = {
    "H": UP,
    "P": DOWN,
    "M": RIGHT,
    "K": LEFT,
    "G": HOME,
    "O": END,
    "I": PGUP,
    "Q": PGDN,
}


def _read_posix() -> str:  # pragma: no cover -- exercised on POSIX only
    # 🪟 `termios` / `tty` do not exist on Windows; import lazily and
    #    type them as Any so mypy on Windows does not see a missing module.
    termios: Any = importlib.import_module("termios")
    tty: Any = importlib.import_module("tty")

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "":
            seq = sys.stdin.read(1)
            if seq in ("[", "O"):
                seq += sys.stdin.read(1)
                while seq[-1].isdigit() or seq[-1] == ";":
                    seq += sys.stdin.read(1)
                return _POSIX_SEQ.get(seq, ESC)
            return ESC
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return _normalise(ch)


def _read_windows() -> str:
    # 🧷 Dynamic import typed `Any`: typeshed only knows `msvcrt.getwch` on
    #    Windows, and mypy in CI runs on Linux. Tests inject a fake module
    #    into `sys.modules`, which `import_module` honours.
    msvcrt: Any = importlib.import_module("msvcrt")

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        return _WIN_SEQ.get(msvcrt.getwch(), "")
    return _normalise(ch)


def _normalise(ch: str) -> str:
    if ch in ("\r", "\n"):
        return ENTER
    if ch == "\x1b":
        return ESC
    if ch == "\t":
        return TAB
    if ch in ("\x7f", "\x08"):
        return BACKSPACE
    if ch == " ":
        return SPACE
    if ch == "\x03":
        raise KeyboardInterrupt
    return ch


def read_key() -> str:
    """Block for one key press; returns a symbolic name or the character."""
    if sys.platform == "win32":
        return _read_windows()
    return _read_posix()


def scripted(keys: str) -> KeySource:
    """A `KeySource` that replays *keys* (space-separated names) for tests."""
    it = iter(keys.split())

    def source() -> str:
        try:
            return next(it)
        except StopIteration:  # pragma: no cover -- test author error
            raise EOFError("scripted keys exhausted")

    return source


def interactive_available(stdin=None) -> bool:
    """``True`` when single-key reads are possible on this stdin."""
    s = stdin if stdin is not None else sys.stdin
    try:
        return bool(s.isatty())
    except Exception:
        return False


_default: Optional[KeySource] = None


def default_source() -> KeySource:
    return _default or read_key
