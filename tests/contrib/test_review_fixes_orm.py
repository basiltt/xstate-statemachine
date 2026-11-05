# tests/contrib/test_review_fixes_orm.py
"""0.12.0 code-quality review: regressions for the Django / DRF / Channels /
SQLAlchemy extras (findings CDO-01 .. CDO-39).

Every test names the finding it pins. The Django tests run on the shared
test project (``tests/contrib/django/project``); the SQLAlchemy tests need
no server (SQLite, plus a sync-backed fake session for the async store).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import sys
import threading
import types
import uuid
from typing import Any, Dict, List, Optional

import pytest

pytest.importorskip("django")
pytest.importorskip("pytest_django")
pytest.importorskip("rest_framework")
pytest.importorskip("channels")
pytest.importorskip("sqlalchemy")

from .django import bootstrap  # noqa: E402

bootstrap.ensure()

from django.core.exceptions import ValidationError  # noqa: E402
from django.db import IntegrityError, OperationalError  # noqa: E402
from sqlalchemy.orm import (  # noqa: E402
    DeclarativeBase,
    Mapped,
    mapped_column,
)

from xstate_statemachine import (  # noqa: E402
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.exceptions import (  # noqa: E402
    ConflictError,
    LockTimeoutError,
    StoreError,
)

CFG: Dict[str, Any] = {
    "id": "gate",
    "initial": "idle",
    "states": {
        "idle": {"on": {"GO": {"target": "done", "guard": "ok"}}},
        "done": {},
    },
}


def _true_logic() -> Any:
    return MachineLogic(guards={"ok": lambda c, e: True})


# -----------------------------------------------------------------------------
# CDO-01 / CDO-12: machine resolution
# -----------------------------------------------------------------------------
class TestMachineResolution:
    def test_dotted_per_row_callable_is_not_cached(
        self, monkeypatch: Any
    ) -> None:
        """CDO-01: a ``"pkg.mod:factory"`` taking the row runs per row."""
        from shop.models import Order

        seen: List[Any] = []

        def build(row: Any) -> Any:
            seen.append(row)
            return create_machine(
                {"id": "m", "initial": "a", "states": {"a": {}}}
            )

        mod = types.ModuleType("xsm_review_charts")
        mod.build = build  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "xsm_review_charts", mod)
        cache = Order.__dict__.get("_xsm_machine_cache")
        monkeypatch.setattr(
            Order, "statechart_machine", "xsm_review_charts:build"
        )
        monkeypatch.setattr(Order, "statechart_logic", None)
        if cache is not None:
            delattr(Order, "_xsm_machine_cache")
        try:
            a, b = Order(), Order()
            Order._xsm_resolve(a)
            Order._xsm_resolve(b)
            assert seen == [a, b]
            assert "_xsm_machine_cache" not in Order.__dict__
        finally:
            if "_xsm_machine_cache" in Order.__dict__:
                delattr(Order, "_xsm_machine_cache")
            if cache is not None:
                Order._xsm_machine_cache = cache  # type: ignore[attr-defined]

    def test_static_specs_stay_cacheable(self) -> None:
        from xstate_statemachine.contrib.django._machine import is_static_spec

        assert is_static_spec("machines/order.json", None)
        assert is_static_spec(CFG, "shop.logic")
        assert not is_static_spec(lambda row: None, None)

    def test_machine_node_with_logic_provider_is_not_silently_dropped(
        self,
    ) -> None:
        """CDO-12: a provider instance binds guards on a prebuilt node."""
        from xstate_statemachine.contrib.django._machine import (
            resolve_machine,
        )

        class Provider:
            def ok(self, ctx: Any, event: Any) -> bool:
                return False

        node = create_machine(CFG, logic=_true_logic())
        built = resolve_machine(node, logic=Provider())
        interp = SyncInterpreter(built).start()
        interp.send("GO")
        assert "gate.idle" in interp.current_state_ids  # guard bound: False

    def test_sqlalchemy_machine_must_be_a_machine_node(self) -> None:
        """CDO-12: the SQLAlchemy twin validates what it is handed."""
        _base, Doc = _sa_model()
        Doc.__xsm_machine__ = lambda row: "not a machine"
        with pytest.raises(TypeError, match="MachineNode"):
            Doc()._xsm_machine()


# -----------------------------------------------------------------------------
# CDO-02 / CDO-03: DRF
# -----------------------------------------------------------------------------
class TestDrf:
    def test_history_actor_accepts_any_pk_type(self) -> None:
        """CDO-02: UUID / str actor pks serialise; int pks stay ints."""
        from xstate_statemachine.contrib.drf.viewsets import (
            HistorySerializer,
        )

        base = {
            "seq": 1,
            "event": "E",
            "disposition": "transition",
            "from_states": [],
            "to_states": [],
            "actions": [],
            "reason": "",
            "created": "2026-01-01T00:00:00Z",
        }
        uid = uuid.uuid4()
        got = HistorySerializer({**base, "actor_id": uid}).data["actor"]
        assert got == str(uid)
        assert HistorySerializer({**base, "actor_id": 7}).data["actor"] == 7
        none = HistorySerializer({**base, "actor_id": None}).data["actor"]
        assert none is None

    @pytest.mark.django_db
    def test_unexpected_send_error_is_logged_not_leaked(
        self, monkeypatch: Any, caplog: Any
    ) -> None:
        """CDO-03: 500 body carries the class name; the log the detail."""
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from rest_framework.test import APIClient
        from shop.models import Order

        u = get_user_model().objects.create_user("cdo03", password="p")
        for code in ("view_order", "change_order"):
            u.user_permissions.add(Permission.objects.get(codename=code))
        u = get_user_model().objects.get(pk=u.pk)
        o = Order.objects.create()

        def boom(self: Any, *a: Any, **k: Any) -> Any:
            raise RuntimeError("secret detail")

        monkeypatch.setattr(Order, "send", boom)
        c = APIClient()
        c.force_authenticate(u)
        with caplog.at_level(logging.ERROR):
            r = c.post(f"/api/orders/{o.pk}/inc/", {}, format="json")
        assert r.status_code == 500
        assert r.json()["error"] == "RuntimeError"
        assert "secret detail" not in r.content.decode()
        logged = [
            rec for rec in caplog.records if rec.name.endswith("drf.viewsets")
        ]
        assert logged and logged[0].exc_info is not None


# -----------------------------------------------------------------------------
# CDO-04 / CDO-20 / CDO-23: DjangoStore
# -----------------------------------------------------------------------------
class TestDjangoStore:
    def test_bare_locked_substring_is_not_contention(self) -> None:
        """CDO-04: one anchored classifier, no private naive copy."""
        from xstate_statemachine.contrib.django import stores
        from xstate_statemachine.contrib.django._locking import (
            _is_lock_error,
        )

        assert not hasattr(stores, "_locked")
        assert not _is_lock_error(Exception("no such table: locked_orders"))
        assert _is_lock_error(Exception("database is locked"))

    @pytest.mark.django_db
    def test_schema_error_is_not_mapped_to_lock_timeout(
        self, monkeypatch: Any
    ) -> None:
        from xstate_statemachine.contrib.django.stores import DjangoStore

        s = DjangoStore()

        def bad(*a: Any, **k: Any) -> Any:
            raise OperationalError("no such table: locked_orders")

        monkeypatch.setattr(s, "_write", bad)
        with pytest.raises(OperationalError):
            s._save_raw("k", "{}", None, "", ())

    @pytest.mark.django_db
    def test_first_save_race_retries_the_update(
        self, monkeypatch: Any
    ) -> None:
        """CDO-20: a lost INSERT race becomes an UPDATE, not IntegrityError."""
        from xstate_statemachine.contrib.django.stores import DjangoStore

        s = DjangoStore()
        snap = '{"state_ids": [], "context": {}}'
        assert s.save("race", snap, expected_version=0) == 1
        real = s._bump
        calls: List[int] = []

        def first_misses(key: str, values: Dict[str, Any]) -> bool:
            calls.append(1)
            return False if len(calls) == 1 else bool(real(key, values))

        monkeypatch.setattr(s, "_bump", first_misses)
        assert s.save("race", snap) == 2
        assert len(calls) == 2
        assert IntegrityError  # the race is swallowed, not raised

    @pytest.mark.django_db
    def test_malformed_model_store_key_is_not_found(self) -> None:
        """CDO-23: ``"abc"`` for an integer pk names no row."""
        from shop.models import Order
        from xstate_statemachine.contrib.django.stores import DjangoModelStore

        s = DjangoModelStore(Order)
        assert s.load("abc") is None
        with pytest.raises(ConflictError):
            s._save_raw("abc", '{"state_ids": []}', None, "", ())


# -----------------------------------------------------------------------------
# CDO-05 / CDO-06: async SQLAlchemy store (sync-backed fake session)
# -----------------------------------------------------------------------------
class _NullTx:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *exc: Any) -> None:
        return None


class _FakeAsyncSession:
    def __init__(self, engine: Any) -> None:
        self._engine = engine

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    def begin(self) -> Any:
        return _NullTx()

    async def run_sync(self, fn: Any) -> Any:
        with self._engine.begin() as conn:
            return fn(types.SimpleNamespace(connection=lambda: conn))


def _async_store(tmp_path: Any, **kw: Any) -> Any:
    from sqlalchemy import create_engine

    from xstate_statemachine.contrib.sqlalchemy.store import (
        AsyncSQLAlchemyStore,
    )

    eng = create_engine(f"sqlite:///{tmp_path / 'a.db'}")
    store = AsyncSQLAlchemyStore(lambda: _FakeAsyncSession(eng), **kw)
    store._engine = eng  # type: ignore[attr-defined]
    return store


class TestAsyncSqlAlchemyStore:
    def test_busy_database_maps_to_lock_timeout(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        """CDO-05: save / load / delete / forget all map contention."""
        from sqlalchemy.exc import OperationalError as SAOperationalError

        from xstate_statemachine.contrib.sqlalchemy import _ops

        store = _async_store(tmp_path)

        def busy(*a: Any, **k: Any) -> Any:
            raise SAOperationalError(
                "stmt", {}, Exception("database is locked")
            )

        for name in ("save_raw", "load_raw", "delete_raw", "forget_raw"):
            monkeypatch.setattr(_ops, name, busy)

        async def go() -> None:
            snap = '{"state_ids": []}'
            with pytest.raises(LockTimeoutError):
                await store.save("k", snap)
            with pytest.raises(LockTimeoutError):
                await store.load("k")
            with pytest.raises(LockTimeoutError):
                await store.delete("k")
            with pytest.raises(LockTimeoutError):
                await store.forget("k")

        asyncio.run(go())

    def test_create_tables_false_still_checks_the_schema(
        self, tmp_path: Any
    ) -> None:
        """CDO-06: missing tables are explained, a NEWER schema refused."""
        from sqlalchemy import update

        from xstate_statemachine.contrib.sqlalchemy._schema import (
            ensure_schema,
        )

        store = _async_store(tmp_path, create_tables=False)

        async def missing() -> None:
            with pytest.raises(StoreError, match="missing"):
                await store.load("k")

        asyncio.run(missing())
        with store._engine.begin() as conn:
            ensure_schema(conn, store.tables)
            conn.execute(update(store.tables.schema).values(version=999))

        async def newer() -> None:
            with pytest.raises(StoreError):
                await store.load("k")

        asyncio.run(newer())


# -----------------------------------------------------------------------------
# CDO-07 / CDO-08 / CDO-22: Django fsm dual-write and the fields
# -----------------------------------------------------------------------------
class TestFsmAndFields:
    def test_dual_write_uses_the_written_snapshot(self) -> None:
        """CDO-07: engine steps of the same send are in the snapshot only."""
        from xstate_statemachine.contrib.django import fsm

        captured: Dict[str, Any] = {}

        class Base:
            def _xsm_after_write(self, ctx: Any) -> None:
                return None

        class Row(fsm.FSMDualWriteMixin, Base):  # type: ignore[misc]
            pk = 1

            def statechart_machine_node(self) -> Any:
                return object()

            def _xsm_fsm_value(self, machine: Any, leaves: Any) -> Any:
                captured["leaves"] = leaves
                return fsm._NO_VALUE

        receipt = types.SimpleNamespace(state_ids=["m.a"])
        Row()._xsm_after_write(
            {
                "receipt": receipt,
                "snapshot": {"state_ids": ["m.c", "m.b"]},
                "using": "default",
            }
        )
        assert captured["leaves"] == ["m.b", "m.c"]

    def test_wide_state_column_is_a_clear_validation_error(self) -> None:
        """CDO-08: no silent SQLite-only success; migrations unchanged."""
        from shop.models import Order

        col = Order._meta.get_field("statechart_state")
        assert col.get_prep_value("x" * 10) == "x" * 10
        with pytest.raises(ValidationError, match="state_max_length"):
            col.get_prep_value("x" * 600)
        assert col.deconstruct()[1] == "django.db.models.CharField"

    def test_malformed_snapshot_string_is_a_validation_error(self) -> None:
        """CDO-22: a bare JSONDecodeError no longer escapes the field."""
        from shop.models import Order

        f = Order._meta.get_field("statechart")
        with pytest.raises(ValidationError):
            f.get_prep_value("{not json")


# -----------------------------------------------------------------------------
# CDO-10 / CDO-11: admin
# -----------------------------------------------------------------------------
class TestAdmin:
    def test_render_change_form_keeps_djangos_positional_order(self) -> None:
        """CDO-10: ``(request, context, add, change, form_url, obj)``."""
        from xstate_statemachine.contrib.django.admin import (
            StatechartAdminMixin,
        )

        sig = inspect.signature(StatechartAdminMixin.render_change_form)
        assert list(sig.parameters) == [
            "self",
            "request",
            "context",
            "add",
            "change",
            "form_url",
            "obj",
        ]

    def test_bulk_action_survives_one_bad_row(self) -> None:
        """CDO-11: an unexpected error on one row fails that row only."""
        from xstate_statemachine.contrib.django.admin import (
            StatechartAdminMixin,
        )

        class Row:
            def __init__(self, pk: int, outcome: Any) -> None:
                self.pk, self.outcome = pk, outcome

            def send(self, event: str, **kw: Any) -> Any:
                if isinstance(self.outcome, Exception):
                    raise self.outcome
                return self.outcome

        ok = types.SimpleNamespace(changed=True, error=None, denied=False)
        refused = types.SimpleNamespace(changed=False, error=None, denied=True)
        errored = types.SimpleNamespace(
            changed=False, error=RuntimeError("x"), denied=False
        )
        rows = [
            Row(1, IntegrityError("boom")),
            Row(2, ok),
            Row(3, refused),
            Row(4, errored),
        ]

        class QS:
            def iterator(self, chunk_size: int = 0) -> Any:
                return iter(rows)

        sent: List[Any] = []
        stub = types.SimpleNamespace(
            _allowed=lambda request, obj, event: True,
            model=type(
                "M", (), {"DoesNotExist": type("DNE", (Exception,), {})}
            ),
            message_user=lambda request, text, level: sent.append(
                (text, level)
            ),
        )
        act = StatechartAdminMixin._bulk_action(None, "GO", "Go")  # type: ignore[arg-type]
        act(stub, types.SimpleNamespace(user=None), QS())
        text, _level = sent[0]
        assert "1 changed" in text and "1 denied" in text
        assert "2 failed" in text


# -----------------------------------------------------------------------------
# CDO-13 / CDO-23 / CDO-37: SQLAlchemy mixin and model store
# -----------------------------------------------------------------------------
def _sa_model() -> Any:
    from xstate_statemachine.contrib.sqlalchemy import (
        StatechartMixin,
        StatechartType,
        xsm_sqlalchemy_ddl,
    )

    class Base(DeclarativeBase):
        pass

    class Doc(StatechartMixin, Base):
        __tablename__ = "docs_cdo"
        __xsm_machine__ = create_machine(
            {
                "id": "doc",
                "initial": "a",
                "context": {"pii": "x"},
                "states": {"a": {"on": {"GO": {"actions": "mark"}}}},
            },
            logic=MachineLogic(
                actions={
                    "mark": lambda i, c, e, a: c.update(got=dict(e.payload))
                }
            ),
        )
        id: Mapped[int] = mapped_column(primary_key=True)
        statechart: Mapped[Optional[Dict[str, Any]]] = mapped_column(
            StatechartType, nullable=True
        )
        __mapper_args__ = StatechartMixin.optimistic()

    xsm_sqlalchemy_ddl(Base.metadata)
    return Base, Doc


class TestSqlAlchemyMixin:
    def test_send_takes_an_explicit_payload_mapping(
        self, tmp_path: Any
    ) -> None:
        """CDO-13: ``payload=`` cannot collide with send()'s options."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from xstate_statemachine.contrib.sqlalchemy.mixin import (
            RESERVED_PAYLOAD_KEYS,
            reserved_keys,
        )

        assert reserved_keys({"lock": 1, "x": 2}) == ["lock"]
        assert {"session", "lock", "plugins"} <= RESERVED_PAYLOAD_KEYS
        Base, Doc = _sa_model()
        eng = create_engine(f"sqlite:///{tmp_path / 'd.db'}")
        Base.metadata.create_all(eng)
        with Session(eng) as s:
            d = Doc()
            s.add(d)
            s.commit()
            r = d.send("GO", session=s, payload={"lock": "none", "k": 1})
            assert r.changed
            assert d.statechart["context"]["got"] == {"lock": "none", "k": 1}
        eng.dispose()

    def test_model_store_forget_erases_the_snapshot(
        self, tmp_path: Any
    ) -> None:
        """CDO-37: parity with the Django model store (X0.5)."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session, sessionmaker

        from xstate_statemachine.contrib.sqlalchemy import ModelStore

        Base, Doc = _sa_model()
        eng = create_engine(f"sqlite:///{tmp_path / 'm.db'}")
        Base.metadata.create_all(eng)
        with Session(eng) as s:
            d = Doc()
            s.add(d)
            s.commit()
            d.send("GO", session=s, payload={"k": 1})
            s.commit()
            pk = d.id
        store = ModelStore(sessionmaker(eng), Doc)
        assert store.load(str(pk)) is not None
        assert store.forget(str(pk))["snapshots"] == 1
        assert store.load(str(pk)) is None
        with Session(eng) as s:
            row = s.get(Doc, pk)
            assert row.statechart is None and row.statechart_state is None
        eng.dispose()

    def test_model_store_malformed_key_is_not_found(self) -> None:
        """CDO-23: ``ValueError`` from ``int("abc")`` no longer escapes."""
        from sqlalchemy import Integer

        from xstate_statemachine.contrib.sqlalchemy.model_store import (
            ModelStore,
        )

        stub: Any = types.SimpleNamespace(
            pk=types.SimpleNamespace(type=Integer())
        )
        assert ModelStore._pk_value(stub, "abc") is None
        assert ModelStore._pk_value(stub, "12") == 12


# -----------------------------------------------------------------------------
# CDO-15 / CDO-17 / CDO-26 / CDO-33 / CDO-39: small behaviours
# -----------------------------------------------------------------------------
class TestSmallBehaviours:
    @pytest.mark.django_db
    def test_deadline_worker_survives_a_transient_database_error(
        self,
    ) -> None:
        """CDO-15: only the FIRST pass may abort (migrate hint)."""
        from django.db import DatabaseError

        from xstate_statemachine.contrib.django.management.commands import (
            xsm_deadlines,
        )

        stop = threading.Event()
        passes: List[int] = []

        class Scanner:
            def run_once(self) -> None:
                passes.append(1)
                if len(passes) == 2:
                    raise DatabaseError("server closed the connection")
                if len(passes) >= 3:
                    stop.set()

        cmd = xsm_deadlines.Command()
        cmd.stdout = types.SimpleNamespace(write=lambda *_: None)  # type: ignore[assignment]
        cmd._forever([(object, Scanner())], 0.0, stop)
        assert len(passes) == 3

        class Dead:
            def run_once(self) -> None:
                raise DatabaseError("no such table")

        with pytest.raises(DatabaseError):
            cmd._forever([(object, Dead())], 0.0, threading.Event())

    def test_signals_private_id_helper_matches_django(self) -> None:
        """CDO-17: pin the local copy against Django's private original."""
        from django.dispatch import dispatcher

        from xstate_statemachine.contrib.django.signals import _make_id

        class C:
            def m(self) -> None:
                return None

        c = C()
        private = getattr(dispatcher, "_make_id", None)
        for target in (c.m, C.m, len):
            if private is not None:
                assert _make_id(target) == private(target)
        assert _make_id(c.m) == _make_id(c.m)  # stable across accesses

    def test_permission_guard_rejects_an_always_deny_combo(self) -> None:
        """CDO-26: ``object_level=False, fallback_global=False``."""
        from xstate_statemachine.contrib.django.permissions import (
            PermissionGuard,
        )

        with pytest.raises(ValueError, match="deny every row"):
            PermissionGuard("a.b", object_level=False, fallback_global=False)
        PermissionGuard("a.b", object_level=False)  # global only: fine

    def test_marker_session_unwinds_a_partial_enter(
        self, monkeypatch: Any
    ) -> None:
        """CDO-33: a failing 2nd ``_enter`` leaves nothing counted."""
        from xstate_statemachine.contrib.django import _markers
        from xstate_statemachine.persistence.locking import current_session

        class M:
            buffer_marks = False

            def discard_marks(self) -> None:
                return None

        good, bad = M(), M()
        real = _markers._enter

        def enter(m: Any) -> None:
            if m is bad:
                raise RuntimeError("enter failed")
            real(m)

        monkeypatch.setattr(_markers, "_enter", enter)
        before = current_session.get(None)
        with pytest.raises(RuntimeError):
            with _markers._marker_session([good, bad]):
                pass  # pragma: no cover
        assert id(good) not in _markers._open
        assert current_session.get(None) is before

    def test_lock_timeout_units(self) -> None:
        """CDO-39: ``1h`` / ``250ms`` / bare ms parse (no ``rstrip`` hack)."""
        from xstate_statemachine.contrib.django._locking import _TIMEOUT

        for raw, num, unit in (
            ("1h", "1", "h"),
            ("250ms", "250", "ms"),
            ("5s", "5", "s"),
            ("2min", "2", "min"),
            ("0", "0", ""),
        ):
            m = _TIMEOUT.fullmatch(raw)
            assert m is not None and (m.group(1), m.group(2)) == (num, unit)


# -----------------------------------------------------------------------------
# CDO-34 / CDO-35: Channels consumer
# -----------------------------------------------------------------------------
class TestConsumer:
    @pytest.mark.django_db
    def test_deleted_row_is_a_404_problem_not_a_dead_task(self) -> None:
        """CDO-35: ``refresh_from_db`` on a deleted row."""
        from shop.models import Order
        from xstate_statemachine.contrib.channels.consumer import (
            StatechartConsumer,
        )

        o = Order.objects.create()
        Order.objects.filter(pk=o.pk).delete()
        stub: Any = types.SimpleNamespace(
            _still_allowed=lambda: True,
            scope={"user": None},
            instance=o,
        )
        out = StatechartConsumer._send(stub, "INC", {})
        assert out["problem"]["status"] == 404

    def test_oversize_frame_is_refused_before_decoding(self) -> None:
        """CDO-34: ``max_frame_bytes`` caps inbound text frames."""
        from xstate_statemachine.contrib.channels.consumer import (
            StatechartConsumer,
        )

        errors: List[Any] = []

        async def _error(status: int, title: str) -> None:
            errors.append((status, title))

        def no_decode(text: str) -> Any:
            raise AssertionError("must not decode an oversize frame")

        stub: Any = types.SimpleNamespace(
            instance=object(),
            _error=_error,
            max_frame_bytes=StatechartConsumer.max_frame_bytes,
            decode_json=no_decode,
        )
        big = "x" * (StatechartConsumer.max_frame_bytes + 1)
        asyncio.run(StatechartConsumer.receive(stub, text_data=big))
        assert errors == [(422, "Frame too large")]
