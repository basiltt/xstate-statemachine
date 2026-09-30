# src/xstate_statemachine/contrib/observability/_hygiene.py
# -----------------------------------------------------------------------------
# 🧼 Telemetry hygiene (X0.6) -- one place that decides what may become a
#    metric label or a span attribute
# -----------------------------------------------------------------------------
# 🏛️ A metrics backend is a public, long-retention, cardinality-priced sink.
#    Three rules, enforced here so every plugin shares them:
#      1. Label VALUES come from the chart, not from traffic: an event type
#         the machine does not declare becomes ``unknown`` (allow-list with
#         fallback), so a fuzzer cannot mint series.
#      2. Every label dimension is additionally capped (`max_label_values`);
#         the overflow bucket is ``other``.
#      3. Payloads, instance keys (``interpreter.id`` / store keys) and
#         correlation ids are NEVER labels or attributes by default.
# -----------------------------------------------------------------------------
"""Label allow-list and cardinality guard shared by the plugins."""

from __future__ import annotations

import threading
from typing import Any, Dict, Optional, Set

__all__ = ["LabelGuard", "UNKNOWN", "OTHER", "event_label", "INIT_EVENT"]

#: Fallback for a value outside the chart's allow-list.
UNKNOWN = "unknown"
#: Overflow bucket once a label dimension hits `max_label_values`.
OTHER = "other"
#: The engine's internal init event, reported under XState's name.
INIT_EVENT = "___xstate_statemachine_init___"


def event_label(machine: Any, event_type: Optional[str]) -> str:
    """Map an event type to an allow-listed label value.

    Declared events (``machine.known_events``) pass through, the engine's
    own families (``after.*``, ``done.*``, ``error.*``, ``xstate.*``) are
    collapsed to their family so a per-invocation id cannot leak in, and
    everything else is ``unknown``.
    """
    if not event_type:
        return "always"
    if event_type == INIT_EVENT:
        return "xstate.init"
    known = getattr(machine, "known_events", None) or ()
    if event_type in known:
        return event_type
    for family in ("after", "done", "error", "xstate"):
        if event_type.startswith(family + "."):
            return family
    return UNKNOWN


class LabelGuard:
    """Caps the number of distinct values per label dimension.

    Thread-safe; the first ``max_label_values`` values seen per dimension
    are kept verbatim, later ones become ``other``.
    """

    def __init__(self, max_label_values: int = 100) -> None:
        if max_label_values < 1:
            raise ValueError("max_label_values must be >= 1")
        self.max_label_values = max_label_values
        self._seen: Dict[str, Set[str]] = {}
        self._lock = threading.Lock()

    def __call__(self, dimension: str, value: Any) -> str:
        text = UNKNOWN if value is None else str(value)
        with self._lock:
            seen = self._seen.setdefault(dimension, set())
            if text in seen:
                return text
            if len(seen) >= self.max_label_values:
                return OTHER
            seen.add(text)
            return text
