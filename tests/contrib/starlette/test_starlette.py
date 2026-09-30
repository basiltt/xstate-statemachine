# tests/contrib/starlette/test_starlette.py
"""#275: StatechartRegistry, Receipt → HTTP, Idempotency-Key, SSE/WS,
residents, lifespan + timer scanner, probes, inspector refusal.

Every network read is bounded (`_support.bounded`, httpx timeouts).
Skips without the extra."""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.events import Receipt
from src.xstate_statemachine.exceptions import (
    ConflictError,
    InterpreterStoppedError,
    LockTimeoutError,
    SnapshotDriftError,
    UnknownEventError,
)
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryStore,
    SQLiteStore,
)
from src.xstate_statemachine.persistence.helpers import KeyNotFoundError
from src.xstate_statemachine.persistence.idempotency import (
    IdempotencyInFlightError,
    IdempotencyMismatchError,
)
from src.xstate_statemachine.persistence.migration import (
    MachineVersionMismatchError,
)

from ..conftest import requires_extra
from ._support import (
    RawSSE,
    RawWS,
    bounded,
    build_app,
    counter_machine,
    payment_machine,
)

pytestmark = requires_extra("starlette")
pytest.importorskip("starlette")
httpx = pytest.importorskip("httpx")

from starlette.applications import Starlette  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from src.xstate_statemachine.contrib.starlette import (  # noqa: E402
    ReceiptResponse,
    StatechartRegistry,
    allow_all,
    mount_inspector,
    problem,
    receipt_to_status,
    registry as registry_mod,
    status_for_exception,
)

JSON = {"content-type": "application/json"}
IDS = frozenset({"x.a"})


def run(coro):
    return asyncio.run(coro)


def make(store=None, *, name="payment", machine=None, **kw):
    reg_kw = {k: v for k, v in kw.items() if k in ("strict", "authorize")}
    for k in reg_kw:
        kw.pop(k)
    reg = StatechartRegistry(store or MemoryStore(), **kw)
    reg.register(
        name,
        machine or payment_machine(),
        authorize=reg_kw.get("authorize", allow_all),
        strict=reg_kw.get("strict"),
    )
    return reg


def test_registry_builds_without_a_running_loop_and_uses_one_lock():
    """A registry is module-level state, built at import time. On Python
    3.9 an eager `asyncio.Lock()` binds to the current loop (and raises
    'no current event loop' from a non-loop thread), which took down the
    whole [fastapi] 3.9 CI cell. The lock is lazy and created once."""
    reg = make()  # no loop running here
    seen = []

    async def grab():
        async with reg._lock():
            seen.append(reg._lock())

    asyncio.run(grab())
    asyncio.run(grab())
    assert len(seen) == 2 and seen[0] is seen[1]


# -----------------------------------------------------------------------------
# 🧾 receipt_to_status / exceptions / problem
# -----------------------------------------------------------------------------
class TestReceiptToStatus:
    @pytest.mark.parametrize(
        "receipt,status",
        [
            (Receipt(IDS, True), 200),
            (Receipt(IDS, False), 200),
            (Receipt(IDS, False, denied=True), 409),
            (Receipt(IDS, False, deferred=True), 202),
            (Receipt(IDS, True, duplicate=True), 200),
            (Receipt(IDS, False, error=RuntimeError("x")), 500),
            # 🏁 a finished / stopped instance refuses like a guard, not 500
            (Receipt(IDS, False, error=InterpreterStoppedError("done")), 409),
            (
                Receipt(
                    IDS, False, IdempotencyMismatchError("k"), duplicate=True
                ),
                422,
            ),
            (
                Receipt(
                    IDS, False, IdempotencyInFlightError("k"), duplicate=True
                ),
                409,
            ),
        ],
    )
    def test_table(self, receipt, status):
        assert receipt_to_status(receipt) == status

    def test_overrides(self):
        r = Receipt(IDS, False)
        assert receipt_to_status(r, unchanged=204) == 204
        assert receipt_to_status(Receipt(IDS, True), changed=201) == 201

    @pytest.mark.parametrize(
        "exc,status",
        [
            (UnknownEventError("secret", "m", []), 422),
            (SnapshotDriftError("secret"), 409),
            (MachineVersionMismatchError("m", "2", "1"), 409),
            (ConflictError("secret", 1, 2), 409),
            (LockTimeoutError("secret", 1.0), 409),
            (KeyNotFoundError("secret"), 404),
            (RuntimeError("secret"), 500),
        ],
    )
    def test_status_for_exception(self, exc, status):
        from src.xstate_statemachine.contrib.starlette import (
            problem_for_exception,
        )

        assert status_for_exception(exc) == status
        resp = problem_for_exception(exc)
        assert resp.status_code == status
        assert resp.media_type == "application/problem+json"
        assert b"secret" not in bytes(resp.body)

    def test_version_mismatch_hint(self):
        from src.xstate_statemachine.contrib.starlette import (
            problem_for_exception,
        )
        import json

        resp = problem_for_exception(
            MachineVersionMismatchError("m", "2", "1")
        )
        assert json.loads(bytes(resp.body))["machine_version"] == "2"

    def test_problem_shape(self):
        import json

        body = json.loads(bytes(problem(404, "Nope", "d", x=1).body))
        assert body == {
            "type": "about:blank",
            "title": "Nope",
            "status": 404,
            "detail": "d",
            "x": 1,
        }


# -----------------------------------------------------------------------------
# 🌐 HTTP: statuses, strict, JSON-only, size cap, authorize, idempotency
# -----------------------------------------------------------------------------
class TestHTTP:
    def test_changed_unchanged_and_state_only_body(self):
        reg = make()
        with TestClient(build_app(reg)) as c:
            r = c.post("/m/1/events/SUBMIT", headers=JSON, content=b"{}")
            assert r.status_code == 200
            body = r.json()
            assert body["changed"] is True
            assert "context" not in body  # X0.1
            assert body["state"] == "challenge"
            assert "RESET" in body["available_events"]
            r = c.post("/m/1/events/BOGUS")
            assert r.status_code == 200 and r.json()["changed"] is False

    def test_strict_undeclared_is_422(self):
        reg = make(strict=True)
        with TestClient(build_app(reg)) as c:
            r = c.post("/m/1/events/BOGUS")
            assert r.status_code == 422
            assert r.headers["content-type"] == "application/problem+json"
            assert r.json()["error"] == "UnknownEventError"

    def test_denied_is_409(self):
        from src.xstate_statemachine import stub_logic

        from ._support import PAYMENT_CFG

        m = create_machine(
            PAYMENT_CFG, logic=stub_logic(PAYMENT_CFG, guards=False)
        )
        reg = make(machine=m)
        with TestClient(build_app(reg)) as c:
            r = c.post("/m/1/events/SUBMIT")
            assert r.status_code == 409 and r.json()["denied"] is True

    def test_event_to_finished_instance_is_409_not_500(self):
        """An order that reached its final state is re-loaded as `done`;
        a further POST is a refusal (409 + receipt), not a server fault.
        The sync engine used to return None from `send(wait=True)` here,
        which surfaced as a 500 in the Flask blueprint (battle test)."""
        cfg = {
            "id": "o",
            "initial": "open",
            "states": {
                "open": {"on": {"PAY": "paid"}},
                "paid": {"type": "final"},
            },
        }
        from src.xstate_statemachine import stub_logic

        reg = make(machine=create_machine(cfg, logic=stub_logic(cfg)))
        with TestClient(build_app(reg)) as c:
            assert c.post("/m/1/events/PAY").json()["changed"] is True
            r = c.post("/m/1/events/PAY")
            assert r.status_code == 409, r.text
            body = r.json()
            assert body["changed"] is False
            assert body["error"] == "InterpreterStoppedError"
            assert body["state_ids"] == ["o.paid"]

    def test_context_serializer_opt_in(self):
        reg = StatechartRegistry(MemoryStore())
        reg.register(
            "payment",
            payment_machine(),
            authorize=allow_all,
            context_serializer=lambda ctx: {"amount": ctx["amount"]},
        )
        with TestClient(build_app(reg)) as c:
            r = c.post("/m/1/events/SUBMIT")
            assert r.json()["context"] == {"amount": 149900}

    def test_415_413_422_body(self):
        reg = make(max_body_bytes=16)
        with TestClient(build_app(reg)) as c:
            r = c.post(
                "/m/1/events/SUBMIT",
                content=b"a=1",
                headers={"content-type": "text/plain"},
            )
            assert r.status_code == 415
            r = c.post(
                "/m/1/events/SUBMIT",
                headers=JSON,
                content=b'{"a":"' + b"x" * 64 + b'"}',
            )
            assert r.status_code == 413
            r = c.post("/m/1/events/SUBMIT", headers=JSON, content=b"[1]")
            assert r.status_code == 422

    def test_authorize_denied_403_per_event(self):
        seen = []

        async def authz(conn, *, name, key, event):
            seen.append((name, key, event))
            return event != "SUBMIT"

        reg = make(authorize=authz)
        with TestClient(build_app(reg)) as c:
            r = c.post("/m/7/events/SUBMIT")
            assert r.status_code == 403
            assert c.post("/m/7/events/UPDATE_FORM").status_code == 200
        assert ("payment", "7", "SUBMIT") in seen

    def test_authorize_required(self):
        reg = StatechartRegistry(MemoryStore())
        with pytest.raises(TypeError):
            reg.register("p", payment_machine())  # type: ignore[call-arg]
        with pytest.raises(TypeError):
            reg.register("p", payment_machine(), authorize=None)
        with pytest.raises(ValueError):
            reg.register("a.b", payment_machine(), authorize=allow_all)

    def test_allow_all_warns_once(self, caplog):
        registry_mod._allow_all_warned.clear()
        reg = make()
        with caplog.at_level(logging.WARNING, logger=registry_mod.__name__):
            with TestClient(build_app(reg)) as c:
                c.post("/m/1/events/UPDATE_FORM")
                c.post("/m/1/events/UPDATE_FORM")
        warns = [r for r in caplog.records if "allow_all" in r.getMessage()]
        assert len(warns) == 1

    def test_idempotency_key(self):
        reg = make(
            inbox=MemoryInbox(),
            principal=lambda conn: conn.headers.get("x-user", "anon"),
            machine=counter_machine(),
            name="payment",
        )
        with TestClient(build_app(reg)) as c:
            h = {**JSON, "Idempotency-Key": "k1", "x-user": "alice"}
            r1 = c.post("/m/1/events/INC", headers=h, content=b'{"n":1}')
            r2 = c.post("/m/1/events/INC", headers=h, content=b'{"n":1}')
            assert r1.status_code == r2.status_code == 200
            assert r1.json()["duplicate"] is False
            assert r2.json()["duplicate"] is True
            b1, b2 = r1.json(), r2.json()
            b1.pop("duplicate"), b2.pop("duplicate")
            assert b1 == b2
            r3 = c.post("/m/1/events/INC", headers=h, content=b'{"n":2}')
            assert r3.status_code == 422
            assert r3.json()["error"] == "IdempotencyMismatchError"
            # 🧾 A refusal is an RFC 9457 problem like every other 4xx, not
            #    a receipt body carrying a 4xx status (clean-venv finding).
            assert r3.headers["content-type"].startswith(
                "application/problem+json"
            )
            assert r3.json()["title"] == "Idempotency key reused"
            assert "state_ids" not in r3.json()
            # 🔐 X0.2: another principal with the SAME key is not a dup.
            hb = {**h, "x-user": "bob"}
            r4 = c.post("/m/1/events/INC", headers=hb, content=b'{"n":1}')
            assert r4.json()["duplicate"] is False
        import json

        rec = reg.store.load("payment.1")
        # alice once + bob once; the duplicate and the 422 had no effect.
        assert json.loads(rec.snapshot)["context"]["n"] == 2

    def test_act_requires_principal_with_inbox(self):
        reg = make(inbox=MemoryInbox())

        async def go():
            async with reg.act("payment", "1"):
                pass

        with pytest.raises(ValueError):
            run(go())


# -----------------------------------------------------------------------------
# ⚡ Concurrency: 50 POSTs to one key, no lost updates
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("backend", ["memory", "sqlite"])
def test_fifty_concurrent_posts_no_lost_updates(backend, tmp_path):
    from src.xstate_statemachine.persistence import OptimisticLock

    store = (
        MemoryStore()
        if backend == "memory"
        else SQLiteStore(str(tmp_path / "s.db"))
    )
    reg = make(
        store,
        machine=counter_machine(),
        lock=OptimisticLock(retries=0),
    )
    app = build_app(reg)

    async def one(client):
        # 💡 A conflict (409) is the documented "retry" signal.
        for _ in range(200):
            r = await client.post("/m/k/events/INC")
            if r.status_code != 409:
                return r
            await asyncio.sleep(0)
        raise AssertionError("never won the race")

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t", timeout=10
        ) as client:
            return await asyncio.wait_for(
                asyncio.gather(*(one(client) for _ in range(50))), 60
            )

    results = run(go())
    changed = sum(1 for r in results if r.json()["changed"])
    assert changed == 50
    rec = store.load("payment.k")
    assert rec.version == changed
    import json

    assert json.loads(rec.snapshot)["context"]["n"] == 50


# -----------------------------------------------------------------------------
# 📡 SSE
# -----------------------------------------------------------------------------
class TestSSE:
    def test_snapshot_then_one_transition_per_changed_in_order(self):
        reg = make()
        app = build_app(reg)

        async def go():
            sse = RawSSE(app, "/m/9/stream")
            assert await sse.open() == 200
            seq, ev, data = await sse.next_event()
            assert ev == "snapshot" and data["state"] == "editing"
            assert reg.subscribers.count("payment", "9") == 1
            t0 = time.monotonic()
            for event in ("UPDATE_FORM", "SUBMIT", "BOGUS", "RESET"):
                async with reg.act("payment", "9") as i:
                    await i.send(event, wait=True)
            got = [await sse.next_event() for _ in range(2)]
            assert time.monotonic() - t0 < 1.0
            assert [g[1] for g in got] == ["transition", "transition"]
            assert got[0][2]["state"] == "challenge"
            assert got[1][2]["state"] == "editing"
            assert got[0][0] < got[1][0]
            # no third transition pending (UPDATE_FORM/BOGUS unchanged)
            assert sse.out.empty()
            await sse.close()
            assert reg.subscribers.count() == 0
            assert reg.connections() == 0

        run(go())

    def test_heartbeat(self):
        reg = make(heartbeat_s=0.05)
        app = build_app(reg)

        async def go():
            sse = RawSSE(app, "/m/1/stream")
            await sse.open()
            await sse.next_event()
            _, kind, _ = await sse.next_event()
            assert kind == "comment"
            await sse.close()

        run(go())

    def test_origin_and_authorize_refused(self):
        reg = make(authorize=lambda c, **k: c.headers.get("x-ok") == "1")
        app = build_app(reg)

        async def go():
            bad = RawSSE(
                app, "/m/1/stream", [("origin", "http://evil"), ("x-ok", "1")]
            )
            assert await bad.open() == 403
            await bad.body()
            await bad.close()
            same = RawSSE(
                app,
                "/m/1/stream",
                [("origin", "http://testserver"), ("x-ok", "0")],
            )
            assert await same.open() == 403
            await same.body()
            await same.close()
            assert reg.connections() == 0

        run(go())

    def test_allowed_origin_and_connection_cap(self):
        reg = make(
            allowed_origins=["https://app.example"], max_connections_per_key=1
        )
        app = build_app(reg)

        async def go():
            a = RawSSE(app, "/m/1/stream", [("origin", "https://app.example")])
            assert await a.open() == 200
            b = RawSSE(app, "/m/1/stream")
            assert await b.open() == 429
            await b.body()
            await b.close()
            await a.close()

        run(go())


# -----------------------------------------------------------------------------
# 🔌 WebSocket
# -----------------------------------------------------------------------------
class TestWebSocket:
    def test_snapshot_receipt_transition_push(self):
        reg = make()
        with TestClient(build_app(reg)) as c:
            with (
                c.websocket_connect("/ws/5") as a,
                c.websocket_connect("/ws/5") as b,
            ):
                assert a.receive_json()["kind"] == "snapshot"
                assert b.receive_json()["state"] == "editing"
                a.send_json({"type": "SUBMIT", "payload": {}})
                got = [a.receive_json(), a.receive_json()]
                kinds = sorted(m["kind"] for m in got)
                assert kinds == ["receipt", "transition"]
                pushed = b.receive_json()
                assert pushed["kind"] == "transition"
                assert pushed["state"] == "challenge"
                a.send_json({"type": 1})
                assert a.receive_json()["status"] == 422
            assert reg.residents == 0
        assert reg.connections() == 0
        assert reg.subscribers.count() == 0

    def test_authorize_denied_closes_1008(self):
        from starlette.websockets import WebSocketDisconnect

        reg = make(authorize=lambda c, **k: k["event"] is None)
        with TestClient(build_app(reg)) as c:
            with c.websocket_connect("/ws/1") as ws:
                ws.receive_json()
                ws.send_json({"type": "SUBMIT"})
                with pytest.raises(WebSocketDisconnect) as ei:
                    ws.receive_json()
                assert ei.value.code == 1008
            reg2 = make(authorize=lambda c, **k: False)
            with TestClient(build_app(reg2)) as c2:
                with pytest.raises(WebSocketDisconnect) as ei:
                    with c2.websocket_connect("/ws/1") as ws:
                        ws.receive_json()
                assert ei.value.code == 1008

    def test_heartbeat_ping(self):
        reg = make(heartbeat_s=0.05)
        with TestClient(build_app(reg)) as c:
            with c.websocket_connect("/ws/1") as ws:
                ws.receive_json()
                assert ws.receive_json() == {"kind": "ping"}


# -----------------------------------------------------------------------------
# 🧹 Leak test (X0.12)
# -----------------------------------------------------------------------------
def test_hundred_connect_disconnect_cycles_leak_nothing():
    reg = make()
    app = build_app(reg)

    async def go():
        baseline = len(asyncio.all_tasks())
        for i in range(100):
            if i % 2:
                ws = RawWS(app, "/ws/1")
                accept = await ws.open()
                assert accept["type"] == "websocket.accept"
                assert (await ws.recv_json())["kind"] == "snapshot"
                await ws.close()
            else:
                sse = RawSSE(app, "/m/1/stream")
                await sse.open()
                await sse.next_event()
                await sse.close()
        await asyncio.sleep(0)
        assert reg.residents == 0
        assert reg.connections() == 0
        assert reg.subscribers.count() == 0
        assert len(asyncio.all_tasks()) <= baseline

    run(go())


# -----------------------------------------------------------------------------
# 🏠 Residents
# -----------------------------------------------------------------------------
class TestResidents:
    def test_lru_cap_saves_evicted(self):
        reg = make(machine=counter_machine(), max_residents=2)

        async def go():
            a = await reg.resident("payment", "a")
            await a.send("INC", wait=True)
            assert await reg.resident("payment", "a") is a
            await reg.resident("payment", "b")
            await reg.resident("payment", "a")  # a is now MRU
            await reg.resident("payment", "c")  # evicts b
            assert reg.residents == 2
            assert set(k for _, k in reg._residents) == {"a", "c"}
            await reg.release_resident("payment", "a")
            assert reg.residents == 1
            assert a.status != "running"

        run(go())
        import json

        rec = reg.store.load("payment.a")
        assert json.loads(rec.snapshot)["context"]["n"] == 1

    def test_idle_ttl(self):
        reg = make(resident_idle_ttl_s=10)
        clock = [0.0]
        reg.monotonic = lambda: clock[0]

        async def go():
            await reg.resident("payment", "a")
            clock[0] = 5
            await reg.resident("payment", "b")
            clock[0] = 12
            assert await reg.evict_idle() == 1
            assert [k for _, k in reg._residents] == ["b"]

        run(go())

    def test_stopped_on_shutdown(self):
        reg = make()
        seen = {}

        async def route(request):
            i = await reg.resident("payment", "z")
            seen["i"] = i
            return ReceiptResponse(i, await i.send("SUBMIT", wait=True))

        from starlette.routing import Route

        app = Starlette(
            routes=[Route("/r", route, methods=["POST"])],
            lifespan=reg.lifespan,
        )
        with TestClient(app) as c:
            assert c.post("/r").json()["state"] == "challenge"
            assert reg.residents == 1
        assert reg.residents == 0
        assert seen["i"].status != "running"
        assert reg.store.load("payment.z") is not None

    def test_bad_limits(self):
        with pytest.raises(ValueError):
            StatechartRegistry(MemoryStore(), max_residents=0)


# -----------------------------------------------------------------------------
# â° lifespan + DueTimerScanner, probes, inspector
# -----------------------------------------------------------------------------
def test_lifespan_scanner_fires_persisted_after():
    store = MemoryStore()
    m = create_machine(
        {
            "id": "t",
            "initial": "wait",
            "states": {"wait": {"after": {"1000": "done"}}, "done": {}},
        }
    )
    reg = StatechartRegistry(
        store,
        run_timers=True,
        scanner_interval_s=0.02,
        scanner_now=lambda: time.time() + 3600,
    )
    reg.register("t", m, authorize=allow_all)

    async def seed():
        async with reg.act("t", "1") as i:
            assert i.value == "wait"

    app = Starlette(routes=[reg.ready_route()], lifespan=reg.lifespan)
    with TestClient(app) as c:
        run(seed())
        assert reg.scanner is not None
        assert c.get("/_xsm/ready").json()["timers"] is True
        deadline = time.monotonic() + 1.0
        import json

        while time.monotonic() < deadline:
            snap = json.loads(store.load("t.1").snapshot)
            if "t.done" in str(snap):
                break
            time.sleep(0.01)
        assert "t.done" in str(json.loads(store.load("t.1").snapshot))
    assert reg.scanner is None


def test_health_and_ready():
    reg = make()
    app = build_app(reg)
    c = TestClient(app)
    assert c.get("/_xsm/health").json() == {"status": "ok"}
    assert c.get("/_xsm/ready").status_code == 503  # lifespan not started
    with TestClient(app) as c2:
        r = c2.get("/_xsm/ready")
        assert r.status_code == 200 and r.json()["status"] == "ready"


def test_mount_inspector_refuses_without_debug():
    app = Starlette()
    reg = make()
    with pytest.raises(RuntimeError):
        mount_inspector(app, reg)


class TestInspectorWebSocket:
    """#274: the 501 placeholder is replaced by the real `WebSocketSink`."""

    def _app(self, **kw):
        app = Starlette()
        reg = make()
        sink = mount_inspector(app, reg, debug=True, **kw)
        app.router.routes.append(reg.health_route("/h"))
        return app, reg, sink

    def test_stream_carries_protocol_messages_from_act(self):
        from starlette.routing import Route
        from starlette.responses import JSONResponse

        app, reg, sink = self._app(context_allowlist=["amount"])

        async def pay(request):
            async with reg.act("payment", "k1") as i:
                r = await i.send("SUBMIT", wait=True)
            return JSONResponse({"changed": r.changed})

        app.router.routes.append(Route("/pay", pay, methods=["POST"]))
        with TestClient(app) as c:
            with c.websocket_connect(
                "/_xsm/inspect", headers={"X-XSM-Token": sink.token}
            ) as ws:
                c.post("/pay")
                got = []
                for _ in range(10):  # bounded: actor, init x2, PAY x2, ...
                    got.append(ws.receive_json())
                    if got[-1]["type"] == "@xstate.snapshot" and (
                        got[-1]["event"]["type"] == "SUBMIT"
                    ):
                        break
        kinds = [m["type"] for m in got]
        assert kinds[0] == "@xstate.actor"
        assert all(m["_version"] for m in got)
        pay = [m for m in got if m.get("event", {}).get("type") == "SUBMIT"]
        assert [m["type"] for m in pay] == [
            "@xstate.event",
            "@xstate.snapshot",
        ]
        assert pay[1]["snapshot"]["context"] == {"amount": 0} or (
            set(pay[1]["snapshot"]["context"]) <= {"amount"}
        )

    def test_token_cookie_host_and_origin(self):
        from starlette.websockets import WebSocketDisconnect

        app, reg, sink = self._app()
        with TestClient(app) as c:
            with pytest.raises(WebSocketDisconnect) as ei:
                with c.websocket_connect("/_xsm/inspect") as ws:
                    ws.receive_json()
            assert ei.value.code == 1008
            with pytest.raises(WebSocketDisconnect):
                with c.websocket_connect(
                    "/_xsm/inspect",
                    headers={
                        "X-XSM-Token": sink.token,
                        "Origin": "http://evil.example",
                    },
                ) as ws:
                    ws.receive_json()
            assert c.get("/_xsm/inspect").status_code == 401
            assert c.get("/_xsm/inspect?token=nope").status_code == 401
            r = c.get(
                f"/_xsm/inspect?token={sink.token}", follow_redirects=False
            )
            assert r.status_code == 303
            assert "httponly" in r.headers["set-cookie"].lower()
            assert "samesite=strict" in r.headers["set-cookie"].lower()
            # cookie now carried by the client
            assert c.get("/_xsm/inspect").status_code == 200
        with TestClient(app, base_url="http://evil.example") as c2:
            r = c2.get("/_xsm/inspect", headers={"X-XSM-Token": sink.token})
            assert r.status_code == 421
        app2, _, sink2 = self._app(allow_remote=True)
        with TestClient(app2, base_url="http://lan.example") as c3:
            r = c3.get(
                "/_xsm/inspect",
                headers={"Authorization": f"Bearer {sink2.token}"},
            )
            assert r.status_code == 200

    def test_registry_is_not_forked_and_context_denied(self):
        app, reg, sink = self._app()
        assert any(type(p).__name__ == "InspectorPlugin" for p in reg.plugins)

        async def go():
            async with reg.act("payment", "k2") as i:
                await i.send("SUBMIT", wait=True)

        run(go())
        assert sink.messages
        for m in sink.messages:
            if "snapshot" in m:
                assert m["snapshot"]["context"] == {}


def test_bounded_helper_times_out():
    async def go():
        with pytest.raises(asyncio.TimeoutError):
            await bounded(asyncio.sleep(1), 0.01)

    run(go())
