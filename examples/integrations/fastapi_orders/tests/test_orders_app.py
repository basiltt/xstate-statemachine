# examples/integrations/fastapi_orders/tests/test_orders_app.py
"""Battle tests for the order service: the web layer under the chart.

Plain pytest + `TestClient` / `httpx.ASGITransport` (the `[testing]`
fixtures arrive with #268). Every store is a fresh SQLite file under
``tmp_path``; timers are driven by `DueTimerScanner.scan(now)`.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple

import pytest

pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

import app as orders  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    SQLiteInbox,
    SQLiteStore,
)

ANN = {"x-customer": "ann"}
Email = Tuple[str, Optional[str], str]


# -----------------------------------------------------------------------------
# 🧰 Helpers
# -----------------------------------------------------------------------------
@pytest.fixture
def registry(tmp_path):
    store = SQLiteStore(str(tmp_path / "orders.db"))
    return orders.build_registry(store, SQLiteInbox(store))


@pytest.fixture
def emails() -> List[Email]:
    return []


@pytest.fixture
def app(registry, emails):
    return orders.create_app(
        registry, email=lambda *a: emails.append(a), debug=False
    )


def post(client, order: str, event: str, body=None, headers=None):
    return client.post(
        f"/orders/{order}/events/{event}",
        json=body,
        headers={**ANN, **(headers or {})},
    )


def checkout(client, order: str) -> None:
    assert post(client, order, "ADD_ITEM", {"sku": "tea", "qty": 2}).is_success
    r = post(client, order, "CHECKOUT")
    assert r.json()["state"] == "awaitingPayment"


def state(client, order: str) -> Dict[str, Any]:
    return client.get(f"/orders/{order}", headers=ANN).json()


# -----------------------------------------------------------------------------
# ✅ Happy path
# -----------------------------------------------------------------------------
def test_happy_path_cart_to_shipped(app, emails):
    with TestClient(app) as c:
        checkout(c, "o1")
        r = post(c, "o1", "PAY", {"card_token": "tok_ok"})
        body = r.json()
        assert r.status_code == 200 and body["state"] == "paid"
        assert body["context"]["total_cents"] == 900
        assert "card_token" not in body["context"]  # X0.1
        r = post(c, "o1", "FULFIL")
        assert r.json()["state"] == {
            "fulfilment": {"packing": "inProgress", "labelling": "inProgress"}
        }
        post(c, "o1", "PACKED")
        assert post(c, "o1", "LABEL_PRINTED").json()["state"] == "shipped"
    assert emails == [("o1", body["context"]["charge_id"], "ann")]


def test_validation_and_auth(app):
    with TestClient(app) as c:
        bad = post(c, "o1", "ADD_ITEM", {"sku": "tea", "qty": 0})
        assert bad.status_code == 422
        assert c.get("/orders/o1").status_code == 403  # no customer
        # an empty cart cannot check out (guard → 409 denied)
        assert post(c, "o2", "CHECKOUT").status_code == 409
        # PAY cannot bypass the email hook through /send
        r = c.post(
            "/orders/o1/send",
            json={"type": "PAY", "card_token": "x"},
            headers=ANN,
        )
        assert r.status_code == 403


# -----------------------------------------------------------------------------
# 🔁 Payment failure → RetryPolicy → onError path
# -----------------------------------------------------------------------------
def test_flaky_card_retries_then_pays(app, registry, emails):
    scanner = orders.build_scanner(registry)
    with TestClient(app) as c:
        checkout(c, "o1")
        r = post(c, "o1", "PAY", {"card_token": "tok_flaky"})
        assert r.json()["state"] == "retrying"
        assert r.json()["context"]["attempt"] == 1
        assert emails == []  # not paid: no email
        assert scanner.scan(time.time() + 60).woken == 1
        after = state(c, "o1")
        assert after["state"] == "paid"
        assert after["context"]["attempt"] == 0  # retryReset


def test_declined_card_exhausts_retries(app, registry):
    scanner = orders.build_scanner(registry)
    with TestClient(app) as c:
        checkout(c, "o1")
        assert post(c, "o1", "PAY", {"card_token": "tok_declined"}).is_success
        now = time.time()
        for _ in range(3):
            now += 3600
            scanner.scan(now)
        after = state(c, "o1")
        assert after["state"] == "paymentFailed"
        assert after["context"]["attempt"] == 3
        # another card works from paymentFailed
        r = post(c, "o1", "PAY", {"card_token": "tok_ok"})
        assert r.json()["state"] == "paid"


# -----------------------------------------------------------------------------
# ⏰ `after` payment timeout via the scanner
# -----------------------------------------------------------------------------
def test_unpaid_order_expires(app, registry):
    scanner = orders.build_scanner(registry)
    with TestClient(app) as c:
        checkout(c, "o1")
        assert scanner.scan(time.time() + 60).woken == 0  # not yet
        assert scanner.scan(time.time() + 901).woken == 1
        assert state(c, "o1")["state"] == "expired"
        assert post(c, "o1", "PAY", {"card_token": "tok_ok"}).json()[
            "changed"
        ] is False


# -----------------------------------------------------------------------------
# 🔑 Idempotency-Key
# -----------------------------------------------------------------------------
def test_idempotency_key_duplicate(app, emails):
    with TestClient(app) as c:
        checkout(c, "o1")
        key = {"Idempotency-Key": "pay-1"}
        first = post(c, "o1", "PAY", {"card_token": "tok_ok"}, key)
        again = post(c, "o1", "PAY", {"card_token": "tok_ok"}, key)
        assert first.json()["duplicate"] is False
        assert again.status_code == 200 and again.json()["duplicate"] is True
        assert again.json()["context"] == first.json()["context"]
        # same key, different body: refused (fingerprint mismatch)
        other = post(c, "o1", "PAY", {"card_token": "tok_other"}, key)
        assert other.status_code == 422
    assert len(emails) == 1


# -----------------------------------------------------------------------------
# ⚡ 200 concurrent PAYs, in-process
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("idem", [None, "pay-all"])
def test_two_hundred_concurrent_pays_one_winner(app, emails, idem):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t", timeout=60
        ) as client:
            await client.post(
                "/orders/hot/events/ADD_ITEM",
                json={"sku": "tea", "qty": 1},
                headers=ANN,
            )
            await client.post("/orders/hot/events/CHECKOUT", headers=ANN)
            headers = dict(ANN)
            if idem:
                headers["Idempotency-Key"] = idem

            async def one():
                return await client.post(
                    "/orders/hot/events/PAY",
                    json={"card_token": "tok_ok"},
                    headers=headers,
                )

            return await asyncio.wait_for(
                asyncio.gather(*(one() for _ in range(200))), 120
            )

    results = asyncio.run(go())
    changed = [
        r
        for r in results
        if r.status_code == 200
        and r.json()["changed"]
        and not r.json()["duplicate"]
    ]
    assert len(changed) == 1
    assert {r.status_code for r in results} <= {200, 409}
    assert len(emails) == 1


# -----------------------------------------------------------------------------
# 📡 SSE: one `transition` per committed change
# -----------------------------------------------------------------------------
class _SSE:
    """Minimal raw-ASGI GET stream driver on the current loop."""

    def __init__(self, app, path: str) -> None:
        self.app, self.path = app, path
        self.out: "asyncio.Queue[Dict[str, Any]]" = asyncio.Queue()
        self.gone = asyncio.Event()
        self.sent = False
        self.buf = b""

    async def _receive(self):
        if not self.sent:
            self.sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await self.gone.wait()
        return {"type": "http.disconnect"}

    async def open(self) -> int:
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": self.path,
            "raw_path": self.path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"t"), (b"x-customer", b"ann")],
            "client": ("127.0.0.1", 1),
            "server": ("t", 80),
        }
        self.task = asyncio.ensure_future(
            self.app(scope, self._receive, self.out.put)
        )
        start = await asyncio.wait_for(self.out.get(), 5)
        return start["status"]

    async def next(self) -> Tuple[str, Any]:
        while b"\n\n" not in self.buf:
            msg = await asyncio.wait_for(self.out.get(), 5)
            self.buf += msg.get("body", b"")
        raw, self.buf = self.buf.split(b"\n\n", 1)
        fields = dict(
            line.split(": ", 1)
            for line in raw.decode().splitlines()
            if not line.startswith(":")
        )
        return fields.get("event", ""), json.loads(fields["data"])

    async def close(self) -> None:
        self.gone.set()
        await asyncio.wait_for(self.task, 5)


def test_sse_transition_per_change(app):
    async def go():
        sse = _SSE(app, "/orders/s1/stream")
        assert await sse.open() == 200
        kind, snap = await sse.next()
        assert kind == "snapshot" and snap["state"] == "cart"
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://t", timeout=10
        ) as client:
            for event, body in (
                ("ADD_ITEM", {"sku": "mug", "qty": 1}),
                ("PAY", {"card_token": "tok_ok"}),  # not handled in cart
                ("CHECKOUT", None),
            ):
                await client.post(
                    f"/orders/s1/events/{event}", json=body, headers=ANN
                )
        got = [await sse.next() for _ in range(2)]
        assert [k for k, _ in got] == ["transition", "transition"]
        assert [d["state"] for _, d in got] == ["cart", "awaitingPayment"]
        assert sse.out.empty()
        await sse.close()

    asyncio.run(go())


# -----------------------------------------------------------------------------
# 🧩 Wiring
# -----------------------------------------------------------------------------
def test_probes_index_and_openapi(app):
    with TestClient(app) as c:
        assert c.get("/_xsm/health").status_code == 200
        assert c.get("/_xsm/ready").status_code == 200
        assert "EventSource" in c.get("/").text
        doc = app.openapi()
        send = doc["paths"]["/orders/{id}/send"]["post"]
        schema = send["requestBody"]["content"]["application/json"]["schema"]
        assert schema["discriminator"]["propertyName"] == "type"
        assert "/orders/{id}/events/PAY" in doc["paths"]


def test_inspector_only_in_debug(registry):
    routes = orders.create_app(registry, debug=True).router.routes
    paths = {getattr(r, "path", None) for r in routes}
    assert "/_xsm/inspect" in paths


def test_machine_parity_with_stub_logic():
    """The chart builds with `stub_logic` -- what `xsm simulate` runs."""
    from xstate_statemachine import SyncInterpreter, create_machine
    from xstate_statemachine.testing_utils import stub_logic

    cfg = json.loads((orders.HERE / "machine.json").read_text("utf-8"))
    m = create_machine(cfg, logic=stub_logic(cfg))
    i = SyncInterpreter(m).start()
    for e in ("ADD_ITEM", "CHECKOUT", "PAY"):
        i.send(e)
    assert "order.paid" in i.current_state_ids
    i.stop()
