# src/xstate_statemachine/contrib/sqlalchemy/outbox.py
# -----------------------------------------------------------------------------
# 📤 SQLAlchemyOutboxStore -- the transactional outbox on any RDBMS (#284 p3)
# -----------------------------------------------------------------------------
# 🏛️ Implements the EDA core's `OutboxStore` protocol (#293) on the
#    ``xsm_outbox`` table, joining the `SQLAlchemyStore`'s per-thread
#    `transaction()` exactly like `SQLAlchemyInbox` / `SQLAlchemyLog`.
#    Under `PessimisticLock` (or an explicit ``with store.transaction():``)
#    `persisted()` writes the snapshot and then flushes `OutboxPlugin`'s
#    rows in the SAME transaction: a rollback drops both (X0.3).
#
# 📝 The table is additive and not part of the versioned shared schema: it
#    is created on construction (``create_table=True``) and put on the
#    store's `MetaData`, so Alembic autogenerate sees it when you pass
#    your own metadata to the store.
# -----------------------------------------------------------------------------
"""`SQLAlchemyOutboxStore`."""

from __future__ import annotations

import time
from typing import Any, List

from sqlalchemy import (
    Column,
    Float,
    Index,
    Integer,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)

from ...eda.envelope import Envelope
from ...eda.outbox import OutboxRecord
from .store import SQLAlchemyStore

__all__ = ["OUTBOX_TABLE", "SQLAlchemyOutboxStore", "outbox_table"]

OUTBOX_TABLE = "xsm_outbox"


def outbox_table(metadata: Any) -> Table:
    """Define (or reuse) ``xsm_outbox`` on *metadata*."""
    existing = metadata.tables.get(OUTBOX_TABLE)
    if existing is not None:
        return existing
    return Table(
        OUTBOX_TABLE,
        metadata,
        Column("seq", Integer, primary_key=True, autoincrement=True),
        Column("id", String(64), nullable=False),
        Column("topic", String(255), nullable=False),
        Column("subject", String(200), nullable=True),
        Column("envelope", Text, nullable=False),
        Column("created_at", Float, nullable=False),
        Column("sent_at", Float, nullable=True),
        Index("xsm_outbox_pending", "sent_at", "seq"),
    )


class SQLAlchemyOutboxStore:
    """`OutboxStore` in the ``xsm_outbox`` table of a `SQLAlchemyStore`."""

    def __init__(
        self, store: SQLAlchemyStore, *, create_table: bool = True
    ) -> None:
        if not isinstance(store, SQLAlchemyStore):
            raise TypeError(
                "SQLAlchemyOutboxStore(store) needs a SQLAlchemyStore"
            )
        self.store = store
        self.t = outbox_table(store.tables.metadata)
        if create_table:
            with store._fresh() as conn:
                self.t.create(conn, checkfirst=True)

    @property
    def shares_connection_with(self) -> Any:
        return self.store

    def add(self, topic: str, envelope: Envelope) -> None:
        with self.store._tx() as conn:
            conn.execute(
                insert(self.t).values(
                    id=envelope.id,
                    topic=topic,
                    subject=envelope.subject,
                    envelope=envelope.to_json(),
                    created_at=time.time(),
                )
            )

    def pending(self, *, limit: int = 100) -> List[OutboxRecord]:
        t = self.t
        with self.store._tx() as conn:
            rows = conn.execute(
                select(t.c.seq, t.c.topic, t.c.envelope)
                .where(t.c.sent_at.is_(None))
                .order_by(t.c.seq)
                .limit(int(limit))
            ).all()
        return [
            OutboxRecord(int(r[0]), r[1], Envelope.from_json(r[2]))
            for r in rows
        ]

    def mark_sent(self, seqs: List[int]) -> int:
        if not seqs:
            return 0
        t = self.t
        with self.store._tx() as conn:
            return int(
                conn.execute(
                    update(t)
                    .where(t.c.seq.in_([int(s) for s in seqs]))
                    .where(t.c.sent_at.is_(None))
                    .values(sent_at=time.time())
                ).rowcount
                or 0
            )

    def count(self, *, pending_only: bool = False) -> int:
        from sqlalchemy import func

        t = self.t
        q = select(func.count()).select_from(t)
        if pending_only:
            q = q.where(t.c.sent_at.is_(None))
        with self.store._tx() as conn:
            return int(conn.execute(q).scalar_one())
