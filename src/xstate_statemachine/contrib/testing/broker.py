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

from typing import Any, Iterable, Optional

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

    *log* is an iterable of `TransitionRecord` or a `TransitionLogStore`
    (read under *key*). Returns the replayed interpreter (stopped by the
    caller). Raises `AssertionError` naming the first divergent ``seq``.
    """
    records: Iterable[Any]
    if hasattr(log, "read"):
        if key is None:
            raise ValueError("reading a log store needs key=")
        records = log.read(key)
    else:
        records = log
    try:
        return replay(machine, list(records), verify=True)
    except ReplayDivergenceError as exc:
        raise AssertionError(f"replay diverged: {exc}") from exc
