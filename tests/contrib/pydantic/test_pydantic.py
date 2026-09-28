# tests/contrib/pydantic/test_pydantic.py
"""#266: typed context via the `context_validator` seam, typed events via
`event_schemas` + `__xstate_event__`, `validate_machine_json` in
lock-step with the parser and against the whole Stately corpus,
`machine_json_schema`. Both engines. Skips without the extra."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, List

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
    stub_logic,
)
from src.xstate_statemachine.exceptions import (
    InvalidConfigError,
    InvalidEventPayloadError,
    UnknownEventError,
)

from ..conftest import requires_extra

pytestmark = requires_extra("pydantic")
pydantic = pytest.importorskip("pydantic")
from pydantic import BaseModel  # noqa: E402
from typing import Literal  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"


class Ctx(BaseModel):
    total: Decimal = Decimal(0)
    currency: Literal["USD", "EUR"] = "USD"


CFG = {
    "id": "o",
    "initial": "open",
    "actionErrorPolicy": "rollback",
    "states": {
        "open": {
            "on": {
                "PAY": {"actions": "add"},
                "BREAK": {"actions": "bad"},
                "CLOSE": "closed",
            }
        },
        "closed": {"type": "final"},
    },
}


def _add(i: Any, c: Any, e: Any, a: Any) -> None:
    c["total"] = c["total"] + e.payload["amount"]


def _bad(i: Any, c: Any, e: Any, a: Any) -> None:
    c["currency"] = "GBP"


def logic() -> MachineLogic:
    return MachineLogic(actions={"add": _add, "bad": _bad})


def typed_machine(**kw: Any):
    from src.xstate_statemachine.contrib.pydantic import (
        context_model,
        events_union,
        typed_context,
    )

    return create_machine(
        typed_context(Ctx, CFG),
        logic=logic(),
        context_validator=context_model(Ctx),
        event_schemas=events_union(Pay),
        **kw,
    )


from src.xstate_statemachine.contrib.pydantic import EventModel  # noqa: E402


class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    amount: Decimal


# -----------------------------------------------------------------------------
# typed context
# -----------------------------------------------------------------------------
class TestTypedContext:
    def test_initial_context_completed_and_coerced(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import typed_context

        cfg = typed_context(Ctx, {**CFG, "context": {"total": "12.50"}})
        assert cfg["context"] == {"total": Decimal("12.50"), "currency": "USD"}
        assert (
            "context" not in CFG or CFG.get("context") is None
        )  # not mutated

    def test_invalid_initial_context_refused(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            ContextValidationError,
            typed_context,
        )

        with pytest.raises(ContextValidationError) as ei:
            typed_context(Ctx, {**CFG, "context": {"currency": "GBP"}})
        assert ei.value.model is Ctx
        assert ei.value.errors[0]["loc"] == ("currency",)
        assert "currency" in str(ei.value)

    def test_action_breaking_the_model_is_rolled_back_sync(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            ContextValidationError,
            context_of,
        )

        i = SyncInterpreter(typed_machine()).start()
        i.send(Pay(amount=Decimal("9.5")))
        assert context_of(i, Ctx) == Ctx(total=Decimal("9.5"))
        r = i.send("BREAK", wait=True)
        assert isinstance(r.error, ContextValidationError)
        assert i.context["currency"] == "USD"  # rollback restored it
        assert i.context["total"] == Decimal("9.5")
        i.stop()

    def test_async_parity(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            ContextValidationError,
        )

        async def go() -> Any:
            i = await Interpreter(typed_machine()).start()
            await i.send(Pay(amount=Decimal("1")), wait=True)
            r = await i.send("BREAK", wait=True)
            out = (dict(i.context), type(r.error))
            await i.stop()
            return out

        ctx, err = asyncio.run(go())
        assert ctx == {"total": Decimal("1"), "currency": "USD"}
        assert err is ContextValidationError

    def test_validator_not_called_when_context_unchanged(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import context_model

        calls = {"n": 0}
        base = context_model(Ctx)

        def counting(ctx: Any) -> None:
            calls["n"] += 1
            base(ctx)

        m = create_machine(CFG, logic=logic(), context_validator=counting)
        i = SyncInterpreter(m).start()
        i.send("CLOSE")  # no actions -> no context change
        assert calls["n"] == 0
        i.stop()

    def test_context_model_rejects_non_model(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import context_model

        with pytest.raises(TypeError):
            context_model(dict)  # type: ignore[arg-type]

    def test_typed_context_plugin_recoerces_after_restore(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import TypedContextPlugin

        m = typed_machine()
        i = SyncInterpreter(m).start()
        i.send(Pay(amount=Decimal("2.25")))
        blob = i.get_snapshot()
        i.stop()
        assert (
            json.loads(blob)["context"]["total"] == "2.25"
        )  # a string at rest
        r = (
            SyncInterpreter.from_snapshot(blob, m)
            .use(TypedContextPlugin(Ctx))
            .start()
        )
        assert r.context["total"] == Decimal("2.25")  # a Decimal again
        r.send(Pay(amount=Decimal("0.75")))
        assert r.context["total"] == Decimal("3.00")
        r.stop()

    def test_pydantic_codec_with_a_store(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            PydanticCodec,
            TypedContextPlugin,
        )
        from src.xstate_statemachine.persistence import MemoryStore, persisted

        store = MemoryStore(codec=PydanticCodec(Ctx))
        m = typed_machine()
        with persisted(store, "k", m, plugins=[TypedContextPlugin(Ctx)]) as i:
            i.send(Pay(amount=Decimal("9.5")))
        raw = json.loads(store.load("k").snapshot)
        assert raw["context"]["total"] == "9.5"  # exact, not float
        with persisted(store, "k", m, plugins=[TypedContextPlugin(Ctx)]) as i:
            assert i.context["total"] == Decimal("9.5")


# -----------------------------------------------------------------------------
# typed events
# -----------------------------------------------------------------------------
class TestTypedEvents:
    def test_event_model_is_an_event(self) -> None:
        i = SyncInterpreter(typed_machine()).start()
        i.send(Pay(amount=Decimal("3")))
        i.send_events([Pay(amount=Decimal("1")), Pay(amount=Decimal("1"))])
        assert i.context["total"] == Decimal("5")
        assert Pay(amount=Decimal("1")).__xstate_event__() == {
            "type": "PAY",
            "amount": Decimal("1"),
        }
        i.stop()

    def test_bad_payload_is_invalid_event_payload_error(self) -> None:
        i = SyncInterpreter(typed_machine()).start()
        with pytest.raises(InvalidEventPayloadError) as ei:
            i.send("PAY", amount="x")
        assert isinstance(ei.value.cause, pydantic.ValidationError)
        assert ei.value.cause.errors()[0]["loc"] == ("amount",)
        with pytest.raises(InvalidEventPayloadError):
            i.send("PAY")  # missing amount
        with pytest.raises(InvalidEventPayloadError):
            i.send("PAY", amount=1, extra="nope")  # extra="forbid"
        i.stop()

    def test_unknown_type_under_strict(self) -> None:
        i = SyncInterpreter(typed_machine(), strict=True).start()
        with pytest.raises(UnknownEventError):
            i.send("REFUND", amount=1)
        i.stop()

    def test_events_union_validation(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            EventModel,
            events_union,
            models_of,
        )

        class Dup(EventModel):
            type: Literal["PAY"] = "PAY"

        class NoType(EventModel):
            type: str

        with pytest.raises(TypeError, match="unique"):
            events_union(Pay, Dup)
        with pytest.raises(TypeError, match="Literal"):
            events_union(NoType)
        with pytest.raises(TypeError):
            events_union(Ctx)  # type: ignore[arg-type]
        union = events_union(Pay)
        assert set(union) == {"PAY"} and models_of(union) == (Pay,)

    def test_async_send_model(self) -> None:
        async def go() -> Any:
            i = await Interpreter(typed_machine()).start()
            r = await i.send(Pay(amount=Decimal("4")), wait=True)
            with pytest.raises(InvalidEventPayloadError):
                await i.send("PAY", amount="nope")
            t = i.context["total"]
            await i.stop()
            return r.changed, t

        assert asyncio.run(go()) == (True, Decimal("4"))


# -----------------------------------------------------------------------------
# config validation
# -----------------------------------------------------------------------------
class TestValidateMachineJson:
    def test_static_errors_with_paths(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            validate_machine_json,
        )

        cases = {
            "initial": (
                {"id": "o", "initial": "nope", "states": {"a": {}}},
                "initial state 'nope'",
            ),
            "id": ({"id": "", "states": {"a": {}}}, "id:"),
            "policy": (
                {
                    "id": "o",
                    "initial": "a",
                    "actionErrorPolicy": "explode",
                    "states": {"a": {}},
                },
                "actionErrorPolicy",
            ),
            "maxIterations": (
                {
                    "id": "o",
                    "initial": "a",
                    "maxIterations": "lots",
                    "states": {"a": {}},
                },
                "maxIterations",
            ),
            "target type": (
                {
                    "id": "o",
                    "initial": "a",
                    "states": {"a": {"on": {"X": {"target": 5}}}},
                },
                "states.a.on.X.target",
            ),
            "no states": ({"id": "o", "initial": "a"}, "at least one state"),
            "bad type": (
                {
                    "id": "o",
                    "initial": "a",
                    "states": {"a": {"type": "weird"}},
                },
                "states.a.type",
            ),
        }
        for name, (cfg, needle) in cases.items():
            with pytest.raises(InvalidConfigError) as ei:
                validate_machine_json(cfg)
            assert needle in str(ei.value), (name, str(ei.value))

    def test_unknown_keys_reported_with_paths_under_strict(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            validate_machine_json,
        )

        cfg = {
            "id": "o",
            "initial": "a",
            "x-tool": 1,
            "states": {
                "a": {
                    "entryy": "x",
                    "on": {"GO": {"target": "b", "gaurd": "g"}},
                },
                "b": {"invoke": {"src": "s", "onDon": "a"}},
            },
        }
        model = validate_machine_json(cfg)  # lenient: passes
        assert sorted(model.unknown_key_paths()) == [
            "states.a.entryy",
            "states.a.on.GO.gaurd",
            "states.b.invoke[0].onDon",
        ]
        with pytest.raises(InvalidConfigError) as ei:
            validate_machine_json(cfg, strict=True)
        assert "states.a.on.GO.gaurd" in str(ei.value) and "x-tool" not in str(
            ei.value
        )

    def test_accepts_str_and_helpers(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            validate_machine_json,
        )

        m = validate_machine_json(json.dumps(CFG))
        assert m.id == "o" and m.all_state_ids() == ["o", "o.open", "o.closed"]
        with pytest.raises(InvalidConfigError):
            validate_machine_json("[]")

    def test_corpus_parity_with_create_machine(self) -> None:
        """Every corpus chart `create_machine` accepts, the model accepts;
        and its state ids match the parser's."""
        from src.xstate_statemachine.contrib.pydantic import (
            validate_machine_json,
        )
        from src.xstate_statemachine.validation import walk

        files = sorted(CORPUS.glob("*.json"))
        assert len(files) > 20
        checked = 0
        for path in files:
            cfg = json.loads(path.read_text(encoding="utf-8"))
            try:
                machine = create_machine(cfg, logic=stub_logic(cfg))
            except (
                Exception
            ):  # noqa: BLE001 -- corpus files the parser refuses
                continue
            model = validate_machine_json(cfg)
            assert sorted(model.all_state_ids()) == sorted(
                n.id for n in walk(machine)
            ), path.name
            assert model.unknown_key_paths() == [], (
                path.name,
                model.unknown_key_paths(),
            )
            checked += 1
        assert checked > 20

    def test_model_fields_track_the_parser_key_sets(self) -> None:
        """Lock-step: the fields declared here == the keys the parser reads."""
        from src.xstate_statemachine.contrib.pydantic import (
            InvokeConfig,
            MachineConfig,
            StateConfig,
            TransitionConfig,
        )
        from src.xstate_statemachine.validation import (
            KNOWN_INVOKE_KEYS,
            KNOWN_ROOT_KEYS,
            KNOWN_STATE_KEYS,
            KNOWN_TRANSITION_KEYS,
        )

        assert set(StateConfig.model_fields) == set(KNOWN_STATE_KEYS)
        assert set(MachineConfig.model_fields) == set(KNOWN_ROOT_KEYS)
        assert set(TransitionConfig.model_fields) == set(KNOWN_TRANSITION_KEYS)
        assert set(InvokeConfig.model_fields) == set(KNOWN_INVOKE_KEYS)


# -----------------------------------------------------------------------------
# JSON schema
# -----------------------------------------------------------------------------
class TestMachineJsonSchema:
    def test_schema_shape_and_round_trip(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            EventModel,
            machine_json_schema,
        )

        class Cancel(EventModel):
            type: Literal["CANCEL"] = "CANCEL"
            reason: str = ""

        m = typed_machine()
        doc = machine_json_schema(m, events=[Pay, Cancel], context_model=Ctx)
        again = json.loads(json.dumps(doc))
        assert again == doc
        assert (
            doc["x-machine-id"] == "o"
            and doc["x-machine-hash"] == m.structure_hash
        )
        assert doc["properties"]["state"]["enum"] == [
            "o",
            "o.closed",
            "o.open",
        ]
        assert doc["properties"]["state"]["x-leaf-states"] == [
            "o.closed",
            "o.open",
        ]
        ev = doc["properties"]["event"]
        assert (
            "oneOf" in ev
            and ev.get("discriminator", {}).get("propertyName") == "type"
        )
        assert {"Pay", "Cancel"} <= set(doc["$defs"])
        ctx = doc["properties"]["context"]
        assert ctx["properties"]["currency"]["enum"] == ["USD", "EUR"]

    def test_defaults_from_machine_event_schemas(self) -> None:
        from src.xstate_statemachine.contrib.pydantic import (
            machine_json_schema,
        )

        doc = machine_json_schema(typed_machine())
        assert (
            "event" in doc["properties"]
        )  # found via events_union's validators
        assert "context" not in doc["properties"]
        doc2 = machine_json_schema(
            create_machine({"id": "x", "initial": "a", "states": {"a": {}}})
        )
        assert set(doc2["properties"]) == {"state"} and "$defs" not in doc2
