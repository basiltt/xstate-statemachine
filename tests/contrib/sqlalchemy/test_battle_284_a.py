# tests/contrib/sqlalchemy/test_battle_284_a.py
"""#284 battle, adversary A: transactions, concurrency, parity, lifecycle.

Defects (each test failed before its fix):

* an `IdempotencyPlugin(SQLAlchemyInbox)` passed to ``row.send(plugins=)``
  committed its inbox mark on its OWN connection: the caller rolled the
  row back, the redelivery was answered ``duplicate=True`` and the event's
  effect was lost for good (`_joined` only looked at ``plugin.sink``);
* ``bound_to`` silently joined whatever transaction the thread already
  had open (``store.transaction()``), so the plugin rows committed with
  THAT transaction and not with the row's session;
* a plugin store on a DIFFERENT database than the row was bound to the
  row's connection without a word;
* on Postgres a ``lock_timeout`` / deadlock on ``lock="pessimistic"``
  leaked as a raw `OperationalError` (only SQLite's "locked"/"busy" were
  mapped), so `send_with_retry` did not retry it.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pytest

from ..conftest import requires_extra

pytestmark = [requires_extra("sqlalchemy"), pytest.mark.timeout(600)]
pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.exc import OperationalError  # noqa: E402
from sqlalchemy.orm import (  # noqa: E402
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from src.xstate_statemachine import create_machine  # noqa: E402

from src.xstate_statemachine.contrib.sqlalchemy import (  # noqa: E402
    SQLAlchemyInbox,
    SQLAlchemyOutboxStore,
    SQLAlchemyStore,
    StatechartMixin,
    StatechartType,
    send_with_retry,
)
from src.xstate_statemachine.contrib.sqlalchemy.mixin import (  # noqa: E402
    state_string,
)
from src.xstate_statemachine.contrib.sqlalchemy.store import (  # noqa: E402
    _is_locked,
)
from src.xstate_statemachine.eda import OutboxPlugin  # noqa: E402
from src.xstate_statemachine.exceptions import (  # noqa: E402
    ConflictError,
    LockTimeoutError,
    SnapshotTooLargeError,
)
from src.xstate_statemachine.persistence import DueTimerScanner  # noqa: E402
from src.xstate_statemachine.persistence.idempotency import (  # noqa: E402
    IdempotencyPlugin,
)

from .test_battle_284_scenario import (  # noqa: E402
    DEADLINES,
    Base,
    Order,
    _new_order,
    _pg_url,
    _send,
    pg_container_url,
)

__all__ = ["pg_container_url"]  # the fixture, re-exported for pytest


@pytest.fixture(params=["sqlite", "postgres"])
def engine(request: Any, tmp_path: Path, pg_container_url: Any) -> Iterator:
    if request.param == "sqlite":
        eng = create_engine(
            f"sqlite:///{(tmp_path / 'a.db').as_posix()}",
            connect_args={"timeout": 30},
        )
    else:
        url = _pg_url() or pg_container_url
        if not url:
            pytest.skip("no Postgres: set DATABASE_URL or XSM_CONTAINERS=1")
        eng = create_engine(url, pool_size=10, max_overflow=20)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


@pytest.fixture
def pg(engine: Any) -> Any:
    if engine.dialect.name != "postgresql":
        pytest.skip("Postgres-only")
    return engine


def _store(eng: Any) -> SQLAlchemyStore:
    return SQLAlchemyStore(sessionmaker(eng), metadata=Base.metadata)


def _checked_out(eng: Any) -> int:
    return int(eng.pool.checkedout())


def _ready_to_pay(eng: Any) -> int:
    oid = _new_order(eng)
    _send(eng, oid, "ADD_ITEM", price_cents=3)
    _send(eng, oid, "CHECKOUT")
    return oid


# -----------------------------------------------------------------------------
# 1. bound_to / _joined
# -----------------------------------------------------------------------------
def test_inbox_mark_rolls_back_with_the_row(engine: Any) -> None:
    inbox = SQLAlchemyInbox(_store(engine))
    plugin = IdempotencyPlugin(inbox, principal=lambda e: "sys")
    oid = _new_order(engine)
    with Session(engine) as s:
        s.get(Order, oid).send(
            "ADD_ITEM",
            session=s,
            plugins=[plugin],
            price_cents=1,
            idempotency_key="k1",
        )
        s.rollback()
    with Session(engine) as s:
        n = s.execute(select(func.count()).select_from(inbox.t)).scalar_one()
        assert n == 0, "the inbox mark survived the row's rollback"
    # the redelivery is NOT a duplicate: its effect was never stored
    with Session(engine) as s:
        r = s.get(Order, oid).send(
            "ADD_ITEM",
            session=s,
            plugins=[plugin],
            price_cents=1,
            idempotency_key="k1",
        )
        s.commit()
    assert not r.duplicate
    with Session(engine) as s:
        assert s.get(Order, oid).machine.context["items"] == 1
    # ... and a redelivery AFTER the commit is one
    with Session(engine) as s:
        r = s.get(Order, oid).send(
            "ADD_ITEM",
            session=s,
            plugins=[plugin],
            price_cents=1,
            idempotency_key="k1",
        )
        s.commit()
    assert r.duplicate
    assert _checked_out(engine) == 0


def test_send_inside_store_transaction_is_refused(engine: Any) -> None:
    store = _store(engine)
    plugin = OutboxPlugin(SQLAlchemyOutboxStore(store), topic="o")
    oid = _ready_to_pay(engine)
    with store.transaction():
        with Session(engine) as s:
            with pytest.raises(RuntimeError, match="already bound"):
                s.get(Order, oid).send("PAY", session=s, plugins=[plugin])
            s.rollback()
    # nothing leaked on either side; the binding is clean afterwards
    assert getattr(store._local, "conn", None) is None
    assert SQLAlchemyOutboxStore(store).count() == 0
    with Session(engine) as s:
        s.get(Order, oid).send("PAY", session=s, plugins=[plugin])
        s.commit()
    assert SQLAlchemyOutboxStore(store).count() == 1


def test_same_connection_rebinding_is_reentrant(engine: Any) -> None:
    store = _store(engine)
    with Session(engine) as s:
        conn = s.connection()
        with store.bound_to(conn):
            with store.bound_to(conn) as inner:
                assert inner is conn
            assert store._local.conn is conn
        assert store._local.conn is None


def test_binding_cleared_when_send_raises(engine: Any) -> None:
    store = _store(engine)
    plugin = OutboxPlugin(SQLAlchemyOutboxStore(store), topic="o")
    oid = _ready_to_pay(engine)
    with Session(engine) as s:
        row = s.get(Order, oid)

        def boom(*a: Any, **k: Any) -> None:
            raise RuntimeError("flush failed")

        row._xsm_write_aux = boom  # type: ignore[method-assign]
        with pytest.raises(RuntimeError, match="flush failed"):
            row.send("PAY", session=s, plugins=[plugin])
        s.rollback()
    assert getattr(store._local, "conn", None) is None


def test_plugin_store_on_another_database_is_refused(
    engine: Any, tmp_path: Path
) -> None:
    other = create_engine(f"sqlite:///{(tmp_path / 'other.db').as_posix()}")
    try:
        plugin = OutboxPlugin(
            SQLAlchemyOutboxStore(SQLAlchemyStore(sessionmaker(other))),
            topic="o",
        )
        oid = _ready_to_pay(engine)
        with Session(engine) as s:
            with pytest.raises(ValueError, match="same database"):
                s.get(Order, oid).send("PAY", session=s, plugins=[plugin])
            s.rollback()
        with Session(engine) as s:
            assert s.get(Order, oid).state == "order.awaitingPayment"
    finally:
        other.dispose()


def test_one_plugin_shared_by_threads_each_row_own_tx(engine: Any) -> None:
    store = _store(engine)
    outbox = SQLAlchemyOutboxStore(store)
    plugin = OutboxPlugin(outbox, topic="o")
    ids = [_ready_to_pay(engine) for _ in range(12)]
    errors: List[BaseException] = []

    def pay(oid: int) -> None:
        try:
            with Session(engine) as s:
                s.get(Order, oid).send("PAY", session=s, plugins=[plugin])
                if oid % 2:
                    s.commit()
                else:
                    s.rollback()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ts = [threading.Thread(target=pay, args=(i,)) for i in ids]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert errors == [], errors[:2]
    committed = sorted(i for i in ids if i % 2)
    assert outbox.count() == len(committed)


# -----------------------------------------------------------------------------
# 2. optimistic vs pessimistic on Postgres
# -----------------------------------------------------------------------------
def test_pessimistic_fleet_never_conflicts(pg: Any) -> None:
    oid = _new_order(pg)
    errors: List[BaseException] = []

    def w() -> None:
        try:
            for _ in range(25):
                with Session(pg) as s:
                    s.get(Order, oid).send(
                        "ADD_ITEM",
                        session=s,
                        lock="pessimistic",
                        price_cents=1,
                    )
                    s.commit()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    ts = [threading.Thread(target=w) for _ in range(16)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert errors == [], errors[:2]
    with Session(pg) as s:
        assert s.get(Order, oid).machine.context["items"] == 400
    assert _checked_out(pg) == 0


def test_pg_lock_timeout_is_lock_timeout_error_and_retried(pg: Any) -> None:
    oid = _new_order(pg)
    holder = Session(pg)
    try:
        holder.get(Order, oid).send(
            "ADD_ITEM", session=holder, lock="pessimistic", price_cents=1
        )
        # 📝 a per-connection setting: a SET inside the transaction would
        #    be undone by send_with_retry's rollback and the retry would
        #    wait forever.
        short = create_engine(
            pg.url, connect_args={"options": "-c lock_timeout=100"}
        )
        try:
            with Session(short) as s:
                with pytest.raises(LockTimeoutError):
                    s.get(Order, oid).send(
                        "ADD_ITEM",
                        session=s,
                        lock="pessimistic",
                        price_cents=1,
                    )
                s.rollback()
                with pytest.raises(LockTimeoutError) as ei:
                    send_with_retry(
                        s.get(Order, oid),
                        "ADD_ITEM",
                        session=s,
                        retries=2,
                        lock="pessimistic",
                        price_cents=1,
                    )
                # budget exhausted: 1 try + 2 retries, and it says so
                assert getattr(ei.value, "attempts") == 3
                s.rollback()
        finally:
            short.dispose()
    finally:
        holder.rollback()
        holder.close()


def test_pg_deadlock_maps_to_lock_timeout_error(pg: Any) -> None:
    a, b = _new_order(pg), _new_order(pg)
    bar = threading.Barrier(2)
    out: List[str] = []

    def run(x: int, y: int) -> None:
        with Session(pg) as s:
            try:
                s.get(Order, x).send(
                    "ADD_ITEM", session=s, lock="pessimistic", price_cents=1
                )
                bar.wait()
                time.sleep(0.2)
                s.get(Order, y).send(
                    "ADD_ITEM", session=s, lock="pessimistic", price_cents=1
                )
                s.commit()
                out.append("ok")
            except LockTimeoutError:
                s.rollback()
                out.append("lock")
            except OperationalError:  # pragma: no cover - the defect
                s.rollback()
                out.append("raw")

    t1 = threading.Thread(target=run, args=(a, b))
    t2 = threading.Thread(target=run, args=(b, a))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert sorted(out) == ["lock", "ok"], out


def test_is_locked_recognises_dialects() -> None:
    class Orig(Exception):
        sqlstate = None

    def wrap(msg: str, code: Any = None) -> Exception:
        o = Orig(msg)
        o.sqlstate = code
        return OperationalError("stmt", {}, o)

    assert _is_locked(wrap("database is locked"))
    assert _is_locked(wrap("x", "55P03"))
    assert _is_locked(wrap("x", "40P01"))
    assert _is_locked(wrap("Lock wait timeout exceeded"))
    assert not _is_locked(wrap("connection refused", "08001"))


def test_retry_budget_exhaustion_sets_attempts(engine: Any) -> None:
    oid = _new_order(engine)
    with Session(engine) as s:
        row = s.get(Order, oid)
        with Session(engine) as other:  # bump the version under it
            other.get(Order, oid).send(
                "ADD_ITEM", session=other, price_cents=1
            )
            other.commit()
        calls = [0]
        real = type(row).send

        def always_stale(self: Any, *a: Any, **k: Any) -> Any:
            calls[0] += 1
            raise ConflictError(str(oid), 0, None)

        type(row).send = always_stale  # type: ignore[method-assign]
        try:
            with pytest.raises(ConflictError) as ei:
                send_with_retry(row, "ADD_ITEM", session=s, retries=3)
        finally:
            type(row).send = real  # type: ignore[method-assign]
        assert ei.value.attempts == 4 and calls[0] == 4  # type: ignore


# -----------------------------------------------------------------------------
# 4/5. scanners over ModelStore; a wake racing a web send
# -----------------------------------------------------------------------------
def test_four_scanners_one_crashing_wake_each_key_once(engine: Any) -> None:
    n = 400 if engine.dialect.name == "sqlite" else 2000
    with Session(engine) as s:
        rows = [Order() for _ in range(n)]
        s.add_all(rows)
        s.commit()
        ids = [r.id for r in rows]
    # one session per batch keeps the setup fast
    for chunk in range(0, n, 200):
        with Session(engine) as s:
            for oid in ids[chunk : chunk + 200]:
                row = s.get(Order, oid)
                row.send("ADD_ITEM", session=s, price_cents=1)
                row.send("CHECKOUT", session=s)
            s.commit()
    store = Order.statechart_store(sessionmaker(engine))
    machine = Order.__xsm_machine__
    woke: Dict[str, int] = {}
    now = time.time() + 901

    class Crash(Exception):
        pass

    def crashing(key: str) -> Any:
        if int(key) % 7 == 0:
            raise Crash(key)
        return machine

    def run(name: str, factory: Any) -> None:
        try:
            woke[name] = DueTimerScanner(store, factory).run_once(now=now)
        except Crash:
            woke[name] = -1

    ts = [
        threading.Thread(target=run, args=(f"s{i}", lambda k: machine))
        for i in range(3)
    ]
    ts.append(threading.Thread(target=run, args=("crash", crashing)))
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    # whatever the crashing scanner did, a fresh pass finishes the rest
    rest = DueTimerScanner(store, lambda k: machine).run_once(now=now)
    total = sum(v for v in woke.values() if v > 0) + rest
    with Session(engine) as s:
        expired = s.execute(
            select(func.count())
            .select_from(Order)
            .where(Order.in_state("order.expired"))
        ).scalar_one()
        versions = set(
            s.scalars(
                select(Order.statechart_version).where(Order.id.in_(ids))
            )
        )
    assert expired == n
    assert total == n, (woke, rest)  # every key woken exactly once
    assert versions == {4}, versions  # insert, add, checkout, ONE wake
    assert DueTimerScanner(store, lambda k: machine).run_once(now=now) == 0
    with Session(engine) as s:
        assert (
            s.execute(select(func.count()).select_from(DEADLINES)).scalar_one()
            == 0
        )


def test_scanner_wake_racing_web_send_one_loses(engine: Any) -> None:
    oid = _ready_to_pay(engine)
    store = Order.statechart_store(sessionmaker(engine))
    rec = store.load(str(oid))
    # the web request pays while the scanner holds the stale version
    _send(engine, oid, "PAY", charge_id="ch")
    with pytest.raises(ConflictError):
        store.save(
            str(oid),
            rec.snapshot,
            expected_version=rec.version,
            machine_version="",
        )
    machine = Order.__xsm_machine__
    assert (
        DueTimerScanner(store, lambda k: machine).run_once(
            now=time.time() + 901
        )
        == 0
    )
    with Session(engine) as s:
        assert s.get(Order, oid).state == "order.paid"


# -----------------------------------------------------------------------------
# 6. resources and size
# -----------------------------------------------------------------------------
def test_no_connection_leak_across_many_sends(engine: Any) -> None:
    store = _store(engine)
    plugin = OutboxPlugin(SQLAlchemyOutboxStore(store), topic="o")
    oid = _new_order(engine)
    for i in range(300):
        with Session(engine) as s:
            s.get(Order, oid).send(
                "ADD_ITEM", session=s, plugins=[plugin], price_cents=1
            )
            if i % 3:
                s.commit()
            else:
                s.rollback()
        assert _checked_out(engine) == 0
    with Session(engine) as s:
        assert s.get(Order, oid).machine.context["items"] == 200


def test_snapshot_size_cap_on_the_mixin_path(engine: Any) -> None:
    oid = _ready_to_pay(engine)
    with Session(engine) as s:
        row = s.get(Order, oid)
        row.statechart = dict(row.statechart, junk="x" * (1 << 20))
        with pytest.raises(Exception) as ei:
            s.flush()
        assert isinstance(
            ei.value.__cause__ or ei.value, SnapshotTooLargeError
        ) or "SnapshotTooLarge" in repr(ei.value)
        s.rollback()
    # just under the cap round-trips
    with Session(engine) as s:
        row = s.get(Order, oid)
        row.statechart = dict(row.statechart, junk="x" * 1_000_000)
        s.commit()
    with Session(engine) as s:
        row = s.get(Order, oid)
        assert len(row.statechart["junk"]) == 1_000_000
        row.send("PAY", session=s, charge_id="c")
        s.commit()


# -----------------------------------------------------------------------------
# 7. cross-area (from adversary B): schema missing, wide parallel charts
# -----------------------------------------------------------------------------
def test_create_tables_false_on_empty_db_says_run_migrations(
    engine: Any,
) -> None:
    from src.xstate_statemachine.exceptions import StoreError

    Base.metadata.drop_all(engine)  # an EMPTY database
    with pytest.raises(StoreError, match="tables are missing.*migrations"):
        SQLAlchemyStore(sessionmaker(engine), create_tables=False)
    SQLAlchemyStore(sessionmaker(engine))  # creates them
    SQLAlchemyStore(sessionmaker(engine), create_tables=False)  # now fine


class _WideBase(DeclarativeBase):
    pass


_REGIONS = 12


def _wide_chart() -> Dict[str, Any]:
    leaf = "a_rather_long_leaf_state_name_for_region"
    return {
        "id": "wide_parallel_chart_with_a_long_id",
        "type": "parallel",
        "states": {
            f"region_number_{i:02d}": {
                "initial": f"{leaf}_{i:02d}",
                "states": {f"{leaf}_{i:02d}": {}},
            }
            for i in range(_REGIONS)
        },
    }


class Wide(StatechartMixin, _WideBase):
    __tablename__ = "b284a_wide"
    __xsm_machine__ = create_machine(_wide_chart())
    id: Mapped[int] = mapped_column(primary_key=True)
    statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        StatechartType, nullable=True
    )
    __mapper_args__ = StatechartMixin.optimistic()


def test_wide_parallel_state_string_round_trips(engine: Any) -> None:
    _WideBase.metadata.create_all(engine)
    try:
        with Session(engine) as s:
            w = Wide()
            s.add(w)
            s.flush()
            w.send("NOTHING", session=s)
            s.commit()
            wid = w.id
        with Session(engine) as s:
            w = s.get(Wide, wid)
            assert len(w.statechart_state) > 512, len(w.statechart_state)
            assert len(w.statechart_state.split(",")) == _REGIONS
            assert w.statechart_state == state_string(
                w.machine.current_state_ids
            )
            hit = s.scalars(
                select(Wide.id).where(
                    Wide.in_state(
                        "wide_parallel_chart_with_a_long_id.region_number_11"
                    )
                )
            ).all()
            assert hit == [wid]
    finally:
        _WideBase.metadata.drop_all(engine)
