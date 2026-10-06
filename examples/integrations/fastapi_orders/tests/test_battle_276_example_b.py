"""#276 battle (adversary B): the example's claims, end to end.

* the README ``curl`` walkthrough produces exactly the states it claims;
* the PAY gate lives on ``authorize`` -- a WebSocket client sending
  ``PAY`` is closed with 1008, nothing is charged, no email is sent;
* the static page's identity (the ``customer`` cookie) authorises the
  SSE stream, which is the route the page opens;
* every route ``loadtest.py`` and ``static/index.html`` call exists in
  the OpenAPI document;
* ``public_context`` never contains ``card_token``; ``charge_id`` IS
  public by design (the processor's reference the customer quotes to
  support -- not a credential).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, List

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

import app as orders  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    SQLiteInbox,
    SQLiteStore,
)

pytestmark = pytest.mark.timeout(120)
HERE = Path(__file__).resolve().parents[1]
ANN = {"x-customer": "ann"}


@pytest.fixture
def emails() -> List[Any]:
    return []


@pytest.fixture
def client(tmp_path, emails):
    store = SQLiteStore(str(tmp_path / "o.db"))
    reg = orders.build_registry(store, SQLiteInbox(store))
    app = orders.create_app(reg, email=lambda *a: emails.append(a))
    with TestClient(app) as c:
        yield c


def _post(c: Any, path: str, body: Any = None, **h: str) -> Any:
    return c.post(f"/orders/o1{path}", json=body, headers={**ANN, **h})


def _checkout(c: Any) -> None:
    assert _post(c, "/events/ADD_ITEM", {"sku": "tea", "qty": 2}).is_success
    assert _post(c, "/events/CHECKOUT").json()["state"] == "awaitingPayment"


def test_readme_walkthrough(client, emails) -> None:
    c = client
    _checkout(c)
    key = {"Idempotency-Key": "pay-o1-1"}
    first = _post(c, "/events/PAY", {"card_token": "tok_ok"}, **key).json()
    again = _post(c, "/events/PAY", {"card_token": "tok_ok"}, **key).json()
    assert first["state"] == "paid" and again["duplicate"] is True
    nokey = _post(c, "/events/PAY", {"card_token": "tok_ok"}).json()
    assert nokey["changed"] is False
    got = c.get("/orders/o1", headers=ANN).json()
    assert got["available_events"] == ["FULFIL"]
    assert _post(c, "/send", {"type": "FULFIL"}).status_code == 200
    _post(c, "/events/PACKED")
    assert _post(c, "/events/LABEL_PRINTED").json()["state"] == "shipped"
    assert len(emails) == 1


def test_websocket_pay_is_refused_1008(client, emails) -> None:
    _checkout(client)
    with client.websocket_connect("/orders/o1/ws", headers=ANN) as ws:
        assert ws.receive_json()["kind"] == "snapshot"
        ws.send_json({"type": "PAY", "payload": {"card_token": "tok_ok"}})
        with pytest.raises(WebSocketDisconnect) as info:
            ws.receive_json()
    assert info.value.code == 1008
    state = client.get("/orders/o1", headers=ANN).json()["state"]
    assert state == "awaitingPayment"
    assert emails == []


def test_websocket_non_gated_event_works(client) -> None:
    with client.websocket_connect("/orders/o2/ws", headers=ANN) as ws:
        assert ws.receive_json()["kind"] == "snapshot"
        ws.send_json({"type": "ADD_ITEM", "payload": {"sku": "tea", "qty": 1}})
        kinds = sorted(ws.receive_json()["kind"] for _ in range(2))
    assert kinds == ["receipt", "transition"]


def test_static_page_identity_cookie_authorises_its_routes(client) -> None:
    html = (HERE / "static" / "index.html").read_text("utf-8")
    assert '"customer="' in html and "/stream" in html
    assert orders.CUSTOMER_COOKIE == "customer"
    client.cookies.set("customer", "ann")
    try:
        assert client.get("/orders/o1").status_code == 200
        assert client.get("/").status_code == 200
    finally:
        client.cookies.clear()
    assert client.get("/orders/o1").status_code == 403


def test_page_and_loadtest_routes_exist_in_openapi(client) -> None:
    paths = set(client.get("/openapi.json").json()["paths"])
    load = (HERE / "loadtest.py").read_text("utf-8")
    page = (HERE / "static" / "index.html").read_text("utf-8")
    # loadtest: prepare (ADD_ITEM, CHECKOUT), fire (PAY), final GET.
    for ev in ("ADD_ITEM", "CHECKOUT"):
        assert f'"{ev}"' in load
        assert f"/orders/{{id}}/events/{ev}" in paths
    assert 'f"/orders/{order}/events/PAY"' in load
    assert "/orders/{id}/events/PAY" in paths
    assert 'f"/orders/{order}"' in load and "/orders/{id}" in paths
    assert '"/stream"' in page and "/orders/{id}/stream" in paths


def test_public_context_hides_the_card_token(client) -> None:
    _checkout(client)
    r = _post(client, "/events/PAY", {"card_token": "tok_ok"})
    body = r.text + client.get("/orders/o1", headers=ANN).text
    assert "tok_ok" not in body and "card_token" not in body
    assert r.json()["context"]["charge_id"].startswith("ch_")
