# src/xstate_statemachine/contrib/sqlalchemy/_schema.py
# -----------------------------------------------------------------------------
# 🗄️ The [sqlalchemy] tables, the schema-version row, and the DDL helper
# -----------------------------------------------------------------------------
# 🏛️ Every table the extra owns is built here, once, as plain Core `Table`
#    objects -- so `SQLAlchemyStore`, the inbox, the log, the mixin's
#    deadline rows and Alembic autogenerate all see the SAME definitions.
#    Only the snapshot table's name is configurable; the auxiliary tables
#    (`xsm_deadlines`, `xsm_locks`, `xsm_inbox`, `xsm_transitions`,
#    `xsm_schema`) are shared and carry a `source` column where two owners
#    (a store and a mapped model) could otherwise collide.
#
# 🔐 X0.10: `xsm_schema` records the layout version per component; upgrades
#    are explicit steps; a NEWER version is refused with an upgrade message,
#    never guessed at.
# -----------------------------------------------------------------------------
"""Table definitions, schema versioning and `xsm_sqlalchemy_ddl`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    insert,
    select,
    update,
)

from ...exceptions import StoreError

__all__ = [
    "SCHEMA_VERSION",
    "XsmTables",
    "build_tables",
    "ensure_schema",
    "xsm_sqlalchemy_ddl",
]

#: Bump with an entry in `_UPGRADES`. Never edit an existing step.
SCHEMA_VERSION = 1
_COMPONENT = "sqlalchemy"
#: schema_version -> callables ``(connection, tables)`` that bring it to +1.
_UPGRADES: Dict[int, Tuple[Any, ...]] = {}

DEFAULT_TABLE = "xsm_snapshots"


@dataclass(frozen=True)
class XsmTables:
    """The tables one store (or `xsm_sqlalchemy_ddl`) works with."""

    metadata: MetaData
    snapshots: Table
    deadlines: Table
    locks: Table
    inbox: Table
    transitions: Table
    schema: Table

    def all(self) -> Tuple[Table, ...]:
        return (
            self.schema,
            self.snapshots,
            self.deadlines,
            self.locks,
            self.inbox,
            self.transitions,
        )


def build_tables(
    metadata: MetaData, snapshots: str = DEFAULT_TABLE
) -> XsmTables:
    """Define (or reuse) the extra's tables on *metadata*."""

    def table(name: str, *cols: Any) -> Table:
        existing = metadata.tables.get(name)
        if existing is not None:
            return existing
        return Table(name, metadata, *cols)

    snap = table(
        snapshots,
        Column("key", String(200), primary_key=True),
        Column("snapshot", Text, nullable=False),
        Column("version", Integer, nullable=False),
        Column("machine_version", String(255), nullable=False, default=""),
        Column("updated_at", Float, nullable=False),
    )
    deadlines = table(
        "xsm_deadlines",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("source", String(255), nullable=False),
        Column("key", String(200), nullable=False),
        Column("state_id", String(512), nullable=False),
        Column("entry_seq", Integer, nullable=False),
        Column("due_at_wall", Float, nullable=False),
        Column("delay_ms", BigInteger, nullable=False),
        Column("event_type", String(512), nullable=False),
        Index("xsm_deadlines_due", "due_at_wall"),
        Index("xsm_deadlines_key", "source", "key"),
    )
    locks = table(
        "xsm_locks",
        Column("source", String(255), primary_key=True),
        Column("key", String(200), primary_key=True),
        Column("owner", String(64), nullable=False),
        Column("expires_at", Float, nullable=False),
    )
    inbox = table(
        "xsm_inbox",
        Column("scope", String(400), primary_key=True),
        Column("key", String(255), primary_key=True),
        Column("fingerprint", String(128), nullable=False),
        Column("receipt", Text, nullable=True),
        Column("expires_at", Float, nullable=True),
        Index("xsm_inbox_exp", "expires_at"),
    )
    transitions = table(
        "xsm_transitions",
        Column("machine_id", String(255), primary_key=True),
        Column("seq", Integer, primary_key=True, autoincrement=False),
        Column("ts", Float, nullable=False),
        Column("record", Text, nullable=False),
        Index("xsm_transitions_ts", "ts"),
    )
    schema = table(
        "xsm_schema",
        Column("component", String(64), primary_key=True),
        Column("version", Integer, nullable=False),
    )
    return XsmTables(
        metadata, snap, deadlines, locks, inbox, transitions, schema
    )


def xsm_sqlalchemy_ddl(
    metadata: MetaData, *, snapshots_table: str = DEFAULT_TABLE
) -> MetaData:
    """Add the extra's tables to *metadata* and return it.

    Call it on your declarative ``Base.metadata`` so Alembic autogenerate
    sees ``xsm_deadlines`` / ``xsm_transitions`` / ``xsm_inbox`` /
    ``xsm_locks`` / ``xsm_schema`` (and the `SQLAlchemyStore` snapshot
    table) and does not propose dropping them::

        xsm_sqlalchemy_ddl(Base.metadata).create_all(engine)
    """
    build_tables(metadata, snapshots_table)
    return metadata


def ensure_schema(connection: Any, tables: XsmTables) -> int:
    """Create missing tables, record / upgrade the schema version.

    Idempotent. Raises `StoreError` when the database was written by a
    NEWER release (X0.10).
    """
    tables.metadata.create_all(connection, tables=list(tables.all()))
    sc = tables.schema
    row = connection.execute(
        select(sc.c.version).where(sc.c.component == _COMPONENT)
    ).first()
    if row is None:
        connection.execute(
            insert(sc).values(component=_COMPONENT, version=SCHEMA_VERSION)
        )
        return SCHEMA_VERSION
    current = int(row[0])
    if current > SCHEMA_VERSION:
        raise StoreError(
            f"xstate-statemachine [sqlalchemy] schema is version {current}, "
            f"newer than this library supports ({SCHEMA_VERSION}). Upgrade "
            f"xstate-statemachine."
        )
    while current < SCHEMA_VERSION:  # pragma: no cover - no upgrades yet
        for step in _UPGRADES[current]:
            step(connection, tables)
        current += 1
        connection.execute(
            update(sc)
            .where(sc.c.component == _COMPONENT)
            .values(version=current)
        )
    return current
