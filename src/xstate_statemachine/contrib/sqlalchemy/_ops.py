# src/xstate_statemachine/contrib/sqlalchemy/_ops.py
# -----------------------------------------------------------------------------
# ⚙️ Statement-level primitives shared by the sync and async stores
# -----------------------------------------------------------------------------
# 🏛️ Every primitive takes a SYNC `Connection`. `SQLAlchemyStore` calls them
#    inside ``session.begin()``; `AsyncSQLAlchemyStore` calls the very same
#    functions through ``AsyncSession.run_sync`` -- so the two stores cannot
#    drift in their locking or conflict semantics.
#
# 🔒 Optimistic writes lead with the WRITE, never with a read: a conditional
#    ``UPDATE ... WHERE key=? AND version=?`` (or an ``INSERT`` for
#    ``expected_version=0``). On SQLite that means the connection takes the
#    RESERVED lock first and waits on ``busy_timeout`` instead of dead-
#    locking a read lock against another writer; on Postgres the row lock
#    is taken by the UPDATE itself. The follow-up ``SELECT`` only shapes the
#    `ConflictError`.
# -----------------------------------------------------------------------------
"""Connection-level store primitives (internal)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.exc import IntegrityError

from ...exceptions import ConflictError
from ...persistence.deadline import Deadline
from ._schema import XsmTables

__all__: List[str] = []

RawRecord = Tuple[str, int, str, float, Sequence[Deadline]]


def _prefix_clause(col: Any, prefix: str) -> Any:
    # 📝 `substr` rather than LIKE: SQLite's LIKE is case-insensitive and
    #    both need escaping; an exact prefix comparison is neither.
    return func.substr(col, 1, len(prefix)) == prefix


def load_raw(conn: Any, t: XsmTables, key: str) -> Optional[RawRecord]:
    s = t.snapshots
    row = conn.execute(
        select(
            s.c.snapshot, s.c.version, s.c.machine_version, s.c.updated_at
        ).where(s.c.key == key)
    ).first()
    if row is None:
        return None
    d = t.deadlines
    deadlines = [
        Deadline(
            state_id=r[0],
            entry_seq=int(r[1]),
            due_at_wall=float(r[2]),
            delay_ms=int(r[3]),
            event_type=r[4],
        )
        for r in conn.execute(
            select(
                d.c.state_id,
                d.c.entry_seq,
                d.c.due_at_wall,
                d.c.delay_ms,
                d.c.event_type,
            )
            .where(d.c.source == s.name, d.c.key == key)
            .order_by(d.c.due_at_wall, d.c.id)
        )
    ]
    return (row[0], int(row[1]), row[2] or "", float(row[3]), deadlines)


def _current_version(conn: Any, t: XsmTables, key: str) -> Optional[int]:
    s = t.snapshots
    row = conn.execute(select(s.c.version).where(s.c.key == key)).first()
    return None if row is None else int(row[0])


def write_deadlines(
    conn: Any,
    t: XsmTables,
    source: str,
    key: str,
    deadlines: Sequence[Deadline],
) -> int:
    """Replace the deadline rows of (*source*, *key*); return how many
    were removed."""
    d = t.deadlines
    removed = conn.execute(
        delete(d).where(d.c.source == source, d.c.key == key)
    ).rowcount
    if deadlines:
        conn.execute(
            insert(d),
            [
                {
                    "source": source,
                    "key": key,
                    "state_id": x.state_id,
                    "entry_seq": int(x.entry_seq),
                    "due_at_wall": float(x.due_at_wall),
                    "delay_ms": int(x.delay_ms),
                    "event_type": x.event_type,
                }
                for x in deadlines
            ],
        )
    return int(removed or 0)


def save_raw(
    conn: Any,
    t: XsmTables,
    key: str,
    data: str,
    expected_version: Optional[int],
    machine_version: str,
    deadlines: Tuple[Deadline, ...],
) -> int:
    s = t.snapshots
    now = time.time()
    values = {
        "snapshot": data,
        "machine_version": machine_version,
        "updated_at": now,
    }
    if expected_version == 0:
        # Create-only. A concurrent creator makes the INSERT fail; the
        # nested transaction keeps the outer one usable on Postgres.
        exists = _current_version(conn, t, key)
        if exists is not None:
            raise ConflictError(key, 0, exists)
        try:
            with conn.begin_nested():
                conn.execute(insert(s).values(key=key, version=1, **values))
        except IntegrityError:
            raise ConflictError(key, 0, _current_version(conn, t, key))
        new_version = 1
    elif expected_version is not None:
        res = conn.execute(
            update(s)
            .where(s.c.key == key, s.c.version == expected_version)
            .values(version=expected_version + 1, **values)
        )
        if res.rowcount != 1:
            raise ConflictError(
                key, expected_version, _current_version(conn, t, key)
            )
        new_version = expected_version + 1
    else:
        res = conn.execute(
            update(s)
            .where(s.c.key == key)
            .values(version=s.c.version + 1, **values)
        )
        if res.rowcount == 1:
            new_version = int(_current_version(conn, t, key) or 1)
        else:
            conn.execute(insert(s).values(key=key, version=1, **values))
            new_version = 1
    write_deadlines(conn, t, s.name, key, deadlines)
    return new_version


def delete_raw(conn: Any, t: XsmTables, key: str) -> bool:
    s = t.snapshots
    n = conn.execute(delete(s).where(s.c.key == key)).rowcount
    write_deadlines(conn, t, s.name, key, ())
    return bool(n)


def forget_raw(conn: Any, t: XsmTables, key: str) -> Dict[str, int]:
    """X0.5: the record, its deadlines, its lock row AND its transition
    log -- in one transaction."""
    s = t.snapshots
    dl = write_deadlines(conn, t, s.name, key, ())
    lk = conn.execute(
        delete(t.locks).where(t.locks.c.source == s.name, t.locks.c.key == key)
    ).rowcount
    tr = conn.execute(
        delete(t.transitions).where(t.transitions.c.machine_id == key)
    ).rowcount
    sn = conn.execute(delete(s).where(s.c.key == key)).rowcount
    return {
        "snapshots": int(sn or 0),
        "deadlines": int(dl),
        "locks": int(lk or 0),
        "log_entries": int(tr or 0),
    }


def list_keys_raw(
    conn: Any, t: XsmTables, prefix: str, limit: int
) -> List[str]:
    s = t.snapshots
    q = select(s.c.key)
    if prefix:
        q = q.where(_prefix_clause(s.c.key, prefix))
    rows = conn.execute(q.order_by(s.c.key).limit(limit)).all()
    return [r[0] for r in rows]


def due_keys_raw(
    conn: Any, t: XsmTables, source: str, until_wall: float, limit: int
) -> List[Tuple[str, float]]:
    d = t.deadlines
    rows = conn.execute(
        select(d.c.key, func.min(d.c.due_at_wall))
        .where(d.c.source == source, d.c.due_at_wall <= until_wall)
        .group_by(d.c.key)
        .order_by(func.min(d.c.due_at_wall))
        .limit(limit)
    ).all()
    return [(str(r[0]), float(r[1])) for r in rows]


def try_lock(
    conn: Any, t: XsmTables, source: str, key: str, owner: str, ttl: float
) -> bool:
    """One attempt at the lease row. Expired leases are reclaimed."""
    lk = t.locks
    now = time.time()
    conn.execute(
        delete(lk).where(
            lk.c.source == source, lk.c.key == key, lk.c.expires_at < now
        )
    )
    try:
        with conn.begin_nested():
            conn.execute(
                insert(lk).values(
                    source=source, key=key, owner=owner, expires_at=now + ttl
                )
            )
    except IntegrityError:
        return False
    return True


def unlock(conn: Any, t: XsmTables, source: str, key: str, owner: str) -> None:
    lk = t.locks
    conn.execute(
        delete(lk).where(
            lk.c.source == source, lk.c.key == key, lk.c.owner == owner
        )
    )
