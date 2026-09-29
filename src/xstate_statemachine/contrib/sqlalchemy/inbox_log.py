# src/xstate_statemachine/contrib/sqlalchemy/aux.py
# -----------------------------------------------------------------------------
# 📥 SQLAlchemyInbox / 📜 SQLAlchemyLog -- share the store's transaction
# -----------------------------------------------------------------------------
# 🏛️ The SQLite pair (`SQLiteInbox`, `SQLiteLog`) join a `SQLiteStore`'s
#    per-thread connection; these join a `SQLAlchemyStore`'s per-thread
#    `transaction()`. Under `PessimisticLock` (or an explicit
#    ``with store.transaction():``) the inbox mark and the audit rows commit
#    WITH the snapshot save or not at all (X0.3). Outside one, each call is
#    its own short transaction -- the in-snapshot processed-id ring covers
#    the save-then-mark gap, exactly as for the stdlib stores.
#
#    ``xsm_transitions`` is keyed by the store key, so
#    `SQLAlchemyStore.forget(key)` erases the log with the record (X0.5).
#    Inbox rows are keyed by principal scope and are erased with
#    `SQLAlchemyInbox.forget(scope)`, as in every other backend.
# -----------------------------------------------------------------------------
"""`SQLAlchemyInbox` and `SQLAlchemyLog`."""

from __future__ import annotations

import json
import time
from typing import Any, List, Optional

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from ...persistence.idempotency import InboxEntry, _expiry
from ...persistence.log import TransitionRecord
from .store import SQLAlchemyStore

__all__ = ["SQLAlchemyInbox", "SQLAlchemyLog"]


class SQLAlchemyInbox:
    """`InboxStore` in the ``xsm_inbox`` table of a `SQLAlchemyStore`."""

    def __init__(self, store: SQLAlchemyStore) -> None:
        if not isinstance(store, SQLAlchemyStore):
            raise TypeError("SQLAlchemyInbox(store) needs a SQLAlchemyStore")
        self.store = store
        self.t = store.tables.inbox

    @property
    def shares_connection_with(self) -> Any:
        return self.store

    def get(self, scope: str, key: str) -> Optional[InboxEntry]:
        t = self.t
        with self.store._tx() as conn:
            row = conn.execute(
                select(t.c.fingerprint, t.c.receipt, t.c.expires_at).where(
                    t.c.scope == scope,
                    t.c.key == key,
                    (t.c.expires_at.is_(None))
                    | (t.c.expires_at > time.time()),
                )
            ).first()
        return InboxEntry(row[0], row[1], row[2]) if row else None

    def claim(
        self, scope: str, key: str, fp: str, *, ttl_s: Optional[float]
    ) -> bool:
        t = self.t
        now = time.time()
        with self.store._tx() as conn:
            conn.execute(
                delete(t).where(
                    t.c.scope == scope,
                    t.c.key == key,
                    t.c.expires_at.is_not(None),
                    t.c.expires_at <= now,
                )
            )
            try:
                with conn.begin_nested():
                    conn.execute(
                        insert(t).values(
                            scope=scope,
                            key=key,
                            fingerprint=fp,
                            receipt=None,
                            expires_at=_expiry(ttl_s, now),
                        )
                    )
            except IntegrityError:
                return False
        return True

    def mark(
        self,
        scope: str,
        key: str,
        receipt_json: str,
        *,
        ttl_s: Optional[float],
    ) -> None:
        t = self.t
        with self.store._tx() as conn:
            conn.execute(
                update(t)
                .where(t.c.scope == scope, t.c.key == key)
                .values(
                    receipt=receipt_json,
                    expires_at=_expiry(ttl_s, time.time()),
                )
            )

    def release(self, scope: str, key: str) -> None:
        t = self.t
        with self.store._tx() as conn:
            conn.execute(
                delete(t).where(
                    t.c.scope == scope,
                    t.c.key == key,
                    t.c.receipt.is_(None),
                )
            )

    def purge_expired(self, *, now: Optional[float] = None) -> int:
        t = self.t
        now = time.time() if now is None else now
        with self.store._tx() as conn:
            return int(
                conn.execute(
                    delete(t).where(
                        t.c.expires_at.is_not(None), t.c.expires_at <= now
                    )
                ).rowcount
                or 0
            )

    def forget(self, scope: str) -> int:
        t = self.t
        with self.store._tx() as conn:
            return int(
                conn.execute(delete(t).where(t.c.scope == scope)).rowcount or 0
            )


class SQLAlchemyLog:
    """`TransitionLogStore` in the ``xsm_transitions`` table of a
    `SQLAlchemyStore`. ``append(..., connection=conn)`` writes on *conn*
    (a SQLAlchemy `Connection`), so a caller-held transaction -- the
    mixin's session flush -- carries the audit row."""

    def __init__(self, store: SQLAlchemyStore) -> None:
        if not isinstance(store, SQLAlchemyStore):
            raise TypeError("SQLAlchemyLog(store) needs a SQLAlchemyStore")
        self.store = store
        self.t = store.tables.transitions

    def append(self, rec: TransitionRecord, *, connection: Any = None) -> None:
        stmt = insert(self.t).values(
            machine_id=rec.machine_id,
            seq=rec.seq,
            ts=rec.ts,
            record=json.dumps(rec.to_dict(), sort_keys=True, default=str),
        )
        if connection is not None and hasattr(connection, "execute"):
            connection.execute(stmt)
            return
        with self.store._tx() as conn:
            conn.execute(stmt)

    def next_seq(self, machine_id: str, *, connection: Any = None) -> int:
        t = self.t
        q = select(func.coalesce(func.max(t.c.seq), 0)).where(
            t.c.machine_id == machine_id
        )
        if connection is not None:
            return int(connection.execute(q).scalar_one()) + 1
        with self.store._tx() as conn:
            return int(conn.execute(q).scalar_one()) + 1

    def read(
        self, machine_id: str, *, after_seq: int = 0, limit: int = 1000
    ) -> List[TransitionRecord]:
        t = self.t
        with self.store._tx() as conn:
            rows = conn.execute(
                select(t.c.record)
                .where(t.c.machine_id == machine_id, t.c.seq > after_seq)
                .order_by(t.c.seq)
                .limit(limit)
            ).all()
        return [TransitionRecord.from_dict(json.loads(r[0])) for r in rows]

    def purge_older_than(self, cutoff_ts: float) -> int:
        t = self.t
        with self.store._tx() as conn:
            return int(
                conn.execute(delete(t).where(t.c.ts < cutoff_ts)).rowcount or 0
            )

    def forget(self, machine_id: str) -> int:
        t = self.t
        with self.store._tx() as conn:
            return int(
                conn.execute(
                    delete(t).where(t.c.machine_id == machine_id)
                ).rowcount
                or 0
            )
