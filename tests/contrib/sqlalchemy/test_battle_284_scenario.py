# tests/contrib/sqlalchemy/test_battle_284_scenario.py
"""#284 battle: an orders service on SQLAlchemy, as a team would run it.

The `sqlalchemy_orders` example is the host. The scenario is the shape a
production team recognises -- many rows, writers that collide, a relay
that crashes between publish and mark, a migration applied from an empty
database, a Postgres variant when one is reachable -- not a unit test:

* **a fleet of writers on one row** -- 16 threads x 25 sends through
  `send_with_retry` on one order: every increment lands, `ConflictError`
  is what the loser sees (never a lost update, never a raw
  `StaleDataError`), the audit log has exactly one row per processed
  event and its `seq` numbers are gapless;
* **many rows, one scanner** -- 200 orders checked out; half pay; the
  scanner wakes exactly the unpaid ones at the deadline, in bounded time,
  and a second scanner process started concurrently wakes none twice;
* **the outbox is transactional WITH THE ROW** -- a chart that declares
  `meta.publish` on PAY, driven through `Order.send(plugins=[OutboxPlugin])`
  inside the caller's session: a rollback of that session must leave
  neither the state change nor the outbox row (X0.3). Then the relay:
  a broker that acks the first row and dies on the second leaves the
  second pending and re-publishes it with the SAME envelope id
  (at-least-once, consumers dedup);
* **forget() cascades** -- deadlines, audit rows (X0.5);
* **Alembic from scratch** -- `upgrade head` on an empty file, the
  example's demo runs on it, autogenerate proposes nothing, `downgrade
  base` leaves an empty schema;
* **Postgres parity** -- the same fleet and outbox checks on a real
  server when `DATABASE_URL` is set, or on a throwaway testcontainer
  when `XSM_CONTAINERS=1` and Docker is present; skipped otherwise.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pytest

from ..conftest import requires_extra

pytestmark = [requires_extra("sqlalchemy"), pytest.mark.timeout(600)]
pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine, func, select  # noqa: E402
from sqlalchemy.orm import (  # noqa: E402
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from src.xstate_statemachine import MachineLogic, create_machine  # noqa: E402
from src.xstate_statemachine.contrib.sqlalchemy import (  # noqa: E402
    SQLAlchemyOutboxStore,
    SQLAlchemyStore,
    StatechartMixin,
    StatechartType,
    send_with_retry,
    xsm_sqlalchemy_ddl,
)
from src.xstate_statemachine.eda import (  # noqa: E402
    Envelope,
    OutboxPlugin,
    OutboxRelay,
)
from src.xstate_statemachine.exceptions import ConflictError  # noqa: E402
from src.xstate_statemachine.persistence import DueTimerScanner  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = ROOT / "examples" / "integrations" / "sqlalchemy_orders"
WRITERS, SENDS = 16, 25


# -----------------------------------------------------------------------------
# 🗃️ a publishing variant of the example's chart on a mixin row
# -----------------------------------------------------------------------------
def _chart() -> Dict[str, Any]:
    cfg = json.loads((EXAMPLE / "machine.json").read_text("utf-8"))
    cfg["states"]["awaitingPayment"]["on"]["PAY"]["meta"] = {
        "publish": {"type": "order.paid", "data": ["total_cents"]}
    }
    return cfg


def _logic() -> MachineLogic:
    def add_item(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        ctx["items"] = int(ctx["items"]) + 1
        ctx["total_cents"] = int(ctx["total_cents"]) + int(
            e.payload.get("price_cents", 0)
        )

    def record_charge(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        ctx["charge_id"] = str(e.payload.get("charge_id", "ch"))

    return MachineLogic(
        actions={"addItem": add_item, "recordCharge": record_charge},
        guards={"hasItems": lambda ctx, e: int(ctx["items"]) > 0},
    )


class Base(DeclarativeBase):
    pass


class Order(StatechartMixin, Base):
    __tablename__ = "b284_orders"
    __xsm_machine__ = create_machine(_chart(), logic=_logic())
    __xsm_audit__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        StatechartType, nullable=True
    )
    __mapper_args__ = StatechartMixin.optimistic()


xsm_sqlalchemy_ddl(Base.metadata)
TRANSITIONS = Base.metadata.tables["xsm_transitions"]
DEADLINES = Base.metadata.tables["xsm_deadlines"]


# -----------------------------------------------------------------------------
# 🔌 engines: SQLite always; Postgres when reachable
# -----------------------------------------------------------------------------
def _pg_url() -> Optional[str]:
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgresql"):
        return url
    return None


@pytest.fixture(scope="module")
def pg_container_url() -> Iterator[Optional[str]]:
    """A throwaway Postgres when ``XSM_CONTAINERS=1`` (else ``None``)."""
    if os.environ.get("XSM_CONTAINERS") != "1":
        yield None
        return
    tc = pytest.importorskip("testcontainers.postgres")
    pytest.importorskip("psycopg")
    with tc.PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(params=["sqlite", "postgres"])
def engine(request: Any, tmp_path: Path, pg_container_url: Any) -> Iterator:
    if request.param == "sqlite":
        eng = create_engine(
            f"sqlite:///{(tmp_path / 'o.db').as_posix()}",
            connect_args={"timeout": 30},
        )
    else:
        url = _pg_url() or pg_container_url
        if not url:
            pytest.skip("no Postgres: set DATABASE_URL or XSM_CONTAINERS=1")
        eng = create_engine(url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    try:
        yield eng
    finally:
        Base.metadata.drop_all(eng)
        eng.dispose()


def _new_order(eng: Any) -> int:
    with Session(eng) as s:
        o = Order()
        s.add(o)
        s.commit()
        return o.id


def _send(eng: Any, oid: int, event: str, **payload: Any) -> Any:
    with Session(eng) as s:
        r = send_with_retry(
            s.get(Order, oid), event, session=s, retries=200, **payload
        )
        s.commit()
        return r


def _count(eng: Any, table: Any, **where: Any) -> int:
    q = select(func.count()).select_from(table)
    for k, v in where.items():
        q = q.where(getattr(table.c, k) == v)
    with Session(eng) as s:
        return int(s.execute(q).scalar_one())


@pytest.fixture
def example_modules() -> Iterator[Any]:
    """The example's ``logic`` / ``models`` / ``sync_app`` imported from
    ITS directory and kept in ``sys.modules`` for the test (Alembic's
    env.py does ``from models import Base`` and must get the same module);
    same-named modules another example suite left behind (fastapi_orders,
    flask_wizard -- CI's Coverage job runs them all in one process) are
    set aside and restored afterwards."""
    import importlib

    names = ("logic", "models", "sync_app")
    saved = {k: sys.modules.pop(k) for k in names if k in sys.modules}
    sys.path.insert(0, str(EXAMPLE))
    try:
        yield tuple(importlib.import_module(n) for n in names)
    finally:
        sys.path.remove(str(EXAMPLE))
        for k in names:
            sys.modules.pop(k, None)
        sys.modules.update(saved)


# -----------------------------------------------------------------------------
# 1. a fleet of writers on one row
# -----------------------------------------------------------------------------
def test_fleet_of_writers_loses_nothing_and_audit_is_gapless(
    engine: Any,
) -> None:
    oid = _new_order(engine)
    errors: List[BaseException] = []
    raw_stale: List[BaseException] = []
    conflicts = [0]
    lock = threading.Lock()

    def worker() -> None:
        try:
            for _ in range(SENDS):
                with Session(engine) as s:
                    try:
                        s.get(Order, oid).send(
                            "ADD_ITEM", session=s, price_cents=1
                        )
                        s.commit()
                    except ConflictError:
                        with lock:
                            conflicts[0] += 1
                        s.rollback()
                        # the documented recovery
                        send_with_retry(
                            s.get(Order, oid),
                            "ADD_ITEM",
                            session=s,
                            retries=500,
                            price_cents=1,
                        )
                        s.commit()
        except BaseException as exc:  # noqa: BLE001 - reported below
            if "StaleDataError" in type(exc).__name__:
                raw_stale.append(exc)
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(WRITERS)]
    t0 = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    took = time.perf_counter() - t0
    assert raw_stale == [], "a raw StaleDataError escaped"
    assert errors == [], errors[:3]
    want = WRITERS * SENDS
    with Session(engine) as s:
        row = s.get(Order, oid)
        ctx = row.machine.context
        assert ctx["items"] == want and ctx["total_cents"] == want
        # the INSERT is version 1; every processed send bumps it once
        assert row.statechart_version == want + 1, row.statechart_version
        seqs = sorted(
            s.scalars(
                select(TRANSITIONS.c.seq).where(
                    TRANSITIONS.c.machine_id == row._xsm_log_id()
                )
            )
        )
    # one audit row per PROCESSED event, numbered 1..N without a gap: a
    # retried attempt's buffered row was discarded with its rollback
    assert seqs == list(range(1, want + 1)), (len(seqs), seqs[:5], seqs[-5:])
    assert took < 240, took


# -----------------------------------------------------------------------------
# 2. many rows, one scanner (and a second one that must find nothing)
# -----------------------------------------------------------------------------
def test_two_hundred_orders_and_one_scanner(engine: Any, tmp_path) -> None:
    ids = [_new_order(engine) for _ in range(200)]
    for oid in ids:
        _send(engine, oid, "ADD_ITEM", price_cents=5)
        _send(engine, oid, "CHECKOUT")
    for oid in ids[::2]:
        _send(engine, oid, "PAY", charge_id=f"ch_{oid}")
    assert _count(engine, DEADLINES) == 100  # paid orders left the state
    store = Order.statechart_store(sessionmaker(engine))
    machine = Order.__xsm_machine__
    now = time.time()
    a = DueTimerScanner(store, lambda k: machine)
    b = DueTimerScanner(store, lambda k: machine)
    woke: Dict[str, int] = {}

    def run(name: str, sc: DueTimerScanner) -> None:
        woke[name] = sc.run_once(now=now + 901)

    ta = threading.Thread(target=run, args=("a", a))
    tb = threading.Thread(target=run, args=("b", b))
    t0 = time.perf_counter()
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    took = time.perf_counter() - t0
    assert woke["a"] + woke["b"] == 100, woke  # each order woken ONCE
    assert took < 120, took
    with Session(engine) as s:
        expired = s.scalars(
            select(Order.id).where(Order.in_state("order.expired"))
        ).all()
        paid = s.scalars(
            select(Order.id).where(Order.in_state("order.paid"))
        ).all()
    assert sorted(expired) == sorted(ids[1::2])
    assert sorted(paid) == sorted(ids[::2])
    assert _count(engine, DEADLINES) == 0
    assert a.run_once(now=now + 902) == 0


# -----------------------------------------------------------------------------
# 3. the outbox is transactional WITH THE ROW
# -----------------------------------------------------------------------------
def test_outbox_row_rolls_back_with_the_row_and_relay_is_at_least_once(
    engine: Any,
) -> None:
    store = SQLAlchemyStore(sessionmaker(engine), metadata=Base.metadata)
    outbox = SQLAlchemyOutboxStore(store)
    oid = _new_order(engine)
    _send(engine, oid, "ADD_ITEM", price_cents=7)
    _send(engine, oid, "CHECKOUT")
    plugin = OutboxPlugin(outbox, topic="orders")
    # -- the caller's session rolls back AFTER send(): nothing may remain
    with Session(engine) as s:
        row = s.get(Order, oid)
        row.send("PAY", session=s, plugins=[plugin], charge_id="ch_x")
        assert row.state == "order.paid"
        # 🔥 not yet committed: no other connection may see the row
        assert outbox.count() == 0, "outbox row visible before commit"
        s.rollback()
    with Session(engine) as s:
        assert s.get(Order, oid).state == "order.awaitingPayment"
    assert outbox.count() == 0, "outbox row survived the rollback"
    # -- commit: exactly one row, carrying the chart's declared data
    with Session(engine) as s:
        s.get(Order, oid).send(
            "PAY", session=s, plugins=[plugin], charge_id="ch_y"
        )
        s.commit()
    [rec] = outbox.pending()
    assert rec.topic == "orders" and rec.envelope.type == "order.paid"
    assert rec.envelope.data == {"total_cents": 7}
    first_id = rec.envelope.id
    # a second publishing event on another order, then a relay that acks
    # the first row and crashes before the second is marked
    oid2 = _new_order(engine)
    _send(engine, oid2, "ADD_ITEM", price_cents=1)
    _send(engine, oid2, "CHECKOUT")
    with Session(engine) as s:
        s.get(Order, oid2).send("PAY", session=s, plugins=[plugin])
        s.commit()
    assert outbox.count(pending_only=True) == 2

    class CrashyBroker:
        def __init__(self) -> None:
            self.published: List[Envelope] = []
            self.calls = 0

        def publish(self, topic: str, env: Envelope) -> None:
            self.calls += 1
            self.published.append(env)
            if self.calls == 2:
                raise ConnectionError("broker went away mid-batch")

    broker = CrashyBroker()
    with pytest.raises(ConnectionError):
        OutboxRelay(outbox, broker).relay_once_sync()
    # 📝 the first row was acked and MUST be marked (no duplicate for it);
    #    the second was published but not marked -> re-sent next time
    #    with the same envelope id (at-least-once; consumers dedup on id)
    assert outbox.count(pending_only=True) == 1, outbox.pending()
    [again] = outbox.pending()
    assert again.envelope.id != first_id
    assert OutboxRelay(outbox, broker).relay_once_sync() == 1
    assert outbox.count(pending_only=True) == 0
    ids = [e.id for e in broker.published]
    assert len(ids) == 3 and len(set(ids)) == 2  # one dup, same id


# -----------------------------------------------------------------------------
# 4. forget() cascades (X0.5)
# -----------------------------------------------------------------------------
def test_forget_removes_deadlines_and_audit_rows(engine: Any) -> None:
    oid = _new_order(engine)
    _send(engine, oid, "ADD_ITEM", price_cents=1)
    _send(engine, oid, "CHECKOUT")
    key = str(oid)
    assert _count(engine, DEADLINES, key=key) == 1
    with Session(engine) as s:
        log_id = s.get(Order, oid)._xsm_log_id()
    assert _count(engine, TRANSITIONS, machine_id=log_id) == 2
    store = Order.statechart_store(sessionmaker(engine))
    store.forget(key)
    assert _count(engine, DEADLINES, key=key) == 0
    assert _count(engine, TRANSITIONS, machine_id=log_id) == 0
    with Session(engine) as s:
        # the BUSINESS row is the application's to delete (documented)
        assert s.get(Order, oid) is not None


# -----------------------------------------------------------------------------
# 5. Alembic from scratch, demo on it, downgrade to nothing
# -----------------------------------------------------------------------------
def test_alembic_upgrade_demo_no_diff_downgrade(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, example_modules: Any
) -> None:
    pytest.importorskip("alembic")
    from alembic import command
    from alembic.autogenerate import compare_metadata
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from sqlalchemy import inspect

    _logic, ex_models, sync_app = example_modules
    url = f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}"
    monkeypatch.setenv("ORDERS_DB_URL", url)
    cfg = Config(str(EXAMPLE / "alembic.ini"))
    cfg.set_main_option("script_location", str(EXAMPLE / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")
    eng = create_engine(url)
    try:
        names = set(inspect(eng).get_table_names())
        assert {"orders", "xsm_deadlines", "xsm_transitions"} <= names, names
        # the demo runs on the MIGRATED schema (not create_all)
        a = sync_app.create_order(eng, "alice")
        sync_app.send(eng, a, "ADD_ITEM", price_cents=1)
        sync_app.send(eng, a, "CHECKOUT")
        assert sync_app.state_of(eng, a) == "order.awaitingPayment"
        with eng.connect() as conn:
            ctx = MigrationContext.configure(conn)
            assert compare_metadata(ctx, ex_models.Base.metadata) == []
    finally:
        eng.dispose()
    command.downgrade(cfg, "base")
    eng = create_engine(url)
    try:
        left = set(inspect(eng).get_table_names()) - {"alembic_version"}
        assert left == set(), left
    finally:
        eng.dispose()
