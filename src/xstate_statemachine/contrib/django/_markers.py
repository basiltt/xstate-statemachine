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
from typing import Any, Iterator, List

__all__ = ["_marker_plugins", "_marker_session"]


def _marker_plugins(plugins: List[Any]) -> List[Any]:
    """Plugins that buffer post-save writes (`flush_marks`), ordered by
    ``flush_priority`` like `persisted()` does."""
    found = [p for p in plugins if callable(getattr(p, "flush_marks", None))]
    return sorted(found, key=lambda p: getattr(p, "flush_priority", 0))


@contextlib.contextmanager
def _marker_session(markers: List[Any]) -> Iterator[None]:
    """A `persisted()`-style session for *markers*: `buffer_marks` on, a
    fresh `current_session` token so their buffers are keyed to THIS send;
    restored on exit, and any leftover buffer discarded."""
    from ...persistence.locking import current_session

    token = current_session.set(object())
    previous = [(m, getattr(m, "buffer_marks", False)) for m in markers]
    for m in markers:
        m.buffer_marks = True
    try:
        yield
    finally:
        for m, was in previous:
            try:
                m.discard_marks()
            except Exception:  # pragma: no cover - best effort
                pass
            m.buffer_marks = was
        current_session.reset(token)
