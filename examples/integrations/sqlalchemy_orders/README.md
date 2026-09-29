# SQLAlchemy orders — a statechart on your ORM row

An order lifecycle on SQLAlchemy 2.0, built on `xstate-statemachine[sqlalchemy]`,
in two variants that share one chart and one database:

- **sync** (`sync_app.py`): the statechart lives **on the `orders` row**
  (`StatechartMixin`), with optimistic locking via `version_id_col`.
- **async** (`async_app.py`): `AsyncSQLAlchemyStore` + `apersisted()` on
  aiosqlite, for services that run on asyncio.

```
cart ──CHECKOUT (hasItems)──▶ awaitingPayment ──PAY──▶ paid ──SHIP──▶ shipped
  │                              │  after 15 min ─▶ expired
  └──CANCEL──▶ cancelled ◀──CANCEL┘
```

| File | What it is |
|:--|:--|
| `machine.json` | The chart. Passes `xsm validate --plain`. |
| `logic.py` | Actions and the `hasItems` guard; builds the machine with `strict_config=True`. |
| `models.py` | `Order(StatechartMixin, Base)` with `StatechartMixin.optimistic()` and `__xsm_audit__ = True`; `xsm_sqlalchemy_ddl(Base.metadata)`. |
| `sync_app.py` | `create_order`, `send` (via `send_with_retry`), `orders_in` (`Order.in_state`), the `DueTimerScanner`, and a small CLI. |
| `async_app.py` | The same lifecycle through `AsyncSQLAlchemyStore`. |
| `alembic.ini`, `migrations/` | An Alembic environment and the **generated** migration `0001` for `orders` plus every `xsm_*` table. |
| `tests/` | Plain pytest on a temp SQLite file. |

## Run it

```bash
pip install "xstate-statemachine[sqlalchemy]" "sqlalchemy[asyncio]" aiosqlite alembic
cd examples/integrations/sqlalchemy_orders
alembic upgrade head                        # creates orders.db
python sync_app.py demo                     # two orders: one paid, one waiting
python sync_app.py scan --at-offset 901     # pretend 15 min passed: "woke 1 order(s)"
python async_app.py                         # the async variant, same file
alembic check                               # "No new upgrade operations detected."
python -m pytest tests -q
```

`ORDERS_DB_URL` (sync and Alembic) and `ORDERS_DB_PATH` (async) point the
example at another database. `python sync_app.py init` creates the tables
with `create_all` if you want to skip Alembic.

## What to look at

**The row is the state.** `order.send("PAY", session=s)` restores a
`SyncInterpreter` from the `statechart` column, applies the event and
*flushes* four things together: the snapshot, the queryable
`statechart_state` column, the deadline index row for the `after` timer, and
(because of `__xsm_audit__`) an `xsm_transitions` audit row. You commit.
Roll back and none of them happened. `Order.in_state("order.awaitingPayment")`
is a plain SQL `WHERE`, so a dashboard query never parses a snapshot.

**Concurrent writers.** `StatechartMixin.optimistic()` turns the
`statechart_version` column into SQLAlchemy's `version_id_col`. Two sessions
that load the same row both try to write version *n + 1*, and the loser gets
`ConflictError`. `send_with_retry` rolls back, reloads and re-applies. The
test `test_concurrent_writers_lose_no_update` runs four threads against one
order and checks every increment landed. ⚠️ A retried send runs its actions
again, which is why `logic.py` only touches `context`.

**Timers without a live process.** The 15-minute payment window is an
`after` in the chart. Nobody keeps the order in memory, so the deadline is
written to `xsm_deadlines` with the row. `sync_app.scanner()` is
`DueTimerScanner(Order.statechart_store(sessionmaker(engine)), ...)`. Run
**exactly one** scanner process (`run_forever()` in production); it wakes
the orders whose deadline has passed and moves them to `expired`. The async
variant writes the same index, so the sync `SQLAlchemyStore` scanner serves
it too.

**Migrations.** `migrations/env.py` imports `models.Base.metadata`, which
`xsm_sqlalchemy_ddl` has extended with the extra's tables, and renders
`StatechartType` as plain `sa.JSON()` (the size cap is a Python-side guard).
The test `test_upgrade_head_then_autogenerate_sees_no_diff` runs
`alembic upgrade head` on a temp file and asserts autogenerate proposes
nothing.

## Not in this example yet

- **Transactional outbox.** Publishing an event in the same transaction as
  the state change (`xsm_outbox`, drained to a broker) ships with the EDA
  core, [#293](https://github.com/basiltt/xstate-statemachine/issues/293).
  This example publishes nothing and does not pretend to.
- **Postgres.** The code is dialect-neutral; point `ORDERS_DB_URL` at
  `postgresql+psycopg://...` and use `lock="pessimistic"` if you want
  `SELECT ... FOR UPDATE`.

See the [SQLAlchemy integration guide](../../../docs/_guide/integration-sqlalchemy.md).
