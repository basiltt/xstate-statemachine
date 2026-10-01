---
title: "Pydantic integration"
description: "Typed, validated context and events for statecharts with Pydantic v2 — plus static config validation and JSON Schema for your frontend."
---

# Pydantic

Modern Python expects typed, validated data at every boundary. `python-statemachine` and `transitions` are stringly typed; XState v5's `setup()` gives TypeScript users typed context and events. The Python equivalent is Pydantic v2 — and it is the validation layer the FastAPI, DRF and agents integrations reuse. *Silent acceptance is a bug*: a typo'd context key or a malformed payload should fail **at the boundary**, not deep inside an action. This extra makes that the default, through seams core already has — core never imports pydantic.

## Install

```bash
pip install "xstate-statemachine[pydantic]"
```

Requires `pydantic>=2.5`. Tested versions are in the [compatibility table](#compatibility).

**Runnable example.** [`examples/integrations/fastapi_orders`](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/fastapi_orders) uses this extra: its `models.py` imports `EventModel` and `events_union` from `xstate_statemachine.contrib.pydantic`, and its `app.py` imports `context_model`. The `agents_support_bot` example does not import the extra itself; its `lookup_order` tool calls the `fastapi_orders` app in-process, so it exercises these validated events through that app's HTTP surface.

## Quick start

<!-- doc-requires: pydantic -->
```python
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine
from xstate_statemachine.contrib.pydantic import (
    ContextValidationError, EventModel, TypedContextPlugin, context_model, context_of,
    events_union, typed_context,
)

class OrderContext(BaseModel):
    total: Decimal = Decimal(0)
    currency: Literal["USD", "EUR"] = "USD"

class Pay(EventModel):                       # an instance IS an event
    type: Literal["PAY"] = "PAY"
    amount: Decimal

cfg = {"id": "order", "initial": "open", "actionErrorPolicy": "rollback",
       "states": {"open": {"on": {"PAY": {"actions": "add"}, "BREAK": {"actions": "bad"}}}}}
logic = MachineLogic(actions={
    "add": lambda i, ctx, e, a: ctx.__setitem__("total", ctx["total"] + e.payload["amount"]),
    "bad": lambda i, ctx, e, a: ctx.__setitem__("currency", "GBP"),   # not in the Literal
})
machine = create_machine(
    typed_context(OrderContext, cfg),                      # initial context validated + completed
    logic=logic,
    context_validator=context_model(OrderContext),         # re-validated after every mutating action
    event_schemas=events_union(Pay),                       # payloads validated at send()
)
order = SyncInterpreter(machine).use(TypedContextPlugin(OrderContext)).start()

order.send(Pay(amount=Decimal("9.50")))                    # typed event, no dict
assert context_of(order, OrderContext) == OrderContext(total=Decimal("9.50"))

receipt = order.send("BREAK", wait=True)                   # the action breaks the model...
assert isinstance(receipt.error, ContextValidationError)   # ...reported as an action error...
assert order.context["currency"] == "USD"                  # ...and rolled back: never an invalid context
```

## Reference

### Typed context

| Name | What it does |
|:--|:--|
| `context_model(model, *, write_back=True) -> callable` | Builds the `context_validator=` for `create_machine()`. The engine calls it after any action that changed `context` (never when unchanged); a failure is `ContextValidationError`, an **action error**, so `actionErrorPolicy: "rollback"` restores the previous context. With `write_back` the model's defaults and coerced values are written into the live dict (`ctx["total"]` is a `Decimal`). |
| `typed_context(model, config) -> config` | Validates and completes the chart's `"context"` before `create_machine()`, so the initial context satisfies the model. Does not mutate `config`. |
| `TypedContextPlugin(model)` | Re-validates (and re-coerces) the context on `on_interpreter_start` — fresh **or restored**. A snapshot stores `Decimal("9.5")` as `"9.5"`; this plugin makes it a `Decimal` again before the first action. Attach it wherever you use `context_model`. |
| `context_of(interpreter, model) -> model` | A typed view: `model.model_validate(interpreter.context)`. Fresh each call; the dict stays the source of truth. |
| `PydanticCodec(model)` | A store `codec=` that serialises `context` through the model's JSON mode (`Decimal` → exact string, `datetime` → ISO 8601) instead of the engine's `str()` fallback. Pair with `TypedContextPlugin` for the way back. |
| `ContextValidationError` | `XStateMachineError` with `.model`, `.cause` (the pydantic `ValidationError`) and `.errors` (its `.errors()` list). |

### Typed events

| Name | What it does |
|:--|:--|
| `EventModel` | Base class: `type: Literal["PAY"] = "PAY"` + payload fields (`extra="forbid"`). Implements `__xstate_event__`, so an instance is accepted by `send()`, `send_events()`, `send_threadsafe()` and `sendTo` on both engines; `type` is the event type, every other field the payload (Python-mode dump — `Decimal` stays `Decimal`). |
| `events_union(*models) -> dict` | The `event_schemas=` mapping (type → validator). A bad payload raises the existing `InvalidEventPayloadError` at the `send()` call site with the pydantic `ValidationError` as `.cause`; an undeclared type is rejected under `strict`. Duplicate `type`s are a `TypeError`. |
| `models_of(schemas)` | The models behind an `events_union()` mapping. |

### Config validation

| Name | What it does |
|:--|:--|
| `validate_machine_json(raw, *, strict=False) -> MachineConfig` | A Pydantic model of the XState JSON subset this library implements. Raises `InvalidConfigError` **with JSON paths** (`states.paying.on.PAY.target: Input should be a valid string`) before `create_machine()`: missing/empty `id`, an `initial` naming no child, wrong `type` / policy values, a non-integer `maxIterations`, malformed transitions and invokes. `strict=True` also reports every unrecognised key with its path (`x-` keys are always allowed), mirroring `strictConfig`. Unknown transition *targets* remain the parser's job. |
| `MachineConfig` / `StateConfig` / `TransitionConfig` / `InvokeConfig` | The models. `MachineConfig.all_state_ids()`, `.unknown_key_paths()`. A test keeps their fields in lock-step with the parser's known-key sets and checks the whole Stately corpus. |

### JSON Schema

| Name | What it does |
|:--|:--|
| `machine_json_schema(machine, *, events=None, context_model=None, title=None) -> dict` | A JSON Schema (2020-12) with `properties.event` (a discriminated `oneOf` on `type`), `properties.context`, `properties.state` (an `enum` of every state id + `x-leaf-states`), `$defs`, and `x-machine-id` / `x-machine-version` / `x-machine-hash` so a frontend or OpenAPI consumer can tell which chart revision produced it. `events` defaults to the models behind the machine's `event_schemas`. |

## Guarantees

> **What this does:** the machine never *holds* a context that violates the model — an action that breaks it is an action error and `rollback` restores the previous context; a payload that does not fit its `EventModel` never enters the machine; a chart that fails `validate_machine_json` never reaches `create_machine`.
>
> **What this does not do:** validate context on every *read* (only after a mutating action, and on start with `TypedContextPlugin`); type-check guards or services; replace `create_machine`'s own tree validation (unknown targets, dead `always` loops). With `actionErrorPolicy: "continue"` (the pre-1.0 default) an invalid context IS kept and only reported — set `"rollback"`.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** whoever can `send()` — the same surface as any event. Validation runs in the sender's call, before queueing, so a malformed payload costs the sender, not the machine.
>
> **What it exposes:** `ContextValidationError` / `InvalidEventPayloadError` messages include pydantic's field paths and messages (not values by default — pydantic omits `input` from `str()`); `machine_json_schema` publishes your event and context *shapes* — review it before serving it publicly.
>
> **You must configure:** `actionErrorPolicy: "rollback"` for the never-invalid guarantee; `extra="forbid"` on your context model if unknown keys should be refused; the store `codec=` if `Decimal` / `datetime` precision at rest matters.

## Compatibility

| pydantic | Python | Tested in CI |
|:--|:--|:--|
| 2.5 – 2.x | 3.9 – 3.14 | ✅ `[pydantic]` cell (Linux, Windows) |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[pydantic]"` | extra not installed | run the command |
| Restored machine's action fails with `unsupported operand type(s) for +: 'str' and 'Decimal'` | a snapshot stores `Decimal` as text | attach `TypedContextPlugin(Model)` (and use `PydanticCodec` on the store) |
| `ContextValidationError` but the context kept the bad value | `actionErrorPolicy` is `"continue"` | set `"rollback"` on the machine |
| `TypeError: event type 'PAY' declared by both …` | two `EventModel`s share a `type` | make discriminators unique |
| `validate_machine_json` accepts a chart `create_machine` rejects | unknown targets / dead loops need the whole tree | run both; the model is the *fast, path-reporting* first pass |
