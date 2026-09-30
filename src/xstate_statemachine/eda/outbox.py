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
import json
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

__all__ = [
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
    relay.
    """

    def add(self, topic: str, envelope: Envelope) -> None:
        """Protocol member."""

    def pending(self, *, limit: int = 100) -> List[OutboxRecord]:
        """Protocol member."""

    def mark_sent(self, seqs: List[int]) -> int:
        """Protocol member."""


# -----------------------------------------------------------------------------
# 🗄️ Stores
# -----------------------------------------------------------------------------
class MemoryOutboxStore:
    """In-memory `OutboxStore` for tests (pairs with `MemoryStore`)."""

    def __init__(self) -> None:
        self._rows: List[Tuple[int, str, Envelope, bool]] = []
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
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    id         TEXT NOT NULL,
    topic      TEXT NOT NULL,
    subject    TEXT,
    envelope   TEXT NOT NULL,
    created_at REAL NOT NULL,
    sent_at    REAL
)
"""
_CREATE_OUTBOX_IDX = (
    "CREATE INDEX IF NOT EXISTS xsm_outbox_pending ON xsm_outbox(sent_at, seq)"
)


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

    @property
    def shares_connection_with(self) -> Any:
        return self._store if self._own is None else None

    def _conn(self) -> sqlite3.Connection:
        return self._store._conn()

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
    """

    def __init__(self, store: Any, broker: Any, *, batch: int = 100) -> None:
        self.store = store
        self.broker = broker
        self.batch = int(batch)

    async def relay_once(self) -> int:
        sent: List[int] = []
        try:
            for rec in self.store.pending(limit=self.batch):
                result = self.broker.publish(rec.topic, rec.envelope)
                if asyncio.iscoroutine(result):
                    await result
                sent.append(rec.seq)
        finally:
            self.store.mark_sent(sent)
        return len(sent)

    def relay_once_sync(self) -> int:
        sent: List[int] = []
        try:
            for rec in self.store.pending(limit=self.batch):
                self.broker.publish(rec.topic, rec.envelope)
                sent.append(rec.seq)
        finally:
            self.store.mark_sent(sent)
        return len(sent)
