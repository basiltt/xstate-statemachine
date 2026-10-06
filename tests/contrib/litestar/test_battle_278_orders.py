# tests/contrib/litestar/test_battle_278_orders.py
"""#278 battle: the order service's chart served through Litestar.

There is no Litestar example app; the scenario is the `fastapi_orders`
chart (`machine.json`, its pydantic event models and logic) behind
`create_statechart_controller` + `XStatePlugin`, driven the way the
#275 / #276 battles drove the FastAPI surface, so every hardening those
battles added to the shared registry is pinned HERE too:

* **idempotency is honest** -- with an inbox a replay is `duplicate` and
  a different body under the same key is 422 with no echoed value; on a
  registry without an inbox the header is 501, never ignored; the same
  on a custom `get_interpreter` route (`Provide`);
* **`get_interpreter` persists exactly on success** -- a handler that
  raises after a send persists nothing and leaks no exception text;
* **the gate** -- `PAY` is refused by the registry's `authorize` unless
  the request was marked by the dedicated route, on `/send`, on
  `/events/PAY` of a second controller, and over the WebSocket (1008);
* **bodies** -- unknown `type` 422 (msgspec and pydantic flavours), a
  1 MB body 413 before parsing, `text/plain` 415, an oversized string
  422; none echo the value;
* **OpenAPI** -- generates in bounded time, every route has an
  `operationId`, `/send` is a discriminated union, 409/422 documented,
  no response schema promises `card_token`;
* **50 concurrent `PAY`s** under one key on SQLite charge once;
* **streams** -- `/stream` yields the snapshot immediately over a raw
  ASGI driver (Litestar's `TestClient.stream` buffers SSE -- a harness
  artefact, documented), a stalled subscriber is cut at `MAX_BACKLOG`
  and the slot is released on close; the WebSocket round-trips an event
  and closes 1001 on shutdown;
* **readiness** -- `/_xsm/ready` 503 before lifespan / after shutdown.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.persistence import SQLiteInbox, SQLiteStore

from ..conftest import requires_extra
from ..starlette._support import RawSSE, RawWS, bounded

pytestmark = [requires_extra("litestar"), pytest.mark.timeout(300)]
pytest.importorskip("litestar")
pytest.importorskip("pydantic")
httpx = pytest.importorskip("httpx")

from litestar import Litestar, Request, Response, post  # noqa: E402
from litestar.testing import TestClient  # noqa: E402

from src.xstate_statemachine.contrib.litestar import (  # noqa: E402
    ReceiptResponse,
    StatechartRegistry,
    XStatePlugin,
    create_statechart_controller,
    get_interpreter,
)
from src.xstate_statemachine.contrib.starlette import _fanout  # noqa: E402

ORDERS = (
    Path(__file__).resolve().parents[3]
    / "examples"
    / "integrations"
    / "fastapi_orders"
)
ANN = {"x-customer": "ann"}
PAY_GATE = "xsm_pay_gate"


def _orders_modules() -> Tuple[Any, Any]:
    if str(ORDERS) not in sys.path:
        sys.path.insert(0, str(ORDERS))
    import logic  # type: ignore[import-not-found]
    import models  # type: ignore[import-not-found]

    return logic, models


def _customer(conn: Any) -> str:
    return str(conn.headers.get("x-customer") or "")


def _authorize(
    conn: Any, *, name: str, key: str, event: Optional[str]
) -> bool:
    if not _customer(conn):
        return False
    if event == "PAY":
        return bool(getattr(getattr(conn, "state", None), PAY_GATE, False))
    return True


def _machine() -> Any:
    logic, models = _orders_modules()
    cfg = json.loads((ORDERS / "machine.json").read_text("utf-8"))
    return create_machine(
        cfg,
        logic=logic.build_logic(None),
        event_schemas=models.EVENT_SCHEMAS,
    )


def _registry(tmp_path: Path, *, inbox: bool = True) -> StatechartRegistry:
    _orders_modules()
    import models  # type: ignore[import-not-found]

    store = SQLiteStore(str(tmp_path / "orders.db"))
    reg = StatechartRegistry(
        store,
        inbox=SQLiteInbox(store) if inbox else None,
        principal=_customer,
        heartbeat_s=0.5,
    )
    reg.register(
        "order",
        _machine(),
        authorize=_authorize,
        context_serializer=models.public_context,
    )
    return reg


def _pay_route(reg: StatechartRegistry, emails: List[str]) -> Any:
    @post("/orders/{id:str}/events/PAY", status_code=200)
    async def pay(request: Request, id: str) -> Response:  # noqa: A002
        from src.xstate_statemachine.contrib.litestar._edge import (
            to_litestar,
            to_starlette,
        )

        body = await request.json()
        conn = to_starlette(request)
        setattr(conn.state, PAY_GATE, True)
        resp = await reg.send_event(conn, "order", id, "PAY", body)
        if resp.status_code == 200:
            data = json.loads(bytes(resp.body))
            if data.get("changed") and data.get("state") == "paid":
                emails.append(id)
        return to_litestar(resp)

    return pay


def _app(
    reg: StatechartRegistry, emails: Optional[List[str]] = None, *extra: Any
) -> Litestar:
    ctl = create_statechart_controller(
        reg, "order", path="/orders", exclude_events=("PAY",)
    )
    handlers = [_pay_route(reg, emails if emails is not None else []), ctl]
    handlers += list(extra)
    return Litestar(
        route_handlers=handlers,
        plugins=[XStatePlugin(reg)],
        logging_config=None,
        debug=False,
    )


def _post(c: Any, order: str, event: str, body: Any = None, **h: str) -> Any:
    return c.post(
        f"/orders/{order}/events/{event}", json=body, headers={**ANN, **h}
    )


def _checkout(c: Any, order: str) -> None:
    assert (
        _post(c, order, "ADD_ITEM", {"sku": "tea", "qty": 2}).status_code
        == 200
    )
    r = _post(c, order, "CHECKOUT")
    assert r.json()["state"] == "awaitingPayment", r.text


# -----------------------------------------------------------------------------
# 1. idempotency is honest
# -----------------------------------------------------------------------------
def test_idempotency_with_and_without_inbox(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with TestClient(_app(reg)) as c:
        body = {"sku": "tea", "qty": 1}
        r1 = _post(c, "o1", "ADD_ITEM", body, **{"Idempotency-Key": "k"})
        r2 = _post(c, "o1", "ADD_ITEM", body, **{"Idempotency-Key": "k"})
        assert (r1.status_code, r2.status_code) == (200, 200)
        assert r1.json()["duplicate"] is False and r2.json()["duplicate"]
        r3 = _post(
            c,
            "o1",
            "ADD_ITEM",
            {"sku": "tea", "qty": 9},
            **{"Idempotency-Key": "k"},
        )
        assert r3.status_code == 422 and '"9"' not in r3.text
        assert (
            len(c.get("/orders/o1", headers=ANN).json()["context"]["items"])
            == 1
        )
    (tmp_path / "noinbox").mkdir(exist_ok=True)
    reg2 = _registry(tmp_path / "noinbox", inbox=False)
    with TestClient(_app(reg2)) as c:
        r = _post(
            c,
            "o1",
            "ADD_ITEM",
            {"sku": "tea", "qty": 1},
            **{"Idempotency-Key": "k"},
        )
        assert r.status_code == 501, r.text
        assert (
            c.get("/orders/o1", headers=ANN).json()["context"]["items"] == []
        )


def test_provide_route_persists_on_return_not_on_raise(tmp_path: Path) -> None:
    reg = _registry(tmp_path)

    dep = {"order": get_interpreter(reg, "order")}

    @post("/custom/{id:str}/boom", dependencies=dep)
    async def boom(order: Any) -> None:
        await order.send("ADD_ITEM", sku="tea", qty=1, wait=True)
        raise RuntimeError("db password=hunter2 in the trace")

    @post("/custom/{id:str}/ok", dependencies=dep)
    async def ok(order: Any) -> Response:
        return ReceiptResponse(
            order, await order.send("ADD_ITEM", sku="tea", qty=1, wait=True)
        )

    with TestClient(
        _app(reg, None, boom, ok), raise_server_exceptions=False
    ) as c:
        r = c.post("/custom/o1/boom", headers=ANN)
        assert r.status_code == 500
        assert "hunter2" not in r.text and "password" not in r.text
        assert (
            c.get("/orders/o1", headers=ANN).json()["context"]["items"] == []
        )
        assert c.post("/custom/o1/ok", headers=ANN).status_code == 200
        assert (
            len(c.get("/orders/o1", headers=ANN).json()["context"]["items"])
            == 1
        )


# -----------------------------------------------------------------------------
# 2. the gate
# -----------------------------------------------------------------------------
def test_pay_gate_holds_on_send_second_controller_and_websocket(
    tmp_path: Path,
) -> None:
    reg = _registry(tmp_path)
    emails: List[str] = []
    admin = create_statechart_controller(reg, "order", path="/admin")
    app = _app(reg, emails, admin)
    with TestClient(app) as c:
        _checkout(c, "o1")
        r = c.post(
            "/orders/o1/send",
            json={"type": "PAY", "card_token": "tok_ok"},
            headers=ANN,
        )
        assert r.status_code == 403
        r = c.post(
            "/admin/o1/events/PAY", json={"card_token": "tok_ok"}, headers=ANN
        )
        assert r.status_code == 403
        assert emails == []
        r = _post(c, "o1", "PAY", {"card_token": "tok_ok"})
        assert r.json()["state"] == "paid" and emails == ["o1"]

    async def ws() -> None:
        async with reg.lifespan():
            s = RawWS(app, "/orders/o2/ws", headers=[("x-customer", "ann")])
            first = await s.open()
            assert first["type"] == "websocket.accept", first
            await s.recv_json()  # snapshot
            await s.send_json({"type": "PAY", "payload": {"card_token": "x"}})
            msg = await bounded(s.out.get())
            assert (
                msg["type"] == "websocket.close" and msg["code"] == 1008
            ), msg
            await s.close()

    asyncio.run(ws())


# -----------------------------------------------------------------------------
# 3. bodies
# -----------------------------------------------------------------------------
def test_body_rules_and_no_echo(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    with TestClient(_app(reg)) as c:
        r = c.post("/orders/o1/send", json={"type": "NOPE"}, headers=ANN)
        assert r.status_code == 422 and "NOPE" not in r.text
        big = "x" * (1024 * 1024)
        r = c.post(
            "/orders/o1/send",
            content=json.dumps({"type": "ADD_ITEM", "sku": big, "qty": 1}),
            headers={**ANN, "content-type": "application/json"},
        )
        assert r.status_code in (413, 422) and big[:64] not in r.text
        r = c.post(
            "/orders/o1/events/ADD_ITEM",
            content="sku=tea",
            headers={**ANN, "content-type": "text/plain"},
        )
        assert r.status_code == 415
        r = _post(c, "o1", "ADD_ITEM", {"sku": "s" * 5000, "qty": 1})
        assert r.status_code == 422 and "sssss" not in r.text


# -----------------------------------------------------------------------------
# 4. OpenAPI
# -----------------------------------------------------------------------------
def test_openapi_bounded_complete_and_leak_free(tmp_path: Path) -> None:
    app = _app(_registry(tmp_path))
    t0 = time.perf_counter()
    with TestClient(app) as c:
        r = c.get("/schema/openapi.json")  # what a client actually fetches
    assert time.perf_counter() - t0 < 10.0
    assert r.status_code == 200
    doc = r.json()
    paths = doc["paths"]
    ours = [p for p in paths if p.startswith("/orders/")]
    assert len(ours) >= 10, sorted(paths)
    for p in ours:
        for method, op in paths[p].items():
            assert op.get("operationId"), (p, method)
    send = paths["/orders/{id}/send"]["post"]
    assert {"409", "422"} <= set(send["responses"]), send["responses"].keys()
    schema = send["requestBody"]["content"]["application/json"]["schema"]
    schemas = doc["components"]["schemas"]
    target = schema
    if "$ref" in schema:
        target = schemas[schema["$ref"].rsplit("/", 1)[-1]]
    assert "oneOf" in target or "anyOf" in target, target
    blob = json.dumps(doc)
    assert "card_token" in blob
    for name, s in schemas.items():
        if name.lower().startswith(("state", "receipt")):
            assert "card_token" not in json.dumps(s), name


# -----------------------------------------------------------------------------
# 5. 50 concurrent PAYs
# -----------------------------------------------------------------------------
def test_fifty_concurrent_pays_charge_once(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    emails: List[str] = []
    app = _app(reg, emails)

    async def go() -> List[int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t"
        ) as ac:
            async with reg.lifespan():
                await ac.post(
                    "/orders/o1/events/ADD_ITEM",
                    json={"sku": "tea", "qty": 1},
                    headers=ANN,
                )
                await ac.post("/orders/o1/events/CHECKOUT", headers=ANN)
                rs = await asyncio.gather(
                    *[
                        ac.post(
                            "/orders/o1/events/PAY",
                            json={"card_token": "tok_ok"},
                            headers={**ANN, "Idempotency-Key": "once"},
                        )
                        for _ in range(50)
                    ]
                )
                return [r.status_code for r in rs]

    codes = asyncio.run(go())
    assert set(codes) <= {200, 409}, codes
    assert emails == ["o1"], emails


# -----------------------------------------------------------------------------
# 6. streams
# -----------------------------------------------------------------------------
def test_sse_snapshot_first_stalled_cut_and_slot_released(
    tmp_path: Path,
) -> None:
    reg = _registry(tmp_path)
    app = _app(reg)

    async def go() -> None:
        async with reg.lifespan():
            s = RawSSE(
                app, "/orders/o1/stream", headers=[("x-customer", "ann")]
            )
            assert await s.open() == 200
            seq, kind, body = await bounded(s.next_event())
            assert kind == "snapshot" and body["state"] == "cart"
            stalled = reg.subscribers.subscribe("order", "o1")
            assert reg.subscribers.count("order", "o1") == 2
            for k in range(_fanout.MAX_BACKLOG + 5):
                async with reg.act("order", "o1", principal="ann") as i:
                    r = await i.send("ADD_ITEM", sku="tea", qty=1, wait=True)
                    assert r.changed
                seq, kind, body = await bounded(s.next_event())
                assert kind == "transition" and seq == k + 1
            assert reg.subscribers.count("order", "o1") == 1  # stalled cut
            assert stalled.queue.get_nowait() is not None
            await s.close()
            await asyncio.sleep(0.05)
            assert reg.subscribers.count() == 0
            assert reg.connections() == 0

    asyncio.run(go())


def test_websocket_round_trip_and_shutdown_1001(tmp_path: Path) -> None:
    reg = _registry(tmp_path)
    app = _app(reg)

    async def go() -> None:
        lifespan = reg.lifespan()
        await lifespan.__aenter__()
        s = RawWS(app, "/orders/o1/ws", headers=[("x-customer", "ann")])
        assert (await s.open())["type"] == "websocket.accept"
        assert (await s.recv_json())["kind"] == "snapshot"
        await s.send_json(
            {"type": "ADD_ITEM", "payload": {"sku": "tea", "qty": 1}}
        )
        kinds = {(await s.recv_json())["kind"] for _ in range(2)}
        assert kinds == {"receipt", "transition"}
        await lifespan.__aexit__(None, None, None)
        closing = await bounded(s.out.get())
        assert closing["type"] == "websocket.close" and closing["code"] == 1001
        await s.close()
        assert reg.connections() == 0

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 7. readiness
# -----------------------------------------------------------------------------
def test_ready_tracks_lifespan(tmp_path: Path) -> None:
    app = _app(_registry(tmp_path))
    bare = TestClient(app)
    assert bare.get("/_xsm/ready").status_code == 503
    with TestClient(app) as c:
        assert c.get("/_xsm/ready").status_code == 200
    assert bare.get("/_xsm/ready").status_code == 503
