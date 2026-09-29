# tests/contrib/sqlalchemy/test_sqlalchemy_mixin.py
"""#284 part 1: `StatechartType` + `StatechartMixin` -- optimistic locking
via ``version_id_col``, `in_state()`, parallel leaf ids, the
``before_update`` consistency listener, audit rows in the same flush,
deadlines → `DueTimerScanner`, Alembic autogenerate with no diff."""

from __future__ import annotations

import json
import threading
import time
from typing import Any, Dict, List, Optional

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("sqlalchemy")
# 📝 The marker only SKIPS; it cannot stop the module-level import below
#    from running at collection in a job without the extra (the default
#    Test matrix). importorskip first, like every other contrib suite.
pytest.importorskip("sqlalchemy")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import (  # noqa: E402
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from src.xstate_statemachine import MachineLogic, create_machine  # noqa: E402
from src.xstate_statemachine.contrib.sqlalchemy import (  # noqa: E402
    StatechartMixin,
    StatechartType,
    send_with_retry,
    xsm_sqlalchemy_ddl,
)
from src.xstate_statemachine.exceptions import (  # noqa: E402
    ConflictError,
    SnapshotTooLargeError,
)
from src.xstate_statemachine.persistence import DueTimerScanner  # noqa: E402

from .conftest import sqlite_engine  # noqa: E402

CFG = {
    "id": "o",
    "initial": "draft",
    "context": {"n": 0},
    "states": {
        "draft": {
            "on": {"T": {"actions": "inc"}, "SUBMIT": "review"},
        },
        "review": {
            "after": {"3600000": "expired"},
            "on": {"APPROVE": "live"},
        },
        "live": {
            "type": "parallel",
            "states": {
                "pay": {"initial": "due", "states": {"due": {}}},
                "ship": {"initial": "packing", "states": {"packing": {}}},
            },
        },
        "expired": {"type": "final"},
    },
}


def _inc(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] = c["n"] + 1


def machine() -> Any:
    return create_machine(CFG, logic=MachineLogic(actions={"inc": _inc}))


M = machine()


class Base(DeclarativeBase):
    pass


class Order(StatechartMixin, Base):
    __tablename__ = "orders"
    __xsm_machine__ = M
    __xsm_audit__ = True
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[Optional[str]] = mapped_column(nullable=True)
    statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        StatechartType, nullable=True
    )
    __mapper_args__ = StatechartMixin.optimistic()


xsm_sqlalchemy_ddl(Base.metadata)


@pytest.fixture
def engine(tmp_path: Any) -> Any:
    eng = sqlite_engine(tmp_path / "app.db")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


def _new(engine: Any, **kw: Any) -> int:
    with Session(engine) as s:
        o = Order(**kw)
        s.add(o)
        s.commit()
        return o.id


class TestColumnsAndQueries:
    def test_send_flushes_snapshot_and_columns(self, engine: Any) -> None:
        oid = _new(engine)
        with Session(engine) as s:
            o = s.get(Order, oid)
            r = o.send("T", session=s)
            assert r.changed and o.statechart["context"]["n"] == 1
            s.commit()
        with Session(engine) as s:
            o = s.get(Order, oid)
            assert o.state == "o.draft"
            assert o.statechart_state_ids == ["o.draft"]
            assert o.statechart_version == 2  # insert=1, one send
            assert o.machine.context["n"] == 1

    def test_in_state_and_parallel_leaf_ids(self, engine: Any) -> None:
        a, b, c = _new(engine), _new(engine), _new(engine)
        with Session(engine) as s:
            for ev in ("SUBMIT", "APPROVE"):
                s.get(Order, a).send(ev, session=s)
            s.get(Order, b).send("SUBMIT", session=s)
            s.get(Order, c).send("T", session=s)
            s.commit()
        with Session(engine) as s:
            live = s.get(Order, a)
            assert live.statechart_state_ids == [
                "o.live.pay.due",
                "o.live.ship.packing",
            ]
            q = select(Order.id).where(Order.in_state("o.live"))
            assert s.scalars(q).all() == [a]  # ancestor matches leaves
            q = select(Order.id).where(Order.in_state("o.live.ship.packing"))
            assert s.scalars(q).all() == [a]
            q = select(Order.id).where(Order.in_state("o.review", "o.draft"))
            assert sorted(s.scalars(q).all()) == [b, c]
            # "o.dr" is not a prefix match of "o.draft"
            q = select(Order.id).where(Order.in_state("o.dr"))
            assert s.scalars(q).all() == []
            assert s.scalars(
                select(Order.id).where(Order.state == "o.review")
            ).all() == [b]
        with pytest.raises(ValueError):
            Order.in_state()

    def test_before_update_keeps_columns_consistent(self, engine: Any):
        oid = _new(engine)
        with Session(engine) as s:
            s.get(Order, oid).send("SUBMIT", session=s)
            s.commit()
        with Session(engine) as s:
            o = s.get(Order, oid)
            snap = json.loads(json.dumps(o.statechart))
            snap["state_ids"] = ["o.expired"]
            snap["value"] = "expired"
            snap["configuration"] = ["o", "o.expired"]
            o.statechart = snap  # edited directly, no send()
            s.commit()
        with Session(engine) as s:
            o = s.get(Order, oid)
            assert o.state == "o.expired"
            assert o.statechart_state_ids == ["o.expired"]

    def test_insert_computes_columns_and_row_without_snapshot(self, engine):
        oid = _new(engine, title="blank")
        with Session(engine) as s:
            o = s.get(Order, oid)
            assert o.state is None and o.statechart is None
            assert o.machine.status == "uninitialized"

    def test_send_requires_session_and_valid_lock(self) -> None:
        with pytest.raises(ValueError):
            Order().send("T")
        with pytest.raises(ValueError):
            Order().send("T", session=object(), lock="nope")

    def test_statechart_type_size_cap(self, engine: Any) -> None:
        small = StatechartType(max_snapshot_bytes=16)
        with pytest.raises(SnapshotTooLargeError):
            small.process_bind_param({"context": "x" * 64}, None)
        with pytest.raises(TypeError):
            small.process_bind_param([1], None)
        assert small.process_result_value(None, None) is None
        assert StatechartType().process_result_value('{"a": 1}', None) == {
            "a": 1
        }


class TestOptimisticLocking:
    def test_stale_row_raises_conflict(self, engine: Any) -> None:
        oid = _new(engine)
        s1, s2 = Session(engine), Session(engine)
        try:
            a, b = s1.get(Order, oid), s2.get(Order, oid)
            a.send("T", session=s1)
            s1.commit()
            with pytest.raises(ConflictError):
                b.send("T", session=s2)
            s2.rollback()
            assert send_with_retry(b, "T", session=s2).changed
            s2.commit()
        finally:
            s1.close()
            s2.close()
        with Session(engine) as s:
            assert s.get(Order, oid).machine.context["n"] == 2

    def test_sixteen_by_hundred_concurrent_sends(self, engine: Any) -> None:
        """16 threads × 100 `send_with_retry` on ONE row → exactly 1600."""
        oid = _new(engine)
        conflicts: List[int] = []
        errors: List[BaseException] = []
        real = Order.send

        def counting_send(self: Any, *a: Any, **kw: Any) -> Any:
            try:
                return real(self, *a, **kw)
            except ConflictError:
                conflicts.append(1)
                raise

        def worker() -> None:
            try:
                for _ in range(100):
                    with Session(engine) as s:
                        o = s.get(Order, oid)
                        send_with_retry(o, "T", session=s, retries=10_000)
                        s.commit()
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        Order.send = counting_send  # type: ignore[method-assign]
        try:
            ts = [threading.Thread(target=worker) for _ in range(16)]
            for t in ts:
                t.start()
            for t in ts:
                t.join(600)
        finally:
            Order.send = real  # type: ignore[method-assign]
        assert errors == []
        with Session(engine) as s:
            o = s.get(Order, oid)
            assert o.machine.context["n"] == 1600
            assert o.statechart_version == 1601
        assert conflicts, "expected at least one ConflictError under load"

    def test_pessimistic_lock_path(self, engine: Any) -> None:
        oid = _new(engine)
        with Session(engine) as s:
            o = s.get(Order, oid)
            assert o.send("T", session=s, lock="pessimistic").changed
            s.commit()
        with Session(engine) as s:
            assert s.get(Order, oid).machine.context["n"] == 1


class TestAuditInOneFlush:
    def _rows(self, engine: Any, oid: int) -> List[Any]:
        t = Base.metadata.tables["xsm_transitions"]
        with Session(engine) as s:
            return list(
                s.execute(
                    select(t.c.seq, t.c.record).where(
                        t.c.machine_id == f"orders:{oid}"
                    )
                )
            )

    def test_audit_row_commits_with_state(self, engine: Any) -> None:
        oid = _new(engine)
        with Session(engine) as s:
            o = s.get(Order, oid)
            o.send("SUBMIT", session=s, actor="basil")
            o.send("APPROVE", session=s, actor="ops")
            s.commit()
        rows = self._rows(engine, oid)
        assert [r[0] for r in rows] == [1, 2]
        assert json.loads(rows[1][1])["actor"] == "ops"

    def test_raising_inside_send_leaves_neither(
        self, engine: Any, monkeypatch
    ):
        from src.xstate_statemachine.contrib.sqlalchemy import _ops

        oid = _new(engine)

        def boom(*a: Any, **k: Any) -> Any:
            raise RuntimeError("disk on fire")

        # Fail AFTER the row UPDATE was flushed, before the aux rows.
        monkeypatch.setattr(_ops, "write_deadlines", boom)
        with Session(engine) as s:
            o = s.get(Order, oid)
            with pytest.raises(RuntimeError):
                o.send("SUBMIT", session=s, actor="basil")
            s.rollback()
        monkeypatch.undo()
        with Session(engine) as s:
            assert s.get(Order, oid).statechart is None
        assert self._rows(engine, oid) == []

    def test_caller_rollback_after_send_leaves_neither(self, engine: Any):
        oid = _new(engine)
        with Session(engine) as s:
            s.get(Order, oid).send("SUBMIT", session=s)
            s.rollback()
        with Session(engine) as s:
            assert s.get(Order, oid).state is None
        assert self._rows(engine, oid) == []

    def test_audit_without_ddl_fails_loudly(self, tmp_path: Any) -> None:
        class B2(DeclarativeBase):
            pass

        class Doc(StatechartMixin, B2):
            __tablename__ = "docs"
            __xsm_machine__ = M
            __xsm_audit__ = True
            id: Mapped[int] = mapped_column(primary_key=True)
            statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
                StatechartType, nullable=True
            )

        eng = sqlite_engine(tmp_path / "d.db")
        B2.metadata.create_all(eng)
        with Session(eng) as s:
            d = Doc()
            s.add(d)
            s.flush()
            with pytest.raises(TypeError, match="xsm_sqlalchemy_ddl"):
                d.send("T", session=s)
        eng.dispose()


class TestLogicAndMachineFactories:
    def test_callable_machine_and_logic(self, tmp_path: Any) -> None:
        seen: List[str] = []

        class B3(DeclarativeBase):
            pass

        def logic_for(row: Any) -> Any:
            return MachineLogic(
                actions={"inc": lambda i, c, e, a: seen.append(row.tenant)}
            )

        class Item(StatechartMixin, B3):
            __tablename__ = "items"
            __xsm_machine__ = staticmethod(lambda row: M)
            __xsm_logic__ = staticmethod(logic_for)
            id: Mapped[int] = mapped_column(primary_key=True)
            tenant: Mapped[str] = mapped_column(default="acme")
            statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
                StatechartType, nullable=True
            )

        eng = sqlite_engine(tmp_path / "i.db")
        B3.metadata.create_all(eng)
        with Session(eng) as s:
            it = Item()
            s.add(it)
            s.flush()
            it.send("T", session=s)
            s.commit()
            assert it.statechart_version == 1  # no version_id_col: bumped
        assert seen == ["acme"]
        assert M.logic.actions["inc"] is _inc  # shared machine untouched
        eng.dispose()


class TestDeadlines:
    def test_deadlines_indexed_and_fired_by_scanner(self, engine: Any):
        oid = _new(engine)
        with Session(engine) as s:
            s.get(Order, oid).send("SUBMIT", session=s)
            s.commit()
        t = Base.metadata.tables["xsm_deadlines"]
        with Session(engine) as s:
            rows = s.execute(select(t.c.source, t.c.key, t.c.event_type)).all()
        assert rows == [("orders", str(oid), "after.3600000.o.review")]

        store = Order.statechart_store(sessionmaker(engine))
        rec = store.load(str(oid))
        assert rec is not None and len(rec.deadlines) == 1
        assert store.list_keys() == [str(oid)]
        now = time.time()
        sc = DueTimerScanner(store, lambda k: M)
        assert sc.run_once(now=now + 60) == 0
        assert sc.run_once(now=now + 3601) == 1
        assert sc.run_once(now=now + 3601) == 0
        with Session(engine) as s:
            o = s.get(Order, oid)
            assert o.state == "o.expired"
            assert o.statechart_version == 3  # insert, SUBMIT, timer
        with Session(engine) as s:
            assert s.execute(select(t.c.key)).all() == []
        assert store.forget(str(oid))["deadlines"] == 0

    def test_leaving_the_state_clears_the_deadline(self, engine: Any):
        oid = _new(engine)
        with Session(engine) as s:
            o = s.get(Order, oid)
            o.send("SUBMIT", session=s)
            o.send("APPROVE", session=s)
            s.commit()
        t = Base.metadata.tables["xsm_deadlines"]
        with Session(engine) as s:
            assert s.execute(select(t.c.key)).all() == []

    def test_model_store_conflict_and_guards(self, engine: Any) -> None:
        oid = _new(engine)
        with Session(engine) as s:
            s.get(Order, oid).send("T", session=s)
            s.commit()
        store = Order.statechart_store(sessionmaker(engine))
        rec = store.load(str(oid))
        with pytest.raises(ConflictError):
            store.save(str(oid), rec.snapshot, expected_version=99)
        with pytest.raises(ConflictError):
            store.save("999", rec.snapshot)
        with pytest.raises(NotImplementedError):
            store.delete(str(oid))
        assert store.load("12345") is None


class TestAlembic:
    def test_autogenerate_no_diff(self, engine: Any) -> None:
        """X0.10: after `create_all` of the model + `xsm_sqlalchemy_ddl`,
        Alembic autogenerate proposes NOTHING."""
        pytest.importorskip("alembic")
        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        with engine.connect() as conn:
            mc = MigrationContext.configure(conn)
            assert compare_metadata(mc, Base.metadata) == []
