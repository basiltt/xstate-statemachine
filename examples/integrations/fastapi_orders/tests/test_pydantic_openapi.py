# examples/integrations/fastapi_orders/tests/test_pydantic_openapi.py
"""#266 battle (B): the typed boundary as the OUTSIDE world sees it --
the OpenAPI document and the error bodies of every route.

* **OpenAPI is self-contained**: every ``$ref`` in ``app.openapi()``
  resolves inside ``components.schemas``; each generated event route
  carries its `EventModel` as the request body; ``/send`` carries a
  ``oneOf`` with a ``discriminator.mapping`` naming every model.
* **no route echoes a value (X0.7)**: a hostile body to EVERY
  POST route -- generated, ``/send`` and the app-added ``PAY`` -- is a
  ``422`` whose errors carry only ``loc`` (strings) and ``type``; never
  ``input``, ``msg``, ``url`` or ``ctx``.
* **``type`` cannot re-route**: a body whose ``type`` names another
  event is ``422`` on the per-event route; on ``/send`` an unknown
  ``type`` is ``422``, never ``500``.
* **size and media type are checked before validation**: 1 MB to every
  POST route is ``413``; ``text/plain`` JSON is ``415``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterator, List

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

import app as orders  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from xstate_statemachine.persistence import (  # noqa: E402
    SQLiteInbox,
    SQLiteStore,
)

ANN = {"x-customer": "ann"}
FORBIDDEN_KEYS = {"input", "msg", "url", "ctx"}


@pytest.fixture
def client(tmp_path: Any) -> Iterator[Any]:
    store = SQLiteStore(str(tmp_path / "orders.db"))
    reg = orders.build_registry(store, SQLiteInbox(store))
    app = orders.create_app(reg, email=lambda *a: None, debug=False)
    with TestClient(app) as c:
        yield c


def _refs(node: Any, out: List[str]) -> List[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                out.append(v)
            _refs(v, out)
    elif isinstance(node, list):
        for v in node:
            _refs(v, out)
    return out


def _post_routes(doc: Dict[str, Any]) -> List[str]:
    return sorted(p for p, ops in doc["paths"].items() if "post" in ops)


def test_openapi_refs_all_resolve_and_event_bodies_are_typed(
    client: Any,
) -> None:
    doc = client.get("/openapi.json").json()
    assert doc["openapi"].startswith("3.")
    schemas = doc["components"]["schemas"]
    dangling = [
        r
        for r in _refs(doc, [])
        if not r.startswith("#/components/schemas/")
        or r.rsplit("/", 1)[-1] not in schemas
    ]
    assert dangling == []
    for model in orders.EVENT_MODELS:
        et = model.event_type()
        op = doc["paths"].get("/orders/{id}/events/" + et, {}).get("post")
        assert op is not None, et
        body = op.get("requestBody")
        if model.model_fields.keys() - {"type"}:
            assert body is not None, et
            assert model.__name__ in str(body), et
    send = doc["paths"]["/orders/{id}/send"]["post"]["requestBody"]
    schema = send["content"]["application/json"]["schema"]
    mapping = schema["discriminator"]["mapping"]
    assert set(mapping) == {m.event_type() for m in orders.EVENT_MODELS}
    assert all(v.startswith("#/components/schemas/") for v in mapping.values())


def _assert_safe_422(r: Any, secret: str) -> None:
    assert r.status_code == 422, (r.status_code, r.text)
    body = r.json()
    assert secret not in r.text
    for err in body["errors"]:
        assert not FORBIDDEN_KEYS & set(err), err
        assert all(isinstance(p, str) for p in err["loc"]), err


def test_every_post_route_hides_the_offending_value(client: Any) -> None:
    secret = "tok_s3cr3t_should_never_echo"
    doc = client.get("/openapi.json").json()
    routes = _post_routes(doc)
    assert any(r.endswith("/events/PAY") for r in routes)
    for path in routes:
        url = path.replace("{id}", "o1")
        bad = {"type": 12345, "card_token": [secret], "sku": [secret]}
        _assert_safe_422(client.post(url, json=bad, headers=ANN), secret)


def test_type_in_the_body_cannot_reroute_the_event(client: Any) -> None:
    r = client.post(
        "/orders/o2/events/ADD_ITEM",
        json={"type": "CANCEL", "sku": "tea", "qty": 1},
        headers=ANN,
    )
    _assert_safe_422(r, "never")
    assert {e["type"] for e in r.json()["errors"]} == {"literal_error"}
    r = client.post(
        "/orders/o2/send", json={"type": "DROP_TABLES"}, headers=ANN
    )
    _assert_safe_422(r, "DROP_TABLES")


def test_size_and_media_type_are_checked_before_validation(
    client: Any,
) -> None:
    doc = client.get("/openapi.json").json()
    big = b'{"sku": "' + b"x" * 1_100_000 + b'"}'
    for path in _post_routes(doc):
        url = path.replace("{id}", "o3")
        r = client.post(
            url,
            content=big,
            headers={**ANN, "content-type": "application/json"},
        )
        assert r.status_code == 413, (path, r.status_code)
        r = client.post(
            url,
            content=b'{"sku": "tea", "qty": 1}',
            headers={**ANN, "content-type": "text/plain"},
        )
        assert r.status_code == 415, (path, r.status_code, r.text[:200])
