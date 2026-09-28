"""Verification for #266 (A9 pydantic). `python scripts/verify/266_pydantic.py`.

Runs against the installed package with the [pydantic] extra. The issue's
scenario via the core seams (context_validator / event_schemas /
__xstate_event__): typed event send, typed context view, an action that
breaks the model is rolled back, a bad payload is InvalidEventPayloadError,
static config validation with paths, JSON schema.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Literal


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from pydantic import BaseModel

    from xstate_statemachine import (
        MachineLogic,
        SyncInterpreter,
        create_machine,
    )
    from xstate_statemachine.contrib.pydantic import (
        ContextValidationError,
        EventModel,
        TypedContextPlugin,
        context_model,
        context_of,
        events_union,
        machine_json_schema,
        typed_context,
        validate_machine_json,
    )
    from xstate_statemachine.exceptions import (
        InvalidConfigError,
        InvalidEventPayloadError,
    )

    class Ctx(BaseModel):
        total: Decimal = Decimal(0)
        currency: Literal["USD", "EUR"] = "USD"

    class Pay(EventModel):
        type: Literal["PAY"] = "PAY"
        amount: Decimal

    cfg = {
        "id": "o",
        "initial": "open",
        "actionErrorPolicy": "rollback",
        "states": {
            "open": {
                "on": {"PAY": {"actions": "add"}, "BREAK": {"actions": "bad"}}
            }
        },
    }
    logic = MachineLogic(
        actions={
            "add": lambda i, c, e, a: c.__setitem__(
                "total", c["total"] + e.payload["amount"]
            ),
            "bad": lambda i, c, e, a: c.__setitem__("currency", "GBP"),
        }
    )
    m = create_machine(
        typed_context(Ctx, cfg),
        logic=logic,
        context_validator=context_model(Ctx),
        event_schemas=events_union(Pay),
    )

    step("typed event + typed context view")
    i = SyncInterpreter(m).use(TypedContextPlugin(Ctx)).start()
    i.send(Pay(amount=Decimal("9.5")))
    print(" ", context_of(i, Ctx))
    assert context_of(i, Ctx).total == Decimal("9.5")

    step("action breaking the model -> ContextValidationError, rolled back")
    r = i.send("BREAK", wait=True)
    print("  rolled back:", i.context["currency"], type(r.error).__name__)
    assert i.context["currency"] == "USD" and isinstance(
        r.error, ContextValidationError
    )

    step("bad payload -> InvalidEventPayloadError with pydantic detail")
    try:
        i.send("PAY", amount="x")
        raise SystemExit("accepted a bad payload")
    except InvalidEventPayloadError as e:
        print("  ", type(e.cause).__name__, e.cause.errors()[0]["loc"])
    i.stop()

    step("validate_machine_json: paths, before create_machine")
    for bad in (
        {"id": "o", "initial": "nope", "states": {"a": {}}},
        {
            "id": "o",
            "initial": "a",
            "states": {"a": {"on": {"X": {"target": 5}}}},
        },
        {"id": "o", "initial": "a", "states": {"a": {"entryy": "x"}}},
    ):
        try:
            validate_machine_json(bad, strict=True)
            raise SystemExit(f"accepted {bad}")
        except InvalidConfigError as e:
            print("  ", str(e).splitlines()[-1].strip())

    step("machine_json_schema round-trips")
    doc = machine_json_schema(m, events=[Pay], context_model=Ctx)
    assert json.loads(json.dumps(doc)) == doc
    print(
        "  properties:",
        sorted(doc["properties"]),
        "| states:",
        doc["properties"]["state"]["enum"],
    )

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
