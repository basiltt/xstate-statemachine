# src/xstate_statemachine/persistence/idempotency.py
# -----------------------------------------------------------------------------
# 📥 IdempotencyPlugin + InboxStore -- at-least-once, deduplicated (#261)
# -----------------------------------------------------------------------------
# 🏛️ Every broker, webhook provider (Stripe, GitHub, Twilio) and retrying
#    HTTP client delivers AT LEAST ONCE. Duplicate deliveries double-credit
#    wallets and double-ship orders. The honest fix is deduplication at the
#    consumer keyed by a stable event id -- the "inbox" pattern -- and no
#    Python statechart library ships it. Here it is a plugin: attach it and
#    a duplicate is answered from the inbox BEFORE the machine sees it, via
#    `on_before_send` (#304), with the SAME receipt the first delivery got.
#
# 🔐 Scope (X0.2): the inbox key is `(scope, key)` where scope is
#    `principal / machine_name / instance_key` -- never just the actor id.
#    Two tenants reusing "evt_123" must not collide, and a tenant must not
#    be able to replay another tenant's outcome. The `principal` callable
#    is required; HTTP helpers supply it from the authenticated user.
#
# 🔏 Fingerprint: same key + DIFFERENT payload is a client bug (or an
#    attack), not a retry. The inbox stores sha256(type + canonical payload
#    minus the key) and answers a mismatch with `IdempotencyMismatchError`
#    (HTTP 422 in the adapters). A key whose first delivery is still in
#    flight answers `IdempotencyInFlightError` (HTTP 409).
#
# 📝 How a refusal reaches the caller: plugin hooks are CONTAINED (a
#    raising hook is reported and the event admitted -- fail-open, #304),
#    so a refusal cannot be an exception. It is a short-circuit `Receipt`
#    whose `error` is the typed error and `duplicate=True`: the send
#    returns it, the machine never sees the event, `receipt_to_status`
#    maps it to 422 / 409, and a caller who wants an exception checks
#    `receipt.error`. `send(wait=False)` callers see nothing -- exactly
#    like any other refused event; use `wait=True` at an ingress.
#
# ⚠️ Crash-consistency (X0.3): the mark must be visible iff the snapshot
#    that includes the effect is. Two mechanisms:
#      1. When the inbox and the state store share a backend
#         (`SQLiteInbox(store)` on the same file) the mark is BUFFERED in
#         the plugin and written inside the store's `lock()` transaction
#         that saves the snapshot, so they commit together.
#      2. Otherwise save-then-mark, and a per-instance `processed_ids`
#         ring of the last N keys travels INSIDE the snapshot, so a crash
#         between save and mark is caught on the next delivery from the
#         snapshot itself.
#    Side effects performed by ACTIONS are not covered by either -- put
#    them in services or an outbox (documented, not hidden).
# -----------------------------------------------------------------------------
"""`IdempotencyPlugin`, `InboxStore` protocol and the three inbox backends."""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)
from collections import deque

try:  # pragma: no cover
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from ..events import Receipt
from ..exceptions import StoreError
from ..plugins import PluginBase
from ..receipts import receipt_from_json, receipt_to_json

__all__ = [
    "DEFAULT_TTL_S",
    "IdempotencyInFlightError",
    "IdempotencyMismatchError",
    "IdempotencyPlugin",
    "InboxEntry",
    "InboxStore",
    "MemoryInbox",
    "SQLiteInbox",
    "default_key",
    "fingerprint",
    "validate_idempotency_key",
]

#: 7 days -- Stripe's own idempotency window; long enough that a retry
#: storm days later is still a retry, short enough that keys are reusable.
DEFAULT_TTL_S: float = 7 * 86_400
#: Keys are identifiers from OUTSIDE the trust boundary: bounded and plain.
MAX_KEY_LEN = 255
#: How many processed keys each instance remembers inside its snapshot.
PROCESSED_RING_SIZE = 64
IN_FLIGHT = "__in_flight__"


class IdempotencyMismatchError(StoreError, ValueError):
    """The same idempotency key arrived with a DIFFERENT event (type or
    payload). Adapters map it to HTTP 422."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(
            f"Idempotency key {key!r} was already used for a different "
            f"event; keys must not be reused with a different payload."
        )


class IdempotencyInFlightError(StoreError):
    """The first delivery with this key is still being processed (another
    worker holds it). Adapters map it to HTTP 409; the client retries."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(
            f"Idempotency key {key!r} is being processed; retry shortly."
        )


def validate_idempotency_key(key: Any) -> str:
    """Keys are ≤ 255 printable ASCII characters; anything else raises
    ``ValueError`` (the sender's bug, surfaced at the send call)."""
    if not isinstance(key, str) or not key:
        raise ValueError("idempotency key must be a non-empty str")
    if len(key) > MAX_KEY_LEN:
        raise ValueError(f"idempotency key exceeds {MAX_KEY_LEN} characters")
    if not all(32 <= ord(c) < 127 for c in key):
        raise ValueError("idempotency key must be printable ASCII")
    return key


def _default_instance_key(interpreter: Any) -> str:
    """The store key when `persisted()` / `load_interpreter()` set one,
    else the interpreter id (an in-memory machine)."""
    return str(getattr(interpreter, "store_key", None) or interpreter.id)


def default_key(event: Any) -> Optional[str]:
    """``payload["idempotency_key"]`` or ``payload["id"]``; ``None`` means
    "not deduplicated"."""
    payload = getattr(event, "payload", None) or {}
    for name in ("idempotency_key", "id"):
        val = payload.get(name)
        if val is not None:
            return str(val)
    return None


def fingerprint(
    event: Any, *, key_fields: Tuple[str, ...] = ("idempotency_key", "id")
) -> str:
    """sha256 of the event type + canonical JSON payload minus the key
    field(s), so the SAME key with a different payload is detectable."""
    payload = dict(getattr(event, "payload", None) or {})
    for f in key_fields:
        payload.pop(f, None)
    canon = json.dumps(
        {"type": getattr(event, "type", None), "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class InboxEntry:
    """What an inbox remembers per ``(scope, key)``."""

    fingerprint: str
    receipt_json: Optional[str]  # None while in flight
    expires_at: Optional[float]


@runtime_checkable
class InboxStore(Protocol):
    """Where processed idempotency keys live.

    Implementations must be safe from multiple threads / processes.
    ``claim`` is the primitive that makes "first delivery wins" atomic.
    """

    def get(self, scope: str, key: str) -> Optional[InboxEntry]:
        """The entry, or ``None`` if unseen / expired."""
        ...  # pragma: no cover

    def claim(
        self, scope: str, key: str, fp: str, *, ttl_s: Optional[float]
    ) -> bool:
        """Atomically record ``(scope, key)`` as IN FLIGHT with *fp*.
        Returns ``True`` if this caller won (the key was unseen or
        expired), ``False`` if it already exists."""
        ...  # pragma: no cover

    def mark(
        self,
        scope: str,
        key: str,
        receipt_json: str,
        *,
        ttl_s: Optional[float],
    ) -> None:
        """Store the final receipt for a claimed key."""
        ...  # pragma: no cover

    def release(self, scope: str, key: str) -> None:
        """Drop an in-flight claim (the delivery failed before a receipt
        existed) so a retry can claim it again."""
        ...  # pragma: no cover

    def purge_expired(self, *, now: Optional[float] = None) -> int:
        """Delete expired entries; return how many."""
        ...  # pragma: no cover

    def forget(self, scope: str) -> int:
        """Delete every entry for *scope* (X0.5). Returns how many."""
        ...  # pragma: no cover


def _expiry(ttl_s: Optional[float], now: float) -> Optional[float]:
    return None if ttl_s is None else now + float(ttl_s)


# -----------------------------------------------------------------------------
# 🧠 MemoryInbox
# -----------------------------------------------------------------------------
class MemoryInbox:
    """Dict-backed inbox for tests and single-process apps."""

    def __init__(self) -> None:
        self._rows: Dict[Tuple[str, str], InboxEntry] = {}
        self._lock = threading.Lock()

    def _live(self, entry: Optional[InboxEntry], now: float) -> bool:
        return entry is not None and (
            entry.expires_at is None or entry.expires_at > now
        )

    def get(self, scope: str, key: str) -> Optional[InboxEntry]:
        now = time.time()
        with self._lock:
            e = self._rows.get((scope, key))
            return e if self._live(e, now) else None

    def claim(
        self, scope: str, key: str, fp: str, *, ttl_s: Optional[float]
    ) -> bool:
        now = time.time()
        with self._lock:
            e = self._rows.get((scope, key))
            if self._live(e, now):
                return False
            self._rows[(scope, key)] = InboxEntry(
                fp, None, _expiry(ttl_s, now)
            )
            return True

    def mark(
        self,
        scope: str,
        key: str,
        receipt_json: str,
        *,
        ttl_s: Optional[float],
    ) -> None:
        now = time.time()
        with self._lock:
            e = self._rows.get((scope, key))
            fp = e.fingerprint if e else ""
            self._rows[(scope, key)] = InboxEntry(
                fp, receipt_json, _expiry(ttl_s, now)
            )

    def release(self, scope: str, key: str) -> None:
        with self._lock:
            e = self._rows.get((scope, key))
            if e is not None and e.receipt_json is None:
                del self._rows[(scope, key)]

    def purge_expired(self, *, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        with self._lock:
            dead = [k for k, e in self._rows.items() if not self._live(e, now)]
            for k in dead:
                del self._rows[k]
        return len(dead)

    def forget(self, scope: str) -> int:
        with self._lock:
            dead = [k for k in self._rows if k[0] == scope]
            for k in dead:
                del self._rows[k]
        return len(dead)

    def __len__(self) -> int:
        with self._lock:
            return len(self._rows)


# -----------------------------------------------------------------------------
# 🗄️ SQLiteInbox -- shares the SQLiteStore file when given one
# -----------------------------------------------------------------------------
_CREATE_INBOX = """
CREATE TABLE IF NOT EXISTS inbox (
    scope       TEXT NOT NULL,
    key         TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    receipt     TEXT,
    expires_at  REAL,
    PRIMARY KEY (scope, key)
)
"""
_CREATE_INBOX_IDX = "CREATE INDEX IF NOT EXISTS inbox_exp ON inbox(expires_at)"


class SQLiteInbox:
    """Inbox in a SQLite table.

    Pass a `SQLiteStore` to share its file AND its per-thread connection:
    then a mark written inside ``store.lock()`` lands in the same
    transaction as the snapshot save (crash-consistent, X0.3). Or pass a
    path for a standalone inbox database.
    """

    def __init__(
        self, store_or_path: Any, *, busy_timeout: float = 5.0
    ) -> None:
        from .sqlite_store import SQLiteStore

        if isinstance(store_or_path, SQLiteStore):
            self._store: Optional[SQLiteStore] = store_or_path
            self._own: Optional[SQLiteStore] = None
        else:
            self._own = SQLiteStore(store_or_path, busy_timeout=busy_timeout)
            self._store = self._own
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            conn.execute(_CREATE_INBOX)
            conn.execute(_CREATE_INBOX_IDX)

    @property
    def shares_connection_with(self) -> Any:
        """The `SQLiteStore` whose transaction a mark can join (or None)."""
        return self._store if self._own is None else None

    def _conn(self) -> sqlite3.Connection:
        assert self._store is not None
        return self._store._conn()

    def get(self, scope: str, key: str) -> Optional[InboxEntry]:
        row = (
            self._conn()
            .execute(
                "SELECT fingerprint, receipt, expires_at FROM inbox "
                "WHERE scope=? AND key=? AND (expires_at IS NULL OR expires_at > ?)",
                (scope, key, time.time()),
            )
            .fetchone()
        )
        return InboxEntry(row[0], row[1], row[2]) if row else None

    def claim(
        self, scope: str, key: str, fp: str, *, ttl_s: Optional[float]
    ) -> bool:
        now = time.time()
        conn = self._conn()
        assert self._store is not None
        with self._store._tx(conn, immediate=True):
            row = conn.execute(
                "SELECT expires_at FROM inbox WHERE scope=? AND key=?",
                (scope, key),
            ).fetchone()
            if row is not None and (row[0] is None or row[0] > now):
                return False
            conn.execute(
                "INSERT OR REPLACE INTO inbox"
                "(scope, key, fingerprint, receipt, expires_at) "
                "VALUES (?, ?, ?, NULL, ?)",
                (scope, key, fp, _expiry(ttl_s, now)),
            )
            return True

    def mark(
        self,
        scope: str,
        key: str,
        receipt_json: str,
        *,
        ttl_s: Optional[float],
    ) -> None:
        conn = self._conn()
        assert self._store is not None
        with self._store._tx(conn, immediate=True):
            conn.execute(
                "UPDATE inbox SET receipt=?, expires_at=? WHERE scope=? AND key=?",
                (receipt_json, _expiry(ttl_s, time.time()), scope, key),
            )

    def release(self, scope: str, key: str) -> None:
        conn = self._conn()
        assert self._store is not None
        with self._store._tx(conn, immediate=True):
            conn.execute(
                "DELETE FROM inbox WHERE scope=? AND key=? AND receipt IS NULL",
                (scope, key),
            )

    def purge_expired(self, *, now: Optional[float] = None) -> int:
        now = time.time() if now is None else now
        conn = self._conn()
        assert self._store is not None
        with self._store._tx(conn, immediate=True):
            return conn.execute(
                "DELETE FROM inbox WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (now,),
            ).rowcount

    def forget(self, scope: str) -> int:
        conn = self._conn()
        assert self._store is not None
        with self._store._tx(conn, immediate=True):
            return conn.execute(
                "DELETE FROM inbox WHERE scope=?", (scope,)
            ).rowcount

    def close(self) -> None:
        if self._own is not None:
            self._own.close()


# -----------------------------------------------------------------------------
# 🔌 IdempotencyPlugin
# -----------------------------------------------------------------------------
class IdempotencyPlugin(PluginBase[Any]):
    """Drop duplicate deliveries before the machine sees them.

    Args:
        inbox: Where keys live (`MemoryInbox`, `SQLiteInbox`, a contrib
            backend).
        principal: ``(event) -> str`` naming the tenant / user the event
            belongs to. **Required** (X0.2): the inbox scope is
            ``principal / machine.id / instance_key``. Pass
            ``lambda e: "system"`` for a single-tenant consumer.
        key: ``(event) -> Optional[str]``; ``None`` = not deduplicated.
            Default reads ``payload["idempotency_key"]`` or ``payload["id"]``.
        instance_key: ``(interpreter) -> str``; default: the store key
            `persisted()` loaded it under, else ``interpreter.id``.
        ttl_s: Retention of a processed key; ``None`` = forever.
        key_fields: Payload fields excluded from the fingerprint.

    Behaviour (both engines):
        * unseen key → ``claim`` → event enters the machine → after its
          macrostep the real `Receipt` is ``mark``ed;
        * seen + same fingerprint + receipt stored → the send is
          short-circuited with that receipt, ``duplicate=True``;
        * seen + different fingerprint → `IdempotencyMismatchError`;
        * seen + still in flight → `IdempotencyInFlightError`;
        * processing raised before a receipt existed → ``release``.
    """

    def __init__(
        self,
        inbox: InboxStore,
        *,
        principal: Callable[[Any], str],
        key: Callable[[Any], Optional[str]] = default_key,
        instance_key: Optional[Callable[[Any], str]] = None,
        ttl_s: Optional[float] = DEFAULT_TTL_S,
        key_fields: Tuple[str, ...] = ("idempotency_key", "id"),
    ) -> None:
        self.inbox = inbox
        self.principal = principal
        self.key_fn = key
        self.instance_key = instance_key or _default_instance_key
        self.ttl_s = ttl_s
        self.key_fields = key_fields
        #: Claims awaiting their receipt: id(event) -> (scope, key).
        self._pending: Dict[int, Tuple[str, str]] = {}
        #: Marks buffered for a shared-transaction commit (see
        #: `flush_marks`); drained by `persisted()` inside the store lock
        #: when the inbox shares the store's backend.
        self._buffered: List[Tuple[str, str, str]] = []
        self.buffer_marks: bool = False
        self._lock = threading.Lock()

    # -- scope --------------------------------------------------------------------
    def scope_for(self, interpreter: Any, event: Any) -> str:
        return "/".join(
            (
                str(self.principal(event)),
                str(interpreter.machine.id),
                str(self.instance_key(interpreter)),
            )
        )

    # -- ring inside the snapshot (mechanism 2) -----------------------------------
    @staticmethod
    def _ring(interpreter: Any) -> Deque[str]:
        ctx = interpreter.context
        if not isinstance(ctx, dict):
            return deque(maxlen=PROCESSED_RING_SIZE)
        ring = ctx.get("__xsm_processed_ids__")
        if not isinstance(ring, list):
            return deque(maxlen=PROCESSED_RING_SIZE)
        return deque(ring, maxlen=PROCESSED_RING_SIZE)

    @staticmethod
    def _store_ring(interpreter: Any, ring: Deque[str]) -> None:
        ctx = interpreter.context
        if isinstance(ctx, dict):
            ctx["__xsm_processed_ids__"] = list(ring)

    # -- hooks --------------------------------------------------------------------
    @staticmethod
    def _refuse(interpreter: Any, error: Exception) -> Receipt:
        """A refusal as a receipt: nothing ran, the error says why."""
        return Receipt(
            frozenset(interpreter.current_state_ids),
            False,
            error,
            duplicate=True,
        )

    def on_before_send(
        self, interpreter: Any, event: Any
    ) -> Optional[Receipt]:
        key = self.key_fn(event)
        if key is None:
            return None
        try:
            key = validate_idempotency_key(key)
        except ValueError as exc:
            return self._refuse(interpreter, exc)
        scope = self.scope_for(interpreter, event)
        fp = fingerprint(event, key_fields=self.key_fields)
        entry = self.inbox.get(scope, key)
        if entry is not None:
            if entry.fingerprint != fp:
                return self._refuse(interpreter, IdempotencyMismatchError(key))
            if entry.receipt_json is not None:
                cached = receipt_from_json(json.loads(entry.receipt_json))
                return cached._replace(duplicate=True)
            # 🔁 Mechanism 2: the inbox says IN FLIGHT but the snapshot
            #    says PROCESSED -- that is exactly the crash window between
            #    the snapshot save and the mark. The snapshot is the truth
            #    (its save is what made the effect durable); answer a
            #    conservative duplicate and repair the inbox. An in-flight
            #    entry with no ring evidence is a genuine concurrent worker.
            if f"{scope}|{key}" in self._ring(interpreter):
                receipt = Receipt(
                    frozenset(interpreter.current_state_ids),
                    False,
                    None,
                    duplicate=True,
                )
                with contextlib.suppress(Exception):
                    self.inbox.mark(
                        scope,
                        key,
                        json.dumps(receipt_to_json(receipt)),
                        ttl_s=self.ttl_s,
                    )
                return receipt
            return self._refuse(interpreter, IdempotencyInFlightError(key))
        # 📝 No inbox entry: the key is unseen OR its TTL expired. The ring
        #    deliberately does NOT override this -- it is a crash-window
        #    net (above), not a second inbox without a TTL.
        if not self.inbox.claim(scope, key, fp, ttl_s=self.ttl_s):
            # Lost the race to another worker between get and claim.
            entry = self.inbox.get(scope, key)
            if entry is not None and entry.fingerprint != fp:
                return self._refuse(interpreter, IdempotencyMismatchError(key))
            if entry is not None and entry.receipt_json is not None:
                return receipt_from_json(
                    json.loads(entry.receipt_json)
                )._replace(duplicate=True)
            return self._refuse(interpreter, IdempotencyInFlightError(key))
        with self._lock:
            self._pending[id(event)] = (scope, key)
        return None

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Receipt
    ) -> None:
        with self._lock:
            claim = self._pending.pop(id(event), None)
        if claim is None:
            return
        scope, key = claim
        if receipt.error is not None and not receipt.changed:
            # The delivery did not take effect; let a retry try again.
            self.inbox.release(scope, key)
            return
        ring = self._ring(interpreter)
        ring.append(f"{scope}|{key}")
        self._store_ring(interpreter, ring)
        payload = json.dumps(receipt_to_json(receipt))
        if self.buffer_marks:
            with self._lock:
                self._buffered.append((scope, key, payload))
        else:
            self.inbox.mark(scope, key, payload, ttl_s=self.ttl_s)

    def on_interpreter_stop(self, interpreter: Any) -> None:
        # Claims whose event never finished (stopped mid-flight): release.
        with self._lock:
            pending, self._pending = self._pending, {}
        for scope, key in pending.values():
            with contextlib.suppress(Exception):
                self.inbox.release(scope, key)

    # -- shared-transaction commit (mechanism 1) ----------------------------------
    def flush_marks(self) -> int:
        """Write buffered marks now. `persisted()` calls this inside the
        store's lock/transaction right after the snapshot save when the
        inbox shares the store's backend."""
        with self._lock:
            batch, self._buffered = self._buffered, []
        for scope, key, payload in batch:
            self.inbox.mark(scope, key, payload, ttl_s=self.ttl_s)
        return len(batch)

    def discard_marks(self) -> int:
        """Drop buffered marks and release their claims (the save failed)."""
        with self._lock:
            batch, self._buffered = self._buffered, []
        for scope, key, _payload in batch:
            with contextlib.suppress(Exception):
                self.inbox.release(scope, key)
        return len(batch)
