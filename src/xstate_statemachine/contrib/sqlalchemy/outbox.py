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
    text,
    update,
)

from ...eda.envelope import Envelope
from ...eda.outbox import OutboxRecord
from .store import SQLAlchemyStore

__all__ = [
    "LEASE_COLUMNS",
    "OUTBOX_TABLE",
    "SQLAlchemyOutboxStore",
    "outbox_table",
]

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
        # 🔁 #293 battle: relay lease (see `SQLiteOutboxStore.claim`)
        Column("claimed_by", String(128), nullable=True),
        Column("claimed_until", Float, nullable=True),
        Index("xsm_outbox_pending", "sent_at", "seq"),
    )


LEASE_COLUMNS = ("claimed_by", "claimed_until")


def _ensure_lease_columns(conn: Any, t: Table, *, create: bool) -> None:
    """Add the relay-lease columns to an ``xsm_outbox`` created by 0.11.0.

    🔥 #293 review H1: ``create_all`` never adds columns to an existing
    table, and `OutboxRelay` now always claims -- every relay on an
    upgraded deployment would have died with "no such column" at the
    first tick, silently stopping the outbox. With *create* the columns
    are added here; without it (``create_table=False`` -- migrations are
    yours) the store refuses to start and names the migration.
    """
    from sqlalchemy import inspect as sa_inspect

    from ...persistence.store import StoreError

    have = {c["name"] for c in sa_inspect(conn).get_columns(t.name)}
    missing = [c for c in LEASE_COLUMNS if c not in have]
    if not missing:
        return
    if not create:
        raise StoreError(
            f"{t.name} lacks {', '.join(missing)} (relay leases, 0.12): "
            "add the columns in your next migration -- see the "
            "sqlalchemy_orders example's 0003_xsm_outbox_relay_lease.py"
        )
    for name in missing:
        col = t.c[name]
        ddl = col.type.compile(dialect=conn.dialect)
        conn.execute(text(f"ALTER TABLE {t.name} ADD COLUMN {name} {ddl}"))


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
        with store._fresh() as conn:
            if create_table:
                self.t.create(conn, checkfirst=True)
            _ensure_lease_columns(conn, self.t, create=create_table)

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

    def claim(
        self, *, limit: int, owner: str, lease_s: float
    ) -> List[OutboxRecord]:
        """Lease pending rows to *owner* (see `SQLiteOutboxStore.claim`).

        🏛️ Review H2: the CLAIM is the guard, on every dialect -- the
        UPDATE re-states the "free or mine" predicate, so two relays that
        selected the same rows under READ COMMITTED cannot both win them;
        each then reads back ONLY the rows stamped with its own lease.
        ``FOR UPDATE SKIP LOCKED`` (Postgres, MySQL 8) is an optimisation
        that keeps the losers from blocking.
        """
        from sqlalchemy import or_

        t = self.t
        now = time.time()
        until = now + float(lease_s)
        free = or_(
            t.c.claimed_until.is_(None),
            t.c.claimed_until <= now,
            t.c.claimed_by == owner,
        )
        with self.store._tx() as conn:
            pick = (
                select(t.c.seq)
                .where(t.c.sent_at.is_(None))
                .where(free)
                .order_by(t.c.seq)
                .limit(int(limit))
            )
            if conn.dialect.name in ("postgresql", "mysql"):
                pick = pick.with_for_update(skip_locked=True)
            seqs = [int(r[0]) for r in conn.execute(pick).all()]
            if not seqs:
                return []
            conn.execute(
                update(t)
                .where(t.c.seq.in_(seqs))
                .where(t.c.sent_at.is_(None))
                .where(free)
                .values(claimed_by=owner, claimed_until=until)
            )
            rows = conn.execute(
                select(t.c.seq, t.c.topic, t.c.envelope)
                .where(t.c.seq.in_(seqs))
                .where(t.c.claimed_by == owner)
                .where(t.c.claimed_until == until)
                .order_by(t.c.seq)
            ).all()
        return [
            OutboxRecord(int(r[0]), r[1], Envelope.from_json(r[2]))
            for r in rows
        ]

    def release(self, seqs: List[int], *, owner: str) -> int:
        """Give *owner*'s leases on *seqs* back (see `SQLiteOutboxStore`)."""
        if not seqs:
            return 0
        t = self.t
        with self.store._tx() as conn:
            return int(
                conn.execute(
                    update(t)
                    .where(t.c.seq.in_([int(s) for s in seqs]))
                    .where(t.c.claimed_by == owner)
                    .values(claimed_by=None, claimed_until=None)
                ).rowcount
                or 0
            )

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
