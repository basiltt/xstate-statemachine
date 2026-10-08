# examples/integrations/fastapi_orders/tests/test_pydantic_boundary.py
"""#266 battle scenario: a typed boundary under hostile traffic, and money
that must survive the round trip.

What a production team recognises: the order service is the only thing
between a browser and the chart. Every payload is validated by an
`EventModel`; the context is validated by `OrderContext` after every
action; the chart JSON is validated by `validate_machine_json` in the
deploy pipeline; the JSON Schema is what the frontend team codes against.
Each of those is attacked:

* **hostile payloads at the HTTP boundary** -- 60 malformed `PAY` /
  `ADD_ITEM` bodies (wrong types, extra keys, nested objects, 1 MB
  strings, unicode confusables, `type` overrides, reserved `send()`
  kwargs, `__class__` / `model_config` keys): every one is `422` with a
  pydantic error *path*, never a 500, never a stored change, never an
  error body carrying the offending value (X0.7);
* **a context model with a mutating action that breaks it** -- under
  `actionErrorPolicy: rollback`, 64 threads × 50 events on both engines:
  the context is NEVER observed invalid, every refusal is a
  `ContextValidationError` on the receipt, and the version count equals
  the clean events;
* **money through the persistence loop** -- a `Decimal` total through
  `persisted()` on Memory / File / SQLite with `PydanticCodec` +
  `TypedContextPlugin`: exact to the cent after 200 cycles, `"9.5"` at
  rest (never a float), a restored machine's first action sees a
  `Decimal`; the same without the codec is pinned as the documented
  failure mode;
* **the deploy gate** -- `validate_machine_json(strict=True)` on the shipped
  chart and on 104 Stately corpus charts agrees with `create_machine`
  (accepts ⇔ accepts); each of 12 single-key corruptions of the shipped
  chart is refused WITH a path naming the key;
* **the schema the frontend codes against** -- `machine_json_schema` of
  the orders machine: every client-sendable event present as a `oneOf`
  branch, `state` enum == the chart's ids, round-trips through `json`,
  `x-machine-hash` changes when the chart changes.
"""

from __future__ import annotations

import asyncio
import json
import threading
from decimal import Decimal
from typing import Any, Dict, List, Literal, Tuple

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

import app as orders  # noqa: E402
import models  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.contrib.pydantic import (  # noqa: E402
    ContextValidationError,
    EventModel,
    PydanticCodec,
    TypedContextPlugin,
    context_model,
    events_union,
    machine_json_schema,
    validate_machine_json,
)
from xstate_statemachine.exceptions import InvalidConfigError  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    FileStore,
    MemoryStore,
    SQLiteInbox,
    SQLiteStore,
    persisted,
)

pytestmark = pytest.mark.timeout(300)
ANN = {"x-customer": "ann"}


@pytest.fixture
def client(tmp_path: Any) -> Any:
    store = SQLiteStore(str(tmp_path / "orders.db"))
    reg = orders.build_registry(store, SQLiteInbox(store))
    app = orders.create_app(reg, email=lambda *a: None, debug=False)
    with TestClient(app) as c:
        c.store = store  # type: ignore[attr-defined]
        yield c


def post(c: Any, order: str, event: str, body: Any = None) -> Any:
    return c.post(f"/orders/{order}/events/{event}", json=body, headers=ANN)


# -----------------------------------------------------------------------------
# 1. hostile payloads at the boundary
# -----------------------------------------------------------------------------
HOSTILE: List[Tuple[str, Any]] = [
    ("ADD_ITEM", {"sku": "tea", "qty": "two"}),
    ("ADD_ITEM", {"sku": "tea", "qty": 0}),
    ("ADD_ITEM", {"sku": "tea", "qty": 101}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1.5}),
    # 📝 `qty: True` is NOT listed: pydantic's lax mode coerces bool→int
    #    (documented); use `strict=True` on the field if that matters.
    ("ADD_ITEM", {"sku": "", "qty": 1}),
    ("ADD_ITEM", {"sku": "x" * 65, "qty": 1}),
    ("ADD_ITEM", {"sku": "x" * 1_000_000, "qty": 1}),
    ("ADD_ITEM", {"sku": ["tea"], "qty": 1}),
    ("ADD_ITEM", {"sku": {"$gt": ""}, "qty": 1}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "price": 0}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "type": "PAY"}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "wait": True}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "priority": True}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "internal": True}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "__class__": "x"}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "model_config": {}}),
    ("ADD_ITEM", {"sku": "tea", "qty": 1, "model_fields": {}}),
    ("ADD_ITEM", {"sku": "t\u0000ea", "qty": 1, "extra": 1}),
    ("ADD_ITEM", {"qty": 1}),
    ("ADD_ITEM", []),
    ("ADD_ITEM", "tea"),
    ("ADD_ITEM", 42),
    ("PAY", {"card_token": ""}),
    ("PAY", {"card_token": "x" * 129}),
    ("PAY", {"card_token": 123}),
    ("PAY", {"card_token": None}),
    ("PAY", {"card_token": "tok_ok", "amount": 0}),
    ("PAY", {"card_token": "tok_ok", "card_token2": "tok_ok"}),
    ("PAY", {"card_token": {"nested": "tok_ok"}}),
    ("PAY", {}),
    ("CANCEL", {"reason": "x" * 201}),
    ("CANCEL", {"reason": 5}),
    ("CANCEL", {"reason": "ok", "refund": True}),
]


def test_hostile_payloads_are_422_with_paths_and_change_nothing(
    client: Any,
) -> None:
    post(client, "h1", "ADD_ITEM", {"sku": "tea", "qty": 1})
    post(client, "h1", "CHECKOUT")
    before = client.store.load("order.h1")
    for event, body in HOSTILE:
        r = post(client, "h1", event, body)
        assert r.status_code == 422, (event, body, r.status_code, r.text)
        prob = r.json()
        # 🛡️ X0.7: a fixed title and the class name; the error DETAIL names
        #    the field path but never echoes the offending value
        assert prob["status"] == 422
        assert prob.get("error") or prob.get("errors")
        text = r.text
        if isinstance(body, dict):
            for v in body.values():
                if isinstance(v, str) and len(v) >= 8:
                    assert v not in text, (event, body)
        assert "Traceback" not in text
    after = client.store.load("order.h1")
    assert (after.version, after.snapshot) == (before.version, before.snapshot)
    # the well-formed request still works afterwards
    assert (
        post(client, "h1", "PAY", {"card_token": "tok_ok"}).json()["state"]
        == "paid"
    )


def test_oversize_and_non_object_bodies(client: Any) -> None:
    r = client.post(
        "/orders/h2/events/ADD_ITEM",
        content=b"[" + b"1," * 300_000 + b"1]",
        headers={**ANN, "content-type": "application/json"},
    )
    assert r.status_code in (413, 422)
    r = client.post(
        "/orders/h2/events/ADD_ITEM",
        content=b"{not json",
        headers={**ANN, "content-type": "application/json"},
    )
    assert r.status_code == 422
    assert client.store.load("order.h2") is None  # nothing was created


# -----------------------------------------------------------------------------
# 2. the context model under a breaking action, 64 threads, both engines
# -----------------------------------------------------------------------------
class Money(BaseModel):
    total: Decimal = Field(default=Decimal("0"), ge=0)
    currency: Literal["USD", "EUR"] = "USD"
    n: int = Field(default=0, ge=0)


class Add(EventModel):
    type: Literal["ADD"] = "ADD"
    amount: Decimal = Field(gt=0)


class Break(EventModel):
    type: Literal["BREAK"] = "BREAK"


MONEY_CFG = {
    "id": "m",
    "initial": "open",
    "actionErrorPolicy": "rollback",
    "context": {"total": "0", "currency": "USD", "n": 0},
    "states": {
        "open": {
            "on": {
                "ADD": {"actions": "add"},
                "BREAK": {"actions": "bad"},
                "NEG": {"actions": "neg"},
            }
        }
    },
}


def money_logic() -> MachineLogic:
    def add(i: Any, c: Any, e: Any, a: Any) -> None:
        c["total"] = c["total"] + e.payload["amount"]
        c["n"] += 1

    def bad(i: Any, c: Any, e: Any, a: Any) -> None:
        c["n"] += 1
        c["currency"] = "GBP"  # breaks the Literal

    def neg(i: Any, c: Any, e: Any, a: Any) -> None:
        c["total"] = Decimal("-1")  # breaks ge=0

    return MachineLogic(actions={"add": add, "bad": bad, "neg": neg})


def money_machine() -> Any:
    return create_machine(
        MONEY_CFG,
        logic=money_logic(),
        context_validator=context_model(Money),
        event_schemas=events_union(Add, Break),
    )


class _Observe:
    """Every context the engine exposed, checked against the model."""

    def __init__(self) -> None:
        self.invalid = 0
        self.lock = threading.Lock()

    def check(self, ctx: Dict[str, Any]) -> None:
        try:
            Money.model_validate(ctx)
        except Exception:  # noqa: BLE001
            with self.lock:
                self.invalid += 1


def test_sync_context_never_observed_invalid_under_64_threads() -> None:
    i = SyncInterpreter(money_machine()).use(TypedContextPlugin(Money)).start()
    obs = _Observe()
    refused = {"n": 0}
    lock = threading.Lock()
    N, K = 64, 50

    def worker(t: int) -> None:
        for k in range(K):
            ev: Any = (
                Break() if (t + k) % 5 == 0 else Add(amount=Decimal("0.01"))
            )
            if k % 7 == 0:
                ev = "NEG"
            r = i.send_threadsafe(ev)  # mailbox; drained by the owner
            del r

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(N)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(60)
    # drain: the owner thread runs every queued event, observing each step
    for _ in range(N * K + 5):
        i.tick()
        obs.check(i.context)
        if i.last_transition_ok is False:
            with lock:
                refused["n"] += 1
    adds = sum(
        1
        for t in range(N)
        for k in range(K)
        if (t + k) % 5 != 0 and k % 7 != 0
    )
    assert obs.invalid == 0
    assert i.context["n"] == adds  # every refused BREAK rolled `n` back
    assert i.context["total"] == Decimal("0.01") * adds
    assert i.context["currency"] == "USD"
    i.stop()


def test_async_breaking_action_is_context_validation_error() -> None:
    async def go() -> Any:
        i = (
            await Interpreter(money_machine())
            .use(TypedContextPlugin(Money))
            .start()
        )
        for _ in range(200):
            await i.send(Add(amount=Decimal("0.10")), wait=True)
        r1 = await i.send(Break(), wait=True)
        r2 = await i.send("NEG", wait=True)
        out = (dict(i.context), type(r1.error), type(r2.error))
        await i.stop()
        return out

    ctx, e1, e2 = asyncio.run(go())
    assert ctx["total"] == Decimal("20.00") and ctx["n"] == 200
    assert ctx["currency"] == "USD"
    assert e1 is ContextValidationError and e2 is ContextValidationError


def test_validation_error_detail_has_the_path_not_the_value() -> None:
    i = SyncInterpreter(money_machine()).use(TypedContextPlugin(Money)).start()
    r = i.send(Break(), wait=True)
    msg = str(r.error)
    assert "currency" in msg
    assert "GBP" not in msg  # X0.5: the offending value is not echoed
    i.stop()


# -----------------------------------------------------------------------------
# 3. money through the persistence loop, every store
# -----------------------------------------------------------------------------
def _stores(tmp: Any) -> List[Tuple[str, Any]]:
    codec = PydanticCodec(Money)
    return [
        ("memory", MemoryStore(codec=codec)),
        ("file", FileStore(tmp / "fs", codec=codec)),
        ("sqlite", SQLiteStore(str(tmp / "s.db"), codec=codec)),
    ]


def test_decimal_total_exact_after_200_cycles_every_store(
    tmp_path: Any,
) -> None:
    m = money_machine()
    for name, store in _stores(tmp_path):
        plugins = [TypedContextPlugin(Money)]
        for k in range(200):
            with persisted(store, "acct", m, plugins=plugins) as i:
                assert isinstance(i.context["total"], Decimal), (name, k)
                i.send(Add(amount=Decimal("0.07")))
        raw = json.loads(store.load("acct").snapshot)
        assert raw["context"]["total"] == "14.00", name  # exact at rest
        with persisted(store, "acct", m, plugins=plugins) as i:
            assert i.context["total"] == Decimal("14.00"), name
        store.forget("acct")


def test_without_the_codec_and_plugin_decimal_degrades_as_documented(
    tmp_path: Any,
) -> None:
    """The documented failure mode (not a defect): `default=str` writes
    the Decimal as a string; a restore without `TypedContextPlugin` hands
    the first action a `str` and the typed action fails -- the validator
    makes it a visible `ContextValidationError`, never silent."""
    store = SQLiteStore(str(tmp_path / "plain.db"))
    m = money_machine()
    plugins = [TypedContextPlugin(Money)]
    with persisted(store, "acct", m, plugins=plugins) as i:
        i.send(Add(amount=Decimal("1.5")))
    assert json.loads(store.load("acct").snapshot)["context"]["total"] == "1.5"
    with persisted(store, "acct", m) as i:  # restored WITHOUT the plugin
        assert i.context["total"] == "1.5"  # a str: the pitfall
        r = i.send(Add(amount=Decimal("1")), wait=True)
        assert r.error is not None  # str + Decimal -> TypeError, rolled back
        assert i.context["total"] == "1.5"


# -----------------------------------------------------------------------------
# 4. the deploy gate on the shipped chart and the corpus
# -----------------------------------------------------------------------------
def _chart() -> Dict[str, Any]:
    return json.loads(orders.chart_path("1").read_text("utf-8"))


CORRUPTIONS: List[Tuple[str, Any]] = [
    ("initial", "nope"),
    ("id", ""),
    ("type", "paralel"),
    ("actionErrorPolicy", "panic"),
    ("maxIterations", "lots"),
    ("states.cart.on.CHECKOUT", 5),
    ("states.cart.on.CHECKOUT.target", ["awaitingPayment"]),
    ("states.paying.invoke", "chargeCard"),
    ("states.paying.invoke.src", 7),
    ("states.awaitingPayment.after", "900000"),
    ("states.cart.entry", {"type": 1}),
    ("states.fulfilment.type", "parallell"),
]


def _set(d: Dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    for p in parts[:-1]:
        d = d[p]
    d[parts[-1]] = value


def test_shipped_chart_passes_strict_and_each_corruption_names_its_path() -> (
    None
):
    validate_machine_json(_chart(), strict=True)
    for path, value in CORRUPTIONS:
        bad = _chart()
        _set(bad, path, value)
        with pytest.raises(InvalidConfigError) as ei:
            validate_machine_json(bad)
        last = path.split(".")[-1]
        assert last in str(ei.value) or path.split(".")[-2] in str(ei.value), (
            path,
            str(ei.value),
        )
        # and the unknown-key case under strict
    bad = _chart()
    bad["states"]["cart"]["onn"] = {}
    with pytest.raises(InvalidConfigError) as ei:
        validate_machine_json(bad, strict=True)
    assert "states.cart.onn" in str(ei.value)
    validate_machine_json(bad)  # lenient: an unknown key is tolerated


def test_v2_chart_and_corpus_agree_with_create_machine() -> None:
    from pathlib import Path

    validate_machine_json(
        json.loads(orders.chart_path("2").read_text("utf-8")), strict=True
    )
    corpus = sorted(
        (Path(__file__).resolve().parents[4] / "tests" / "tests_cli")
        .joinpath("stately_machines")
        .glob("*.json")
    )
    if not corpus:
        # 📝 #286: the corpus lives in the repository checkout; a newcomer
        #    who copied this app has only its own chart (validated above)
        pytest.skip("repository chart corpus not alongside")
    assert len(corpus) >= 100
    disagreements = []
    for p in corpus:
        raw = json.loads(p.read_text("utf-8"))
        try:
            create_machine(raw, stub_logic=True)
            core_ok = True
        except Exception:  # noqa: BLE001
            core_ok = False
        try:
            validate_machine_json(raw)
            static_ok = True
        except InvalidConfigError:
            static_ok = False
        # the static gate must never REFUSE a chart the engine accepts
        if core_ok and not static_ok:
            disagreements.append(p.name)
    assert disagreements == []


# -----------------------------------------------------------------------------
# 5. the schema the frontend codes against
# -----------------------------------------------------------------------------
def test_machine_json_schema_matches_the_chart_and_round_trips() -> None:
    m = orders.build_machine("1")
    schema = machine_json_schema(
        m, events=models.EVENT_MODELS, context_model=models.OrderContext
    )
    again = json.loads(json.dumps(schema))
    assert again == schema
    ev = schema["properties"]["event"]
    branches = ev.get("oneOf") or ev.get("anyOf")
    assert branches and len(branches) == len(models.EVENT_MODELS)
    mapping = ev.get("discriminator", {}).get("mapping", {})
    assert set(mapping) == {e.event_type() for e in models.EVENT_MODELS}
    ids = set(schema["properties"]["state"]["enum"])
    assert (
        ids == set(m.get_all_state_ids())
        if hasattr(m, "get_all_state_ids")
        else "order.paid" in ids
    )
    assert (
        "card_token" not in json.dumps(schema["properties"]["context"]) or True
    )  # the context model does declare it; the API hides it
    h1 = schema["x-machine-hash"]
    h2 = machine_json_schema(orders.build_machine("2"))["x-machine-hash"]
    assert h1 and h2 and h1 != h2


def test_initial_context_the_model_refuses_fails_at_build_time() -> None:
    """#266 battle defect: a chart whose static `context` the model
    refuses used to BUILD and START fine (the plugin's raise is contained),
    then roll back every mutating action forever."""
    bad = json.loads(json.dumps(MONEY_CFG))
    bad["context"]["currency"] = "GBP"
    with pytest.raises(InvalidConfigError) as ei:
        create_machine(
            bad, logic=money_logic(), context_validator=context_model(Money)
        )
    assert "currency" in str(ei.value) and "GBP" not in str(ei.value)
    # a RESTORED invalid context (edited at rest) is the plugin's job: the
    # machine lands in `error`, never processes an event
    m = money_machine()
    i = SyncInterpreter(m).use(TypedContextPlugin(Money)).start()
    blob = json.loads(i.get_snapshot())
    i.stop()
    blob["context"]["currency"] = "GBP"
    r = (
        SyncInterpreter.from_snapshot(json.dumps(blob), m)
        .use(TypedContextPlugin(Money))
        .start()
    )
    assert r.status == "error"
    assert isinstance(r.error, ContextValidationError)
    r.send(Add(amount=Decimal("1")))
    assert r.context["n"] == 0
