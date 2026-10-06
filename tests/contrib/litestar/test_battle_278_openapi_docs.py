"""#278 battle (adversary B): Litestar's OpenAPI / body-schema surface.

Pinned:

* **golden** -- the AdvancePayment corpus controller's SERVED document
  (``GET /schema/openapi.json``) equals ``openapi_golden.json`` after
  normalisation. Regenerate with
  ``XSM_UPDATE_GOLDEN=1 pytest tests/contrib/litestar -k golden``;
* the served document is deterministic (Litestar generated random
  msgspec examples for ``Problem`` on every start) and valid;
* operationIds are unique and stable, the same rule as ``[fastapi]``
  (``ORDER.PAID`` + ``ORDER_PAID`` + ``get`` answered 500 on /schema);
* aliased model fields round-trip (they were a 422 on a valid body);
* 200 responses are typed and never promise context fields;
* both body backends (msgspec Struct, pydantic RootModel union) validate
  and produce value-free, capped 422 problems;
* fallback body component names are distinct per machine.
"""

from __future__ import annotations

import collections
import json
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.persistence import MemoryStore

from ..conftest import requires_extra
from ..starlette._support import payment_machine

pytestmark = requires_extra("litestar")
pytest.importorskip("litestar")
pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from litestar import Litestar  # noqa: E402
from litestar.testing import TestClient  # noqa: E402
from pydantic import Field  # noqa: E402

from src.xstate_statemachine.contrib.litestar import (  # noqa: E402
    StatechartRegistry,
    XStatePlugin,
    allow_all,
    create_statechart_controller,
)
from src.xstate_statemachine.contrib.litestar.controller import (  # noqa: E402
    MAX_VALIDATION_ERRORS,
)
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    EventModel,
    events_union,
)

GOLDEN = Path(__file__).with_name("openapi_golden.json")


def _app(machine: Any, name: str = "o", plugin: bool = True, **kw: Any):
    reg = StatechartRegistry(MemoryStore())
    reg.register(name, machine, authorize=allow_all)
    return Litestar(
        [create_statechart_controller(reg, name, **kw)],
        plugins=[XStatePlugin(reg)] if plugin else [],
        lifespan=[] if plugin else [reg.lifespan],
        logging_config=None,
    )


def _served(app: Any) -> Dict[str, Any]:
    """The document as a client fetches it (not `app.openapi_schema`)."""
    with TestClient(app) as c:
        r = c.get("/schema/openapi.json")
        assert r.status_code == 200, r.text[:300]
        return r.json()


def _chart(events: Any, **kw: Any) -> Any:
    cfg = {
        "id": "o",
        "initial": "a",
        "states": {"a": {"on": {e: "a" for e in events}}},
    }
    return create_machine(cfg, **kw)


def assert_valid(doc: Dict[str, Any]) -> None:
    ops = [
        op["operationId"]
        for path in doc["paths"].values()
        for op in path.values()
        if isinstance(op, dict) and "operationId" in op
    ]
    dups = [k for k, v in collections.Counter(ops).items() if v > 1]
    assert not dups, dups
    assert all(re.fullmatch(r"[A-Za-z0-9_]+", o) for o in ops), ops
    refs = set(re.findall(r'"#/components/schemas/([^"]+)"', json.dumps(doc)))
    assert refs <= set(doc.get("components", {}).get("schemas", {}))
    try:
        from openapi_spec_validator import validate
    except ImportError:  # pragma: no cover -- structural check above
        return
    validate(doc)


def normalise(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Drop what varies with Litestar / Python versions, not with us."""
    out = json.loads(json.dumps(doc, sort_keys=True))
    for k in ("openapi", "info", "servers"):
        out.pop(k, None)
    for path in out.get("paths", {}).values():
        for op in path.values():
            if isinstance(op, dict):
                for resp in op.get("responses", {}).values():
                    if isinstance(resp, dict):
                        resp.pop("description", None)
    return out


# -----------------------------------------------------------------------------
# 🥇 Golden + determinism
# -----------------------------------------------------------------------------
def test_openapi_golden_advance_payment() -> None:
    raw = _served(_app(payment_machine(), "payment", tags=["payment"]))
    assert_valid(raw)
    doc = normalise(raw)
    text = json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False)
    if os.environ.get("XSM_UPDATE_GOLDEN") == "1":
        GOLDEN.write_text(text + "\n", encoding="utf-8")
    golden = json.loads(GOLDEN.read_text("utf-8"))
    assert doc == golden, (
        "OpenAPI drifted from the golden; if intended, rerun with "
        "XSM_UPDATE_GOLDEN=1 and review the diff"
    )


@pytest.mark.parametrize("events", [["X", "Y"], []])
def test_served_document_is_deterministic(events: List[str]) -> None:
    a = json.dumps(_served(_app(_chart(events))), sort_keys=True)
    b = json.dumps(_served(_app(_chart(events))), sort_keys=True)
    assert a == b


def test_problem_examples_are_pinned_per_status() -> None:
    doc = _served(_app(payment_machine(), "p"))
    problem = doc["components"]["schemas"]["Problem"]
    assert "examples" not in json.dumps(problem)
    resp = doc["paths"]["/p/{id}/send"]["post"]["responses"]["409"]
    examples = resp["content"]["application/problem+json"]["examples"]
    (body,) = examples.values()
    assert body["value"]["status"] == 409


# -----------------------------------------------------------------------------
# 🆔 operationIds
# -----------------------------------------------------------------------------
def test_colliding_event_names_get_unique_stable_ids() -> None:
    names = ["ORDER.PAID", "ORDER_PAID", "get", "send", "éclair"]
    doc = _served(_app(_chart(names)))
    assert_valid(doc)
    ids = {
        p.rsplit("/", 1)[1]: op["post"]["operationId"]
        for p, op in doc["paths"].items()
        if "/events/" in p
    }
    assert ids["ORDER_PAID"] == "o_order_paid"
    assert ids["ORDER.PAID"] == "o_order_paid_2"
    assert ids["get"] == "o_get_2" and ids["send"] == "o_send_2"
    assert ids["éclair"] == "o_eclair"
    assert doc["paths"]["/o/{id}"]["get"]["operationId"] == "o_get"


def test_routers_share_one_operation_id_rule() -> None:
    pytest.importorskip("fastapi")  # the [litestar] CI cell has no fastapi
    from src.xstate_statemachine.contrib import _openapi
    from src.xstate_statemachine.contrib.fastapi import router

    assert router._operation_ids is _openapi.operation_ids


def test_every_colliding_event_route_is_reachable() -> None:
    with TestClient(_app(_chart(["ORDER.PAID", "ORDER_PAID"]))) as c:
        for e in ("ORDER.PAID", "ORDER_PAID"):
            assert c.post(f"/o/k/events/{e}").status_code == 200


# -----------------------------------------------------------------------------
# 🧾 Bodies: pydantic union / msgspec fallback
# -----------------------------------------------------------------------------
class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    amount: Decimal
    note: Optional[str] = None
    ref: int = Field(1, alias="x-ref")
    items: List[int] = []


class Refund(EventModel):
    type: Literal["REFUND"] = "REFUND"


def _pay_machine(*models: Any, seen: Optional[Dict] = None) -> Any:
    def keep(i, ctx, e, a):
        if seen is not None:
            seen.update(e.payload)

    cfg = {
        "id": "o",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"on": {"PAY": {"target": "b", "actions": "keep"}}},
            "b": {"on": {"REFUND": "a"}},
        },
    }
    return create_machine(
        cfg,
        logic=MachineLogic(actions={"keep": keep}),
        event_schemas=events_union(*models),
    )


@pytest.mark.parametrize("path", ["/o/k/send", "/o/k/events/PAY"])
def test_aliased_field_is_accepted(path: str) -> None:
    seen: Dict[str, Any] = {}
    body: Dict[str, Any] = {"amount": "1.5", "x-ref": 3}
    if path.endswith("send"):
        body["type"] = "PAY"
    with TestClient(_app(_pay_machine(Pay, Refund, seen=seen))) as c:
        r = c.post(path, json=body)
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "b"
    assert seen["x-ref"] == 3 and seen["amount"] == Decimal("1.5")


def test_union_shapes_one_and_many_models() -> None:
    def body_schema(doc: Dict[str, Any]) -> Dict[str, Any]:
        rb = doc["paths"]["/o/{id}/send"]["post"]["requestBody"]
        return rb["content"]["application/json"]["schema"]

    one = body_schema(_served(_app(_pay_machine(Pay))))
    assert one == {"$ref": "#/components/schemas/Pay"}
    many = body_schema(_served(_app(_pay_machine(Pay, Refund))))
    assert many["discriminator"] == {"propertyName": "type"}
    assert len(many["oneOf"]) == 2


@pytest.mark.parametrize("plugin", [True, False])
def test_pydantic_backend_validates_with_and_without_plugin(
    plugin: bool,
) -> None:
    """Litestar auto-registers its PydanticPlugin, so the RootModel body
    VALIDATES without `XStatePlugin`; only the document's shape (``root``
    wrapper) needs our plugin -- see the Troubleshooting table."""
    with TestClient(_app(_pay_machine(Pay, Refund), plugin=plugin)) as c:
        ok = c.post("/o/k/send", json={"type": "PAY", "amount": "2"})
        bad = c.post("/o/k/send", json={"type": "PAY", "amount": "s3cr3t"})
    assert ok.status_code == 200, ok.text
    assert bad.status_code == 422 and "s3cr3t" not in bad.text
    assert bad.json()["errors"][0]["key"].endswith("amount")


def test_msgspec_backend_unknown_key_is_named_value_free() -> None:
    with TestClient(_app(_chart(["X"]))) as c:
        r = c.post("/o/k/send", json={"type": "X", "sneaky": "s3cr3t"})
        bad_t = c.post("/o/k/send", json={"type": "Z"})
        ok = c.post("/o/k/send", json={"type": "X"})
    assert r.status_code == 422 and "s3cr3t" not in r.text
    assert r.json()["errors"] == [{"key": "sneaky", "source": "body"}]
    assert bad_t.status_code == 422
    assert bad_t.json()["errors"][0]["key"] == "type"
    assert ok.status_code == 200


def test_validation_errors_are_capped() -> None:
    body = {"type": "PAY", "amount": "1", "items": ["x"] * 10_000}
    with TestClient(_app(_pay_machine(Pay, Refund))) as c:
        r = c.post("/o/k/send", json=body)
    assert r.status_code == 422
    got = r.json()
    assert len(got["errors"]) == MAX_VALIDATION_ERRORS
    assert got["errors_total"] == 10_000
    assert len(r.content) < 10_000


def test_fallback_body_names_are_distinct() -> None:
    reg = StatechartRegistry(MemoryStore())
    reg.register("a_b", _chart(["X"]), authorize=allow_all)
    reg.register("aB", _chart(["Y"]), authorize=allow_all)
    app = Litestar(
        [create_statechart_controller(reg, n) for n in ("a_b", "aB")],
        plugins=[XStatePlugin(reg)],
        logging_config=None,
    )
    schemas = _served(app)["components"]["schemas"]
    assert schemas["A_bEvent"]["properties"]["type"]["const"] == "X"
    assert schemas["ABEvent"]["properties"]["type"]["const"] == "Y"


# -----------------------------------------------------------------------------
# 📤 Responses
# -----------------------------------------------------------------------------
def test_200_responses_are_typed_and_hide_context_fields() -> None:
    doc = _served(_app(payment_machine(), "p"))
    paths = doc["paths"]

    def ref(path: str, method: str) -> str:
        ok = paths[path][method]["responses"]["200"]
        return ok["content"]["application/json"]["schema"]["$ref"]

    assert ref("/p/{id}", "get").endswith("/StateBody")
    assert ref("/p/{id}/send", "post").endswith("/ReceiptBody")
    assert ref("/p/{id}/events", "get").endswith("/EventsBody")
    state = doc["components"]["schemas"]["StateBody"]["properties"]
    assert set(state) == {
        "state",
        "state_ids",
        "available_events",
        "machine_version",
        "context",
    }


def test_every_returnable_status_is_documented() -> None:
    doc = _served(_app(payment_machine(), "p"))
    send = doc["paths"]["/p/{id}/send"]["post"]["responses"]
    want = {"200", "400", "401", "403", "404", "409", "413", "415", "422"}
    assert want <= set(send)
