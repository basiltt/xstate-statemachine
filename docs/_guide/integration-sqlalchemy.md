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

For a complete, runnable service -- `StatechartMixin` on an orders table, optimistic `send_with_retry`, the transactional outbox, an Alembic migration and a test suite -- see the [`sqlalchemy_orders` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/sqlalchemy_orders).

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

A `TypeDecorator` over `JSON`, and `JSONB` on Postgres through `with_variant`. `cache_ok = True`. The Python value is the snapshot **dict**, meaning `json.loads(interpreter.get_snapshot())`, or `None`. The size is checked on write **and** on read (X0.4) and raises `SnapshotTooLargeError` (the same class, unwrapped, that `SQLAlchemyStore` raises). A stored value that is not a JSON object is `SnapshotCorruptError`; writing anything but a dict or `None` is `TypeError`. A `NULL` column means "never sent": `.state` is `None`, `in_state()` matches nothing, and the first `send()` starts from the initial state. Context values that are not JSON (`datetime`, `Decimal`, `set`) are stored as their `str()`, exactly as `get_snapshot()` does everywhere, so convert them in your actions if you need them back. It never hydrates an interpreter itself. `row.machine` does that lazily.

### `StatechartMixin`

Mix it into a declarative model that declares a `statechart` column of type `StatechartType`.

| Class attribute | Meaning |
|:--|:--|
| `__xsm_machine__` | A `MachineNode`, or `(row) -> MachineNode` |
| `__xsm_logic__` | Optional `MachineLogic` or `(row) -> MachineLogic`, applied to a shallow copy of the machine for each send |
| `__xsm_audit__` | `True` writes one `xsm_transitions` row per processed event **in the same flush** (needs `xsm_sqlalchemy_ddl`) |

The mixin adds four columns: `statechart_state` (`Text`, indexed -- it was `String(512)` before 0.11.0, which Postgres truncated with an error on wide parallel charts; existing schemas need an `ALTER COLUMN ... TYPE TEXT` migration; the sorted leaf ids joined with `,`), `statechart_state_ids` (`JSON`; every leaf id, so parallel regions are all listed), `statechart_version` (`Integer`) and `statechart_machine_version` (`String`).

- `StatechartMixin.optimistic()` returns `{"version_id_col": statechart_version}` for `__mapper_args__`. Without it, the listener still increments the version whenever the snapshot changes. It just does not fence the write.
- `.state` is a hybrid property. On an instance it returns the state string. In SQL it is the column.
- `Model.in_state(*ids)` returns a `WHERE` clause that matches rows where any of the ids is active, either as a leaf or as an ancestor of one: `in_state("order.live")` matches `order.live.pay.due`. Ids match literally: `_` and `%` (legal in XState ids) are escaped, never `LIKE` wildcards, on every dialect.
- `row.send(event, *, session=None, lock="optimistic", plugins=(), **payload) -> Receipt` restores a `SyncInterpreter` from the snapshot, sends the event, then **flushes** the snapshot, the denormalised columns, the deadline index and the audit rows. The caller commits. A stale `version_id_col` raises `ConflictError`, and the session must then be rolled back. `lock="pessimistic"` first re-selects the row with `FOR UPDATE` (Postgres/MySQL).
- `row.send_with_retry(...)` and the module-level `send_with_retry(row, event, *, session, retries=10, backoff=None, lock=...)` catch `ConflictError`/`LockTimeoutError`, roll back the session, reload the row, back off and try again. ⚠️ **Actions may run once per attempt** (X0.3), so put side effects in services.
- `plugins=` sinks that live in a `SQLAlchemyStore` (`SQLAlchemyOutboxStore`, `SQLAlchemyInbox`, `SQLAlchemyLog`) are bound to the row's session for the send, so their rows commit or roll back **with** the row. Two refusals keep that honest: a send inside an open `store.transaction()` on the same thread is a `RuntimeError` (its rows would have landed in the wrong transaction), and a plugin store whose engine points at a **different database** than the row's session is a `ValueError`.
- On Postgres / MySQL a lock timeout, deadlock or serialization failure (SQLSTATE `55P03`, `40P01`, `40001`) from `send()` -- including the `FOR UPDATE` refresh of `lock="pessimistic"` -- is a `LockTimeoutError`, so `send_with_retry` retries it. Set Postgres `lock_timeout` **per connection** (`connect_args={"options": "-c lock_timeout=2000"}`): a `SET` inside the transaction is undone by the retry's rollback and the next attempt waits forever.
- `row.machine` is a restored, not-started `SyncInterpreter`, for reading `.context`, `.can()` and `.value`.
- `Model.statechart_store(session_factory)` returns a `ModelStore`, a `StateStore` view over the rows (key = the primary key as a string). Hand it to `DueTimerScanner` and `after` timers fire for rows nobody touches.
- A `before_insert` / `before_update` mapper listener recomputes the columns from the snapshot on **every** flush, so they stay correct even when code edits `row.statechart` directly.

### `xsm_sqlalchemy_ddl(metadata, *, snapshots_table="xsm_snapshots") -> MetaData`

Adds the extra's tables to your metadata: `xsm_deadlines`, `xsm_transitions`, `xsm_inbox`, `xsm_locks`, `xsm_schema`, `xsm_outbox` and the `SQLAlchemyStore` snapshot table. Alembic autogenerate then sees them, and does not propose dropping the outbox that `SQLAlchemyOutboxStore` created.

📝 **Alembic.** Call `xsm_sqlalchemy_ddl(Base.metadata)` in the module your `env.py` imports for `target_metadata`, and pass the library's `render_item` hook so `StatechartType` is written as `sa.JSON().with_variant(postgresql.JSONB(), "postgresql")`, the DDL `create_all` emits. A migration generated on SQLite then creates `JSONB` on Postgres:

<!-- doc-requires: sqlalchemy -->
```python
# migrations/env.py (excerpt)
from xstate_statemachine.contrib.sqlalchemy import render_statechart_type

def configure(context, connection, target_metadata):
    context.configure(connection=connection, target_metadata=target_metadata,
                      render_item=render_statechart_type)
```

`render_statechart_type(type_, obj, autogen_context)` returns that string for a `StatechartType` and `False` for everything else (Alembic's default rendering), adding the `postgresql` import to the migration. `StatechartType.compare_against_backend` tells autogenerate that a `JSONB` (Postgres) or `JSON` column is this type, so there is no `modify_type` diff. Tests pin `compare_metadata(...) == []` after `alembic upgrade head` on SQLite **and** Postgres, plus a second migration autogenerated on top that contains only the team's `add_column`. The size cap is a Python-side guard, not a database type.

### `SQLAlchemyStore(session_factory, *, table="xsm_snapshots", metadata=None, create_tables=True, lock_ttl_s=60, codec=None, max_snapshot_bytes=1 MiB)`

Implements `StateStore`. `session_factory` is a `sessionmaker`.

- `save(..., expected_version=)` is a conditional `UPDATE ... WHERE version = ?`, or an `INSERT` for `0`. A mismatch raises `ConflictError` carrying the real version, and nothing is written.
- `lock(key, timeout=)` is a **lease row** in `xsm_locks`, reclaimed after `lock_ttl_s`. It works on every dialect. Inside the block, every store, inbox and log call on the same thread joins **one** transaction that commits when the block exits. `PessimisticLock` still saves with `expected_version`, so an expired lease produces `ConflictError`, never a lost update.
- `transaction()` gives you the same grouping without a lease.
- `forget(key)` erases the record, its deadlines, its lease and its transition log in one transaction (X0.5).
- `due_keys(until_wall, limit=)` reads the deadline index. `DueTimerScanner` uses it.
- `xsm_schema` stores the layout version. Creation is idempotent, and a **newer** version is refused with `StoreError` (X0.10), with `create_tables=True` or `False`.

### `AsyncSQLAlchemyStore(async_session_factory, ...)`

Implements `AsyncStateStore` and runs the same statements through `AsyncSession.run_sync`. Use it with `apersisted()`. Tables are created on first use. `lock()` is the same lease, but it does not open a shared transaction -- so with the async store the outbox, inbox and audit writes of a plugin run **right after** the save on their own connection, not atomically with it. A block that raises before the save still leaves no outbox row (the rows are buffered until the save); a crash between the save and the plugin flush loses them. For the one-transaction guarantee use the sync `StatechartMixin.send(plugins=...)` or `SQLAlchemyStore` under `PessimisticLock`.

### `SQLAlchemyInbox(store)` / `SQLAlchemyLog(store)`

`InboxStore` and `TransitionLogStore` in `xsm_inbox` / `xsm_transitions`, sharing the store's per-thread transaction. When used with `PessimisticLock`, the inbox mark and the audit rows commit **with** the snapshot, or not at all (X0.3).

### `ModelStore(session_factory, model)`

Behind `Model.statechart_store()`. Saves are a conditional Core `UPDATE` on `statechart_version`, the same fence the ORM applies. It never creates or deletes rows, and `forget()` erases only the auxiliary rows.

### `SQLAlchemyOutboxStore(store, *, create_table=True)`

The EDA core's `OutboxStore` ([#293](https://github.com/basiltt/xstate-statemachine/issues/293); see the [EDA guide](../integration-eda/)) in the `xsm_outbox` table of a `SQLAlchemyStore`. Pass `OutboxPlugin(SQLAlchemyOutboxStore(store))` to `row.send(..., plugins=[...])` or `send_with_retry`: the plugin's rows are written on the **caller's session connection**, so the event commits with the state change or not at all. `OutboxRelay(outbox, broker).relay_once_sync()` drains it.

<!-- doc-requires: sqlalchemy -->
```python
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from xstate_statemachine import create_machine
from xstate_statemachine.contrib.sqlalchemy import (
    SQLAlchemyOutboxStore, SQLAlchemyStore, StatechartMixin, StatechartType, xsm_sqlalchemy_ddl)
from xstate_statemachine.eda import OutboxPlugin, OutboxRelay, SyncFakeBrokerAdapter

chart = create_machine({"id": "inv", "initial": "open", "context": {"n": 7},
    "states": {"open": {"on": {"PAY": {"target": "paid",
                                       "meta": {"publish": {"type": "invoice.paid", "data": ["n"]}}}}},
               "paid": {}}})

class Base(DeclarativeBase):
    pass

class Invoice(StatechartMixin, Base):
    __tablename__ = "invoices"
    __xsm_machine__ = chart
    id: Mapped[int] = mapped_column(primary_key=True)
    statechart: Mapped[Optional[dict]] = mapped_column(StatechartType, nullable=True)
    __mapper_args__ = StatechartMixin.optimistic()

engine = create_engine("sqlite://")
xsm_sqlalchemy_ddl(Base.metadata).create_all(engine)       # includes xsm_outbox
outbox = SQLAlchemyOutboxStore(SQLAlchemyStore(sessionmaker(engine), metadata=Base.metadata))
plugin = OutboxPlugin(outbox, topic="billing")

with Session(engine) as s:                                  # rolled back: no event
    inv = Invoice(); s.add(inv); s.flush()
    inv.send("PAY", session=s, plugins=[plugin])
    s.rollback()
assert outbox.count() == 0

with Session(engine) as s:                                  # committed: one event
    inv = Invoice(); s.add(inv); s.flush()
    inv.send("PAY", session=s, plugins=[plugin])
    s.commit()
broker = SyncFakeBrokerAdapter()
assert OutboxRelay(outbox, broker).relay_once_sync() == 1
[d] = list(broker.subscribe("billing", timeout=0))
assert d.envelope.type == "invoice.paid" and d.envelope.data == {"n": 7}
```

The relay marks a row sent only **after** the broker accepted it. A crash in between re-publishes that row with the **same envelope id** (at-least-once), so consumers dedup on `envelope.id`. Several relays (one per replica) may drain one outbox: `claim()` leases rows through the `claimed_by` / `claimed_until` columns ([leases](../integration-eda/#several-relays-on-one-outbox-leases)).

> ⚠️ **Upgrading from 0.11.0:** an `xsm_outbox` table created before the relay leases lacks `claimed_by VARCHAR(128) NULL` and `claimed_until FLOAT NULL`. `create_all` does not alter existing tables, so add an Alembic migration (the example's `migrations/versions/0003_xsm_outbox_relay_lease.py` is one). `SQLiteOutboxStore` adds the columns itself. The [`sqlalchemy_orders` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/sqlalchemy_orders) runs it end to end (`python sync_app.py relay`).

## Guarantees

> **What this does:** a row's snapshot, its state columns, its deadline index and (with `__xsm_audit__`) its audit rows are written in **one flush**, so a rollback leaves none of them. `version_id_col` makes a concurrent write a `ConflictError`, never a lost update (16 threads × 100 `send_with_retry` on one SQLite row → exactly 1600). The columns always match the snapshot, because a listener recomputes them on every flush. `SQLAlchemyStore` passes the stdlib store contract suite. Under `PessimisticLock` the save, the inbox mark and the audit rows commit together. `forget()` erases every table for a key. With `OutboxPlugin(SQLAlchemyOutboxStore(...))` passed to `row.send()`, the outbox row commits **with** the row (one transaction, X0.3), and `OutboxRelay` delivers it **at least once**: a row is marked sent only after the broker accepted it, a crash in between re-sends the same envelope id, and consumers dedup on it.
>
> **What this does not do:** it does not give exactly-once effects: a retried send may run its actions again (X0.3). The mixin's `lock="pessimistic"` gives no row lock on SQLite (SQLite serialises writers on its own). It cannot see writes that bypass the ORM *and* the version column.
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
| 2.0.x | PostgreSQL 16 (psycopg 3) | 3.9 – 3.14 | opt-in: `DATABASE_URL=postgresql+<driver>://…`, or `XSM_CONTAINERS=1` for a throwaway testcontainer (no CI job yet) |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[sqlalchemy]"` | extra not installed | run the command |
| `ConflictError` from `row.send()` | another session changed the row after you loaded it | roll back and retry, or use `send_with_retry` |
| `TypeError: … __xsm_audit__ needs the xsm_transitions table` | audit enabled without the DDL | call `xsm_sqlalchemy_ddl(Base.metadata)` |
| `StoreError: … schema is version N, newer than this library supports` | a newer library wrote this database | upgrade xstate-statemachine |
| Alembic wants to drop `xsm_*` tables (incl. `xsm_outbox`) | the tables are not on `target_metadata` | call `xsm_sqlalchemy_ddl(Base.metadata)` where `env.py` imports your models |
| Alembic proposes `modify_type` on `statechart` (Postgres), or a migration made on SQLite created `json`, not `jsonb` | `render_item` rendered `sa.JSON()` | use `render_item=render_statechart_type` |
| `SnapshotCorruptError` loading a row | the `statechart` column holds invalid JSON or a non-object | repair it, or set it to `NULL` (= never sent) |
| `RuntimeError: ... already bound to another transaction` from `row.send(plugins=...)` | the send ran inside `store.transaction()` on the same thread | send outside the store transaction (the row's session is the transaction) |
| `ValueError: ... different database` from `row.send(plugins=...)` | the plugin's `SQLAlchemyStore` engine is not the row's database | build the store on the same engine as the session |
| `StoreError: ... tables are missing ... run your migrations` | `create_tables=False` on a database without the `xsm_*` tables | run your Alembic migrations (with `xsm_sqlalchemy_ddl` on `target_metadata`) |
| `LockTimeoutError` on SQLite under load | many writers on one file | raise the driver `timeout` (`connect_args={"timeout": 30}`) or use Postgres |
