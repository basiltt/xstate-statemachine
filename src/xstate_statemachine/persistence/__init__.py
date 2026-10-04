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

from typing import TYPE_CHECKING, Any

from ..exceptions import (
    ConflictError,
    InvalidKeyError,
    LockTimeoutError,
    SnapshotTooLargeError,
    StoreError,
    StoreUnavailableError,
)
from .async_store import AsyncStateStore, AsyncStoreAdapter, as_async
from .migration import (
    MachineVersionMismatchError,
    MigrationStep,
    NoMigrationPathError,
    SnapshotMigrator,
)
from .deadline import Deadline, check_deadline_record
from .file_store import FileStore
from .sqlite_store import SQLiteStore
from .store import (
    DEFAULT_MAX_SNAPSHOT_BYTES,
    MAX_KEY_LENGTH,
    BaseStore,
    MemoryStore,
    SnapshotCodec,
    StateStore,
    StoredSnapshot,
    validate_key,
)
from .snapshot import (
    SNAPSHOT_VERSION,
    check_identity,
    check_minimum_version,
    check_shape,
    check_version,
    structure_hash,
    upcast,
)

# 🔁 #259: the helpers import the engines, and the engines import this
#    package -- resolve the cycle by loading them on first attribute access.
_LAZY = {
    "load_interpreter": ".helpers",
    "aload_interpreter": ".helpers",
    "save_interpreter": ".helpers",
    "KeyNotFoundError": ".helpers",
    # 🔐 #260
    "LockStrategy": ".locking",
    "OptimisticLock": ".locking",
    "PessimisticLock": ".locking",
    "NoLock": ".locking",
    "persisted": ".locking",
    "apersisted": ".locking",
    "persisted_retry": ".locking",
    "DEFAULT_BACKOFF": ".locking",
    # 📥 #261
    "IdempotencyPlugin": ".idempotency",
    "InboxStore": ".idempotency",
    "InboxEntry": ".idempotency",
    "MemoryInbox": ".idempotency",
    "SQLiteInbox": ".idempotency",
    "IdempotencyMismatchError": ".idempotency",
    "IdempotencyInFlightError": ".idempotency",
    "InboxUnavailableError": ".idempotency",
    "default_key": ".idempotency",
    "fingerprint": ".idempotency",
    "DEFAULT_TTL_S": ".idempotency",
    # 📜 #262
    "TransitionRecord": ".log",
    "TransitionLogStore": ".log",
    "MemoryLog": ".log",
    "JSONLinesLog": ".log",
    "LogCorruptError": ".log",
    "SQLiteLog": ".log",
    "TransitionLogPlugin": ".log",
    "AuditPlugin": ".log",
    "ReplayDivergenceError": ".log",
    "replay": ".log",
    "correlation_id_var": ".log",
    # ⏰ #264
    "DueTimerScanner": ".timers",
    "ScanResult": ".timers",
    "DEFAULT_RESTART_TIMERS": ".locking",
    "DEFAULT_SETTLE_TIMEOUT": ".locking",  # ⏳ #263 battle
    # 🧬 #310: adopt an existing record
    "from_state_ids": ".adopt",
}

if TYPE_CHECKING:  # pragma: no cover
    from .helpers import (  # noqa: F401
        KeyNotFoundError,
        aload_interpreter,
        load_interpreter,
        save_interpreter,
    )
    from .idempotency import (  # noqa: F401
        DEFAULT_TTL_S,
        IdempotencyInFlightError,
        InboxUnavailableError,
        IdempotencyMismatchError,
        IdempotencyPlugin,
        InboxEntry,
        InboxStore,
        MemoryInbox,
        SQLiteInbox,
        default_key,
        fingerprint,
    )
    from .log import (  # noqa: F401
        AuditPlugin,
        JSONLinesLog,
        LogCorruptError,
        MemoryLog,
        ReplayDivergenceError,
        SQLiteLog,
        TransitionLogPlugin,
        TransitionLogStore,
        TransitionRecord,
        correlation_id_var,
        replay,
    )
    from .adopt import from_state_ids  # noqa: F401
    from .timers import DueTimerScanner, ScanResult  # noqa: F401
    from .locking import (  # noqa: F401
        DEFAULT_RESTART_TIMERS,
        DEFAULT_SETTLE_TIMEOUT,
        DEFAULT_BACKOFF,
        LockStrategy,
        NoLock,
        OptimisticLock,
        PessimisticLock,
        apersisted,
        persisted,
        persisted_retry,
    )


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module, __name__), name)


__all__ = [
    "SNAPSHOT_VERSION",
    "Deadline",
    "check_deadline_record",
    # 💾 stores (#259)
    "StateStore",
    "AsyncStateStore",
    "AsyncStoreAdapter",
    "as_async",
    "StoredSnapshot",
    "SnapshotCodec",
    "BaseStore",
    "MemoryStore",
    "FileStore",
    "SQLiteStore",
    "validate_key",
    "DEFAULT_MAX_SNAPSHOT_BYTES",
    "MAX_KEY_LENGTH",
    "StoreError",
    "StoreUnavailableError",
    "ConflictError",
    "LockTimeoutError",
    "SnapshotTooLargeError",
    "InvalidKeyError",
    "KeyNotFoundError",
    "load_interpreter",
    "aload_interpreter",
    "save_interpreter",
    # 🔐 locking (#260)
    "LockStrategy",
    "OptimisticLock",
    "PessimisticLock",
    "NoLock",
    "persisted",
    "apersisted",
    "persisted_retry",
    "DEFAULT_BACKOFF",
    # 📥 idempotency (#261)
    "IdempotencyPlugin",
    "InboxStore",
    "InboxEntry",
    "MemoryInbox",
    "SQLiteInbox",
    "IdempotencyMismatchError",
    "IdempotencyInFlightError",
    "InboxUnavailableError",
    "default_key",
    "fingerprint",
    "DEFAULT_TTL_S",
    # 📜 transition log (#262)
    "TransitionRecord",
    "TransitionLogStore",
    "MemoryLog",
    "JSONLinesLog",
    "LogCorruptError",
    "SQLiteLog",
    "TransitionLogPlugin",
    "AuditPlugin",
    "ReplayDivergenceError",
    "replay",
    "correlation_id_var",
    # ⏰ durable timers (#264)
    "DueTimerScanner",
    "ScanResult",
    "DEFAULT_RESTART_TIMERS",
    "DEFAULT_SETTLE_TIMEOUT",  # #263 battle
    "from_state_ids",  # #310
    # 🧬 versioning (#263)
    "SnapshotMigrator",
    "MigrationStep",
    "MachineVersionMismatchError",
    "NoMigrationPathError",
    # envelope
    "check_identity",
    "check_minimum_version",
    "check_shape",
    "check_version",
    "structure_hash",
    "upcast",
]
