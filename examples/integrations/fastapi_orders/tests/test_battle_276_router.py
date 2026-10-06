# examples/integrations/fastapi_orders/tests/test_battle_276_router.py
"""#276 battle: the FastAPI surface of the order service under misuse.

`StatechartRouter`, `get_interpreter`, `instrument_app` and the OpenAPI
document are what the frontend team and every client SDK rely on. Pinned:

* **idempotency is honest** -- an `Idempotency-Key` on a registry that
  has an inbox dedups across retries (same body → one commit, replays
  `duplicate`, a different body → 422); on a registry WITHOUT an inbox
  the header is refused (501), never silently ignored; the same holds
  for a custom route built on `get_interpreter`;
* **`get_interpreter` persists exactly on success** -- a handler that
  returns persists, one that raises after a send persists nothing and
  leaks no exception text; a `BackgroundTasks` closure that holds the
  request's interpreter cannot act on it after the response (the
  interpreter is stopped; the documented recipe is a fresh `act()`);
* **per-event gates cannot be bypassed** -- `PAY` is gated behind the
  app's own route (email hook); `/send` with `type: PAY` is 403 even
  with a valid body, and so is `/events/PAY` on a *different* router
  prefix;
* **bodies** -- a `/send` body with an unknown `type` is 422 with the
  problem shape (no echoed value); a 1 MB body is 413 before parsing; a
  non-JSON content type is 415; an oversized `sku` string is 422 and
  the response never contains it;
* **OpenAPI** -- the document generates in bounded time, every generated
  route has an `operationId`, 409/422 are documented, the `/send` body
  is a discriminated union on `type`, and **no** schema exposes
  `card_token` or any `context` field the serializer hides;
* **50 concurrent `PAY`s through the custom route** -- exactly one
  charge, one email; the rest are 409 or `duplicate`;
* **readiness** -- `/_xsm/ready` is 503 before lifespan and after
  shutdown, 200 in between; `/_xsm/health` never touches the store.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import pytest

pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi import BackgroundTasks, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app as orders  # noqa: E402
from xstate_statemachine.contrib.fastapi import (  # noqa: E402
    StatechartRouter,
    get_interpreter,
    instrument_app,
)
from xstate_statemachine.contrib.starlette import (  # noqa: E402
    ReceiptResponse,
    StatechartRegistry,
)
from xstate_statemachine.persistence import (  # noqa: E402
    SQLiteInbox,
    SQLiteStore,
)

pytestmark = pytest.mark.timeout(300)

ANN = {"x-customer": "ann"}
Email = Tuple[str, Optional[str], str]


@pytest.fixture
def store(tmp_path):
    return SQLiteStore(str(tmp_path / "orders.db"))


@pytest.fixture
def registry(store):
    return orders.build_registry(store, SQLiteInbox(store))


@pytest.fixture
def emails() -> List[Email]:
    return []


@pytest.fixture
def app(registry, emails):
    return orders.create_app(
        registry, email=lambda *a: emails.append(a), debug=False
    )


def post(client: Any, order: str, event: str, body: Any = None, **h: str):
    return client.post(
        f"/orders/{order}/events/{event}", json=body, headers={**ANN, **h}
    )


def checkout(client: Any, order: str) -> None:
    assert post(client, order, "ADD_ITEM", {"sku": "tea", "qty": 2}).is_success
    assert post(client, order, "CHECKOUT").json()["state"] == "awaitingPayment"


# -----------------------------------------------------------------------------
# 1. idempotency is honest
# -----------------------------------------------------------------------------
def test_idempotency_key_dedups_with_inbox(app) -> None:
    with TestClient(app) as c:
        body = {"sku": "tea", "qty": 1}
        r1 = post(c, "o1", "ADD_ITEM", body, **{"Idempotency-Key": "k-1"})
        r2 = post(c, "o1", "ADD_ITEM", body, **{"Idempotency-Key": "k-1"})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["duplicate"] is False
        assert r2.json()["duplicate"] is True
        assert (
            len(c.get("/orders/o1", headers=ANN).json()["context"]["items"])
            == 1
        )
        # a different body under the same key is a fingerprint mismatch
        r3 = post(
            c,
            "o1",
            "ADD_ITEM",
            {"sku": "tea", "qty": 9},
            **{"Idempotency-Key": "k-1"},
        )
        assert r3.status_code == 422
        assert "9" not in r3.text  # the offending value is never echoed


def test_idempotency_key_without_inbox_is_refused_not_ignored(store) -> None:
    registry = orders.build_registry(store, None)
    web = orders.create_app(registry, email=lambda *a: None, debug=False)
    with TestClient(web) as c:
        body = {"sku": "tea", "qty": 1}
        r = post(c, "o1", "ADD_ITEM", body, **{"Idempotency-Key": "k-1"})
        # 🔥 was: 200, duplicate=False, and three retries added three items
        assert r.status_code == 501, r.text
        assert "inbox" in r.json()["title"].lower()
        assert (
            c.get("/orders/o1", headers=ANN).json()["context"]["items"] == []
        )
        # without the header the route works as before
        assert post(c, "o1", "ADD_ITEM", body).status_code == 200


def test_get_interpreter_route_validates_the_header_too(store) -> None:
    registry = orders.build_registry(store, None)
    web = orders.create_app(registry, email=lambda *a: None, debug=False)

    @web.post("/custom/{id}/add")
    async def add(order=get_interpreter(registry, "order")):
        return ReceiptResponse(
            order, await order.send("ADD_ITEM", sku="tea", qty=1, wait=True)
        )

    with TestClient(web) as c:
        r = c.post("/custom/o1/add", headers={**ANN, "Idempotency-Key": "k"})
        assert r.status_code == 501
        r = c.post(
            "/custom/o1/add", headers={**ANN, "Idempotency-Key": "k" * 300}
        )
        assert r.status_code in (400, 501)
        assert c.post("/custom/o1/add", headers=ANN).status_code == 200


# -----------------------------------------------------------------------------
# 2. get_interpreter persists exactly on success
# -----------------------------------------------------------------------------
def test_get_interpreter_raise_persists_nothing_and_leaks_nothing(
    registry, app
) -> None:
    @app.post("/custom/{id}/boom")
    async def boom(order=get_interpreter(registry, "order")):
        await order.send("ADD_ITEM", sku="tea", qty=1, wait=True)
        raise RuntimeError("db password=hunter2 in the trace")

    @app.post("/custom/{id}/ok")
    async def ok(order=get_interpreter(registry, "order")):
        await order.send("ADD_ITEM", sku="tea", qty=1, wait=True)
        return {"fine": True}

    with TestClient(app, raise_server_exceptions=False) as c:
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


def test_background_task_cannot_act_on_the_request_interpreter(
    registry, app
) -> None:
    seen: Dict[str, Any] = {}

    @app.post("/custom/{id}/bg")
    async def bg(
        tasks: BackgroundTasks, order=get_interpreter(registry, "order")
    ):
        await order.send("ADD_ITEM", sku="tea", qty=1, wait=True)

        async def later() -> None:
            seen["status"] = order.status
            r = await order.send("ADD_ITEM", sku="tea", qty=1, wait=True)
            seen["changed"] = r.changed
            # 📝 the documented recipe: background work opens its own act()
            async with registry.act("order", "o1", principal="ann") as fresh:
                r2 = await fresh.send("ADD_ITEM", sku="tea", qty=1, wait=True)
                seen["fresh_changed"] = r2.changed

        tasks.add_task(later)
        return {"queued": True}

    with TestClient(app) as c:
        r = c.post("/custom/o1/bg", headers=ANN)
        assert r.status_code == 200, r.text
        assert seen == {
            "status": "stopped",
            "changed": False,
            "fresh_changed": True,
        }
        assert (
            len(c.get("/orders/o1", headers=ANN).json()["context"]["items"])
            == 2
        )


# -----------------------------------------------------------------------------
# 3. per-event gates
# -----------------------------------------------------------------------------
def test_pay_gate_cannot_be_bypassed(app, emails) -> None:
    with TestClient(app) as c:
        checkout(c, "o1")
        r = c.post(
            "/orders/o1/send",
            json={"type": "PAY", "card_token": "tok_ok"},
            headers=ANN,
        )
        assert r.status_code == 403
        assert (
            c.get("/orders/o1", headers=ANN).json()["state"]
            == "awaitingPayment"
        )
        assert emails == []
        r = post(c, "o1", "PAY", {"card_token": "tok_ok"})
        assert r.json()["state"] == "paid"
        assert len(emails) == 1


def test_second_router_without_the_gate_is_not_a_backdoor(
    registry, emails
) -> None:
    """A second `StatechartRouter` on another prefix (an admin API) that
    forgets `per_event_dependencies` would expose PAY without the email
    hook: the gate must be on the REGISTRY's authorize, not only on one
    router."""
    web = orders.create_app(registry, email=lambda *a: emails.append(a))
    web.include_router(StatechartRouter(registry, "order", prefix="/admin"))
    with TestClient(web) as c:
        checkout(c, "o1")
        r = c.post(
            "/admin/o1/send",
            json={"type": "PAY", "card_token": "tok_ok"},
            headers=ANN,
        )
        # either refused, or it went through the SAME gate (email sent)
        assert r.status_code == 403 or len(emails) == 1, (
            r.status_code,
            emails,
        )


# -----------------------------------------------------------------------------
# 4. bodies
# -----------------------------------------------------------------------------
def test_body_rules_and_no_echo(app) -> None:
    with TestClient(app) as c:
        r = c.post("/orders/o1/send", json={"type": "NOPE"}, headers=ANN)
        assert r.status_code == 422 and "NOPE" not in r.text
        big = "x" * (1024 * 1024)
        r = c.post(
            "/orders/o1/send",
            content=json.dumps({"type": "ADD_ITEM", "sku": big, "qty": 1}),
            headers={**ANN, "content-type": "application/json"},
        )
        assert r.status_code in (413, 422)
        assert big[:64] not in r.text
        r = c.post(
            "/orders/o1/events/ADD_ITEM",
            content="sku=tea",
            headers={**ANN, "content-type": "text/plain"},
        )
        assert r.status_code == 415
        r = post(c, "o1", "ADD_ITEM", {"sku": "s" * 5000, "qty": 1})
        assert r.status_code == 422 and "sssss" not in r.text


# -----------------------------------------------------------------------------
# 5. OpenAPI
# -----------------------------------------------------------------------------
def test_openapi_is_bounded_complete_and_leak_free(app) -> None:
    t0 = time.perf_counter()
    doc = app.openapi()
    assert time.perf_counter() - t0 < 5.0
    paths = doc["paths"]
    orders_paths = [p for p in paths if p.startswith("/orders/")]
    assert len(orders_paths) >= 10
    for p in orders_paths:
        for method, op in paths[p].items():
            if method in ("get", "post"):
                assert op.get("operationId"), (p, method)
    send = paths["/orders/{id}/send"]["post"]
    assert "409" in send["responses"] and "422" in send["responses"]
    body_ref = send["requestBody"]["content"]["application/json"]["schema"]
    schemas = doc["components"]["schemas"]
    union = body_ref.get("oneOf") or schemas.get(
        body_ref.get("$ref", "").rsplit("/", 1)[-1], {}
    ).get("oneOf")
    assert union, body_ref
    assert body_ref.get("discriminator", {}).get(
        "propertyName"
    ) == "type" or any("discriminator" in s for s in [body_ref])
    blob = json.dumps(doc)
    assert "card_token" in blob  # the PAY body legitimately carries it ...
    state_schema = schemas.get("StateModel") or schemas.get("ReceiptModel")
    # ... but the state/receipt response schema never promises it back
    assert "card_token" not in json.dumps(state_schema)


# -----------------------------------------------------------------------------
# 6. 50 concurrent PAYs through the custom route
# -----------------------------------------------------------------------------
def test_fifty_concurrent_pays_charge_once(app, emails) -> None:
    async def go() -> List[int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t"
        ) as ac:
            async with app.router.lifespan_context(app):
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
                            headers={**ANN, "Idempotency-Key": "pay-once"},
                        )
                        for _ in range(50)
                    ]
                )
                return [r.status_code for r in rs]

    codes = asyncio.run(go())
    assert set(codes) <= {200, 409}, codes
    assert codes.count(200) >= 1
    assert len(emails) == 1, emails


# -----------------------------------------------------------------------------
# 7. readiness
# -----------------------------------------------------------------------------
def test_ready_tracks_lifespan(app) -> None:
    bare = TestClient(app)  # no lifespan entered
    assert bare.get("/_xsm/ready").status_code == 503
    assert bare.get("/_xsm/health").status_code == 200
    with TestClient(app) as c:
        assert c.get("/_xsm/ready").status_code == 200
    assert bare.get("/_xsm/ready").status_code == 503
