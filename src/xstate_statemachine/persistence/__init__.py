# src/xstate_statemachine/persistence/__init__.py
# -----------------------------------------------------------------------------
# 💾 Persistence -- snapshot envelope, stores, locks, idempotency, timers
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: everything in this package is ZERO-DEPENDENCY.
#    The snapshot envelope (`snapshot.py`, formerly the `persistence` module)
#    already lived in core; the store protocol and its stdlib backends
#    (memory / file / sqlite), locking, idempotency and durable timers join
#    it here so that "a snapshot that lives in a store, with a lock and a
#    version stamp" is available to every user. Django, SQLAlchemy and
#    Redis adapters under `contrib/` are thin implementations of the same
#    protocols. Nothing here may import a third-party module -- the
#    zero-dependency guard (`tests/test_zero_dependency.py`) reloads this
#    package with every non-stdlib import blocked.
#
# 🔁 Backwards compatibility: `from xstate_statemachine.persistence import
#    SNAPSHOT_VERSION, structure_hash, ...` keeps working -- the envelope
#    names are re-exported below, and `base_interpreter` still uses
#    `persistence.check_version(...)` etc. through this namespace.
#
# 📝 Programme: epic #257. Filled in by #259 (stores), #260 (locking),
#    #261 (idempotency), #262 (transition log), #263 (versioning),
#    #264 (durable timers).
# -----------------------------------------------------------------------------
"""Durable state for statecharts: envelope, stores, locking, idempotency.

The snapshot an interpreter produces (`get_snapshot()`) is process memory
until something writes it down. This package is where it gets written
down -- and where the concurrency, idempotency and versioning questions
that follow are answered once, for every framework integration.
"""

from __future__ import annotations

from .deadline import Deadline, check_deadline_record
from .snapshot import (
    SNAPSHOT_VERSION,
    check_identity,
    check_minimum_version,
    check_shape,
    check_version,
    structure_hash,
    upcast,
)

__all__ = [
    "SNAPSHOT_VERSION",
    "Deadline",
    "check_deadline_record",
    "check_identity",
    "check_minimum_version",
    "check_shape",
    "check_version",
    "structure_hash",
    "upcast",
]
