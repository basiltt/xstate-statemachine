---
title: "FastAPI integration"
description: "Generate a typed REST API and its OpenAPI document from a statechart: StatechartRouter, Depends(get_interpreter), discriminated-union event bodies, RFC 9457 problems, SSE and WebSocket."
---

# FastAPI

A chart already declares its public surface: its events, their payload models and its states. The `[fastapi]` extra turns that into a whole REST API — a typed `APIRouter` whose OpenAPI document lists every event as a member of a discriminated union, returns RFC 9457 problems for every failure, and streams transitions over SSE and WebSocket. Everything stateful is the `[starlette]` [`StatechartRegistry`](../integration-starlette/) (re-exported here), so the multi-worker model, `Idempotency-Key` handling and `Receipt → HTTP` mapping are exactly the ones documented there. This extra adds only what is specific to FastAPI: typed bodies, `Depends` and the schema.

## Install

```bash
pip install "xstate-statemachine[fastapi]"
```

This installs FastAPI `>=0.100`, Pydantic `>=2.5` and Starlette `>=0.27`. Tested versions are in the [compatibility table](#compatibility). `fastapi.testclient` (used below) also needs `httpx`.

## Quick start

<!-- doc-requires: fastapi, httpx -->
```python
from typing import Literal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.fastapi import (
    StatechartRegistry, StatechartRouter, instrument_app,
)
from xstate_statemachine.contrib.pydantic import EventModel, events_union
from xstate_statemachine.persistence import MemoryStore

class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    amount: int

class Cancel(EventModel):
    type: Literal["CANCEL"] = "CANCEL"

order = create_machine(
    {"id": "order", "initial": "open",
     "states": {"open": {"on": {"PAY": "paid", "CANCEL": "cancelled"}},
                "paid": {}, "cancelled": {}}},
    event_schemas=events_union(Pay, Cancel),
)

def authorize(request, *, name, key, event):
    return request.headers.get("x-user") is not None   # your auth here

registry = StatechartRegistry(MemoryStore())
registry.register("order", order, authorize=authorize)

app = FastAPI()
app.include_router(StatechartRouter(registry, "order", prefix="/orders",
                                    tags=["orders"]))
instrument_app(app, registry)       # probes, lifespan, problem handlers

with TestClient(app) as client:
    user = {"x-user": "ann"}
    r = client.post("/orders/7/send", json={"type": "PAY", "amount": 10},
                    headers=user)
    assert r.status_code == 200 and r.json()["state"] == "paid"
    bad = client.post("/orders/8/send", json={"type": "PAY"}, headers=user)
    assert bad.status_code == 422                     # `amount` missing
    assert bad.headers["content-type"] == "application/problem+json"
    assert client.get("/orders/7").status_code == 403  # no user
    body = app.openapi()["paths"]["/orders/{id}/send"]["post"]["requestBody"]
    union = body["content"]["application/json"]["schema"]
    assert union["discriminator"]["propertyName"] == "type"
```

For a hand-written route, `get_interpreter` is a ready-made `Depends` that yields a started interpreter and persists it when the handler returns:

<!-- doc-fragment -->
```python
from xstate_statemachine.contrib.fastapi import ReceiptResponse, get_interpreter

@app.post("/orders/{order_id}/pay-in-full")
async def pay_in_full(order=get_interpreter(registry, "order", key="order_id")):
    return ReceiptResponse(order, await order.send("PAY", wait=True, amount=100))
```

## Reference

### `StatechartRouter(registry, name, *, prefix=None, tags=None, key_param="id", event_models=None, include_diagram=True, create_if_missing=True, operation_id_prefix=None, dependencies=(), per_event_dependencies=None, actor=None) -> APIRouter`

Returns an `APIRouter` for machine *name* (already registered on *registry*). `prefix` defaults to `/<name>`; `{id}` below is `key_param`.

| Route | Body | Response |
|:--|:--|:--|
| `GET /{id}` | — | `{state, state_ids, available_events, machine_version}` (+ `context` only with a `context_serializer`) |
| `POST /{id}/send` | discriminated union of the event models on `type` | receipt: 200 changed/unchanged/duplicate, 202 deferred, 409 guard denied or conflict, 422 invalid |
| `POST /{id}/events/<EVENT>` | that event's model, optional | same as `/send` — one route per declared event |
| `GET /{id}/events` | — | `{available: [...], declared: [{type, schema}]}` — `available` is what `can()` accepts now |
| `GET /{id}/diagram.mmd` | — | Mermaid, `text/plain` (omit with `include_diagram=False`) |
| `GET /{id}/stream` | — | SSE, via [`transition_stream`](../integration-starlette/#reference) |
| `WS /{id}/ws` | — | [`websocket_endpoint`](../integration-starlette/#reference) protocol |

* **`event_models`** — `EventModel` subclasses. Defaults to the models behind the machine's `events_union()` schemas. Without any, the `/send` body is `{type: Literal[<declared events>], payload: {...}}`, so the schema is still deterministic.
* **`create_if_missing=False`** — reads and sends on an unknown key are `404` instead of starting a new instance.
* **`dependencies`** — FastAPI dependencies on every route (your auth). **`per_event_dependencies={EVENT: [Depends(...)]}`** adds dependencies to that event's `/events/EVENT` route; such an event is refused on `/send` (403) so the extra check cannot be bypassed.
* **`actor`** — a dependency returning the authenticated principal, which scopes `Idempotency-Key`. Defaults to the registry's `principal(conn)`. The principal never comes from the body.
* **`operation_id_prefix`** — operation ids are `<prefix>_get`, `<prefix>_send`, `<prefix>_<event>`, `<prefix>_events`, `<prefix>_diagram`, `<prefix>_stream` (prefix defaults to *name*).

Both POSTs delegate to `registry.send_event`: authorize (with the event type) → `Idempotency-Key` → `act()` → receipt. Bodies must be `application/json` (415) and at most `max_body_bytes` (413); request validation failures are `422` problems listing each error's `loc` and `type` only.

### `get_interpreter(registry, name, *, key="id", actor=None, create_if_missing=True)`

Returns a `Depends(...)` — use it directly as a parameter default. It runs `authorize` with `event=None`, then yields a started interpreter inside `registry.act()`: **saved** with `expected_version` after the handler returns, **not saved** if the handler raises. *key* is a path-parameter name or a `(request) -> str` callable. A save conflict raises `ConflictError`, which `instrument_app` turns into a 409 problem. On FastAPI `>=0.121` the dependency uses `scope="function"`, so the save happens *before* the response is sent — a conflict becomes the response instead of a log line.

### `instrument_app(app, registry, *, health_path="/_xsm/health", ready_path="/_xsm/ready", exception_handlers=True) -> app`

Mounts `registry.health_route()` and `registry.ready_route()`, wraps the app's current lifespan with `registry.lifespan` (timer scanner, resident drain) and, with *exception_handlers*, maps every `XStateMachineError` escaping a handler to a problem response via `problem_for_exception`. Call it before the app starts.

### `compose_lifespan(registry, inner=None)`

`FastAPI(lifespan=compose_lifespan(registry, my_lifespan))`: the registry starts first and stops last, around your own lifespan.

### `Problem` / `StateModel` / `ReceiptModel`

The Pydantic models that describe the wire shapes in OpenAPI. Every 4xx/5xx is documented as `application/problem+json` with the `Problem` schema.

### Re-exports

`StatechartRegistry`, `allow_all`, `ReceiptResponse`, `receipt_to_status`, `problem`, `problem_for_exception` — the same objects as in `xstate_statemachine.contrib.starlette`.

## Guarantees

> **What this does:** the same multi-worker model as [Starlette](../integration-starlette/#guarantees): **create → act → persist → discard** with an optimistic version check, so racing requests produce one winner and a `409` — never a lost update (tested with 50 concurrent `POST /send` to one key on `SQLiteStore`). The OpenAPI document is generated from the chart: every declared event has a route and is in the `/send` union, and every failure status is documented as a problem. SSE subscribers see one `transition` per committed changed receipt. `get_interpreter` persists only when the handler returns.
>
> **What this does not do:** the schema reflects the chart at startup — registering new events later needs a new router. SSE/WebSocket fan-out and residents are per-process, as in Starlette. Nothing retries a `409` for you.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can reach the router. `register(authorize=)` is **required** (X0.1) and runs on every route — reads and stream connects with `event=None`, sends with the event type — so authorization is per instance and per event. Add FastAPI-native checks with `dependencies=` / `per_event_dependencies=`.
>
> **What it exposes:** `GET` returns state, state ids and available events — **not** `context` unless you pass a `context_serializer` (X0.1). `/events` returns event names and their JSON Schemas (which your OpenAPI document already publishes). Problems carry a fixed title and the exception class name; validation problems list field locations and error types but never the input or pydantic's message text (X0.7).
>
> **You must configure:** an `authorize=` callable; an `actor=` dependency (or registry `principal=`) derived from your authenticated identity — `Idempotency-Key` is scoped to that principal so one caller cannot replay another's receipt (X0.2). Bodies are JSON-only and size-capped. **CSRF:** with cookie authentication a cross-site form cannot send `application/json` without a CORS preflight, but add a CSRF token or `SameSite` cookies anyway, and keep CORS origins explicit. `/diagram.mmd` and `/events` reveal the chart's structure — disable the diagram with `include_diagram=False` or gate the router with `dependencies=` if that matters to you.

## Compatibility

| FastAPI | Pydantic | Python | Tested in CI |
|:--|:--|:--|:--|
| 0.100 – 0.1xx | 2.5 – 2.x | 3.9 – 3.14 | ✅ |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[fastapi]"` | extra not installed | run the command |
| `KeyError: No machine registered as 'order'` | router built before `register()` | register first, then build the router |
| `/send` body schema is `{type, payload}` | the machine has no `events_union()` models | pass `event_schemas=events_union(...)` to `create_machine`, or `event_models=` to the router |
| `403 Use this event's dedicated route` | event has `per_event_dependencies` | post to `/{id}/events/<EVENT>` |
| Every POST is `409` under load | optimistic conflicts on a hot key | retry on 409, or `lock=PessimisticLock()` |
| A `get_interpreter` save conflict is logged, response already 200 | FastAPI older than 0.121 (no dependency `scope`) | upgrade FastAPI, or use `registry.act()` inside the handler |
