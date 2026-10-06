"""Battle #275 (adversary B): SSE / WebSocket / fan-out regressions."""

from __future__ import annotations

import asyncio
import json
import threading
import time

import pytest

pytest.importorskip("starlette")

from starlette.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.starlette import (  # noqa: E402
    StatechartRegistry,
    allow_all,
)
from src.xstate_statemachine.contrib.starlette._fanout import (  # noqa: E402
    CLOSED,
    TimerPublisher,
)
from src.xstate_statemachine.persistence import MemoryStore  # noqa: E402

from ._support import (  # noqa: E402
    RawSSE,
    RawWS,
    bounded,
    build_app,
    counter_machine,
)


def make(machine=None, name="payment", **kw):
    reg = StatechartRegistry(MemoryStore(), **kw)
    reg.register(name, machine or counter_machine(), authorize=allow_all)
    return reg


async def inc(reg, key="1", n=1):
    for _ in range(n):
        async with reg.act("payment", key) as i:
            await i.send("INC", wait=True)


async def until(pred, timeout=1.0):
    deadline = time.monotonic() + timeout
    while not pred():
        assert time.monotonic() < deadline, "condition never held"
        await asyncio.sleep(0.01)


class SpecSSE(RawSSE):
    """A `RawSSE` advertising an ASGI spec version, whose peer can die."""

    def __init__(self, *a, spec="2.4", **kw):
        super().__init__(*a, **kw)
        self.spec = spec
        self.dead = False

    async def _send(self, msg):
        if self.dead:
            raise OSError("peer gone")
        await self.out.put(msg)

    async def open(self):
        orig = self.app

        async def app(scope, receive, send):
            scope["asgi"]["spec_version"] = self.spec
            await orig(scope, receive, send)

        self.app = app
        return await super().open()


# -----------------------------------------------------------------------------
# 📡 SSE: dead clients
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("spec", ["2.0", "2.4"])
def test_dead_sse_client_releases_slot_under_traffic(spec):
    """Spec 2.4 (uvicorn's httptools/h11 advertise 2.3/2.4 by server):
    Starlette raises `ClientDisconnect` out of the failed `send` without
    closing the generator -- the connection slot and subscriber leaked
    (`max_connections_per_key` exhausted by dead clients)."""
    reg = make(heartbeat_s=30, max_connections_per_key=1)
    app = build_app(reg)

    async def go():
        sse = SpecSSE(app, "/m/1/stream", spec=spec)
        assert await sse.open() == 200
        await sse.next_event()
        sse.dead = True
        sse._disconnect.set()
        await inc(reg, n=2)
        await until(lambda: reg.connections() == 0)
        assert reg.subscribers.count() == 0
        again = SpecSSE(app, "/m/1/stream", spec=spec)
        assert await again.open() == 200  # slot free: not 429
        await again.close()

    asyncio.run(go())


def test_idle_disconnect_noticed_before_heartbeat_on_spec_24():
    reg = make(heartbeat_s=30)
    app = build_app(reg)

    async def go():
        sse = SpecSSE(app, "/m/1/stream", spec="2.4")
        await sse.open()
        await sse.next_event()
        await sse.close()  # http.disconnect; no traffic, 30 s heartbeat
        assert reg.connections() == 0 and reg.subscribers.count() == 0

    asyncio.run(go())


def test_unserialisable_sse_frame_ends_stream_and_frees_slot(caplog):
    reg = make()
    app = build_app(reg)

    async def go():
        sse = RawSSE(app, "/m/1/stream")
        await sse.open()
        await sse.next_event()
        reg.subscribers.publish("payment", "1", [{"at": object()}])
        await bounded(sse.task)
        assert reg.connections() == 0

    asyncio.run(go())
    assert "not JSON" in caplog.text


# -----------------------------------------------------------------------------
# 🔌 WebSocket wire contract
# -----------------------------------------------------------------------------
def _ws_kinds(ws, n):
    return [ws.receive_json() for _ in range(n)]


def test_ws_malformed_frames_answer_and_keep_session():
    reg = make()
    with TestClient(build_app(reg)) as c:
        with c.websocket_connect("/ws/1") as ws:
            assert ws.receive_json()["kind"] == "snapshot"
            ws.send_text("not json")
            assert ws.receive_json()["status"] == 400
            ws.send_bytes(b"\xff\xfe")
            assert ws.receive_json()["status"] == 400
            for bad in ([1, 2], {"type": 1}, {"type": "INC", "payload": 3}):
                ws.send_json(bad)
                assert ws.receive_json()["status"] == 422
            ws.send_json({"type": "INC", "payload": {"wait": False}})
            assert ws.receive_json()["status"] == 422  # reserved key
            ws.send_bytes(json.dumps({"type": "INC"}).encode())
            kinds = sorted(m["kind"] for m in _ws_kinds(ws, 2))
            assert kinds == ["receipt", "transition"]
    assert reg.connections() == 0


def test_ws_oversized_frame_closes_1009():
    reg = make(max_body_bytes=64)
    with TestClient(build_app(reg)) as c:
        with c.websocket_connect("/ws/1") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"type": "INC", "pad": "x" * 100}))
            with pytest.raises(WebSocketDisconnect) as ei:
                ws.receive_json()
            assert ei.value.code == 1009
    assert reg.connections() == 0


def test_ws_burst_is_processed_in_order():
    reg = make()
    with TestClient(build_app(reg)) as c:
        with c.websocket_connect("/ws/1") as ws:
            ws.receive_json()
            for _ in range(200):
                ws.send_json({"type": "INC"})
            msgs = _ws_kinds(ws, 400)
            seqs = [m["seq"] for m in msgs if m["kind"] == "transition"]
            assert seqs == sorted(seqs) and len(seqs) == 200
    assert reg.connections() == 0


def test_ws_connect_during_drain_closes_1001():
    reg = make()
    reg.draining = True
    with TestClient(build_app(reg)) as c:
        reg.draining = True
        with pytest.raises(WebSocketDisconnect) as ei:
            with c.websocket_connect("/ws/1") as ws:
                ws.receive_json()
        assert ei.value.code == 1001
    assert reg.connections() == 0


def test_ws_slow_consumer_cut_closes_1013():
    reg = make()

    async def go():
        ws = RawWS(build_app(reg), "/ws/1")
        assert (await ws.open())["type"] == "websocket.accept"
        await ws.recv_json()
        sub = next(iter(reg.subscribers._subs[("payment", "1")]))
        reg.subscribers.unsubscribe(sub)
        sub.queue.put_nowait(CLOSED)  # what `publish` does to a laggard
        msg = await bounded(ws.out.get())
        assert msg == {"type": "websocket.close", "code": 1013, "reason": ""}
        await ws.close()
        assert reg.connections() == 0

    asyncio.run(go())


def test_ws_peer_gone_during_snapshot_releases_slot():
    """`on_disconnect` only runs when `on_connect` returns: a peer that
    vanished during accept/snapshot leaked its connection slot."""
    reg = make(max_connections_per_key=1)

    async def go():
        ws = RawWS(build_app(reg), "/ws/1")

        async def put(msg):
            if msg["type"] == "websocket.send":
                raise OSError("peer gone")

        ws.out.put = put
        await ws.inbox.put({"type": "websocket.connect"})
        ws.task = asyncio.ensure_future(
            ws.app(_ws_scope("/ws/1"), ws.inbox.get, put)
        )
        await asyncio.wait({ws.task}, timeout=1.0)
        assert ws.task.done()
        assert reg.connections() == 0
        assert reg.subscribers.count() == 0

    asyncio.run(go())


def _ws_scope(path):
    return {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 1),
        "server": ("testserver", 80),
        "subprotocols": [],
    }


def test_ws_reply_to_closed_peer_is_contained():
    reg = make()

    async def go():
        ws = RawWS(build_app(reg), "/ws/1")
        await ws.open()
        await ws.recv_json()
        real = ws.out.put

        async def put(msg):
            if msg["type"] == "websocket.send" and "receipt" in msg["text"]:
                raise OSError("peer gone")
            await real(msg)

        ws.out.put = put
        await ws.send_json({"type": "INC"})
        await ws.close()  # task ends cleanly, no escaping RuntimeError
        assert ws.task.exception() is None
        assert reg.connections() == 0

    asyncio.run(go())


# -----------------------------------------------------------------------------
# ⏰ Timer-driven transitions reach the streams
# -----------------------------------------------------------------------------
TIMER_CFG = {
    "id": "t",
    "initial": "wait",
    "states": {"wait": {"after": {"1000": "expired"}}, "expired": {}},
}


def test_scanner_fired_after_is_pushed_to_sse():
    reg = StatechartRegistry(
        MemoryStore(),
        run_timers=True,
        scanner_interval_s=0.02,
        scanner_now=lambda: time.time() + 3600,
    )
    reg.register("payment", create_machine(TIMER_CFG), authorize=allow_all)
    app = build_app(reg)

    async def go():
        async with reg.lifespan():
            sse = RawSSE(app, "/m/1/stream")
            await sse.open()
            _, ev, snap = await sse.next_event()
            assert snap["state"] == "wait"
            async with reg.act("payment", "1"):
                pass  # persist the deadline; the scanner fires it
            while True:
                seq, ev, data = await sse.next_event()
                if ev == "transition":
                    break
            assert data["state"] == "expired" and seq == 1
            assert (
                sum(isinstance(p, TimerPublisher) for p in reg.scanner.plugins)
                == 1
            )
            assert not any(isinstance(p, TimerPublisher) for p in reg.plugins)
            await sse.close()

    asyncio.run(go())


def test_timer_publisher_publishes_only_after_commit_and_cross_thread():
    from src.xstate_statemachine.contrib.starlette._fanout import (
        _Subscribers,
    )

    class R:
        changed = True

    class Interp:
        store_key = "payment.7"

    async def go():
        subs = _Subscribers()
        sub = subs.subscribe("payment", "7")
        pub = TimerPublisher(
            subs, asyncio.get_running_loop(), lambda i, r, n: {"n": n}
        )

        def thread():
            pub.on_event_processed(Interp(), None, R())
            pub.discard_marks()  # refused save: nothing goes out
            pub.on_event_processed(Interp(), None, R())
            pub.flush_marks()

        t = threading.Thread(target=thread)
        t.start()
        t.join(1.0)
        item = await bounded(sub.queue.get())
        assert item == (1, {"n": "payment"})
        assert sub.queue.empty()

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 🚀 [fastapi] wrappers
# -----------------------------------------------------------------------------
def test_fastapi_reads_refuse_unauthorized_403():
    pytest.importorskip("fastapi")
    from fastapi import FastAPI

    from src.xstate_statemachine.contrib.fastapi import StatechartRouter

    reg = StatechartRegistry(MemoryStore())
    reg.register(
        "payment",
        counter_machine(),
        authorize=lambda c, **k: c.headers.get("x-ok") == "1",
    )
    app = FastAPI(lifespan=reg.lifespan)
    app.include_router(StatechartRouter(reg, "payment"))
    with TestClient(app) as c:
        for path in ("/payment/1", "/payment/1/events", "/payment/1/stream"):
            r = c.get(path)
            assert r.status_code == 403, path
            assert r.headers["content-type"].startswith(
                "application/problem+json"
            )
            assert "INC" not in r.text
        r = c.get("/payment/1/diagram.mmd")
        assert r.status_code == 403 and "INC" not in r.text
        assert c.get("/payment/1/events", headers={"x-ok": "1"}).json()[
            "available"
        ] == ["INC"]
