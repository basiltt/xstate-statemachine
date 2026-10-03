# src/xstate_statemachine/persistence/store.py
# -----------------------------------------------------------------------------
# 💾 StateStore -- the create → act → persist → discard contract (#259)
# -----------------------------------------------------------------------------
# 🏛️ Why a protocol and not a base class: Django (#275), SQLAlchemy (#276)
#    and Redis (#306) backends live in `contrib/` and must not import
#    anything from here that drags a dependency in; a `Protocol` lets them
#    satisfy the contract structurally. `BaseStore` below is an OPTIONAL
#    helper that implements the shared policy (size cap, key validation,
#    codec) once, so the three stdlib backends and any contrib backend that
#    wants it stay identical in the parts that matter for safety.
#
# 🔐 X0 items honoured here (#303): `max_snapshot_bytes` enforced on save
#    AND load (X0.4); `forget(key)` so a record can be removed on request
#    (X0.5); keys validated before any backend sees them; the codec seam is
#    `str -> str` so an encrypting codec (#302) slots in without touching a
#    backend.
# -----------------------------------------------------------------------------
"""`StateStore` protocol, `StoredSnapshot`, `BaseStore`, `MemoryStore`."""

from __future__ import annotations

import contextlib
import threading
import time
from dataclasses import dataclass
from typing import (
    Any,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

try:  # pragma: no cover - 3.8+ has Protocol; kept defensive like clock.py
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

import math

from ..exceptions import (
    ConflictError,
    InvalidKeyError,
    LockTimeoutError,
    SnapshotCorruptError,
    SnapshotTooLargeError,
    StoreError,
)
from .deadline import Deadline

__all__ = [
    "DEFAULT_MAX_SNAPSHOT_BYTES",
    "MAX_KEY_LENGTH",
    "BaseStore",
    "MemoryStore",
    "SnapshotCodec",
    "StateStore",
    "StoredSnapshot",
    "check_record_fields",
    "check_save_args",
    "validate_key",
]

#: 1 MiB. A statechart snapshot is context + a few hundred bytes of
#: envelope; anything near this is a context that should live elsewhere.
DEFAULT_MAX_SNAPSHOT_BYTES = 1 * 1024 * 1024
#: Keys are identifiers, not documents. 200 leaves room for a FileStore
#: encoding to stay under filesystem limits (255) with a suffix.
MAX_KEY_LENGTH = 200
#: The width of the `machine_version` column in the SQLAlchemy and Django
#: schemas -- the narrowest backend sets the rule for all (#263 battle).
MAX_MACHINE_VERSION_LENGTH = 255


def validate_key(key: str) -> str:
    """Refuse an unusable key with `InvalidKeyError`; return it unchanged.

    Shared by every backend so the rule is one rule: a non-empty ``str``
    of at most `MAX_KEY_LENGTH` characters, no NUL. `FileStore` adds its
    own filesystem rules on top of this.
    """
    if not isinstance(key, str):
        raise InvalidKeyError(
            f"Store key must be str, got {type(key).__name__}."
        )
    if not key:
        raise InvalidKeyError("Store key must not be empty.")
    if len(key) > MAX_KEY_LENGTH:
        raise InvalidKeyError(
            f"Store key is {len(key)} chars; the limit is {MAX_KEY_LENGTH}."
        )
    if "\x00" in key:
        raise InvalidKeyError("Store key must not contain NUL.")
    try:
        key.encode("utf-8")
    except UnicodeEncodeError:
        raise InvalidKeyError(
            "Store key must be valid Unicode (no lone surrogates)."
        ) from None
    return key


def check_record_fields(
    where: str,
    snapshot: Any,
    version: Any,
    machine_version: Any,
    updated_at: Any,
) -> None:
    """Refuse a stored record whose scalar fields have the wrong type.

    Shared by every backend that reads rows/files another writer could have
    damaged: each failure is a `SnapshotCorruptError`, never a bare
    ``ValueError`` / ``TypeError`` from a later ``int()`` / ``float()``.
    """

    def bad(what: str) -> SnapshotCorruptError:
        return SnapshotCorruptError(f"{where}: {what}.")

    if not isinstance(snapshot, str):
        raise bad(f"'snapshot' is {type(snapshot).__name__}, not text")
    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version < 1
    ):
        raise bad(f"'version' {version!r} is not a positive integer")
    if not isinstance(machine_version, str):
        raise bad("'machine_version' is not text")
    if (
        isinstance(updated_at, bool)
        or not isinstance(updated_at, (int, float))
        or not math.isfinite(updated_at)
    ):
        raise bad(f"'updated_at' {updated_at!r} is not a finite number")


def check_save_args(
    expected_version: Any, machine_version: Any, deadlines: Any
) -> Tuple[Optional[int], str, Tuple[Deadline, ...]]:
    """Caller-side argument checks: ``TypeError`` / ``ValueError`` at the
    call site, identically on every backend."""
    if expected_version is not None and (
        isinstance(expected_version, bool)
        or not isinstance(expected_version, int)
    ):
        raise TypeError(
            "expected_version must be an int or None, got "
            f"{type(expected_version).__name__}"
        )
    if machine_version is not None and not isinstance(machine_version, str):
        raise TypeError(
            "machine_version must be str, got "
            f"{type(machine_version).__name__}"
        )
    if machine_version:
        # 🛡️ #263 battle: one rule on every backend. SQLAlchemy/Django keep
        #    the label in a VARCHAR(255) (Postgres raised a driver
        #    DataError, SQLite silently kept 10 kB) and Postgres rejects
        #    NUL in text; Memory/File/SQLite accepted both.
        if len(machine_version) > MAX_MACHINE_VERSION_LENGTH:
            raise ValueError(
                f"machine_version is {len(machine_version)} chars; the "
                f"limit is {MAX_MACHINE_VERSION_LENGTH}."
            )
        if "\x00" in machine_version:
            raise ValueError("machine_version must not contain NUL.")
    dls = tuple(deadlines)
    for d in dls:
        if not isinstance(d, Deadline):
            raise TypeError(
                f"deadlines must be Deadline objects, got {type(d).__name__}"
            )
    return expected_version, machine_version or "", dls


@dataclass(frozen=True)
class StoredSnapshot:
    """What `StateStore.load` returns.

    Attributes:
        key: The record key.
        snapshot: The JSON snapshot string exactly as `get_snapshot()`
            produced it (after the codec's ``decode``).
        version: Monotonic per-key record version, starting at 1 on the
            first save. The optimistic-locking token.
        machine_version: The chart's `MachineNode.version` at save time
            (``""`` when the chart declares none). What the migrator (#263)
            dispatches on.
        updated_at: Epoch seconds of the last save (store clock).
        deadlines: Durable timers persisted with the record (#264).
    """

    key: str
    snapshot: str
    version: int
    machine_version: str
    updated_at: float
    deadlines: Tuple[Deadline, ...] = ()


@runtime_checkable
class SnapshotCodec(Protocol):
    """``str -> str`` transform applied on save (`encode`) and undone on
    load (`decode`). Compression or encryption (#302) plug in here; the
    default is the identity."""

    def encode(self, snapshot: str) -> str:
        pass  # pragma: no cover

    def decode(self, data: str) -> str:
        pass  # pragma: no cover


@runtime_checkable
class StateStore(Protocol):
    """Where snapshots live between requests.

    Every method is synchronous; `as_async()` (in `async_store.py`) wraps
    any implementation for asyncio callers. Implementations MUST be safe
    to call from multiple threads.
    """

    def load(self, key: str) -> Optional[StoredSnapshot]:
        """The current record, or ``None`` if the key is unknown."""
        ...

    def save(
        self,
        key: str,
        snapshot: str,
        *,
        expected_version: Optional[int] = None,
        machine_version: str = "",
        deadlines: Sequence[Deadline] = (),
    ) -> int:
        """Persist *snapshot*; return the NEW version.

        With ``expected_version`` the write is conditional: it succeeds
        only if the stored version equals it (``None`` for "the key must
        not exist yet" is expressed as ``expected_version=0``), otherwise
        `ConflictError` and nothing is written. Without it the write is
        unconditional (last writer wins).
        """
        ...

    def delete(self, key: str) -> bool:
        """Remove the record; return whether it existed."""
        ...

    def forget(self, key: str) -> Dict[str, int]:
        """Erase everything the store holds about *key* -- the record AND
        any auxiliary rows (deadlines, locks, later: transition log) -- and
        report counts per kind (X0.5, right-to-erasure)."""
        ...

    def list_keys(self, *, prefix: str = "", limit: int = 1000) -> List[str]:
        """Keys starting with *prefix*, sorted, at most *limit*."""
        ...

    def lock(self, key: str, *, timeout: float = 10.0) -> ContextManager[None]:
        """Pessimistic per-key lock. `LockTimeoutError` if not acquired in
        *timeout* seconds. Stores that cannot lock document it and return a
        no-op."""
        ...

    def health(self) -> Dict[str, Any]:
        """Cheap liveness probe: ``{"ok": bool, "backend": str, ...}``."""
        ...


class _IdentityCodec:
    def encode(self, snapshot: str) -> str:
        return snapshot

    def decode(self, data: str) -> str:
        return data


class BaseStore:
    """Shared policy for concrete stores: key validation, size cap, codec.

    Subclasses implement the ``_``-prefixed primitives on RAW (encoded)
    strings; the public methods here apply the policy around them so no
    backend can forget the cap or the codec.
    """

    backend: str = "base"

    def __init__(
        self,
        *,
        codec: Optional[SnapshotCodec] = None,
        max_snapshot_bytes: int = DEFAULT_MAX_SNAPSHOT_BYTES,
    ) -> None:
        if max_snapshot_bytes < 1:
            raise ValueError("max_snapshot_bytes must be >= 1")
        self.codec: SnapshotCodec = codec or _IdentityCodec()
        self.max_snapshot_bytes = int(max_snapshot_bytes)

    # -- policy -----------------------------------------------------------------
    def _check_size(self, key: str, data: str) -> None:
        try:
            size = len(data.encode("utf-8"))
        except UnicodeEncodeError as exc:
            raise SnapshotCorruptError(
                f"Snapshot for '{key}' is not valid Unicode text: {exc}"
            ) from exc
        if size > self.max_snapshot_bytes:
            raise SnapshotTooLargeError(key, size, self.max_snapshot_bytes)

    def _decode(self, key: str, data: str) -> str:
        # 🛡️ #259 battle: a codec is user code. Its failure on a stored
        #    blob (bad ciphertext, truncated gzip) is a damaged record --
        #    typed, with the cause chained -- and a non-str result would
        #    otherwise surface later as a TypeError inside json.loads.
        try:
            out = self.codec.decode(data)
        except Exception as exc:
            raise SnapshotCorruptError(
                f"Snapshot for '{key}' could not be decoded by the codec: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(out, str):
            raise SnapshotCorruptError(
                f"Codec.decode returned {type(out).__name__} for '{key}'; "
                "it must return str."
            )
        return out

    def _encode(self, key: str, snapshot: str) -> str:
        try:
            out = self.codec.encode(snapshot)
        except Exception as exc:
            raise StoreError(
                f"Codec.encode failed for '{key}': "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if not isinstance(out, str):
            raise StoreError(
                f"Codec.encode returned {type(out).__name__} for '{key}'; "
                "it must return str."
            )
        return out

    # -- public surface -----------------------------------------------------
    def load(self, key: str) -> Optional[StoredSnapshot]:
        validate_key(key)
        raw = self._load_raw(key)
        if raw is None:
            return None
        data, version, machine_version, updated_at, deadlines = raw
        # 🛡️ X0.4: the cap applies on READ too -- a record another writer
        #    poisoned must not make this process allocate unboundedly.
        self._check_size(key, data)
        return StoredSnapshot(
            key=key,
            snapshot=self._decode(key, data),
            version=version,
            machine_version=machine_version,
            updated_at=updated_at,
            deadlines=tuple(deadlines),
        )

    def save(
        self,
        key: str,
        snapshot: str,
        *,
        expected_version: Optional[int] = None,
        machine_version: str = "",
        deadlines: Sequence[Deadline] = (),
    ) -> int:
        validate_key(key)
        if not isinstance(snapshot, str):
            raise TypeError(
                "snapshot must be the JSON str from get_snapshot(), got "
                f"{type(snapshot).__name__}"
            )
        expected_version, machine_version, dls = check_save_args(
            expected_version, machine_version, deadlines
        )
        if expected_version is not None and expected_version < 0:
            raise ValueError("expected_version must be >= 0 or None")
        data = self._encode(key, snapshot)
        self._check_size(key, data)
        return self._save_raw(
            key,
            data,
            expected_version,
            machine_version,
            dls,
        )

    def delete(self, key: str) -> bool:
        validate_key(key)
        return self._delete_raw(key)

    def forget(self, key: str) -> Dict[str, int]:
        validate_key(key)
        return self._forget_raw(key)

    def list_keys(self, *, prefix: str = "", limit: int = 1000) -> List[str]:
        if limit < 0:
            raise ValueError("limit must be >= 0")
        # 🛡️ #259 battle: a row/file another writer planted under a key
        #    `load()` would refuse (empty, NUL, over-long) must not be
        #    advertised -- "list_keys never returns a key load rejects".
        out: List[str] = []
        if limit == 0:
            return out
        for k in self._list_keys_raw(prefix, limit):
            try:
                validate_key(k)
            except InvalidKeyError:
                continue
            out.append(k)
        return out

    def list_versions(
        self, *, prefix: str = "", limit: int = 1000
    ) -> List[Tuple[str, str]]:
        """``[(key, machine_version)]`` for keys starting with ``prefix``,
        sorted, at most ``limit`` -- without decoding snapshot blobs.

        ``machine_version`` is ``""`` for an unlabelled record. Keys whose
        record vanished between listing and reading are skipped.
        """
        # 🏛️ #263 battle: `xsm snapshots --stale` only needs the label the
        #    store already keeps beside the blob; loading and decoding every
        #    full snapshot to read it made the drain list O(total bytes).
        out: List[Tuple[str, str]] = []
        for key, mv in self._list_versions_raw(prefix, limit):
            try:
                validate_key(key)
            except InvalidKeyError:
                continue
            out.append((key, mv))
        return out

    def _list_versions_raw(
        self, prefix: str, limit: int
    ) -> List[Tuple[str, str]]:
        # 📝 Generic fallback: one `_load_raw` per key (no decode, no size
        #    re-check). Backends with an indexed label column override it.
        out: List[Tuple[str, str]] = []
        for key in self.list_keys(prefix=prefix, limit=limit):
            raw = self._load_raw(key)
            if raw is not None:
                out.append((key, raw[2]))
        return out

    def lock(self, key: str, *, timeout: float = 10.0) -> ContextManager[None]:
        validate_key(key)
        if timeout < 0:
            raise ValueError("timeout must be >= 0")
        return self._lock_raw(key, timeout)

    def health(self) -> Dict[str, Any]:
        return {"ok": True, "backend": self.backend}

    # -- primitives (override) ----------------------------------------------
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        raise NotImplementedError

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        raise NotImplementedError

    def _delete_raw(self, key: str) -> bool:
        raise NotImplementedError

    def _forget_raw(self, key: str) -> Dict[str, int]:
        return {"snapshots": int(self._delete_raw(key))}

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        raise NotImplementedError

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        raise NotImplementedError


# -----------------------------------------------------------------------------
# 🧠 MemoryStore
# -----------------------------------------------------------------------------
class _Record:
    __slots__ = (
        "data",
        "version",
        "machine_version",
        "updated_at",
        "deadlines",
    )

    def __init__(
        self,
        data: str,
        version: int,
        machine_version: str,
        updated_at: float,
        deadlines: Tuple[Deadline, ...],
    ) -> None:
        self.data = data
        self.version = version
        self.machine_version = machine_version
        self.updated_at = updated_at
        self.deadlines = deadlines


class MemoryStore(BaseStore):
    """Dict-backed store for tests and single-process apps.

    Good for: unit tests, CLI tools, a single worker that may restart and
    does not need durability. Not for: anything with two processes -- the
    data lives in this process only.

    Thread-safe: one lock guards the map; `lock(key)` is a per-key
    `threading.Lock` with a timeout.
    """

    backend = "memory"

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self._records: Dict[str, _Record] = {}
        self._guard = threading.Lock()
        self._key_locks: Dict[str, threading.Lock] = {}

    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Any]]:
        with self._guard:
            rec = self._records.get(key)
            if rec is None:
                return None
            return (
                rec.data,
                rec.version,
                rec.machine_version,
                rec.updated_at,
                rec.deadlines,
            )

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        with self._guard:
            rec = self._records.get(key)
            current = rec.version if rec is not None else 0
            if expected_version is not None and expected_version != current:
                raise ConflictError(
                    key, expected_version, current if rec else None
                )
            new_version = current + 1
            self._records[key] = _Record(
                data, new_version, machine_version, time.time(), deadlines
            )
            return new_version

    def _delete_raw(self, key: str) -> bool:
        with self._guard:
            return self._records.pop(key, None) is not None

    def _forget_raw(self, key: str) -> Dict[str, int]:
        with self._guard:
            rec = self._records.pop(key, None)
            self._key_locks.pop(key, None)
            return {
                "snapshots": int(rec is not None),
                "deadlines": len(rec.deadlines) if rec else 0,
            }

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        with self._guard:
            keys = sorted(k for k in self._records if k.startswith(prefix))
        return keys[:limit]

    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        """``(key, earliest due_at)`` with a deadline at or before
        *until_wall*, earliest first, at most *limit*.

        📝 #264 battle (public-API widening, flagged): lets
        `DueTimerScanner` skip decoding every record, and returns the
        EARLIEST *limit* rather than the first *limit* keys by name.
        """
        with self._guard:
            rows = [
                (k, min(d.due_at_wall for d in r.deadlines))
                for k, r in self._records.items()
                if r.deadlines
            ]
        due = sorted(
            ((k, d) for k, d in rows if d <= until_wall),
            key=lambda kv: (kv[1], kv[0]),
        )
        return due[: max(int(limit), 0)]

    def _list_versions_raw(
        self, prefix: str, limit: int
    ) -> List[Tuple[str, str]]:
        with self._guard:
            pairs = sorted(
                (k, r.machine_version)
                for k, r in self._records.items()
                if k.startswith(prefix)
            )
        return pairs[:limit]

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        with self._guard:
            lk = self._key_locks.setdefault(key, threading.Lock())
        return _timed_lock(lk, key, timeout)

    def health(self) -> Dict[str, Any]:
        with self._guard:
            return {
                "ok": True,
                "backend": self.backend,
                "keys": len(self._records),
            }


@contextlib.contextmanager
def _timed_lock(
    lk: threading.Lock, key: str, timeout: float
) -> Iterator[None]:
    if not lk.acquire(timeout=timeout):
        raise LockTimeoutError(key, timeout)
    try:
        yield
    finally:
        lk.release()
