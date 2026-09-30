# src/xstate_statemachine/eda/dead_letter.py
# -----------------------------------------------------------------------------
# 💀 DeadLetterStore protocol, SQLite + broker sinks, audit (#293)
# -----------------------------------------------------------------------------
# 🏛️ `patterns.DeadLetterPlugin` (#265) captures chart-driven dead letters;
#    `InboundDispatcher` adds envelope-driven ones (poison after
#    `max_attempts`, `unknown_event`, corrupt envelopes). Both produce the
#    SAME `patterns.DeadLetter` record, so one store and one CLI
#    (`xsm dlq`) serve both. This module EXTENDS `patterns.dead_letter`; it
#    does not fork the record.
#
# 🔐 X0.5 / X0.8: every record is `redact()`ed before it is written (the
#    plugin and dispatcher do it; `put()` does it again for records built
#    by hand), the SQLite file is 0600 (it is a `SQLiteStore` file), and
#    every replay / purge appends an audit row (who, why, when, what).
# -----------------------------------------------------------------------------
"""`DeadLetterStore` protocol, `SQLiteDeadLetterStore`,
`BrokerDeadLetterSink`."""

from __future__ import annotations

import asyncio
import getpass
import json
import sqlite3
import threading
import time
from dataclasses import replace
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from ..patterns.dead_letter import DeadLetter, MemoryDeadLetterStore
from ..plugins import DEFAULT_REDACT_KEYS, redact
from .broker import settle_awaitable
from .envelope import Envelope

__all__ = [
    "BrokerDeadLetterSink",
    "DeadLetterStoreProtocol",
    "MemoryDeadLetterStore",
    "SQLiteDeadLetterStore",
    "dlq_topic",
    "redact_record",
]


def dlq_topic(topic: str) -> str:
    """``orders`` → ``orders.dlq``."""
    return f"{topic}.dlq"


def redact_record(
    record: DeadLetter, keys: Any = DEFAULT_REDACT_KEYS
) -> DeadLetter:
    """*record* with event payload, snapshot and envelope data redacted."""
    return replace(
        record,
        event=redact(dict(record.event or {}), keys),
        snapshot=redact(dict(record.snapshot or {}), keys),
        envelope=(
            redact(dict(record.envelope), keys)
            if record.envelope is not None
            else None
        ),
    )


@runtime_checkable
class DeadLetterStoreProtocol(Protocol):
    """What a dead-letter store offers the plugin, the dispatcher and the
    CLI. Also exported as ``eda.DeadLetterStore``."""

    def put(self, record: DeadLetter) -> None:
        """Protocol member."""

    def get(self, record_id: str) -> Optional[DeadLetter]:
        """Protocol member."""

    def list(
        self, *, include_resolved: bool = False, limit: int = 1000
    ) -> List[DeadLetter]:
        """Protocol member."""

    def mark_resolved(self, record_id: str, when: float) -> bool:
        """Protocol member."""

    def delete(self, record_id: str) -> bool:
        """Protocol member."""

    def purge_older_than(self, cutoff_wall: float) -> int:
        """Protocol member."""


_CREATE = (
    """CREATE TABLE IF NOT EXISTS xsm_dead_letters (
        id          TEXT PRIMARY KEY,
        taken_at    REAL NOT NULL,
        reason      TEXT NOT NULL,
        machine_id  TEXT NOT NULL,
        topic       TEXT,
        resolved_at REAL,
        record      TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS xsm_dead_letters_taken "
    "ON xsm_dead_letters(taken_at)",
    """CREATE TABLE IF NOT EXISTS xsm_dlq_audit (
        seq       INTEGER PRIMARY KEY AUTOINCREMENT,
        at        REAL NOT NULL,
        action    TEXT NOT NULL,
        record_id TEXT,
        actor     TEXT NOT NULL,
        reason    TEXT NOT NULL,
        detail    TEXT NOT NULL
    )""",
)


class SQLiteDeadLetterStore:
    """Dead letters in SQLite -- the default store behind ``xsm dlq``.

    Pass a `SQLiteStore` to share its file (and 0600 permissions, WAL,
    per-thread connections) or a path for a standalone database.
    """

    def __init__(self, store_or_path: Any, *, busy_timeout: float = 5.0):
        from ..persistence.sqlite_store import SQLiteStore

        if isinstance(store_or_path, SQLiteStore):
            self._store = store_or_path
            self._own: Optional[SQLiteStore] = None
        else:
            self._own = SQLiteStore(store_or_path, busy_timeout=busy_timeout)
            self._store = self._own
        self._lock = threading.Lock()
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            for stmt in _CREATE:
                conn.execute(stmt)

    def _conn(self) -> sqlite3.Connection:
        return self._store._conn()

    def __call__(self, record: DeadLetter) -> None:
        self.put(record)

    def put(self, record: DeadLetter) -> None:
        rec = redact_record(record)
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            conn.execute(
                "INSERT OR REPLACE INTO xsm_dead_letters"
                "(id, taken_at, reason, machine_id, topic, resolved_at, "
                "record) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    rec.id,
                    rec.taken_at,
                    rec.reason,
                    rec.machine_id,
                    rec.topic,
                    rec.resolved_at,
                    rec.to_json(),
                ),
            )

    def get(self, record_id: str) -> Optional[DeadLetter]:
        row = (
            self._conn()
            .execute(
                "SELECT record, resolved_at FROM xsm_dead_letters "
                "WHERE id = ?",
                (record_id,),
            )
            .fetchone()
        )
        if row is None:
            return None
        return replace(
            DeadLetter.from_dict(json.loads(row[0])), resolved_at=row[1]
        )

    def list(
        self, *, include_resolved: bool = False, limit: int = 1000
    ) -> List[DeadLetter]:
        sql = "SELECT record, resolved_at FROM xsm_dead_letters"
        if not include_resolved:
            sql += " WHERE resolved_at IS NULL"
        sql += " ORDER BY taken_at, id LIMIT ?"
        return [
            replace(DeadLetter.from_dict(json.loads(r[0])), resolved_at=r[1])
            for r in self._conn().execute(sql, (int(limit),)).fetchall()
        ]

    def mark_resolved(self, record_id: str, when: float) -> bool:
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            cur = conn.execute(
                "UPDATE xsm_dead_letters SET resolved_at = ? WHERE id = ?",
                (when, record_id),
            )
            return cur.rowcount > 0

    def delete(self, record_id: str) -> bool:
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            cur = conn.execute(
                "DELETE FROM xsm_dead_letters WHERE id = ?", (record_id,)
            )
            return cur.rowcount > 0

    def purge_older_than(self, cutoff_wall: float) -> int:
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            return conn.execute(
                "DELETE FROM xsm_dead_letters WHERE taken_at < ?",
                (cutoff_wall,),
            ).rowcount

    def __len__(self) -> int:
        row = (
            self._conn()
            .execute("SELECT count(*) FROM xsm_dead_letters")
            .fetchone()
        )
        return int(row[0])

    # -- audit ----------------------------------------------------------------
    def audit(
        self,
        action: str,
        record_id: Optional[str],
        reason: str,
        detail: Optional[Dict[str, Any]] = None,
        *,
        actor: Optional[str] = None,
    ) -> None:
        """Append an operator action (replay / purge) to ``xsm_dlq_audit``."""
        conn = self._conn()
        with self._store._tx(conn, immediate=True):
            conn.execute(
                "INSERT INTO xsm_dlq_audit"
                "(at, action, record_id, actor, reason, detail) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    time.time(),
                    action,
                    record_id,
                    actor or _whoami(),
                    reason,
                    json.dumps(redact(detail or {}), default=str),
                ),
            )

    def audit_log(self) -> List[Dict[str, Any]]:
        rows = (
            self._conn()
            .execute(
                "SELECT at, action, record_id, actor, reason, detail "
                "FROM xsm_dlq_audit ORDER BY seq"
            )
            .fetchall()
        )
        return [
            {
                "at": r[0],
                "action": r[1],
                "record_id": r[2],
                "actor": r[3],
                "reason": r[4],
                "detail": json.loads(r[5]),
            }
            for r in rows
        ]

    def close(self) -> None:
        if self._own is not None:
            self._own.close()


def _whoami() -> str:
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001 - no login name in a container
        return "unknown"


class BrokerDeadLetterSink:
    """Publish dead letters to ``<topic>.dlq`` on a broker (#293).

    The published envelope is ``type = "xsm.deadletter"``, ``id`` = the
    record id, ``subject`` = the original subject, ``data`` = the redacted
    record (error chain + snapshot). Works with an async
    `BrokerAdapter` (scheduled on the running loop, or run to completion
    when there is none) or a `SyncBrokerAdapter`. Optionally also writes
    to a *store* first, so the CLI can replay it.
    """

    def __init__(
        self, broker: Any, topic: str, *, store: Optional[Any] = None
    ) -> None:
        self.broker = broker
        self.topic = dlq_topic(topic)
        self.store = store
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self._tasks: List[Any] = []

    def __call__(self, record: DeadLetter) -> None:
        self.put(record)

    def envelope_for(self, record: DeadLetter) -> Envelope:
        rec = redact_record(record)
        subject = (rec.envelope or {}).get("subject") or rec.machine_id
        return Envelope.new(
            type="xsm.deadletter",
            subject=str(subject),
            source=f"xsm/{rec.machine_id}",
            data=rec.to_dict(),
            machineid=rec.machine_id,
            machineversion=rec.machine_version,
        )

    def put(self, record: DeadLetter) -> None:
        if self.store is not None:
            self.store.put(record)
        settle_awaitable(
            self.broker.publish(self.topic, self.envelope_for(record)),
            loop=self.loop,
            tasks=self._tasks,
        )

    async def flush(self) -> None:
        """Await publishes scheduled from inside a running loop."""
        tasks, self._tasks = self._tasks, []
        for t in tasks:
            await t
