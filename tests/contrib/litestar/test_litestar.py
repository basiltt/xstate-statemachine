# tests/contrib/litestar/test_litestar.py
"""#278: XStatePlugin, get_interpreter (Provide), statechart Controller.

Every network read is bounded (TestClient timeouts / `bounded`).
Skips without the extra."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

import pytest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.exceptions import ConflictError
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryStore,
    OptimisticLock,
    SQLiteStore,
)

from ..conftest import requires_extra
from ..starlette._support import RawSSE, counter_machine, payment_machine

pytestmark = requires_extra("litestar")
pytest.importorskip("litestar")
httpx = pytest.importorskip("httpx")

from litestar import Litestar, post  # noqa: E402
from litestar.testing import TestClient  # noqa: E402

from src.xstate_statemachine.contrib.litestar import (  # noqa: E402
    ReceiptResponse,
    StatechartRegistry,
    XStatePlugin,
    allow_all,
    create_statechart_controller,
    get_interpreter,
)


def order_machine():
    from src.xstate_statemachine.contrib.pydantic import (
        EventModel,
        events_union,
    )

    class Pay(EventModel):
        type: Literal["PAY"] = "PAY"
        amount: int

    class Cancel(EventModel):
        type: Literal["CANCEL"] = "CANCEL"

    cfg = {
        "id": "order",
        "initial": "open",
        "states": {
            "open": {"on": {"PAY": "paid", "CANCEL": "cancelled"}},
            "paid": {"on": {"CANCEL": "cancelled"}},
            "cancelled": {},
        },
    }
    return create_machine(cfg, event_schemas=events_union(Pay, Cancel))


def make(machine=None, name="order", store=None, authorize=allow_all, **kw):
    reg = StatechartRegistry(store or MemoryStore(), **kw)
    reg.register(name, machine or order_machine(), authorize=authorize)
    return reg


def app_for(reg, name="order", handlers=(), plugin_kw=None, **ctl_kw):
    ctl = create_statechart_controller(reg, name, **ctl_kw)
    # 📝 `logging_config=None`: Litestar's default `LoggingConfig` installs a
    #    `QueueHandler` on the ROOT logger at app construction and never
    #    removes it, so every `logger.info` in the rest of the pytest
    #    session was retained in its queue -- the tracemalloc leak tests
    #    in tests/persistence read ~800 KB of "library growth" (one
    #    `from_snapshot` log record per cycle) whenever this file ran
    #    first. Found by the #262 battle integration; a test-isolation
    #    defect of THIS suite, not of the library.
    return Litestar(
        route_handlers=[ctl, *handlers],
        plugins=[XStatePlugin(reg, **(plugin_kw or {}))],
        logging_config=None,
    )


class TestRoutes:
    def test_state_send_union_and_problems(self):
        with TestClient(app_for(make())) as c:
            r = c.get("/order/1")
            assert r.status_code == 200 and r.json()["state"] == "open"
            assert "context" not in r.json()
            r = c.post("/order/1/send", json={"type": "PAY", "amount": 2})
            assert r.status_code == 200 and r.json()["changed"] is True
            for bad in ({"type": "PAY"}, {"type": "NOPE"}):
                r = c.post("/order/2/send", json=bad)
                assert r.status_code == 422, bad
                assert r.headers["content-type"].startswith(
                    "application/problem+json"
                )

    def test_path_events_events_diagram(self):
        with TestClient(app_for(make())) as c:
            r = c.post("/order/1/events/PAY", json={"amount": 1})
            assert r.json()["state"] == "paid"
            r = c.post("/order/1/events/CANCEL")
            assert r.json()["state"] == "cancelled"
            body = c.get("/order/2/events").json()
            assert body["available"] == ["CANCEL", "PAY"]
            assert [d["type"] for d in body["declared"]] == ["CANCEL", "PAY"]
            r = c.get("/order/1/diagram.mmd")
            assert r.text.startswith("stateDiagram")
            assert r.headers["content-type"].startswith("text/plain")

    def test_fallback_struct_body(self):
        reg = make(payment_machine(), name="payment")
        with TestClient(app_for(reg, "payment", path="/p")) as c:
            r = c.post("/p/1/send", json={"type": "SUBMIT"})
            assert r.status_code == 200 and r.json()["state"] == "challenge"
            assert c.post("/p/1/send", json={"type": "X"}).status_code == 422

    def test_json_only_size_and_missing(self):
        reg = make(max_body_bytes=64)
        app = app_for(reg, create_if_missing=False)
        with TestClient(app) as c:
            r = c.post(
                "/order/1/send",
                content=b'{"type":"CANCEL"}',
                headers={"content-type": "text/plain"},
            )
            assert r.status_code == 415
            r = c.post("/order/1/send", json={"type": "PAY", "amount": 10**80})
            assert r.status_code == 413
            assert c.get("/order/1").status_code == 404
            r = c.post("/order/1/send", json={"type": "CANCEL"})
            assert r.status_code == 404

    def test_denied_409(self):
        cfg = {
            "id": "g",
            "initial": "a",
            "states": {"a": {"on": {"GO": {"target": "b", "guard": "no"}}}},
        }
        from src.xstate_statemachine import MachineLogic

        m = create_machine(
            {**cfg, "states": {**cfg["states"], "b": {}}},
            logic=MachineLogic(guards={"no": lambda c, e: False}),
        )
        with TestClient(app_for(make(m, name="g"), "g")) as c:
            r = c.post("/g/1/send", json={"type": "GO"})
            assert r.status_code == 409 and r.json()["denied"] is True


class TestSecurity:
    def test_authorize_403(self):
        reg = make(authorize=lambda c, **k: c.headers.get("x-ok") == "1")
        with TestClient(app_for(reg)) as c:
            for r in (
                c.get("/order/1"),
                c.get("/order/1/events"),
                c.get("/order/1/diagram.mmd"),
                c.post("/order/1/send", json={"type": "CANCEL"}),
            ):
                assert r.status_code == 403
            assert c.get("/order/1", headers={"x-ok": "1"}).status_code == 200

    def test_idempotency_duplicate(self):
        reg = make(
            inbox=MemoryInbox(),
            principal=lambda c: c.headers.get("x-user", "anon"),
        )
        with TestClient(app_for(reg)) as c:
            h = {"Idempotency-Key": "k", "x-user": "u"}
            a = c.post("/order/1/send", json={"type": "CANCEL"}, headers=h)
            b = c.post("/order/1/send", json={"type": "CANCEL"}, headers=h)
            assert a.json()["duplicate"] is False
            assert b.json()["duplicate"] is True
            assert a.json()["state"] == b.json()["state"]


def test_openapi_contains_routes_and_union():
    app = app_for(make())
    doc = app.openapi_schema.to_schema()
    paths = sorted(doc["paths"])
    assert "/order/{id}/send" in paths and "/order/{id}/events/PAY" in paths
    validator = pytest.importorskip("openapi_spec_validator")
    validator.validate(doc)
    union = doc["paths"]["/order/{id}/send"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert union["discriminator"]["propertyName"] == "type"
    text = json.dumps(union["oneOf"])
    assert "Pay" in text and "Cancel" in text
    ops = {o["operationId"] for p in doc["paths"].values() for o in p.values()}
    assert {"order_send", "order_pay", "order_get"} <= ops


def test_fifty_concurrent_sends_sqlite(tmp_path):
    store = SQLiteStore(str(tmp_path / "s.db"))
    reg = make(
        counter_machine(),
        name="c",
        store=store,
        lock=OptimisticLock(retries=0),
    )
    app = app_for(reg, "c")

    async def one(client):
        for _ in range(200):
            r = await client.post("/c/k/send", json={"type": "INC"})
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

    results = asyncio.run(go())
    changed = sum(1 for r in results if r.json()["changed"])
    assert changed == 50
    assert store.load("c.k").version == 50


def test_sse_and_websocket():
    reg = make()
    app = app_for(reg)

    async def go():
        sse = RawSSE(app, "/order/9/stream")
        assert await sse.open() == 200
        _, ev, data = await sse.next_event()
        assert ev == "snapshot" and data["state"] == "open"
        async with reg.act("order", "9") as i:
            await i.send("PAY", wait=True, amount=1)
        _, ev, data = await sse.next_event()
        assert ev == "transition" and data["state"] == "paid"
        await sse.close()
        assert reg.connections() == 0

    asyncio.run(go())
    with TestClient(app) as c:
        with c.websocket_connect("/order/3/ws") as ws:
            assert ws.receive_json()["kind"] == "snapshot"
            ws.send_json({"type": "CANCEL", "payload": {}})
            kinds = sorted(ws.receive_json()["kind"] for _ in range(2))
            assert kinds == ["receipt", "transition"]
    assert reg.connections() == 0


class TestPluginAndDependency:
    def _handlers(self, reg):
        dep = {"order": get_interpreter(reg, "order", key="order_id")}

        @post("/orders/{order_id:str}/pay", dependencies=dep)
        async def pay(order: Any) -> Any:
            from litestar import Response

            r = ReceiptResponse(
                order, await order.send("PAY", wait=True, amount=1)
            )
            return Response(bytes(r.body), status_code=r.status_code)

        @post("/orders/{order_id:str}/fail", dependencies=dep)
        async def fail(order: Any) -> None:
            await order.send("PAY", wait=True, amount=1)
            raise RuntimeError("boom")

        return [pay, fail]

    def test_persist_on_return_not_on_raise(self):
        reg = make()
        app = app_for(reg, handlers=self._handlers(reg))
        with TestClient(app) as c:
            assert c.post("/orders/1/fail").status_code == 500
            assert c.get("/order/1").json()["state"] == "open"
            assert c.post("/orders/1/pay").status_code == 200
            assert c.get("/order/1").json()["state"] == "paid"

    def test_conflict_409_problem(self):
        reg = make(lock=OptimisticLock(retries=0))

        async def racing_save(*a, **k):
            raise ConflictError("order.1", 0, 1)

        reg._astore.save = racing_save
        app = app_for(reg, handlers=self._handlers(reg))
        with TestClient(app) as c:
            r = c.post("/orders/1/pay")
            assert r.status_code == 409
            assert "order.1" not in r.text

    def test_lifespan_probes_and_app_dependencies(self):
        reg = make()
        seen = []

        @post("/x/{id:str}")
        async def x(order: Any) -> None:
            seen.append(order.value)

        app = app_for(reg, handlers=[x], plugin_kw={"dependencies": True})
        with TestClient(app) as c:
            assert reg.started is True
            assert c.get("/_xsm/health").json() == {"status": "ok"}
            assert c.get("/_xsm/ready").json()["status"] == "ready"
            c.post("/x/5")
        assert reg.started is False
        assert seen == ["open"]
