# tests/contrib/fastapi/test_fastapi.py
"""#276: StatechartRouter, get_interpreter, OpenAPI, instrument_app.

Every network read is bounded (TestClient / httpx timeouts, `bounded`).
Skips without the extra."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Literal

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
from ..starlette._support import (
    RawSSE,
    bounded,
    counter_machine,
    payment_machine,
)

pytestmark = requires_extra("fastapi")
pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.xstate_statemachine.contrib.fastapi import (  # noqa: E402
    ReceiptResponse,
    StatechartRegistry,
    StatechartRouter,
    allow_all,
    compose_lifespan,
    get_interpreter,
    instrument_app,
)
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    EventModel,
    events_union,
)


class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    amount: int


class Cancel(EventModel):
    type: Literal["CANCEL"] = "CANCEL"


def order_machine():
    cfg = {
        "id": "order",
        "initial": "open",
        "states": {
            "open": {"on": {"PAY": "paid", "CANCEL": "cancelled"}},
            "paid": {"on": {"CANCEL": {"target": "cancelled"}}},
            "cancelled": {},
        },
    }
    return create_machine(cfg, event_schemas=events_union(Pay, Cancel))


def make(machine=None, name="order", store=None, authorize=allow_all, **kw):
    reg = StatechartRegistry(store or MemoryStore(), **kw)
    reg.register(name, machine or order_machine(), authorize=authorize)
    return reg


def app_for(reg, name="order", **router_kw):
    app = FastAPI()
    app.include_router(StatechartRouter(reg, name, **router_kw))
    return instrument_app(app, reg)


def idem_reg(**kw):
    return make(
        inbox=MemoryInbox(),
        principal=lambda c: c.headers.get("x-user", "anon"),
        **kw,
    )


# -----------------------------------------------------------------------------
# 🛣️ Routes
# -----------------------------------------------------------------------------
class TestRoutes:
    def test_get_state_is_state_only(self):
        with TestClient(app_for(make())) as c:
            r = c.get("/order/1")
            assert r.status_code == 200
            body = r.json()
            assert body["state"] == "open"
            assert body["available_events"] == ["CANCEL", "PAY"]
            assert "context" not in body

    def test_send_union_valid_and_invalid(self):
        with TestClient(app_for(make())) as c:
            r = c.post("/order/1/send", json={"type": "PAY", "amount": 3})
            assert r.status_code == 200 and r.json()["changed"] is True
            assert c.get("/order/1").json()["state"] == "paid"
            for bad in (
                {"type": "BOGUS"},
                {"type": "PAY"},
                {"type": "PAY", "amount": "x"},
                {"type": "CANCEL", "extra": 1},
            ):
                r = c.post("/order/2/send", json=bad)
                assert r.status_code == 422, bad
                assert r.headers["content-type"] == "application/problem+json"
                assert "input" not in json.dumps(r.json())

    def test_path_event_routes(self):
        with TestClient(app_for(make())) as c:
            r = c.post("/order/1/events/CANCEL")
            assert r.status_code == 200 and r.json()["state"] == "cancelled"
            r = c.post("/order/1/events/PAY", json={"amount": 1})
            # cancelled has no PAY transition: unchanged, not denied
            assert r.status_code == 200 and r.json()["changed"] is False
            r = c.post("/order/2/events/PAY", json={"amount": "no"})
            assert r.status_code == 422

    def test_events_route(self):
        with TestClient(app_for(make())) as c:
            c.post("/order/1/send", json={"type": "PAY", "amount": 1})
            body = c.get("/order/1/events").json()
            assert body["available"] == ["CANCEL"]
            types = [d["type"] for d in body["declared"]]
            assert types == ["CANCEL", "PAY"]
            pay = body["declared"][1]["schema"]
            assert "amount" in pay["properties"]

    def test_diagram(self):
        with TestClient(app_for(make())) as c:
            r = c.get("/order/1/diagram.mmd")
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/plain")
            assert r.text.startswith("stateDiagram")
        app = app_for(make(), include_diagram=False)
        assert "/order/{id}/diagram.mmd" not in app.openapi()["paths"]

    def test_fallback_body_without_models(self):
        reg = make(payment_machine(), name="payment")
        with TestClient(app_for(reg, "payment", prefix="/p")) as c:
            r = c.post("/p/1/send", json={"type": "SUBMIT"})
            assert r.status_code == 200 and r.json()["changed"]
            r = c.post(
                "/p/1/send", json={"type": "RESET", "payload": {"a": 1}}
            )
            assert r.status_code == 200
            assert c.post("/p/1/send", json={"type": "X"}).status_code == 422

    def test_json_only_and_size(self):
        reg = make(max_body_bytes=64)
        with TestClient(app_for(reg)) as c:
            r = c.post(
                "/order/1/send",
                content=b'{"type":"CANCEL"}',
                headers={"content-type": "text/plain"},
            )
            assert r.status_code == 415
            r = c.post("/order/1/send", json={"type": "PAY", "amount": 10**80})
            assert r.status_code == 413

    def test_create_if_missing_false_is_404(self):
        with TestClient(app_for(make(), create_if_missing=False)) as c:
            assert c.get("/order/nope").status_code == 404
            r = c.post("/order/nope/send", json={"type": "CANCEL"})
            assert r.status_code == 404
            assert r.headers["content-type"] == "application/problem+json"

    def test_custom_key_param_prefix_and_opids(self):
        app = app_for(
            make(),
            prefix="/orders",
            key_param="order_id",
            tags=["orders"],
            operation_id_prefix="ord",
        )
        with TestClient(app) as c:
            assert c.get("/orders/5").status_code == 200
        paths = app.openapi()["paths"]
        assert paths["/orders/{order_id}/send"]["post"]["operationId"] == (
            "ord_send"
        )
        assert paths["/orders/{order_id}"]["get"]["tags"] == ["orders"]


# -----------------------------------------------------------------------------
# 🔐 Authorization / idempotency
# -----------------------------------------------------------------------------
class TestSecurity:
    def test_authorize_denied_403(self):
        reg = make(authorize=lambda c, **k: c.headers.get("x-ok") == "1")
        with TestClient(app_for(reg)) as c:
            for r in (
                c.get("/order/1"),
                c.get("/order/1/events"),
                c.get("/order/1/diagram.mmd"),
                c.post("/order/1/send", json={"type": "CANCEL"}),
                c.post("/order/1/events/CANCEL"),
            ):
                assert r.status_code == 403
                assert r.json()["title"] == "Forbidden"
            ok = {"x-ok": "1"}
            assert c.get("/order/1", headers=ok).status_code == 200

    def test_idempotency_duplicate_same_body(self):
        with TestClient(app_for(idem_reg())) as c:
            h = {"Idempotency-Key": "k1", "x-user": "u1"}
            a = c.post("/order/1/send", json={"type": "CANCEL"}, headers=h)
            b = c.post("/order/1/send", json={"type": "CANCEL"}, headers=h)
            assert a.status_code == b.status_code == 200
            assert a.json()["duplicate"] is False
            assert b.json()["duplicate"] is True

            def strip(d):
                return {k: v for k, v in d.items() if k != "duplicate"}

            assert strip(a.json())["state"] == strip(b.json())["state"]
            # another principal with the same key is NOT a duplicate (X0.2)
            h2 = {"Idempotency-Key": "k1", "x-user": "u2"}
            r = c.post("/order/2/send", json={"type": "CANCEL"}, headers=h2)
            assert r.json()["duplicate"] is False

    def test_idempotency_on_path_route_and_model_body(self):
        with TestClient(app_for(idem_reg())) as c:
            h = {"Idempotency-Key": "p", "x-user": "u"}
            a = c.post("/order/1/events/PAY", json={"amount": 1}, headers=h)
            b = c.post("/order/1/events/PAY", json={"amount": 1}, headers=h)
            assert a.json()["changed"] is True
            assert b.json()["duplicate"] is True

    def test_actor_dependency_is_the_principal(self):
        seen = []

        async def actor(request: Request) -> str:
            seen.append(request.headers.get("x-sub"))
            return request.headers.get("x-sub", "anon")

        reg = make(inbox=MemoryInbox())
        with TestClient(app_for(reg, actor=actor)) as c:
            h = {"Idempotency-Key": "z", "x-sub": "alice"}
            c.post("/order/1/send", json={"type": "CANCEL"}, headers=h)
            r = c.post("/order/1/send", json={"type": "CANCEL"}, headers=h)
            assert r.json()["duplicate"] is True
        assert seen[0] == "alice"

    def test_dependencies_and_per_event_dependencies(self):
        from fastapi import Depends, Header, HTTPException

        def admin(x_admin: str = Header("")) -> None:
            if x_admin != "yes":
                raise HTTPException(401)

        app = app_for(
            make(), per_event_dependencies={"CANCEL": [Depends(admin)]}
        )
        with TestClient(app) as c:
            assert c.post("/order/1/events/CANCEL").status_code == 401
            r = c.post("/order/1/send", json={"type": "CANCEL"})
            assert r.status_code == 403  # the gate cannot be bypassed
            r = c.post("/order/1/events/CANCEL", headers={"x-admin": "yes"})
            assert r.status_code == 200
        app = app_for(make(), dependencies=[Depends(admin)])
        with TestClient(app) as c:
            assert c.get("/order/1").status_code == 401


# -----------------------------------------------------------------------------
# ⚡ Concurrency
# -----------------------------------------------------------------------------
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
    rec = store.load("c.k")
    assert rec.version == changed
    assert json.loads(rec.snapshot)["context"]["n"] == 50


# -----------------------------------------------------------------------------
# 📜 OpenAPI
# -----------------------------------------------------------------------------
class TestOpenAPI:
    def test_schema_validates_with_union_and_problem(self):
        validator = pytest.importorskip("openapi_spec_validator")
        app = app_for(make())
        doc = app.openapi()
        validator.validate(doc)
        send = doc["paths"]["/order/{id}/send"]["post"]
        schema = send["requestBody"]["content"]["application/json"]["schema"]
        assert schema["discriminator"]["propertyName"] == "type"
        refs = sorted(r["$ref"].rsplit("/", 1)[1] for r in schema["oneOf"])
        assert refs == ["Cancel", "Pay"]
        for status in ("403", "409", "422", "500"):
            content = send["responses"][status]["content"]
            assert "application/problem+json" in content
            ref = content["application/problem+json"]["schema"]["$ref"]
            assert ref.endswith("/Problem")
        assert "ReceiptModel" in doc["components"]["schemas"]
        ops = {
            o["operationId"] for p in doc["paths"].values() for o in p.values()
        }
        assert {"order_send", "order_pay", "order_cancel"} <= ops

    def test_fallback_schema_is_deterministic(self):
        reg = make(payment_machine(), name="payment")
        a = app_for(reg, "payment").openapi()
        reg2 = make(payment_machine(), name="payment")
        b = app_for(reg2, "payment").openapi()
        assert a == b
        ev = a["components"]["schemas"]["PaymentEvent"]
        assert sorted(ev["properties"]["type"]["enum"]) == [
            "RESET",
            "RETRY",
            "SUBMIT",
            "UPDATE_FORM",
        ]


# -----------------------------------------------------------------------------
# 📡 Streaming
# -----------------------------------------------------------------------------
def test_sse_one_transition_per_changed_receipt():
    reg = make()
    app = app_for(reg)

    async def go():
        sse = RawSSE(app, "/order/9/stream")
        assert await sse.open() == 200
        _, ev, data = await sse.next_event()
        assert ev == "snapshot" and data["state"] == "open"
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t", timeout=5
        ) as client:
            for body in (
                {"type": "PAY", "amount": 1},
                {"type": "PAY", "amount": 1},  # unchanged: no push
                {"type": "CANCEL"},
            ):
                await client.post("/order/9/send", json=body)
        got = [await sse.next_event() for _ in range(2)]
        assert [g[2]["state"] for g in got] == ["paid", "cancelled"]
        assert sse.out.empty()
        await sse.close()
        assert reg.connections() == 0

    asyncio.run(go())


def test_websocket_round_trip():
    reg = make()
    with TestClient(app_for(reg)) as c:
        with c.websocket_connect("/order/3/ws") as ws:
            assert ws.receive_json()["kind"] == "snapshot"
            ws.send_json({"type": "PAY", "payload": {"amount": 2}})
            kinds = sorted(ws.receive_json()["kind"] for _ in range(2))
            assert kinds == ["receipt", "transition"]
        assert c.get("/order/3").json()["state"] == "paid"
    assert reg.connections() == 0


# -----------------------------------------------------------------------------
# 🪝 get_interpreter
# -----------------------------------------------------------------------------
class TestGetInterpreter:
    def _app(self, reg, **kw):
        app = FastAPI()
        dep = get_interpreter(reg, "order", key="order_id", **kw)

        @app.post("/orders/{order_id}/pay")
        async def pay(order=dep):
            return ReceiptResponse(
                order, await order.send("PAY", wait=True, amount=1)
            )

        @app.post("/orders/{order_id}/pay-then-fail")
        async def fail(order=dep):
            await order.send("PAY", wait=True, amount=1)
            raise RuntimeError("boom")

        app.include_router(StatechartRouter(reg, "order", prefix="/orders"))
        return instrument_app(app, reg)

    def test_persists_on_return_not_on_raise(self):
        reg = make()
        app = self._app(reg)
        with TestClient(app, raise_server_exceptions=False) as c:
            r = c.post("/orders/1/pay-then-fail")
            assert r.status_code == 500
            assert c.get("/orders/1").json()["state"] == "open"
            r = c.post("/orders/1/pay")
            assert r.status_code == 200 and r.json()["changed"]
            assert c.get("/orders/1").json()["state"] == "paid"

    def test_conflict_maps_to_409(self):
        reg = make(lock=OptimisticLock(retries=0))
        orig = reg._astore.save

        async def racing_save(*a, **k):
            raise ConflictError("order.1", 0, 1)

        reg._astore.save = racing_save
        with TestClient(self._app(reg)) as c:
            r = c.post("/orders/1/pay")
            assert r.status_code == 409
            assert r.headers["content-type"] == "application/problem+json"
            assert "order.1" not in r.text
        reg._astore.save = orig

    def test_authorize_and_missing_key(self):
        reg = make(authorize=lambda c, **k: c.headers.get("x-ok") == "1")
        app = self._app(reg, create_if_missing=False)
        with TestClient(app) as c:
            assert c.post("/orders/1/pay").status_code == 403
            r = c.post("/orders/1/pay", headers={"x-ok": "1"})
            assert r.status_code == 404

    def test_callable_key(self):
        reg = make()
        app = FastAPI()

        @app.post("/me/pay")
        async def pay(
            order=get_interpreter(
                reg, "order", key=lambda r: r.headers["x-id"]
            ),
        ):
            await order.send("PAY", wait=True, amount=1)
            return {"ok": True}

        with TestClient(instrument_app(app, reg)) as c:
            c.post("/me/pay", headers={"x-id": "7"})
        rec = reg.store.load("order.7")
        assert rec.version == 1


# -----------------------------------------------------------------------------
# 🧰 instrument_app / compose_lifespan
# -----------------------------------------------------------------------------
def test_lifespan_composition_and_probes():
    reg = make()
    events = []

    @contextlib.asynccontextmanager
    async def mine(app):
        events.append(("up", reg.started))
        yield
        events.append(("down", reg.started))

    app = FastAPI(lifespan=mine)
    instrument_app(app, reg)
    with TestClient(app) as c:
        assert c.get("/_xsm/health").json() == {"status": "ok"}
        assert c.get("/_xsm/ready").status_code == 200
    assert events == [("up", True), ("down", True)]
    assert reg.started is False

    reg2 = make()
    app2 = FastAPI(lifespan=compose_lifespan(reg2))
    with TestClient(app2):
        assert reg2.started
    assert not reg2.started


def test_ready_503_before_start():
    reg = make()
    app = instrument_app(FastAPI(), reg)
    c = TestClient(app)  # no context manager: lifespan not run
    assert c.get("/_xsm/ready").status_code == 503


def test_bounded_helper_is_shared():
    async def slow():
        await asyncio.sleep(5)

    with pytest.raises(asyncio.TimeoutError):
        asyncio.run(bounded(slow(), 0.01))
