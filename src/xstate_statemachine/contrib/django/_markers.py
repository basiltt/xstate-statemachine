# src/xstate_statemachine/contrib/django/_markers.py
# -----------------------------------------------------------------------------
# 📤 Marker plugins inside `StatechartModelMixin.send()` (#281 battle)
# -----------------------------------------------------------------------------
# 🏛️ `OutboxPlugin` / `IdempotencyPlugin` write from `on_event_processed`,
#    which the engine wraps in `_SafePlugin`: a failing outbox INSERT was
#    LOGGED and the approval committed without its integration event.
#    `send()` now runs them the way `persisted()` does -- buffered during
#    the step, flushed after the row's fenced UPDATE, inside the same
#    `atomic()` block and unwrapped, so a failure rolls the send back.
# -----------------------------------------------------------------------------
"""Buffer / flush helpers for marker plugins under the Django mixin."""

from __future__ import annotations

import contextlib
import threading
from typing import Any, Dict, Iterator, List

__all__ = ["_marker_plugins", "_marker_session"]


def _marker_plugins(plugins: List[Any]) -> List[Any]:
    """Plugins that buffer post-save writes (`flush_marks`), ordered by
    ``flush_priority`` like `persisted()` does."""
    found = [p for p in plugins if callable(getattr(p, "flush_marks", None))]
    return sorted(found, key=lambda p: getattr(p, "flush_priority", 0))


#: Open `send()` sessions per marker plugin (by id) and the value of
#: ``buffer_marks`` to restore when the LAST of them exits.
_open: Dict[int, List[Any]] = {}
_open_lock = threading.Lock()


def _enter(m: Any) -> None:
    with _open_lock:
        slot = _open.get(id(m))
        if slot is None:
            _open[id(m)] = [1, getattr(m, "buffer_marks", False)]
        else:
            slot[0] += 1
        m.buffer_marks = True


def _leave(m: Any) -> None:
    with _open_lock:
        slot = _open[id(m)]
        slot[0] -= 1
        if slot[0] == 0:
            del _open[id(m)]
            m.buffer_marks = slot[1]


@contextlib.contextmanager
def _marker_session(markers: List[Any]) -> Iterator[None]:
    """A `persisted()`-style session for *markers*: `buffer_marks` on, a
    fresh `current_session` token so their buffers are keyed to THIS send;
    restored on exit, and any leftover buffer discarded.

    🐛 #281 battle (A): `OutboxPlugin.buffer_marks` is ONE flag per
    instance, not per session. With a plugin shared by every row
    (``statechart_plugins = lambda row: [shared]``) a concurrent send's
    exit restored it to ``False`` mid-run, and this send's failing INSERT
    was swallowed by the engine again. The flag is now reference-counted:
    restored only when the last open send leaves.
    """
    from ...persistence.locking import current_session

    token = current_session.set(object())
    for m in markers:
        _enter(m)
    try:
        yield
    finally:
        for m in markers:
            try:
                m.discard_marks()
            except Exception:  # pragma: no cover - best effort
                pass
            _leave(m)
        current_session.reset(token)
