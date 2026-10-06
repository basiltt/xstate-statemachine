"""#276 battle (adversary B): the OpenAPI / schema surface.

Pinned:

* **golden** -- the AdvancePayment corpus router's OpenAPI document is
  compared, normalised, to ``openapi_golden.json``. Regenerate with
  ``XSM_UPDATE_GOLDEN=1 pytest tests/contrib/fastapi -k golden``;
* every generated document is structurally valid (unique operationIds,
  every ``$ref`` resolves) for 0 / 1 / 50 events and for event names that
  are not identifiers (``ORDER.PAID`` vs ``ORDER_PAID``, ``GET``,
  ``éclair``) -- duplicate operationIds were emitted;
* an aliased model field round-trips through ``/send``, ``/events/X``
  and ``interp.send(Model(...))`` -- it was a 422 on a valid body;
* two machines whose names differ only in ``_`` get distinct, stable
  fallback body schema names (not ``module__ABEvent__1``);
* every status the router can return is documented as a problem;
* ``GET /{id}/events`` runs guards (documented: guards must be pure) and
  ``/diagram.mmd`` honours ``authorize``.
"""

from __future__ import annotations

import collections
import json
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Literal, Optional

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.persistence import MemoryStore

from ..conftest import requires_extra
from ..starlette._support import payment_machine

pytestmark = requires_extra("fastapi")
pytest.importorskip("fastapi")
pytest.importorskip("pydantic")
pytest.importorskip("httpx")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import Field  # noqa: E402

from src.xstate_statemachine.contrib.fastapi import (  # noqa: E402
    StatechartRegistry,
    StatechartRouter,
    allow_all,
    instrument_app,
)
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    EventModel,
    events_union,
)

GOLDEN = Path(__file__).with_name("openapi_golden.json")


def _app(machine: Any, name: str = "o", authorize: Any = allow_all, **kw):
    reg = StatechartRegistry(MemoryStore())
    reg.register(name, machine, authorize=authorize)
    app = FastAPI()
    app.include_router(StatechartRouter(reg, name, **kw))
    return instrument_app(app, reg)


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
    """Drop what varies with FastAPI/pydantic versions, not with us."""
    out = json.loads(json.dumps(doc, sort_keys=True))
    out.pop("openapi", None)
    out.pop("info", None)
    # 📝 FastAPI's own `ValidationError` grows fields across releases
    #    (`input`, `ctx` in 0.11x); its shape is not ours to pin.
    out.get("components", {}).get("schemas", {}).pop("ValidationError", None)
    return out


# -----------------------------------------------------------------------------
# 🥇 Golden
# -----------------------------------------------------------------------------
def test_openapi_golden_advance_payment() -> None:
    raw = _app(payment_machine(), "payment", tags=["payment"]).openapi()
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


def test_openapi_is_deterministic() -> None:
    a = json.dumps(_app(payment_machine(), "p").openapi(), sort_keys=True)
    b = json.dumps(_app(payment_machine(), "p").openapi(), sort_keys=True)
    assert a == b


# -----------------------------------------------------------------------------
# 🆔 operationIds
# -----------------------------------------------------------------------------
def test_zero_events_document_is_valid() -> None:
    assert_valid(_app(_chart([])).openapi())


def test_non_identifier_event_names_get_unique_operation_ids() -> None:
    events = ["ORDER.PAID", "ORDER_PAID", "pay-now", "éclair", "1ST"]
    events += ["GET", "send", "Events"]  # collide with the fixed routes
    doc = _app(_chart(events)).openapi()
    assert_valid(doc)
    ids = {
        p.rsplit("/", 1)[1]: v["post"]["operationId"]
        for p, v in doc["paths"].items()
        if "/events/" in p
    }
    assert ids["ORDER.PAID"] == "o_order_paid"
    assert ids["ORDER_PAID"] == "o_order_paid_2"
    assert ids["éclair"] == "o_eclair"
    assert ids["GET"] == "o_get_2"


def test_fallback_body_names_are_distinct_and_clean() -> None:
    reg = StatechartRegistry(MemoryStore())
    app = FastAPI()
    for name in ("a_b", "aB"):
        reg.register(
            name, _chart(["X"]), authorize=allow_all
        )  # same chart, two names
        app.include_router(StatechartRouter(reg, name))
    schemas = app.openapi()["components"]["schemas"]
    assert {"A_bEvent", "ABEvent"} <= set(schemas)
    assert not [k for k in schemas if "__" in k]


# -----------------------------------------------------------------------------
# 🧾 Models: aliases, Decimal, Optional, 50 models
# -----------------------------------------------------------------------------
class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    amount: Decimal
    note: Optional[str] = None
    ref: int = Field(1, alias="x-ref")


class Refund(EventModel):
    type: Literal["REFUND"] = "REFUND"


def _pay_app(*models: Any) -> Any:
    cfg = {
        "id": "o",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"on": {"PAY": {"target": "b", "actions": "keep"}}},
            "b": {"on": {"REFUND": "a"}},
        },
    }

    def keep(i, ctx, e, a):
        ctx["ref"] = e.payload.get("x-ref")

    m = create_machine(
        cfg,
        logic=MachineLogic(actions={"keep": keep}),
        event_schemas=events_union(*models),
    )
    return _app(m)


@pytest.mark.parametrize("path", ["/o/k/send", "/o/k/events/PAY"])
def test_aliased_field_is_accepted(path: str) -> None:
    body: Dict[str, Any] = {"amount": "1.5", "x-ref": 3}
    if path.endswith("send"):
        body["type"] = "PAY"
    with TestClient(_pay_app(Pay, Refund)) as c:
        r = c.post(path, json=body)
        assert r.status_code == 200, r.text
        assert r.json()["state"] == "b"


def test_event_model_instance_with_alias_sends() -> None:
    from src.xstate_statemachine import SyncInterpreter

    m = create_machine(
        {
            "id": "o",
            "initial": "a",
            "states": {"a": {"on": {"PAY": "b"}}, "b": {}},
        },
        event_schemas=events_union(Pay),
    )
    i = SyncInterpreter(m).start()
    i.send(Pay(amount=Decimal("2"), **{"x-ref": 4}))
    assert i.current_state_ids == {"o.b"}


def test_one_model_body_has_no_union() -> None:
    doc = _pay_app(Pay).openapi()
    assert_valid(doc)
    schema = doc["paths"]["/o/{id}/send"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert schema == {"$ref": "#/components/schemas/Pay"}


def test_fifty_models_union() -> None:
    models = [
        type(
            f"E{n}",
            (EventModel,),
            {"__annotations__": {"type": Literal[f"E{n}"], "n": int}},
        )
        for n in range(50)
    ]
    for n, m in enumerate(models):
        m.model_fields["type"].default = f"E{n}"
        m.model_rebuild(force=True)
    doc = _app(
        _chart(
            [f"E{n}" for n in range(50)], event_schemas=events_union(*models)
        )
    ).openapi()
    assert_valid(doc)
    body = doc["paths"]["/o/{id}/send"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    assert len(body["oneOf"]) == 50
    assert body["discriminator"]["propertyName"] == "type"


# -----------------------------------------------------------------------------
# 📜 Documented statuses
# -----------------------------------------------------------------------------
def test_every_returnable_status_is_documented() -> None:
    paths = _app(_chart(["GO"])).openapi()["paths"]
    send = paths["/o/{id}/send"]["post"]["responses"]
    for s in ("400", "401", "403", "404", "409", "413", "415", "422"):
        assert s in send, s
    for s in ("500", "501", "503"):
        assert s in send, s
    get = paths["/o/{id}"]["get"]["responses"]
    for s in ("400", "401", "403", "404", "503"):
        assert s in get, s
    assert "401" in paths["/o/{id}/diagram.mmd"]["get"]["responses"]
    for s in ("401", "403", "429", "503"):
        assert s in paths["/o/{id}/stream"]["get"]["responses"], s
    problem = send["409"]["content"]["application/problem+json"]["schema"]
    assert problem == {"$ref": "#/components/schemas/Problem"}


def test_state_model_does_not_promise_context_fields() -> None:
    schemas = _app(_chart(["GO"])).openapi()["components"]["schemas"]
    ctx = schemas["StateModel"]["properties"]["context"]
    assert "properties" not in json.dumps(ctx)


# -----------------------------------------------------------------------------
# 🔎 /events and /diagram.mmd
# -----------------------------------------------------------------------------
def test_events_route_runs_guards_and_hides_raising_ones() -> None:
    calls = []

    def counted(ctx, e):
        calls.append(1)
        return True

    def boom(ctx, e):
        raise RuntimeError("secret")

    cfg = {
        "id": "o",
        "initial": "a",
        "states": {
            "a": {
                "on": {
                    "X": {"target": "a", "guard": "counted"},
                    "Y": {"target": "a", "guard": "boom"},
                }
            }
        },
    }
    m = create_machine(
        cfg, logic=MachineLogic(guards={"counted": counted, "boom": boom})
    )
    with TestClient(_app(m)) as c:
        r = c.get("/o/k/events")
    assert r.status_code == 200
    assert r.json()["available"] == ["X"]  # Y's raising guard → hidden
    assert "secret" not in r.text
    # 📝 Guards RUN on a GET: they must be pure (documented in the guide).
    assert calls


def test_events_schema_publishes_model_defaults() -> None:
    """Defaults are part of the model's JSON Schema -- the same document
    `/openapi.json` publishes. Pinned so nobody assumes otherwise: never
    put a secret in an EventModel default (documented)."""

    class Tok(EventModel):
        type: Literal["TOK"] = "TOK"
        token: str = "tok_default"

    m = _chart(["TOK"], event_schemas=events_union(Tok))
    with TestClient(_app(m)) as c:
        declared = c.get("/o/k/events").json()["declared"]
    assert declared[0]["schema"]["properties"]["token"]["default"] == (
        "tok_default"
    )


def test_diagram_is_authorized() -> None:
    m = _chart(["GO"])
    with TestClient(_app(m, authorize=lambda *a, **k: False)) as c:
        r = c.get("/o/k/diagram.mmd")
    assert r.status_code == 403
    assert r.headers["content-type"].startswith("application/problem+json")


def test_diagram_500_states_is_bounded() -> None:
    import time

    states = {
        f"s{n}": {"on": {"NEXT": f"s{(n + 1) % 500}"}} for n in range(500)
    }
    m = create_machine({"id": "o", "initial": "s0", "states": states})
    with TestClient(_app(m)) as c:
        t = time.perf_counter()
        r = c.get("/o/k/diagram.mmd")
        assert time.perf_counter() - t < 5
    assert r.text.count("-->") >= 500
