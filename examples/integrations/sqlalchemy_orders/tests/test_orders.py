# examples/integrations/sqlalchemy_orders/tests/test_orders.py
"""The sqlalchemy_orders example, end to end on a temp SQLite file.

Plain pytest -- no ``[testing]`` fixtures. Covers the committed Alembic
migration (upgrade + no autogenerate diff), the sync mixin variant
(`send_with_retry`, `in_state`, audit rows, concurrent writers), the
payment-timeout `after` fired by `DueTimerScanner`, and the async
`AsyncSQLAlchemyStore` variant.
"""

from __future__ import annotations

import asyncio
import threading
import time
from pathlib import Path
from typing import Any, Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import sync_app
from models import Base, Order

EXAMPLE = Path(__file__).resolve().parents[1]


def _alembic_config(url: str) -> Any:
    from alembic.config import Config

    cfg = Config(str(EXAMPLE / "alembic.ini"))
    cfg.set_main_option("script_location", str(EXAMPLE / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture
def db_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    url = f"sqlite:///{(tmp_path / 'orders.db').as_posix()}"
    # 📝 env.py prefers ORDERS_DB_URL over alembic.ini
    monkeypatch.setenv("ORDERS_DB_URL", url)
    return url


@pytest.fixture
def engine(db_url: str) -> Iterator[Any]:
    eng = sync_app.make_engine(db_url)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


# -----------------------------------------------------------------------------
# 🗃️ Alembic
# -----------------------------------------------------------------------------
class TestAlembic:
    def test_upgrade_head_then_autogenerate_sees_no_diff(self, db_url: str):
        pytest.importorskip("alembic")
        from alembic import command
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        command.upgrade(_alembic_config(db_url), "head")
        eng = sync_app.make_engine(db_url)
        try:
            with eng.connect() as conn:
                mc = MigrationContext.configure(conn)
                assert mc.get_current_revision() == "0001"
                assert compare_metadata(mc, Base.metadata) == []
            # ✅ and the migrated schema actually runs the app
            oid = sync_app.create_order(eng, "zoe")
            sync_app.send(eng, oid, "ADD_ITEM", price_cents=100)
            assert sync_app.state_of(eng, oid) == "order.cart"
        finally:
            eng.dispose()

    def test_migration_file_renders_statechart_as_plain_json(self) -> None:
        text = "".join(
            p.read_text("utf-8")
            for p in (EXAMPLE / "migrations" / "versions").glob("*.py")
        )
        assert "xstate_statemachine" not in text
        assert "xsm_deadlines" in text and "xsm_transitions" in text


# -----------------------------------------------------------------------------
# 🛒 Sync variant (StatechartMixin)
# -----------------------------------------------------------------------------
class TestSyncVariant:
    def test_happy_path_and_state_query(self, engine: Any) -> None:
        a = sync_app.create_order(engine, "alice")
        r = sync_app.send(engine, a, "CHECKOUT")
        assert not r.changed  # 🔒 guard: an empty cart cannot check out
        sync_app.send(engine, a, "ADD_ITEM", price_cents=450)
        sync_app.send(engine, a, "CHECKOUT")
        b = sync_app.create_order(engine, "bob")
        assert sync_app.orders_in(engine, "order.awaitingPayment") == [a]
        sync_app.send(engine, a, "PAY", charge_id="ch_9")
        assert sync_app.state_of(engine, a) == "order.paid"
        assert sync_app.state_of(engine, b) == ""  # never sent: no chart
        with Session(engine) as s:
            order = s.get(Order, a)
            assert order.machine.context["charge_id"] == "ch_9"
            assert order.machine.context["total_cents"] == 450
            # insert + 4 sends (the refused CHECKOUT is a no-op flush)
            assert order.statechart_version >= 4

    def test_audit_rows_written_in_the_same_flush(self, engine: Any) -> None:
        a = sync_app.create_order(engine, "alice")
        sync_app.send(engine, a, "ADD_ITEM", price_cents=1)
        sync_app.send(engine, a, "CHECKOUT")
        t = Base.metadata.tables["xsm_transitions"]
        with Session(engine) as s:
            n = s.execute(select(func.count()).select_from(t)).scalar_one()
        assert n == 2

    def test_concurrent_writers_lose_no_update(self, engine: Any) -> None:
        a = sync_app.create_order(engine, "alice")
        errors: list = []

        def worker() -> None:
            try:
                for _ in range(5):
                    sync_app.send(engine, a, "ADD_ITEM", price_cents=1)
            except Exception as exc:  # pragma: no cover - reported below
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        with Session(engine) as s:
            ctx = s.get(Order, a).machine.context
        assert ctx["items"] == 20 and ctx["total_cents"] == 20

    def test_payment_timeout_fired_by_the_scanner(self, engine: Any) -> None:
        a = sync_app.create_order(engine, "alice")
        sync_app.send(engine, a, "ADD_ITEM", price_cents=1)
        sync_app.send(engine, a, "CHECKOUT")
        paid = sync_app.create_order(engine, "bob")
        sync_app.send(engine, paid, "ADD_ITEM", price_cents=1)
        sync_app.send(engine, paid, "CHECKOUT")
        sync_app.send(engine, paid, "PAY")
        sc = sync_app.scanner(engine)
        now = time.time()
        assert sc.run_once(now=now + 60) == 0  # still inside the window
        assert sc.run_once(now=now + 901) == 1  # only the unpaid order
        assert sc.run_once(now=now + 901) == 0
        assert sync_app.state_of(engine, a) == "order.expired"
        assert sync_app.state_of(engine, paid) == "order.paid"

    def test_cli_demo_and_scan(self, engine: Any, db_url: str, capsys):
        sync_app.main(["demo", "--url", db_url])
        sync_app.main(["scan", "--url", db_url, "--at-offset", "901"])
        out = capsys.readouterr().out
        assert "order.paid" in out and "woke 1 order(s)" in out


# -----------------------------------------------------------------------------
# ⚡ Async variant (AsyncSQLAlchemyStore)
# -----------------------------------------------------------------------------
class TestAsyncVariant:
    def test_async_lifecycle_and_scanner(self, tmp_path: Path) -> None:
        pytest.importorskip("aiosqlite")
        pytest.importorskip("greenlet")
        import async_app

        path = str(tmp_path / "a.db")

        async def go() -> None:
            store = async_app.make_store(path)
            try:
                await async_app.asend(store, "o1", "ADD_ITEM", price_cents=5)
                await async_app.asend(store, "o1", "CHECKOUT")
                await async_app.asend(store, "o2", "ADD_ITEM", price_cents=5)
                await async_app.asend(store, "o2", "CHECKOUT")
                assert (
                    await async_app.asend(store, "o2", "PAY") == "order.paid"
                )
                await asyncio.gather(
                    *(
                        async_app.asend(store, "o3", "ADD_ITEM")
                        for _ in range(5)
                    )
                )
                assert await async_app.astate(store, "o1") == (
                    "order.awaitingPayment"
                )
            finally:
                await store.engine.dispose()

        asyncio.run(go())
        sc = async_app.scanner(path)
        assert sc.run_once(now=time.time() + 901) == 1
        sc.store.session_factory.kw["bind"].dispose()

        async def after() -> str:
            store = async_app.make_store(path)
            try:
                return await async_app.astate(store, "o1")
            finally:
                await store.engine.dispose()

        assert asyncio.run(after()) == "order.expired"
