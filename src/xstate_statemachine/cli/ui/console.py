# src/xstate_statemachine/cli/ui/console.py
# -----------------------------------------------------------------------------
# 🎛️ The Console facade -- what every command module talks to
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: commands never import the primitives directly;
#    they call `console.panel(...)`, `console.table(...)`, `console.status(
#    "…")`, `console.ok(...)`. The facade owns the `Capabilities`, the
#    output stream and the encodability fallback that `_safe_print` used to
#    provide, so switching the whole CLI to plain mode is one flag and the
#    tests can construct a `Console(caps=PLAIN, stream=StringIO())`.
# -----------------------------------------------------------------------------
"""Console: a single object that renders every xsm output primitive."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Iterator, List, Optional, Sequence, TextIO

from . import animate as _anim
from . import banner as _banner
from . import box as _box
from . import keys as _keys
from . import prompt as _prompt
from .progress import ProgressBar, Spinner, StepList
from .style import paint
from .table import Column, Table
from .term import PLAIN, Capabilities, detect
from .tree import Node, render as _render_tree


class Console:
    """Render text, panels, tables, trees and live status for one stream."""

    def __init__(
        self,
        caps: Optional[Capabilities] = None,
        stream: Optional[TextIO] = None,
    ) -> None:
        self.out: TextIO = stream if stream is not None else sys.stdout
        self.caps: Capabilities = (
            caps if caps is not None else detect(self.out)
        )

    # ---------------------------------------------------------------- basics
    def _encodable(self, msg: str) -> str:
        encoding = getattr(self.out, "encoding", None) or "utf-8"
        try:
            msg.encode(encoding)
            return msg
        except (UnicodeEncodeError, LookupError):
            return msg.encode(encoding, errors="replace").decode(
                encoding, errors="replace"
            )

    def print(self, *lines: str) -> None:
        """Write lines (plain or pre-styled). Always newline-terminated."""
        for line in lines or ("",):
            self.out.write(self._encodable(line) + "\n")
        self.out.flush()

    def style(self, text: str, role: str) -> str:
        return paint(text, role, self.caps)

    def ok(self, msg: str) -> None:
        self.print(
            f"{self.style('✓' if self.caps.unicode else 'OK', 'ok')} {msg}"
        )

    def warn(self, msg: str) -> None:
        self.print(
            f"{self.style('!' if not self.caps.unicode else '⚠', 'warn')} {msg}"
        )

    def error(self, msg: str) -> None:
        self.print(
            f"{self.style('✗' if self.caps.unicode else 'X', 'err')} {msg}"
        )

    def info(self, msg: str) -> None:
        self.print(
            f"{self.style('ℹ' if self.caps.unicode else 'i', 'info')} {msg}"
        )

    def blank(self) -> None:
        self.print("")

    # ---------------------------------------------------------------- layout
    def rule(self, title: str = "", *, role: str = "muted") -> None:
        self.print(_box.rule(self.caps, title, role=role))

    def panel(self, body: Sequence[str], **kw) -> None:
        self.print(*_box.panel(self.caps, body, **kw))

    def cards(self, items: Sequence[Sequence[str]], **kw) -> None:
        self.print(*_box.cards(self.caps, items, **kw))

    def table(self, table: Table) -> None:
        self.print(*table.render(self.caps))

    def tree(self, root: Node, **kw) -> None:
        self.print(*_render_tree(self.caps, root, **kw))

    def kv(self, pairs: Sequence[Sequence[str]], *, indent: int = 2) -> None:
        """Aligned ``key   value`` rows."""
        if not pairs:
            return
        w = max(len(k) for k, _ in pairs)
        for k, v in pairs:
            self.print(" " * indent + self.style(k.ljust(w), "key") + "  " + v)

    def banner(self, version: str) -> None:
        _anim.wipe_in(
            self.caps, _banner.render(self.caps, version), stream=self.out
        )

    # ---------------------------------------------------------------- live
    @contextmanager
    def status(self, message: str, **kw) -> Iterator[Spinner]:
        with Spinner(self.caps, message, stream=self.out, **kw) as sp:
            yield sp

    def progress(self, total: int, **kw) -> ProgressBar:
        return ProgressBar(self.caps, total, stream=self.out, **kw)

    def steps(self, names: Sequence[str]) -> StepList:
        return StepList(self.caps, names, stream=self.out)

    def pulse(self, line: str) -> None:
        _anim.pulse(self.caps, line, stream=self.out)

    def typewriter(self, text: str, role: Optional[str] = None) -> None:
        _anim.typewriter(self.caps, text, role=role, stream=self.out)

    # ---------------------------------------------------------------- input
    @property
    def interactive(self) -> bool:
        """Prompts are possible: styled tty out AND a tty stdin."""
        return self.caps.animate and _keys.interactive_available()

    def select(self, title, options, **kw):
        return _prompt.select(self.caps, title, options, stream=self.out, **kw)

    def multiselect(self, title, options, **kw):
        return _prompt.multiselect(
            self.caps, title, options, stream=self.out, **kw
        )

    def confirm(self, question, **kw):
        return _prompt.confirm(self.caps, question, stream=self.out, **kw)

    def text(self, question, **kw):
        return _prompt.text(self.caps, question, stream=self.out, **kw)


# ---------------------------------------------------------------------------
# 🧰 Convenience re-exports so command modules import one name.
# ---------------------------------------------------------------------------
__all__ = ["Console", "Column", "Table", "Node", "PLAIN", "Capabilities"]
