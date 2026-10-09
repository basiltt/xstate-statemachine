# src/xstate_statemachine/eda/outbox.py
# -----------------------------------------------------------------------------
# 📤 OutboxPlugin + OutboxStore -- publish what the CHART says to publish (#293)
# -----------------------------------------------------------------------------
# 🏛️ Selection is declared in the chart, never in Python:
#
#      * a transition with ``meta.publish`` -- ``true``, a type string, or
#        ``{"type": "order.paid", "data": ["total", ...]}`` (context
#        fields copied into ``data``);
#      * a state tagged ``"publish"`` -- entering it publishes
#        ``xsm.<machine>.transition.<state key>`` with the whole
#        (redacted) context as ``data``.
#
#    Envelopes are built during the macrostep and handed to the SINK once
#    the event has settled (`on_event_processed`). Sinks:
#
#      * an `OutboxStore` (`SQLiteOutboxStore`, `SQLAlchemyOutboxStore`) --
#        TRANSACTIONAL when it shares the state store's transaction:
#        `persisted()` buffers the rows and writes them right after the
#        snapshot save, via the same `flush_marks` seam the idempotency
#        inbox uses, so under `PessimisticLock` (the lock IS the
#        transaction) a rollback drops the rows with the snapshot. A relay
#        (`OutboxRelay`) moves rows to a broker afterwards: at-least-once.
#      * a `BrokerAdapter` directly -- published after the step, not in any
#        transaction: at-most-once-ish (a crash between the save and the
#        publish loses the message). Documented as such.
#
# 🔐 X0.8: ``data`` from a state tag is the redacted context; no header or
#    credential is ever copied into extensions (`Envelope` refuses them).
# -----------------------------------------------------------------------------
"""`OutboxPlugin`, `OutboxStore` protocol, `SQLiteOutboxStore`,
`MemoryOutboxStore`, `OutboxRelay`."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import sqlite3
import threading
import time
import weakref
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    runtime_checkable,
)

from ..persistence.locking import after_commit, current_session
from ..plugins import DEFAULT_REDACT_KEYS, PluginBase, redact
from .broker import settle_awaitable
from .envelope import Envelope

logger = logging.getLogger(__name__)

__all__ = [
    "DEFAULT_CLAIM_LEASE_S",
    "PUBLISH_TAG",
    "MemoryOutboxStore",
    "OutboxPlugin",
    "OutboxRecord",
    "OutboxRelay",
    "OutboxStore",
    "SQLiteOutboxStore",
    "publish_specs",
]

#: The state tag that marks "entering this state is an integration event".
PUBLISH_TAG = "publish"


class OutboxRecord(NamedTuple):
    """One pending outbox row."""

    seq: int
    topic: str
    envelope: Envelope


@runtime_checkable
class OutboxStore(Protocol):
    """Where transactional outbox rows live until a relay publishes them.

    ``add`` must join the state store's current transaction when there is
    one (that is the whole point); ``pending`` / ``mark_sent`` are for the
    relay. Optional members the relay uses when present:
    ``claim(limit=, owner=, lease_s=)`` (rows leased to one relay so
    several relays may drain one outbox) and ``release(seqs, owner=)``
    (hand unsent rows back; without it they wait out the lease).
    """

    def add(self, topic: str, envelope: Envelope) -> None:
        """Protocol member."""

    def pending(self, *, limit: int = 100) -> List[OutboxRecord]:
        """Protocol member."""

    def mark_sent(self, seqs: List[int]) -> int:
        """Protocol member."""


#: How long a relay owns the rows it claimed before another relay may
#: take them over (a relay that died mid-batch). Seconds.
DEFAULT_CLAIM_LEASE_S = 30.0


# -----------------------------------------------------------------------------
# 🗄️ Stores
# -----------------------------------------------------------------------------
class MemoryOutboxStore:
    """In-memory `OutboxStore` for tests (pairs with `MemoryStore`)."""

    def __init__(self) -> None:
        self._rows: List[Tuple[int, str, Envelope, bool]] = []
        self._claims: Dict[int, Tuple[str, float]] = {}
        self._seq = 0
        self._lock = threading.Lock()

    def add(self, topic: str, envelope: Envelope) -> None:
        with self._lock:
            self._seq += 1
            self._rows.append((self._seq, topic, envelope, False))

    def pending(self, *, limit: int = 100) -> List[OutboxRecord]:
        with self._lock:
            return [
                OutboxRecord(s, t, e)
                for s, t, e, sent in self._rows
                if not sent
            ][:limit]

    def claim(
        self, *, limit: int, owner: str, lease_s: float
    ) -> List[OutboxRecord]:
        """Pending rows nobody else holds a live lease on, leased to
        *owner* for *lease_s* seconds (see `SQLiteOutboxStore.claim`)."""
        now = time.time()
        out: List[OutboxRecord] = []
        with self._lock:
            for s, t, e, sent in self._rows:
                if sent or len(out) >= limit:
                    continue
                held = self._claims.get(s)
                if held is not None and held[1] > now and held[0] != owner:
                    continue
                self._claims[s] = (owner, now + lease_s)
                out.append(OutboxRecord(s, t, e))
        return out

    def release(self, seqs: List[int], *, owner: str) -> int:
        """Give *owner*'s leases on *seqs* back (a relay that failed
        mid-batch but is still alive hands its rows over at once)."""
        n = 0
        with self._lock:
            for s in seqs:
                held = self._claims.get(s)
                if held is not None and held[0] == owner:
                    del self._claims[s]
                    n += 1
        return n

    def mark_sent(self, seqs: List[int]) -> int:
        wanted = set(seqs)
        n = 0
        with self._lock:
            for i, (s, t, e, sent) in enumerate(self._rows):
                if s in wanted and not sent:
                    self._rows[i] = (s, t, e, True)
                    n += 1
        return n

    def __len__(self) -> int:
        return len(self.pending(limit=1 << 30))


_CREATE_OUTBOX = """
CREATE TABLE IF NOT EXISTS xsm_outbox (
    seq           INTEGER PRIMARY KEY AUTOINCREMENT,
    id            TEXT NOT NULL,
    topic         TEXT NOT NULL,
    subject       TEXT,
    envelope      TEXT NOT NULL,
    created_at    REAL NOT NULL,
    sent_at       REAL,
    claimed_by    TEXT,
    claimed_until REAL
)
"""
_CREATE_OUTBOX_IDX = (
    "CREATE INDEX IF NOT EXISTS xsm_outbox_pending ON xsm_outbox(sent_at, seq)"
)
#: 🔁 #293 battle: tables created by 0.11.0 lack the lease columns.
_OUTBOX_UPGRADES = {
    "claimed_by": "ALTER TABLE xsm_outbox ADD COLUMN claimed_by TEXT",
    "claimed_until": "ALTER TABLE xsm_outbox ADD COLUMN claimed_until REAL",
}


class SQLiteOutboxStore:
    """Zero-dependency transactional outbox in the ``xsm_outbox`` table.

    Pass the `SQLiteStore` that holds the snapshots: rows are written on
    that store's per-thread connection, so inside ``store.lock(key)``
    (`PessimisticLock`) they commit or roll back WITH the snapshot. A
    path gives a standalone (non-transactional) outbox database.
    """

    def __init__(self, store_or_path: Any, *, busy_timeout: float = 5.0):
        from ..persistence.sqlite_store import SQLiteStore

        if isinstance(store_or_path, SQLiteStore):
            self._store = store_or_path
            self._own: Optional[SQLiteStore] = None
        else:
            self._own = SQLiteStore(store_or_path, busy_timeout=busy_timeout)
            self._store = self._own
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            conn.execute(_CREATE_OUTBOX)
            conn.execute(_CREATE_OUTBOX_IDX)
            have = {
                r[1] for r in conn.execute("PRAGMA table_info(xsm_outbox)")
            }
            for column, ddl in _OUTBOX_UPGRADES.items():
                if column not in have:
                    conn.execute(ddl)

    @property
    def shares_connection_with(self) -> Any:
        return self._store if self._own is None else None

    def _conn(self) -> sqlite3.Connection:
        return self._store._conn()

    def claim(
        self, *, limit: int, owner: str, lease_s: float
    ) -> List[OutboxRecord]:
        """Lease up to *limit* pending rows to *owner*: rows no other
        relay holds a live lease on, in ``seq`` order.

        🏛️ #293 battle: two relays (two service replicas, a Celery beat
        and a CLI run) draining ONE outbox each read the same ``pending``
        rows and published every one of them twice. The lease partitions
        the rows between relays; a relay that dies mid-batch loses its
        lease after *lease_s* and another picks the rows up (still
        at-least-once, as documented; never N-times-once).
        """
        now = time.time()
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            rows = conn.execute(
                "SELECT seq, topic, envelope FROM xsm_outbox "
                "WHERE sent_at IS NULL AND (claimed_until IS NULL "
                "OR claimed_until <= ? OR claimed_by = ?) "
                "ORDER BY seq LIMIT ?",
                (now, owner, int(limit)),
            ).fetchall()
            if rows:
                marks = ",".join("?" * len(rows))
                conn.execute(
                    "UPDATE xsm_outbox SET claimed_by = ?, claimed_until = ? "
                    f"WHERE seq IN ({marks})",
                    (owner, now + float(lease_s), *[int(r[0]) for r in rows]),
                )
        return [
            OutboxRecord(int(r[0]), r[1], Envelope.from_json(r[2]))
            for r in rows
        ]

    def add(self, topic: str, envelope: Envelope) -> None:
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            conn.execute(
                "INSERT INTO xsm_outbox"
                "(id, topic, subject, envelope, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    envelope.id,
                    topic,
                    envelope.subject,
                    envelope.to_json(),
                    time.time(),
                ),
            )

    def pending(self, *, limit: int = 100) -> List[OutboxRecord]:
        rows = (
            self._conn()
            .execute(
                "SELECT seq, topic, envelope FROM xsm_outbox "
                "WHERE sent_at IS NULL ORDER BY seq LIMIT ?",
                (int(limit),),
            )
            .fetchall()
        )
        return [
            OutboxRecord(int(r[0]), r[1], Envelope.from_json(r[2]))
            for r in rows
        ]

    def release(self, seqs: List[int], *, owner: str) -> int:
        """Give *owner*'s leases on *seqs* back (see `MemoryOutboxStore`)."""
        if not seqs:
            return 0
        conn = self._conn()
        marks = ",".join("?" * len(seqs))
        with self._store._tx(conn, immediate=True):
            return int(
                conn.execute(
                    "UPDATE xsm_outbox SET claimed_by = NULL, "
                    f"claimed_until = NULL WHERE claimed_by = ? "
                    f"AND seq IN ({marks})",
                    (owner, *[int(sq) for sq in seqs]),
                ).rowcount
            )

    def mark_sent(self, seqs: List[int]) -> int:
        if not seqs:
            return 0
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            return sum(
                conn.execute(
                    "UPDATE xsm_outbox SET sent_at = ? "
                    "WHERE seq = ? AND sent_at IS NULL",
                    (time.time(), int(s)),
                ).rowcount
                for s in seqs
            )

    def purge_sent(self, *, older_than_s: float = 86400.0) -> int:
        """Delete relayed rows older than *older_than_s* (retention)."""
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            return conn.execute(
                "DELETE FROM xsm_outbox WHERE sent_at IS NOT NULL "
                "AND sent_at < ?",
                (time.time() - older_than_s,),
            ).rowcount

    def count(self, *, pending_only: bool = False) -> int:
        sql = "SELECT count(*) FROM xsm_outbox"
        if pending_only:
            sql += " WHERE sent_at IS NULL"
        return int(self._conn().execute(sql).fetchone()[0])

    def close(self) -> None:
        if self._own is not None:
            self._own.close()


# -----------------------------------------------------------------------------
# 🔍 What does the chart publish?
# -----------------------------------------------------------------------------
def _state_key(node: Any, machine_id: str) -> str:
    prefix = f"{machine_id}."
    sid = str(node.id)
    return sid[len(prefix) :] if sid.startswith(prefix) else sid


def publish_specs(machine: Any) -> List[Dict[str, Any]]:
    """Every publication the chart declares, for AsyncAPI and ``xsm docs``.

    Returns ``[{"type", "source": "transition"|"state", "from", "event",
    "fields"}]`` in document order.
    """
    from ..validation import walk

    out: List[Dict[str, Any]] = []
    for node in walk(machine):
        if PUBLISH_TAG in (getattr(node, "tags", None) or ()):
            out.append(
                {
                    "type": _state_type(machine, node),
                    "source": "state",
                    "from": node.id,
                    "event": None,
                    "fields": None,
                }
            )
        for event, transitions in _all_transitions(node):
            for t in transitions:
                spec = _transition_spec(machine, t)
                if spec is not None:
                    out.append(
                        {
                            "type": spec[0],
                            "source": "transition",
                            "from": node.id,
                            "event": event,
                            "fields": spec[1],
                        }
                    )
    return out


def _all_transitions(node: Any) -> List[Tuple[str, List[Any]]]:
    rows: List[Tuple[str, List[Any]]] = [
        (ev, list(ts)) for ev, ts in (getattr(node, "on", None) or {}).items()
    ]
    for delay, ts in (getattr(node, "after", None) or {}).items():
        rows.append((f"after.{delay}", list(ts)))
    for inv in getattr(node, "invoke", None) or ():
        rows.append((f"done.invoke.{inv.id}", list(inv.on_done or ())))
        rows.append((f"error.platform.{inv.id}", list(inv.on_error or ())))
    on_done = getattr(node, "on_done", None)
    if on_done is not None:
        rows.append(
            (
                f"done.state.{node.id}",
                on_done if isinstance(on_done, list) else [on_done],
            )
        )
    return rows


def _state_type(machine: Any, node: Any) -> str:
    return f"xsm.{machine.id}.transition.{_state_key(node, machine.id)}"


def _transition_spec(
    machine: Any, t: Any
) -> Optional[Tuple[str, Optional[List[str]]]]:
    spec = (getattr(t, "meta", None) or {}).get("publish")
    if spec is None or spec is False:
        return None
    if spec is True:
        tgt = getattr(t, "resolved_target", None) or t.source
        return _state_type(machine, tgt), None
    if isinstance(spec, str):
        return spec, None
    if isinstance(spec, dict) and isinstance(spec.get("type"), str):
        fields = spec.get("data")
        if fields is not None and not (
            isinstance(fields, list)
            and all(isinstance(f, str) for f in fields)
        ):
            raise ValueError(
                "meta.publish.data must be a list of context field names"
            )
        return spec["type"], fields
    raise ValueError(
        "meta.publish must be true, an event type string or "
        '{"type": ..., "data": [fields]}'
    )


# -----------------------------------------------------------------------------
# 🔌 The plugin
# -----------------------------------------------------------------------------
class OutboxPlugin(PluginBase[Any]):
    """Turn chart-declared transitions into outbound `Envelope`s.

    Args:
        sink: An `OutboxStore` (transactional with a shared store) or a
            `BrokerAdapter` / `SyncBrokerAdapter` (direct, at-most-once-ish).
        topic: Topic every envelope is written for.
        redact_keys: Keys masked in state-tag ``data`` (whole context).

    Causation: when the interpreter was driven by `InboundDispatcher`, the
    inbound envelope is the cause -- ``causationid`` is its id and the
    ``correlationid`` is inherited.
    """

    #: Flushed AFTER the idempotency inbox (priority 0): a failed outbox
    #: write must not prevent the mark that stops a committed event from
    #: being redelivered.
    flush_priority = 10

    def __init__(
        self,
        sink: Any,
        *,
        topic: str = "events",
        redact_keys: Tuple[str, ...] = DEFAULT_REDACT_KEYS,
    ) -> None:
        self.sink = sink
        self.topic = topic
        self.redact_keys = redact_keys
        # 📝 A sink that implements the `OutboxStore` protocol is a store
        #    even if it also has a convenience `publish`.
        self._is_store = isinstance(sink, OutboxStore) or (
            callable(getattr(sink, "add", None))
            and not callable(getattr(sink, "publish", None))
        )
        #: Envelopes built during the step in progress, per interpreter
        #: (weak: an interpreter dropped without `stop()` leaves nothing).
        self._step: "weakref.WeakKeyDictionary[Any, List[Envelope]]" = (
            weakref.WeakKeyDictionary()
        )
        #: Envelopes awaiting `persisted()`'s post-save flush, keyed by the
        #: persisted() SESSION (`locking.current_session`: per thread AND
        #: per asyncio task), so concurrent blocks sharing this plugin --
        #: dispatcher worker threads, `apersisted` blocks on one loop --
        #: never flush each other's rows.
        self._buffers: Dict[object, List[Envelope]] = {}
        self.buffer_marks: bool = False
        #: Event loop to publish on when called from a worker thread.
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._tasks: List[Any] = []
        self._lock = threading.Lock()

    # -- collection -----------------------------------------------------------
    def on_transition(
        self,
        interpreter: Any,
        from_states: Any,
        to_states: Any,
        transition: Any,
    ) -> None:
        machine = interpreter.machine
        cause = getattr(interpreter, "_xsm_cause", None)
        out: List[Envelope] = []
        spec = _transition_spec(machine, transition) if transition else None
        if spec is not None:
            etype, fields = spec
            ctx = (
                interpreter.context
                if isinstance(interpreter.context, dict)
                else {}
            )
            data = (
                {f: ctx.get(f) for f in fields} if fields is not None else None
            )
            out.append(
                Envelope.from_transition(
                    interpreter, type=etype, data=data, cause=cause
                )
            )
        for node in sorted(
            (n for n in to_states if n not in from_states),
            key=lambda n: str(n.id),
        ):
            if PUBLISH_TAG in (getattr(node, "tags", None) or ()):
                ctx = interpreter.context
                data = (
                    redact(dict(ctx), self.redact_keys)
                    if isinstance(ctx, dict)
                    else None
                )
                out.append(
                    Envelope.from_transition(
                        interpreter,
                        type=_state_type(machine, node),
                        data=_jsonable(data),
                        cause=cause,
                    )
                )
        if out:
            with self._lock:
                self._step.setdefault(interpreter, []).extend(out)

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Any
    ) -> None:
        with self._lock:
            batch = self._step.pop(interpreter, None)
        if not batch:
            return
        session = current_session.get()
        if self.buffer_marks and session is not None:
            with self._lock:
                self._buffers.setdefault(session, []).extend(batch)
            return
        self._emit(batch)

    def on_interpreter_stop(self, interpreter: Any) -> None:
        with self._lock:
            self._step.pop(interpreter, None)

    def _buffer(self) -> List[Envelope]:
        """This session's pending envelopes (created on demand)."""
        with self._lock:
            return self._buffers.setdefault(current_session.get(), [])

    def _take_buffer(self) -> List[Envelope]:
        with self._lock:
            return self._buffers.pop(current_session.get(), [])

    # -- persisted() seam (same as IdempotencyPlugin) -------------------------
    def flush_marks(self) -> int:
        """Write buffered envelopes now -- `persisted()` calls this right
        after the snapshot save, inside the store transaction when there
        is one. A BROKER sink is not transactional: its envelopes are held
        until the persisted() block has fully exited (`after_commit`), so
        a rollback of the outer transaction never publishes a state that
        was not kept."""
        batch = self._take_buffer()
        if self._is_store:
            self._emit(batch)
        else:
            after_commit(lambda: self._emit(batch))
        return len(batch)

    def discard_marks(self) -> int:
        """Drop buffered envelopes (the save failed)."""
        return len(self._take_buffer())

    # -- delivery ---------------------------------------------------------------
    def _emit(self, batch: List[Envelope]) -> None:
        for env in batch:
            if self._is_store:
                self.sink.add(self.topic, env)
            else:
                self._publish(env)

    def _publish(self, env: Envelope) -> None:
        settle_awaitable(
            self.sink.publish(self.topic, env),
            loop=self.loop,
            tasks=self._tasks,
        )

    async def drain(self) -> None:
        """Await publishes scheduled on the running loop."""
        tasks, self._tasks = self._tasks, []
        for t in tasks:
            await t


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return json.loads(json.dumps(value, default=str))


class OutboxRelay:
    """Move pending `OutboxStore` rows to a broker (at-least-once).

    ``relay_once()`` publishes up to *batch* rows in ``seq`` order and marks
    them sent only after the broker accepted them; a failure leaves the
    row pending for the next run. Consumers dedup on the envelope id.

    Several relays may drain one outbox: when the store offers
    ``claim()`` (`SQLiteOutboxStore`, `SQLAlchemyOutboxStore`,
    `MemoryOutboxStore`) each run leases its rows for *lease_s* seconds,
    so two relays never publish the same row at the same time; a relay
    that dies mid-batch loses its lease and the rows are picked up again
    (#293 battle). *owner* defaults to ``host:pid:id(relay)``.

    ⚠️ The duplicate window is one BATCH per expired lease: a relay that
    outlives its lease still publishes the rows it holds in memory while
    another relay may have re-claimed them. Size *lease_s* above the
    slowest batch you expect (``batch`` x the broker's worst publish).
    """

    def __init__(
        self,
        store: Any,
        broker: Any,
        *,
        batch: int = 100,
        owner: Optional[str] = None,
        lease_s: float = DEFAULT_CLAIM_LEASE_S,
    ) -> None:
        if lease_s <= 0:
            raise ValueError("lease_s must be > 0")
        self.store = store
        self.broker = broker
        self.batch = int(batch)
        self.owner = owner or _default_owner(self)
        self.lease_s = float(lease_s)

    def _take(self) -> List[OutboxRecord]:
        claim = getattr(self.store, "claim", None)
        if callable(claim):
            return list(
                claim(limit=self.batch, owner=self.owner, lease_s=self.lease_s)
            )
        return list(self.store.pending(limit=self.batch))

    def _settle(
        self, taken: List[OutboxRecord], sent: List[int], *, failing: bool
    ) -> None:
        """Mark what the broker accepted; hand the rest back at once.

        📝 A relay that RAISED is still alive -- its unsent rows must not
        wait out the lease (the #284 scenario's second relay picks them
        up immediately). A relay that DIED cannot release; the lease
        expiry covers it. Review M1: the release runs even when
        `mark_sent` raised (the DB is locked), and while the broker's
        own error is propagating (*failing*) a failing mark / release is
        LOGGED, not raised over it -- the operator sees the cause.
        """
        release = getattr(self.store, "release", None)
        done = set(sent)
        left = [r.seq for r in taken if r.seq not in done]
        try:
            self.store.mark_sent(sent)
        except Exception:  # noqa: BLE001 - logged or re-raised below
            if not failing:
                self._release(release, left)
                raise
            logger.exception("📤 outbox relay: mark_sent failed")
        if failing:
            try:
                self._release(release, left)
            except Exception:  # noqa: BLE001 - the lease covers it
                logger.exception("📤 outbox relay: release failed")
        else:
            self._release(release, left)

    def _release(self, release: Any, left: List[int]) -> None:
        if left and callable(release):
            release(left, owner=self.owner)

    async def relay_once(self) -> int:
        """Claim (or read) up to ``batch`` pending rows and publish them.

        Returns:
            How many rows the broker accepted and were marked sent. Rows
            the broker refused are released for the next run, and the
            broker's exception propagates.
        """
        sent: List[int] = []
        taken: List[OutboxRecord] = []
        try:
            taken = self._take()
            for rec in taken:
                result = self.broker.publish(rec.topic, rec.envelope)
                if asyncio.iscoroutine(result):
                    await result
                sent.append(rec.seq)
        except BaseException:
            self._settle(taken, sent, failing=True)
            raise
        self._settle(taken, sent, failing=False)
        return len(sent)

    def relay_once_sync(self) -> int:
        """`relay_once` for a `SyncBrokerAdapter` (no event loop).

        Returns:
            How many rows the broker accepted and were marked sent.
        """
        sent: List[int] = []
        taken: List[OutboxRecord] = []
        try:
            taken = self._take()
            for rec in taken:
                result = self.broker.publish(rec.topic, rec.envelope)
                if inspect.isawaitable(result):
                    # 🔥 #292-a battle: a plain ``def publish`` returning a
                    #    coroutine was never awaited, yet the row was
                    #    marked SENT -- a silently lost message.
                    close = getattr(result, "close", None)
                    if callable(close):
                        close()
                    raise TypeError(
                        "broker.publish returned an awaitable on the sync "
                        "relay path; use relay_once() (an async broker)"
                    )
                sent.append(rec.seq)
        except BaseException:
            self._settle(taken, sent, failing=True)
            raise
        self._settle(taken, sent, failing=False)
        return len(sent)


def _default_owner(relay: Any) -> str:
    import os
    import socket

    return f"{socket.gethostname()}:{os.getpid()}:{id(relay):x}"
