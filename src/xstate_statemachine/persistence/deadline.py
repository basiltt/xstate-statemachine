# src/xstate_statemachine/persistence/deadline.py
# -----------------------------------------------------------------------------
# ⏰ Deadline -- the persisted form of an `after` timer (#305, for #264)
# -----------------------------------------------------------------------------
# 🏛️ Why a wall-clock record and not "remaining ms": `scheduled_sends`
#    (#213) persists the delay REMAINING at snapshot time, which is right
#    for a process that restarts within seconds. A durable timer (#264) may
#    fire hours after the writer died, possibly on another host, so it must
#    be anchored to an ABSOLUTE instant a scheduler can compare against its
#    own wall clock. `entry_seq` disambiguates re-entries: the state was
#    entered, exited and re-entered while the old deadline was still in a
#    queue; a deadline whose `entry_seq` is stale must be dropped, not fired.
#
# 📝 This module ships the record and its validator only. No engine WRITES
#    deadlines yet -- `get_snapshot()` emits `deadlines: []` so the layout
#    (v4) is settled before #264 lands and no second bump is needed.
# -----------------------------------------------------------------------------
"""`Deadline` record for durable timers, plus its shape validator."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

__all__ = ["Deadline", "check_deadline_record"]


@dataclass(frozen=True)
class Deadline:
    """An `after` timer anchored to wall-clock time.

    Attributes:
        state_id: Fully-qualified id of the state that armed the timer.
        entry_seq: Monotonic per-interpreter count of state entries at the
            moment the timer was armed. A deadline whose ``entry_seq`` no
            longer matches the state's current entry is stale.
        due_at_wall: Absolute instant the timer fires, as seconds since the
            Unix epoch (``time.time()`` scale -- see ``wall_now()``).
        delay_ms: The declared delay, kept so a restore can recompute the
            remainder against its own clock and for diagnostics.
        event_type: The ``after.<delay>.<state>`` event the timer sends.
    """

    state_id: str
    entry_seq: int
    due_at_wall: float
    delay_ms: int
    event_type: str

    def to_dict(self) -> Dict[str, Any]:
        """JSON-ready mapping (all fields are JSON scalars)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, record: Dict[str, Any]) -> "Deadline":
        """Rebuild from `to_dict()` output. Validate first with
        `check_deadline_record` -- this does not re-check."""
        return cls(
            state_id=record["state_id"],
            entry_seq=int(record["entry_seq"]),
            due_at_wall=float(record["due_at_wall"]),
            delay_ms=int(record["delay_ms"]),
            event_type=record["event_type"],
        )

    def remaining_ms(self, now_wall: float) -> int:
        """Milliseconds until due, clamped at 0 (already overdue)."""
        return max(0, int(round((self.due_at_wall - now_wall) * 1000)))


def check_deadline_record(rec: Any) -> Optional[str]:
    """Return a description of what is wrong with *rec*, or ``None``.

    Shape-only, mirroring `check_shape`'s philosophy: every field present
    with the type `Deadline.from_dict` assumes, so a corrupt blob is refused
    as `SnapshotCorruptError` instead of leaking a bare ``KeyError``.
    """
    if not isinstance(rec, dict):
        return f"expected an object, got {type(rec).__name__}"
    for key in (
        "state_id",
        "entry_seq",
        "due_at_wall",
        "delay_ms",
        "event_type",
    ):
        if key not in rec:
            return f"missing key '{key}'"
    if not isinstance(rec["state_id"], str) or not rec["state_id"]:
        return "'state_id' must be a non-empty string"
    if not isinstance(rec["event_type"], str) or not rec["event_type"]:
        return "'event_type' must be a non-empty string"
    for key in ("entry_seq", "delay_ms"):
        val = rec[key]
        if isinstance(val, bool) or not isinstance(val, int) or val < 0:
            return f"'{key}' must be a non-negative integer"
    due = rec["due_at_wall"]
    if isinstance(due, bool) or not isinstance(due, (int, float)):
        return "'due_at_wall' must be a number (seconds since the epoch)"
    # 🛡️ #263 battle: `json.loads` accepts `NaN` / `Infinity`; a migration
    #    step can inject them too. `remaining_ms` then raised a bare
    #    ValueError / OverflowError from `round()` at `start()`.
    if not math.isfinite(due):
        return "'due_at_wall' must be a finite number"
    return None
