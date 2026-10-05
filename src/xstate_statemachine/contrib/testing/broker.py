# src/xstate_statemachine/contrib/testing/broker.py
# -----------------------------------------------------------------------------
# 📡 Test doubles for event-driven machines (#272)
# -----------------------------------------------------------------------------
# 🏛️ The in-memory broker lives in CORE (`eda.fake`, stdlib only) so the
#    EDA core's own tests need no extra; this module re-exports it at the
#    import path the issue promises (`contrib.testing.FakeBrokerAdapter`)
#    next to the transition-log replay helpers.
# -----------------------------------------------------------------------------
"""`FakeBrokerAdapter`, `replay`, `assert_replay_consistent`."""

from __future__ import annotations

from typing import Any, List, Optional

from ...eda.fake import (
    BrokerPublishError,
    FakeBrokerAdapter,
    SyncFakeBrokerAdapter,
)
from ...persistence.log import ReplayDivergenceError, replay

__all__ = [
    "BrokerPublishError",
    "FakeBrokerAdapter",
    "ReplayDivergenceError",
    "SyncFakeBrokerAdapter",
    "assert_replay_consistent",
    "replay",
]


def assert_replay_consistent(
    machine: Any, log: Any, *, key: Optional[str] = None
) -> Any:
    """Replay *log* against *machine* and fail loudly on divergence.

    *log* is an iterable of `TransitionRecord` (*key* selects one instance
    when it mixes several) or a `TransitionLogStore` (read under *key*,
    EVERY page -- a store's ``read`` returns at most ``limit`` rows).
    Returns the replayed `SyncInterpreter`, still running on a
    `SimulatedClock` (no threads); inspect it, then ``stop()`` it.
    Raises `AssertionError` naming the first divergent ``seq``.
    """
    records: List[Any]
    if hasattr(log, "read"):
        if key is None:
            raise ValueError("reading a log store needs key=")
        records = _read_all(log, key)
    else:
        records = list(log)
    try:
        return replay(machine, records, verify=True, key=key)
    except ReplayDivergenceError as exc:
        raise AssertionError(f"replay diverged: {exc}") from exc


def _read_all(store: Any, key: str, page: int = 1000) -> List[Any]:
    """Every record of *key*, page by page.

    🐛 Battle #272: a single ``read(key)`` stopped at the store's default
    ``limit=1000`` -- a log tampered past record 1000 was reported
    consistent."""
    out: List[Any] = []
    after = 0
    while True:
        chunk = store.read(key, after_seq=after, limit=page)
        out.extend(chunk)
        if len(chunk) < page:
            return out
        after = chunk[-1].seq
