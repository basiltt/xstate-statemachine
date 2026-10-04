# tests/contrib/pydantic/test_battle_266_schema.py
"""#266 battle (agent B): `machine_json_schema` pinned.

* ``state.enum`` equals the parser's state ids exactly (parallel, nested,
  history, custom ``id``); ``x-leaf-states`` lists only leaves that can
  be ACTIVE -- a history pseudo-state is never in ``current_state_ids``;
* every ``$ref`` resolves inside ``$defs``; an event model and the
  context model with a nested model of the same class name no longer
  overwrite each other's ``$defs`` entry (they did: a single
  ``defs.update`` per pass);
* ``oneOf`` + ``discriminator.mapping`` for 1 / 2 / 20 models; a model
  without a ``Literal`` ``type`` in a union is a ``TypeError``, not a
  bare ``PydanticUserError``;
* ``Decimal`` emits ``anyOf [number, string]`` (documented);
  ``x-machine-hash`` == ``structure_hash``; stable and JSON round-trips;
* perf: the gate and the schema on the largest corpus chart stay far
  under 50 ms.
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Literal

import pytest

pytest.importorskip("pydantic")

from pydantic import BaseModel  # noqa: E402

from src.xstate_statemachine import (  # noqa: E402
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.contrib.pydantic import (  # noqa: E402
    EventModel,
    events_union,
    machine_json_schema,
    validate_machine_json,
)
from src.xstate_statemachine.persistence import structure_hash  # noqa: E402
from src.xstate_statemachine.testing_utils import stub_logic  # noqa: E402
from src.xstate_statemachine.validation import walk  # noqa: E402

CORPUS = Path(__file__).resolve().parents[2] / "tests_cli" / "stately_machines"

CFG: Dict[str, Any] = {
    "id": "m",
    "initial": "p",
    "version": "2",
    "states": {
        "p": {
            "type": "parallel",
            "on": {"DONE": "f"},
            "states": {
                "r1": {
                    "initial": "x",
                    "states": {"x": {}, "h": {"type": "history"}},
                },
                "r2": {"initial": "y", "states": {"y": {"id": "custom"}}},
            },
        },
        "f": {"type": "final"},
    },
}


class Item(BaseModel):
    sku: str


class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    amount: Decimal
    items: List[Item] = []


class Cancel(EventModel):
    type: Literal["CANCEL"] = "CANCEL"


def machine() -> Any:
    return create_machine(CFG, event_schemas=events_union(Pay, Cancel))


def _refs(node: Any, out: List[str]) -> List[str]:
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref":
                out.append(v)
            _refs(v, out)
    elif isinstance(node, list):
        for v in node:
            _refs(v, out)
    return out


def _assert_refs_resolve(doc: Dict[str, Any]) -> None:
    defs = doc.get("$defs", {})
    for ref in _refs(doc, []):
        assert ref.startswith("#/$defs/"), ref
        assert ref.split("/")[-1] in defs, ref


def test_state_enum_equals_the_parser_ids_and_leaves_are_activatable() -> None:
    m = machine()
    st = machine_json_schema(m)["properties"]["state"]
    assert st["enum"] == sorted(n.id for n in walk(m))
    assert "m.p.r1.h" in st["enum"]
    assert st["x-leaf-states"] == ["m.f", "m.p.r1.x", "m.p.r2.y"]
    # every leaf the engine can actually be in is listed, and no other
    interp = SyncInterpreter(m).start()
    seen = set(interp.current_state_ids)
    interp.send("DONE")
    seen |= set(interp.current_state_ids)
    assert seen <= set(st["x-leaf-states"])


def test_union_discriminator_mapping_and_refs() -> None:
    doc = machine_json_schema(machine())
    ev = doc["properties"]["event"]
    assert ev["discriminator"]["propertyName"] == "type"
    assert ev["discriminator"]["mapping"] == {
        "PAY": "#/$defs/Pay",
        "CANCEL": "#/$defs/Cancel",
    }
    assert {r["$ref"] for r in ev["oneOf"]} == set(
        ev["discriminator"]["mapping"].values()
    )
    _assert_refs_resolve(doc)


@pytest.mark.parametrize("n", [1, 2, 20])
def test_one_two_and_twenty_models(n: int) -> None:
    models = [
        type(
            f"E{i}",
            (EventModel,),
            {"__annotations__": {"type": Literal[f"E{i}"]}, "type": f"E{i}"},
        )
        for i in range(n)
    ]
    doc = machine_json_schema(machine(), events=models)
    ev = doc["properties"]["event"]
    if n == 1:
        assert ev["type"] == "object"
        assert ev["properties"]["type"]["const"] == "E0"
    else:
        assert len(ev["oneOf"]) == n
        assert len(ev["discriminator"]["mapping"]) == n
    _assert_refs_resolve(doc)


def test_union_member_without_literal_type_is_a_type_error() -> None:
    class Loose(EventModel):
        amount: int

    machine_json_schema(machine(), events=[Loose])  # alone: fine
    with pytest.raises(TypeError, match="Loose"):
        machine_json_schema(machine(), events=[Loose, Cancel])


def test_same_named_nested_models_do_not_overwrite_each_other() -> None:
    other_item = type(
        "Item",
        (BaseModel,),
        {"__annotations__": {"qty": int}, "__module__": "elsewhere"},
    )

    class Ctx(BaseModel):
        cart: List[other_item]  # type: ignore[valid-type]

    doc = machine_json_schema(machine(), context_model=Ctx)
    _assert_refs_resolve(doc)
    defs = doc["$defs"]
    pay_item = doc["$defs"]["Pay"]["properties"]["items"]["items"]["$ref"]
    ctx_item = doc["properties"]["context"]["properties"]["cart"]["items"][
        "$ref"
    ]
    assert pay_item != ctx_item
    assert "sku" in defs[pay_item.rsplit("/", 1)[-1]]["properties"]
    assert "qty" in defs[ctx_item.rsplit("/", 1)[-1]]["properties"]


def test_nested_context_model_refs_resolve() -> None:
    class Addr(BaseModel):
        city: str

    class Ctx(BaseModel):
        total: Decimal = Decimal("0")
        home: Addr
        history: List[Addr] = []

    doc = machine_json_schema(machine(), context_model=Ctx)
    _assert_refs_resolve(doc)
    ctx = doc["properties"]["context"]
    assert ctx["properties"]["home"] == {"$ref": "#/$defs/Addr"}
    # 📝 documented: Decimal is number-or-string
    kinds = {b.get("type") for b in ctx["properties"]["total"]["anyOf"]}
    assert kinds == {"number", "string"}


def test_metadata_hash_stability_and_round_trip() -> None:
    m = machine()
    doc = machine_json_schema(m, context_model=Item, title="T")
    assert doc["x-machine-hash"] == structure_hash(m) == m.structure_hash
    assert doc["x-machine-version"] == "2" and doc["title"] == "T"
    assert machine_json_schema(m, context_model=Item, title="T") == doc
    assert json.loads(json.dumps(doc)) == doc


def test_no_events_no_context_has_only_state() -> None:
    doc = machine_json_schema(create_machine(CFG))
    assert set(doc["properties"]) == {"state"} and "$defs" not in doc


def test_bounded_route_class_puts_an_app_route_in_the_envelope() -> None:
    """X0.7 for a route added BESIDE the router: 413 / 415 / safe 422."""
    pytest.importorskip("fastapi")
    from fastapi import APIRouter, Body, FastAPI
    from fastapi.testclient import TestClient

    from src.xstate_statemachine.contrib.fastapi import (
        bounded_route_class,
        instrument_app,
    )
    from src.xstate_statemachine.contrib.starlette import StatechartRegistry
    from src.xstate_statemachine.persistence import MemoryStore

    reg = StatechartRegistry(MemoryStore(), max_body_bytes=1024)
    app = FastAPI()
    extra = APIRouter(route_class=bounded_route_class(reg))

    @extra.post("/pay")
    async def pay(body: Item = Body(...)) -> dict:
        return {"ok": True}

    app.include_router(extra)
    instrument_app(app, reg)
    json_ct = {"content-type": "application/json"}
    with TestClient(app) as c:
        big = b'{"sku": "' + b"x" * 2000 + b'"}'
        assert c.post("/pay", content=big, headers=json_ct).status_code == 413
        r = c.post(
            "/pay", content=b'{"sku": "a"}', headers={"content-type": "x/y"}
        )
        assert r.status_code == 415
        r = c.post("/pay", json={"sku": ["s3cr3t-token"]})
        assert r.status_code == 422 and "s3cr3t" not in r.text
        assert c.post("/pay", json={"sku": "a"}).json() == {"ok": True}


# -----------------------------------------------------------------------------
# 7. perf rows (generous bound: the measured p50s are ~2 ms / <0.1 ms)
# -----------------------------------------------------------------------------
def _p50(fn: Any, n: int = 30) -> float:
    ts = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t)
    return statistics.median(ts) * 1000


def test_gate_and_schema_on_the_largest_corpus_chart_are_fast() -> None:
    logging.disable(logging.CRITICAL)
    try:
        largest = max(CORPUS.glob("*.json"), key=lambda p: p.stat().st_size)
        raw = json.loads(largest.read_text(encoding="utf-8"))
        assert _p50(lambda: validate_machine_json(raw)) < 50
        m = create_machine(raw, logic=stub_logic(raw))
        assert _p50(lambda: machine_json_schema(m)) < 50
    finally:
        logging.disable(logging.NOTSET)
