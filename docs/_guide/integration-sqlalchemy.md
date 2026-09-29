---
title: "SQLAlchemy integration"
description: "StatechartType and StatechartMixin put a statechart on your mapped rows with optimistic locking; SQLAlchemyStore runs the StateStore contract on Postgres, MySQL or SQLite."
---

# SQLAlchemy

SQLAlchemy sits under Flask, FastAPI and most Python services, so the question "where does the statechart live?" usually has the answer "in the database I already have". This extra gives you two answers. You can put the statechart **on your business row**: a snapshot column, queryable state columns, and SQLAlchemy's `version_id_col` as declarative optimistic locking (the Python answer to django-fsm's `ConcurrentTransition`). Or you can use a **key-value store** (`SQLAlchemyStore`) that passes the same contract suite as `SQLiteStore`, so `persisted()`, the idempotency inbox, the audit log and `DueTimerScanner` work unchanged on any database SQLAlchemy supports.

## Install

```bash
pip install "xstate-statemachine[sqlalchemy]"
```

Requires SQLAlchemy `>=2.0`. For the async store, also install an async driver (`aiosqlite`, `asyncpg`, `psycopg[binary]`). Tested versions are in the [compatibility table](#compatibility).

## Quick start

<!-- doc-requires: sqlalchemy -->
```python
from typing import Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.sqlalchemy import (
    StatechartMixin, StatechartType, send_with_retry, xsm_sqlalchemy_ddl)

def add(i, ctx, e, a):
    ctx["items"] += 1

machine = create_machine(
    {"id": "order", "initial": "cart", "context": {"items": 0},
     "states": {"cart": {"on": {"ADD": {"actions": "add"}, "PAY": "paid"}},
                "paid": {"type": "final"}}},
    logic=MachineLogic(actions={"add": add}))

class Base(DeclarativeBase):
    pass

class Order(StatechartMixin, Base):
    __tablename__ = "orders"
    __xsm_machine__ = machine
    __xsm_audit__ = True                          # audit row in the same flush
    id: Mapped[int] = mapped_column(primary_key=True)
    statechart: Mapped[Optional[dict]] = mapped_column(StatechartType, nullable=True)
    __mapper_args__ = StatechartMixin.optimistic()  # version_id_col

engine = create_engine("sqlite:///shop.db")
xsm_sqlalchemy_ddl(Base.metadata).create_all(engine)   # + xsm_deadlines, xsm_transitions ...

with Session(engine) as s:
    order = Order()
    s.add(order)
    order.send("ADD", session=s, actor="alice")
    send_with_retry(order, "PAY", session=s)        # rolls back + retries on ConflictError
    s.commit()
    paid = s.scalars(select(Order).where(Order.in_state("order.paid"))).all()
    assert paid == [order] and order.state == "order.paid"
    assert order.machine.context["items"] == 1
```

## Reference

### `StatechartType(max_snapshot_bytes=1 MiB)`

A `TypeDecorator` over `JSON`, and `JSONB` on Postgres through `with_variant`. `cache_ok = True`. The Python value is the snapshot **dict**, meaning `json.loads(interpreter.get_snapshot())`, or `None`. The size is checked on write **and** on read (X0.4) and raises `SnapshotTooLargeError`. It never hydrates an interpreter itself. `row.machine` does that lazily.

### `StatechartMixin`

Mix it into a declarative model that declares a `statechart` column of type `StatechartType`.

| Class attribute | Meaning |
|:--|:--|
| `__xsm_machine__` | A `MachineNode`, or `(row) -> MachineNode` |
| `__xsm_logic__` | Optional `MachineLogic` or `(row) -> MachineLogic`, applied to a shallow copy of the machine for each send |
| `__xsm_audit__` | `True` writes one `xsm_transitions` row per processed event **in the same flush** (needs `xsm_sqlalchemy_ddl`) |

The mixin adds four columns: `statechart_state` (`String`, indexed; the sorted leaf ids joined with `,`), `statechart_state_ids` (`JSON`; every leaf id, so parallel regions are all listed), `statechart_version` (`Integer`) and `statechart_machine_version` (`String`).

- `StatechartMixin.optimistic()` returns `{"version_id_col": statechart_version}` for `__mapper_args__`. Without it, the listener still increments the version whenever the snapshot changes. It just does not fence the write.
- `.state` is a hybrid property. On an instance it returns the state string. In SQL it is the column.
- `Model.in_state(*ids)` returns a `WHERE` clause that matches rows where any of the ids is active, either as a leaf or as an ancestor of one: `in_state("order.live")` matches `order.live.pay.due`.
- `row.send(event, *, session=None, lock="optimistic", plugins=(), **payload) -> Receipt` restores a `SyncInterpreter` from the snapshot, sends the event, then **flushes** the snapshot, the denormalised columns, the deadline index and the audit rows. The caller commits. A stale `version_id_col` raises `ConflictError`, and the session must then be rolled back. `lock="pessimistic"` first re-selects the row with `FOR UPDATE` (Postgres/MySQL).
- `row.send_with_retry(...)` and the module-level `send_with_retry(row, event, *, session, retries=10, backoff=None, lock=...)` catch `ConflictError`/`LockTimeoutError`, roll back the session, reload the row, back off and try again. ⚠️ **Actions may run once per attempt** (X0.3), so put side effects in services.
- `row.machine` is a restored, not-started `SyncInterpreter`, for reading `.context`, `.can()` and `.value`.
- `Model.statechart_store(session_factory)` returns a `ModelStore`, a `StateStore` view over the rows (key = the primary key as a string). Hand it to `DueTimerScanner` and `after` timers fire for rows nobody touches.
- A `before_insert` / `before_update` mapper listener recomputes the columns from the snapshot on **every** flush, so they stay correct even when code edits `row.statechart` directly.

### `xsm_sqlalchemy_ddl(metadata, *, snapshots_table="xsm_snapshots") -> MetaData`

Adds the extra's tables to your metadata: `xsm_deadlines`, `xsm_transitions`, `xsm_inbox`, `xsm_locks`, `xsm_schema` and the `SQLAlchemyStore` snapshot table. Alembic autogenerate then sees them.

📝 **Alembic.** Every column is a plain SQLAlchemy type, and `StatechartType` renders as `JSON`. Call `xsm_sqlalchemy_ddl(Base.metadata)` in the module your `env.py` imports for `target_metadata` and autogenerate proposes nothing unexpected. A test pins this (`compare_metadata(...) == []`). If you use a custom `render_item`, render `StatechartType` as `sa.JSON()`. It is only a Python-side guard.

### `SQLAlchemyStore(session_factory, *, table="xsm_snapshots", metadata=None, create_tables=True, lock_ttl_s=60, codec=None, max_snapshot_bytes=1 MiB)`

Implements `StateStore`. `session_factory` is a `sessionmaker`.

- `save(..., expected_version=)` is a conditional `UPDATE ... WHERE version = ?`, or an `INSERT` for `0`. A mismatch raises `ConflictError` carrying the real version, and nothing is written.
- `lock(key, timeout=)` is a **lease row** in `xsm_locks`, reclaimed after `lock_ttl_s`. It works on every dialect. Inside the block, every store, inbox and log call on the same thread joins **one** transaction that commits when the block exits. `PessimisticLock` still saves with `expected_version`, so an expired lease produces `ConflictError`, never a lost update.
- `transaction()` gives you the same grouping without a lease.
- `forget(key)` erases the record, its deadlines, its lease and its transition log in one transaction (X0.5).
- `due_keys(until_wall, limit=)` reads the deadline index. `DueTimerScanner` uses it.
- `xsm_schema` stores the layout version. Creation is idempotent, and a **newer** version is refused with `StoreError` (X0.10).

### `AsyncSQLAlchemyStore(async_session_factory, ...)`

Implements `AsyncStateStore` and runs the same statements through `AsyncSession.run_sync`. Use it with `apersisted()`. Tables are created on first use. `lock()` is the same lease, but it does not open a shared transaction.

### `SQLAlchemyInbox(store)` / `SQLAlchemyLog(store)`

`InboxStore` and `TransitionLogStore` in `xsm_inbox` / `xsm_transitions`, sharing the store's per-thread transaction. When used with `PessimisticLock`, the inbox mark and the audit rows commit **with** the snapshot, or not at all (X0.3).

### `ModelStore(session_factory, model)`

Behind `Model.statechart_store()`. Saves are a conditional Core `UPDATE` on `statechart_version`, the same fence the ORM applies. It never creates or deletes rows, and `forget()` erases only the auxiliary rows.

### Transactional outbox — arrives with the EDA core ([#293](https://github.com/basiltt/xstate-statemachine/issues/293))

Part 3 of [#284](https://github.com/basiltt/xstate-statemachine/issues/284) adds an `xsm_outbox` table written in the same transaction as the state change, drained to a `BrokerAdapter` with at-least-once delivery. It depends on the EDA core's `BrokerAdapter` / `OutboxStore` protocols and ships with them. Nothing in this release pretends to publish events.

## Guarantees

> **What this does:** a row's snapshot, its state columns, its deadline index and (with `__xsm_audit__`) its audit rows are written in **one flush**, so a rollback leaves none of them. `version_id_col` makes a concurrent write a `ConflictError`, never a lost update (16 threads × 100 `send_with_retry` on one SQLite row → exactly 1600). The columns always match the snapshot, because a listener recomputes them on every flush. `SQLAlchemyStore` passes the stdlib store contract suite. Under `PessimisticLock` the save, the inbox mark and the audit rows commit together. `forget()` erases every table for a key.
>
> **What this does not do:** it does not give exactly-once effects: a retried send may run its actions again (X0.3). It does not publish events (the outbox arrives with #293). The mixin's `lock="pessimistic"` gives no row lock on SQLite (SQLite serialises writers on its own). It cannot see writes that bypass the ORM *and* the version column.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** whoever holds the database credentials. Stores and models trust the session you give them.
>
> **What it exposes:** snapshots hold `context` in clear text, unless you pass a `codec=` that encrypts (`SQLAlchemyStore`). Audit rows hold the redacted payload (the shared `redact()` denylist, X0.5). `statechart_state` is plain state ids, which is safe to index.
>
> **You must configure:** database credentials and TLS; the tables in your migrations (`xsm_sqlalchemy_ddl`); `StatechartMixin.optimistic()` in `__mapper_args__` if concurrent writers are possible; `max_snapshot_bytes` if contexts can grow; purging of `xsm_transitions` (`SQLAlchemyLog.purge_older_than`) and `xsm_inbox` (`purge_expired`) on a schedule.

## Compatibility

| SQLAlchemy | Database | Python | Tested in CI |
|:--|:--|:--|:--|
| 2.0.x | SQLite (pysqlite, aiosqlite) | 3.9 – 3.14 | ✅ `[sqlalchemy]` cell |
| 2.0.x | PostgreSQL | 3.9 – 3.14 | opt-in: set `DATABASE_URL=postgresql+<driver>://…` (no testcontainers job yet) |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[sqlalchemy]"` | extra not installed | run the command |
| `ConflictError` from `row.send()` | another session changed the row after you loaded it | roll back and retry, or use `send_with_retry` |
| `TypeError: … __xsm_audit__ needs the xsm_transitions table` | audit enabled without the DDL | call `xsm_sqlalchemy_ddl(Base.metadata)` |
| `StoreError: … schema is version N, newer than this library supports` | a newer library wrote this database | upgrade xstate-statemachine |
| Alembic wants to drop `xsm_*` tables | the tables are not on `target_metadata` | call `xsm_sqlalchemy_ddl(Base.metadata)` where `env.py` imports your models |
| `LockTimeoutError` on SQLite under load | many writers on one file | raise the driver `timeout` (`connect_args={"timeout": 30}`) or use Postgres |
