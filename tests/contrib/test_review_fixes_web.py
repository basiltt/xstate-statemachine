# tests/contrib/test_review_fixes_web.py
"""Regression tests for the contrib-web code-quality review (CW-*).

One test (or a few) per finding, named after its id. Deterministic: no
sleeps beyond the shortest timeouts a case needs, no network.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from typing import Any, Dict, List

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryLog,
    MemoryStore,
)

# -----------------------------------------------------------------------------
# 🧩 Shared machines
# -----------------------------------------------------------------------------
FINAL_CFG = {
    "id": "fin",
    "initial": "idle",
    "states": {"idle": {"on": {"GO": "done"}}, "done": {"type": "final"}},
}

COUNTER_CFG = {
    "id": "counter",
    "initial": "on",
    "context": {"n": 0},
    "states": {"on": {"on": {"INC": {"actions": "inc"}}}},
}


def _counter() -> Any:
    def inc(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        ctx["n"] += 1

    return create_machine(
        COUNTER_CFG, logic=MachineLogic(actions={"inc": inc})
    )


def _entry_machine(calls: List[str]) -> Any:
    def mark(i: Any, ctx: Any, e: Any, a: Any) -> None:
        calls.append("entry")

    return create_machine(
        {
            "id": "ent",
            "initial": "a",
            "states": {"a": {"entry": "mark", "on": {"GO": "b"}}, "b": {}},
        },
        logic=MachineLogic(actions={"mark": mark}),
    )


# =============================================================================
# 🌐 Framework-neutral units (no extra needed beyond core)
# =============================================================================
class TestNeutralHelpers:
    def test_cw13_operation_ids_stable_when_event_added_without_collision(
        self,
    ) -> None:
        from src.xstate_statemachine.contrib._openapi import operation_ids

        before = operation_ids("o", ["ORDER.PAID", "REFUND"])
        after = operation_ids("o", ["ORDER.PAID", "REFUND", "SHIP"])
        assert {k: after[k] for k in before} == before

    def test_cw30_unsafe_event_names_fail_at_build(self) -> None:
        from src.xstate_statemachine.contrib._openapi import (
            require_route_safe_events,
        )

        # 📝 A plain space is served (as `%20`); only control whitespace
        #    and the path-template characters are refused.
        require_route_safe_events(
            ["ORDER.PAID", "pay-now", "pay now", "éclair"]
        )
        for bad in ("order/paid", "a{b}", "a?b", "a#b", "a\tb", "a\nb", "a%b"):
            with pytest.raises(ValueError, match="Event"):
                require_route_safe_events(["OK", bad])

    def test_cw18_positive_finite_rules(self) -> None:
        from src.xstate_statemachine.contrib._compat import positive_finite

        assert positive_finite("x", 2) == 2.0
        assert positive_finite("x", 0, allow_zero=True) == 0.0
        for bad in (0, -1, float("nan"), float("inf"), True, "3", None):
            with pytest.raises(ValueError):
                positive_finite("x", bad)

    def test_cw33_origin_rule_is_case_insensitive_for_host(self) -> None:
        from src.xstate_statemachine.contrib._compat import origin_is_allowed

        assert origin_is_allowed(None, None)
        assert origin_is_allowed("http://Example.COM", "example.com")
        assert origin_is_allowed("http://example.com", "Example.com")
        assert not origin_is_allowed("http://evil.com", "example.com")
        assert not origin_is_allowed("http://example.com", None)
        assert origin_is_allowed("http://x.io", "y", {"http://x.io"})


class TestFlaskHttpNeutral:
    """`flask/_http.py` imports nothing framework-specific."""

    def test_cw08_deeply_nested_json_is_422_not_recursion_error(self) -> None:
        from src.xstate_statemachine.contrib.flask._http import (
            UnprocessableBodyError,
            parse_json_body,
        )

        raw = b"[" * 200_000
        with pytest.raises(UnprocessableBodyError):
            parse_json_body(
                "application/json",
                len(raw),
                lambda n: raw[:n],
                max_body_bytes=1_000_000,
            )

    def test_cw03_idempotency_header_rules(self) -> None:
        from src.xstate_statemachine.contrib.flask._http import (
            BadRequestError,
            IdempotencyNotConfiguredError,
            idempotency_key_from_header,
        )

        assert idempotency_key_from_header(None, has_inbox=False) is None
        assert idempotency_key_from_header("k1", has_inbox=True) == "k1"
        with pytest.raises(BadRequestError):
            idempotency_key_from_header("x" * 300, has_inbox=True)
        with pytest.raises(BadRequestError):
            idempotency_key_from_header("clé", has_inbox=True)
        with pytest.raises(IdempotencyNotConfiguredError):
            idempotency_key_from_header("k1", has_inbox=False)

    def test_cw04_client_body_cannot_carry_idempotency_key(self) -> None:
        from src.xstate_statemachine.contrib.flask._http import (
            ReservedKeyError,
            refuse_reserved_send_keys,
        )

        refuse_reserved_send_keys({"note": "x", "id": 1})
        with pytest.raises(ReservedKeyError):
            refuse_reserved_send_keys({"idempotency_key": "k"})

    def test_cw17b_history_args_reject_negative(self) -> None:
        from src.xstate_statemachine.contrib.flask._http import (
            BadRequestError,
            history_args,
        )

        assert history_args({}) == (0, 100)
        assert history_args({"limit": "5000"}) == (0, 1000)
        for args in ({"limit": "-1"}, {"after": "-3"}, {"after": "x"}):
            with pytest.raises(BadRequestError):
                history_args(args)

    def test_cw06_history_items_drop_payload(self) -> None:
        from src.xstate_statemachine.contrib.flask._http import history_items

        class Row:
            def to_dict(self) -> Dict[str, Any]:
                return {"seq": 1, "event_payload": {"card": "4242"}}

        assert history_items([Row()]) == [{"seq": 1}]

    def test_cw17_status_tables_agree_on_shared_exceptions(self) -> None:
        from src.xstate_statemachine.exceptions import (
            InterpreterStoppedError,
            SnapshotTooLargeError,
        )

        fl = pytest.importorskip("src.xstate_statemachine.contrib.flask._http")
        assert fl.status_for_exception(InterpreterStoppedError("x")) == 409
        assert (
            fl.status_for_exception(SnapshotTooLargeError("k", 10, 5)) == 413
        )

    def test_cw09_log_problem_logs_5xx_with_traceback_not_4xx(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        from src.xstate_statemachine.contrib.flask._http import (
            ForbiddenError,
            log_problem,
        )

        with caplog.at_level(logging.WARNING):
            log_problem(ForbiddenError(), "GET /x")
            assert not caplog.records
            try:
                raise RuntimeError("boom")
            except RuntimeError as exc:
                log_problem(exc, "POST /y")
        assert any(
            r.levelno == logging.ERROR and r.exc_info for r in caplog.records
        )


class TestFlaskFanout:
    def _fan(self) -> Any:
        from src.xstate_statemachine.contrib.flask._core import Fanout

        return Fanout(max_connections_per_key=2)

    def test_cw14_no_state_without_subscribers(self) -> None:
        fan = self._fan()
        fan.publish("m", "1", [{"a": 1}])
        assert fan._seq == {} and fan._last == {}

    def test_cw14_sequence_state_dropped_with_last_unsubscribe(self) -> None:
        fan = self._fan()
        q = fan.subscribe("m", "1")
        fan.publish("m", "1", [{"a": 1}, {"a": 2}])
        assert fan.seq("m", "1") == 2
        fan.unsubscribe("m", "1", q)
        assert fan._seq == {} and fan._last == {} and fan._subs == {}

    def test_cw14_full_queue_cuts_the_client_off(self) -> None:
        from src.xstate_statemachine.contrib.flask._core import (
            CLOSED,
            MAX_BACKLOG,
        )

        fan = self._fan()
        q = fan.subscribe("m", "1")
        fan.publish("m", "1", [{"i": i} for i in range(MAX_BACKLOG + 5)])
        assert fan.connections("m", "1") == 0
        seen = []
        while not q.empty():
            seen.append(q.get_nowait())
        assert seen[-1] is CLOSED

    def test_cw10_wake_callback_fires_on_put(self) -> None:
        fan = self._fan()
        woken: List[int] = []
        fan.subscribe("m", "1", lambda: woken.append(1))
        fan.publish("m", "1", [{"a": 1}])
        assert woken == [1]


# =============================================================================
# 📡 Starlette registry / streaming
# =============================================================================
try:
    import starlette  # noqa: F401

    HAVE_STARLETTE = True
except ImportError:  # pragma: no cover -- a cell without the extra
    HAVE_STARLETTE = False

if HAVE_STARLETTE:
    from src.xstate_statemachine.contrib.starlette import (
        StatechartRegistry,
        allow_all,
    )
    from src.xstate_statemachine.contrib.starlette._http import (
        ReservedKeyError,
        json_body,
        problem_for_exception_logged,
        refuse_reserved_send_keys,
        status_for_exception,
    )

    from .starlette._support import RawSSE, build_app, counter_machine

needs_starlette = pytest.mark.skipif(
    not HAVE_STARLETTE, reason="extra [starlette] not installed"
)


def _reg(machine: Any = None, name: str = "m", **kw: Any) -> Any:
    reg = StatechartRegistry(MemoryStore(), **kw)
    reg.register(name, machine or _counter(), authorize=allow_all)
    return reg


@needs_starlette
class TestStarletteRegistry:
    def test_cw01_resident_that_finished_is_saved_on_release(self) -> None:
        async def go() -> None:
            reg = _reg(create_machine(FINAL_CFG), name="fin")
            interp = await reg.resident("fin", "k")
            await interp.send("GO", wait=True)
            assert interp.status == "done"
            await reg.release_resident("fin", "k")
            body = await reg.peek("fin", "k")
            assert body["state"] == "done"
            assert await reg.exists("fin", "k")

        asyncio.run(go())

    def test_cw01_finished_resident_saved_on_shutdown(self) -> None:
        async def go() -> None:
            reg = _reg(create_machine(FINAL_CFG), name="fin")
            async with reg.lifespan():
                interp = await reg.resident("fin", "k")
                await interp.send("GO", wait=True)
            assert (await reg.peek("fin", "k"))["state"] == "done"

        asyncio.run(go())

    @pytest.mark.parametrize(
        "opt",
        [
            "scanner_interval_s",
            "drain_timeout_s",
            "resident_idle_ttl_s",
            "max_body_bytes",
        ],
    )
    def test_cw18_bad_numeric_options_fail_at_construction(
        self, opt: str
    ) -> None:
        for bad in (0, -1, float("nan")):
            if opt == "max_body_bytes" and bad == 0:
                continue  # 0 = "no body allowed" is a documented setting
            with pytest.raises(ValueError):
                StatechartRegistry(MemoryStore(), **{opt: bad})

    def test_cw18_settle_timeout_zero_allowed_negative_not(self) -> None:
        StatechartRegistry(MemoryStore(), settle_timeout=0)
        with pytest.raises(ValueError):
            StatechartRegistry(MemoryStore(), settle_timeout=-1)

    def test_cw19_missing_principal_is_a_typed_configuration_error(
        self,
    ) -> None:
        from src.xstate_statemachine.contrib.starlette._http import (
            PrincipalNotConfiguredError,
        )

        reg = StatechartRegistry(MemoryStore(), inbox=MemoryInbox())
        with pytest.raises(PrincipalNotConfiguredError) as info:
            reg._principal_of(object())  # type: ignore[arg-type]
        assert isinstance(info.value, ValueError)
        assert status_for_exception(info.value) == 500

    def test_cw04_body_idempotency_key_is_refused(self) -> None:
        with pytest.raises(ReservedKeyError):
            refuse_reserved_send_keys({"idempotency_key": "x" * 300})
        refuse_reserved_send_keys({"id": "ok"})

    def test_cw04_http_send_with_body_key_is_422(self) -> None:
        from starlette.testclient import TestClient

        reg = _reg(counter_machine(), name="payment")
        app = build_app(reg, "payment")
        with TestClient(app) as c:
            r = c.post("/m/1/events/INC", json={"idempotency_key": "k" * 300})
        assert r.status_code == 422

    def test_cw08_deeply_nested_body_is_422(self) -> None:
        from src.xstate_statemachine.contrib.starlette._http import (
            UnprocessableBodyError,
        )

        raw = b"[" * 200_000

        class Req:
            headers = {
                "content-type": "application/json",
                "content-length": str(len(raw)),
            }

            async def stream(self) -> Any:
                yield raw

        with pytest.raises(UnprocessableBodyError):
            asyncio.run(json_body(Req(), max_body_bytes=1_000_000))  # type: ignore[arg-type]

    def test_cw17_snapshot_too_large_maps_to_413(self) -> None:
        from src.xstate_statemachine.exceptions import SnapshotTooLargeError

        assert status_for_exception(SnapshotTooLargeError("k", 10, 5)) == 413

    def test_cw22_logged_problem_traces_5xx(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.ERROR):
            resp = problem_for_exception_logged(RuntimeError("bug"), "GET /x")
        assert resp.status_code == 500
        assert any(r.exc_info for r in caplog.records)

    def test_cw31_cut_off_last_subscriber_leaves_no_sequence(self) -> None:
        from src.xstate_statemachine.contrib.starlette._fanout import (
            MAX_BACKLOG,
            _Subscribers,
        )

        async def go() -> None:
            subs = _Subscribers()
            subs.subscribe("m", "1")
            subs.publish("m", "1", [{"i": i} for i in range(MAX_BACKLOG + 10)])
            assert subs._seq == {} and subs._subs == {}

        asyncio.run(go())

    def test_cw16_transition_between_snapshot_and_subscribe_is_not_lost(
        self,
    ) -> None:
        reg = _reg(counter_machine(), name="payment")
        app = build_app(reg, "payment")
        real_peek = reg.peek

        async def peek_then_commit(name: str, key: str) -> Any:
            body = await real_peek(name, key)
            # a commit lands right after the snapshot was read
            reg.subscribers.publish(name, key, [{"state": "later"}])
            return body

        reg.peek = peek_then_commit  # type: ignore[method-assign]

        async def go() -> None:
            sse = RawSSE(app, "/m/1/stream")
            assert await sse.open() == 200
            _, ev, _snap = await sse.next_event()
            assert ev == "snapshot"
            seq, ev, data = await sse.next_event()
            assert ev == "transition" and data == {"state": "later"}
            assert seq == 1
            await sse.close()

        asyncio.run(go())

    def test_cw32_non_json_snapshot_is_a_problem_not_a_torn_stream(
        self,
    ) -> None:
        reg = StatechartRegistry(MemoryStore())
        reg.register(
            "m",
            _counter(),
            authorize=allow_all,
            context_serializer=lambda ctx: {"bad": object()},
        )
        app = build_app(reg, "m")

        async def go() -> None:
            sse = RawSSE(app, "/m/1/stream")
            assert await sse.open() == 500
            await sse.body()
            assert reg.connections() == 0
            assert reg.subscribers.count() == 0

        asyncio.run(go())


# =============================================================================
# 🧪 Flask extension + blueprint
# =============================================================================
class TestFlask:
    @pytest.fixture(autouse=True)
    def _need_flask(self) -> None:
        pytest.importorskip("flask")

    def _app(self, **kw: Any) -> Any:
        from .flask.conftest import make_app

        return make_app(MemoryStore(), **kw)

    def test_cw03_bad_idempotency_key_is_400_and_no_inbox_is_501(self) -> None:
        c = self._app(inbox=MemoryInbox()).test_client()
        r = c.post(
            "/orders/1/send",
            json={"type": "ADD"},
            headers={"Idempotency-Key": "x" * 300},
        )
        assert r.status_code == 400
        c2 = self._app().test_client()
        r = c2.post(
            "/orders/1/send",
            json={"type": "ADD"},
            headers={"Idempotency-Key": "k1"},
        )
        assert r.status_code == 501

    def test_cw04_body_idempotency_key_is_422(self) -> None:
        c = self._app(inbox=MemoryInbox()).test_client()
        r = c.post(
            "/orders/1/send",
            json={"type": "ADD", "idempotency_key": "x" * 300},
        )
        assert r.status_code == 422

    def test_cw17b_negative_history_bounds_are_400(self) -> None:
        c = self._app(log=MemoryLog()).test_client()
        assert c.get("/orders/1/history?limit=-1").status_code == 400
        assert c.get("/orders/1/history?after=-1").status_code == 400
        assert c.get("/orders/1/history").status_code == 200

    def test_cw05_peek_of_missing_key_runs_no_entry_action(self) -> None:
        from flask import Flask

        from src.xstate_statemachine.contrib.flask import (
            XState,
            allow_all as flask_allow,
            create_statechart_blueprint,
        )

        calls: List[str] = []
        xsm = XState()
        xsm.register("ent", _entry_machine(calls), authorize=flask_allow)
        app = Flask(__name__)
        xsm.init_app(app, store=MemoryStore())
        app.register_blueprint(create_statechart_blueprint(xsm, "ent", "/e"))
        c = app.test_client()
        r = c.get("/e/new")
        assert r.status_code == 200 and r.get_json()["state"] == "a"
        assert c.get("/e/new/events").status_code == 200
        assert calls == []

    def test_cw20_anonymous_act_is_401_not_500(self) -> None:
        from flask import g

        app = self._app(inbox=MemoryInbox(), principal=lambda req: None)

        @app.post("/custom")
        def custom() -> Any:
            with g.xsm.act("order", "1"):
                pass
            return "ok"

        r = app.test_client().post("/custom")
        assert r.status_code == 401

    def test_cw18_flask_registry_validates_heartbeat_and_body_cap(
        self,
    ) -> None:
        from src.xstate_statemachine.contrib.flask._core import AppRegistry

        for bad in (0, -1, float("nan")):
            with pytest.raises(ValueError):
                AppRegistry(MemoryStore(), heartbeat_s=bad)
        with pytest.raises(ValueError):
            AppRegistry(MemoryStore(), max_body_bytes=-1)

    def test_cw16_flask_stream_subscribes_before_reading_snapshot(
        self,
    ) -> None:
        from src.xstate_statemachine.contrib.flask._core import AppRegistry
        from src.xstate_statemachine.contrib.flask.blueprint import _stream

        app = self._app()
        reg = AppRegistry(MemoryStore())
        order: List[str] = []
        real = reg.fanout.subscribe

        def sub(*a: Any, **k: Any) -> Any:
            order.append("subscribe")
            return real(*a, **k)

        reg.fanout.subscribe = sub  # type: ignore[method-assign]

        def snap() -> Dict[str, Any]:
            order.append("snapshot")
            return {"state": "x"}

        with app.test_request_context("/?once=1"):
            resp = _stream(reg, "order", "1", snap)
            body = "".join(resp.response)
        assert order == ["subscribe", "snapshot"]
        assert "event: snapshot" in body

    def test_cw27_cli_exit_codes(self) -> None:
        import click

        from src.xstate_statemachine.contrib.flask.cli import _run

        _run(lambda: (_ for _ in ()).throw(SystemExit(None)))
        _run(lambda: (_ for _ in ()).throw(SystemExit(0)))
        with pytest.raises(click.exceptions.Exit) as info:
            _run(lambda: (_ for _ in ()).throw(SystemExit(3)))
        assert info.value.exit_code == 3
        with pytest.raises(click.exceptions.Exit) as info:
            _run(lambda: (_ for _ in ()).throw(SystemExit("bad thing")))
        assert info.value.exit_code == 1


# =============================================================================
# ⚡ Quart shim
# =============================================================================
class TestQuart:
    @pytest.fixture(autouse=True)
    def _need_quart(self) -> None:
        pytest.importorskip("flask")
        pytest.importorskip("quart")

    def _app(self, machine: Any = None, **kw: Any) -> Any:
        import quart

        from src.xstate_statemachine.contrib.flask.quart import (
            QuartXState,
            create_quart_statechart_blueprint,
        )
        from src.xstate_statemachine.contrib.flask import allow_all as q_allow

        from .flask.conftest import order_machine

        xsm = QuartXState()
        xsm.register("order", machine or order_machine(), authorize=q_allow)
        app = quart.Quart(__name__)
        if kw.get("inbox") is not None:
            kw.setdefault("principal", lambda r: r.headers.get("X-User", "u"))
        xsm.init_app(app, store=MemoryStore(), **kw)
        app.register_blueprint(
            create_quart_statechart_blueprint(xsm, "order", "/orders")
        )
        return app

    def test_cw06_history_omits_payload_and_validates_bounds(self) -> None:
        async def go() -> None:
            app = self._app(log=MemoryLog())
            c = app.test_client()
            r = await c.post(
                "/orders/1/send", json={"type": "ADD", "n": 2, "pin": "1234"}
            )
            assert r.status_code == 200
            r = await c.get("/orders/1/history")
            assert r.status_code == 200
            items = (await r.get_json())["items"]
            assert items and all("event_payload" not in i for i in items)
            assert b"1234" not in await r.get_data()
            r = await c.get("/orders/1/history?limit=-1")
            assert r.status_code == 400

        asyncio.run(go())

    def test_cw03_bad_idempotency_key_is_400_and_no_inbox_501(self) -> None:
        async def go() -> None:
            c = self._app(inbox=MemoryInbox()).test_client()
            r = await c.post(
                "/orders/1/send",
                json={"type": "ADD"},
                headers={"Idempotency-Key": "x" * 300},
            )
            assert r.status_code == 400
            c2 = self._app().test_client()
            r = await c2.post(
                "/orders/1/send",
                json={"type": "ADD"},
                headers={"Idempotency-Key": "k1"},
            )
            assert r.status_code == 501
            r = await c2.post(
                "/orders/1/send",
                json={"type": "ADD", "idempotency_key": "k1"},
            )
            assert r.status_code == 422

        asyncio.run(go())

    def test_cw05_peek_of_missing_key_runs_no_entry_action(self) -> None:
        async def go() -> None:
            calls: List[str] = []
            app = self._app(machine=_entry_machine(calls))
            c = app.test_client()
            r = await c.get("/orders/new")
            assert (await r.get_json())["state"] == "a"
            assert calls == []

        asyncio.run(go())

    def test_cw09_unexpected_500_is_logged_with_traceback(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        async def go() -> None:
            c = self._app().test_client()
            await c.post("/orders/1/send", json={"type": "ADD"})
            await c.post("/orders/1/send", json={"type": "CHECKOUT"})
            r = await c.post("/orders/1/send", json={"type": "BOOM"})
            assert r.status_code == 500

        with caplog.at_level(logging.ERROR):
            asyncio.run(go())
        assert any(r.exc_info for r in caplog.records) or any(
            "statechart request" in r.getMessage() for r in caplog.records
        )

    def test_cw11_body_read_is_capped_and_timed(self) -> None:
        from src.xstate_statemachine.contrib.flask.quart import _read_body

        async def go() -> None:
            app = self._app()
            async with app.test_request_context(
                "/orders/1/send", method="POST", data=b"x" * 100
            ):
                from src.xstate_statemachine.contrib.flask._http import (
                    PayloadTooLargeError,
                )

                with pytest.raises(PayloadTooLargeError):
                    await _read_body(10, 1.0)

        asyncio.run(go())

    def test_cw10_sse_wait_uses_event_not_a_thread(self) -> None:
        from src.xstate_statemachine.contrib.flask._core import Fanout
        from src.xstate_statemachine.contrib.flask.quart import _next_item

        async def go() -> None:
            loop = asyncio.get_running_loop()
            wake = asyncio.Event()
            fan = Fanout(4)
            q = fan.subscribe(
                "m", "1", lambda: loop.call_soon_threadsafe(wake.set)
            )
            assert await _next_item(q, wake, 0.05) is None  # heartbeat
            asyncio.get_running_loop().call_later(
                0.02, fan.publish, "m", "1", [{"a": 1}]
            )
            item = await _next_item(q, wake, 2.0)
            assert item == (1, {"a": 1})

        asyncio.run(go())


# =============================================================================
# 🚀 FastAPI
# =============================================================================
@needs_starlette
class TestFastAPI:
    @pytest.fixture(autouse=True)
    def _need(self) -> None:
        pytest.importorskip("fastapi")

    def _build(self, **router_kw: Any) -> Any:
        from fastapi import FastAPI

        from src.xstate_statemachine.contrib.fastapi import (
            StatechartRouter,
            instrument_app,
        )

        reg = StatechartRegistry(MemoryStore())
        reg.register(
            "m",
            _counter(),
            authorize=lambda conn, *, name, key, event: (
                conn.headers.get("x-ok") == "1"
            ),
        )
        app = FastAPI()
        app.include_router(StatechartRouter(reg, "m", **router_kw))
        return instrument_app(app, reg), reg

    def test_cw02_unauthorised_caller_cannot_probe_key_existence(self) -> None:
        from fastapi.testclient import TestClient

        app, _ = self._build(create_if_missing=False)
        with TestClient(app) as c:
            for path in ("/m/ghost/events/INC", "/m/ghost/send"):
                body = {"type": "INC"} if path.endswith("send") else None
                r = c.post(path, json=body)
                assert r.status_code == 403, (path, r.status_code)
            ok = c.post("/m/ghost/events/INC", headers={"x-ok": "1"}, json={})
            assert ok.status_code == 404

    def test_cw30_unsafe_event_name_fails_router_build(self) -> None:
        from fastapi import FastAPI

        from src.xstate_statemachine.contrib.fastapi import StatechartRouter

        bad = create_machine(
            {
                "id": "b",
                "initial": "a",
                "states": {"a": {"on": {"order/paid": "a"}}},
            }
        )
        reg = StatechartRegistry(MemoryStore())
        reg.register("b", bad, authorize=allow_all)
        with pytest.raises(ValueError, match="order/paid"):
            FastAPI().include_router(StatechartRouter(reg, "b"))

    def test_cw29_probes_first_and_identity_dedup(self) -> None:
        from fastapi import FastAPI

        from src.xstate_statemachine.contrib.fastapi import instrument_app

        reg = StatechartRegistry(MemoryStore())
        app = FastAPI()
        instrument_app(app, reg)
        instrument_app(app, reg)
        paths = [getattr(r, "path", None) for r in app.router.routes]
        assert paths[:2] == ["/_xsm/health", "/_xsm/ready"]
        assert paths.count("/_xsm/health") == 1


# =============================================================================
# 🛰️ Litestar
# =============================================================================
@needs_starlette
class TestLitestar:
    @pytest.fixture(autouse=True)
    def _need(self) -> None:
        pytest.importorskip("litestar")
        pytest.importorskip("httpx")

    def test_cw25_models_for_surfaces_real_errors(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from src.xstate_statemachine.contrib.litestar import controller
        from src.xstate_statemachine.contrib.pydantic import events

        def boom(_: Any) -> Any:
            raise RuntimeError("bug inside contrib.pydantic")

        monkeypatch.setattr(events, "models_of", boom)
        machine = _counter()
        with pytest.raises(RuntimeError, match="bug inside"):
            controller._models_for(machine, None)

    def test_cw12_body_read_times_out(self) -> None:
        from src.xstate_statemachine.contrib.litestar.controller import (
            _json_guard,
        )
        from src.xstate_statemachine.contrib.starlette._http import (
            RequestTimeoutError,
        )

        class Stalled:
            headers: Dict[str, str] = {"content-type": "application/json"}

            async def stream(self) -> Any:
                await asyncio.sleep(30)
                yield b""  # pragma: no cover

        before = _json_guard(1000, 0.05)
        with pytest.raises(RequestTimeoutError):
            asyncio.run(before(Stalled()))

    def test_cw07_anonymous_get_interpreter_does_not_hang_siblings(
        self,
    ) -> None:
        from litestar import Litestar, Response, post
        from litestar.testing import TestClient

        from src.xstate_statemachine.contrib.litestar import (
            ReceiptResponse,
            XStatePlugin,
            get_interpreter,
        )

        reg = StatechartRegistry(
            MemoryStore(),
            inbox=MemoryInbox(),
            principal=lambda conn: None,  # type: ignore[arg-type,return-value]
        )
        reg.register("c", counter_machine(), authorize=allow_all)

        @post(
            "/c/{id:str}/both",
            dependencies={
                "a": get_interpreter(reg, "c"),
                "b": get_interpreter(reg, "c"),
            },
        )
        async def both(a: Any, b: Any) -> Any:  # pragma: no cover
            return ReceiptResponse(a, await a.send("INC", wait=True))

        app = Litestar(
            route_handlers=[both],
            plugins=[XStatePlugin(reg)],
            logging_config=None,
        )
        result: Dict[str, Any] = {}

        def call() -> None:
            with TestClient(app) as c:
                result["status"] = c.post("/c/1/both").status_code

        t = threading.Thread(target=call, daemon=True)
        t.start()
        t.join(15)
        assert not t.is_alive(), "request hung on a stranded future"
        assert result["status"] == 401

    def test_cw02_litestar_unauthorised_caller_gets_403_not_404(self) -> None:
        from litestar import Litestar
        from litestar.testing import TestClient

        from src.xstate_statemachine.contrib.litestar import (
            XStatePlugin,
            create_statechart_controller,
        )

        reg = StatechartRegistry(MemoryStore())
        reg.register(
            "m",
            _counter(),
            authorize=lambda conn, *, name, key, event: False,
        )
        app = Litestar(
            route_handlers=[
                create_statechart_controller(
                    reg, "m", path="/m", create_if_missing=False
                )
            ],
            plugins=[XStatePlugin(reg)],
            logging_config=None,
        )
        with TestClient(app) as c:
            r = c.post("/m/ghost/send", json={"type": "INC"})
            assert r.status_code == 403
            r = c.post("/m/ghost/events/INC", json={})
            assert r.status_code == 403
