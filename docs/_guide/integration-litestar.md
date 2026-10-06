---
title: "Litestar integration"
description: "XStatePlugin, a Provide() interpreter dependency and a generated statechart Controller for Litestar, reusing the Starlette registry, Receipt → HTTP mapping, Idempotency-Key and SSE/WebSocket streams."
---

# Litestar

Litestar apps get the same statechart REST surface as [FastAPI](../integration-fastapi/) — same routes, statuses, problem bodies and operationIds; the one difference is `exclude_events=` instead of shadowing a route: a generated `Controller` with a typed `/send` body documented as a discriminated union, one route per declared event, RFC 9457 problems, SSE and WebSocket. It is built on the `[starlette]` [`StatechartRegistry`](../integration-starlette/) — Litestar speaks ASGI, so the registry, the `Receipt → HTTP` mapping, `Idempotency-Key` handling and the streams are reused unchanged. Only the edges are adapted: a Litestar request is read through a Starlette view of the same ASGI scope, and a Starlette response is converted to a Litestar `Response` / `Stream`.

## Install

```bash
pip install "xstate-statemachine[litestar]"
```

Requires Litestar `>=2.0` (and installs Starlette `>=0.27`). Typed `EventModel` bodies also need `[pydantic]`. Tested versions are in the [compatibility table](#compatibility). `litestar.testing.TestClient` (used below) needs `httpx`.

## Quick start

<!-- doc-requires: litestar, httpx -->
```python
from litestar import Litestar
from litestar.testing import TestClient

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.litestar import (
    StatechartRegistry, XStatePlugin, create_statechart_controller,
)
from xstate_statemachine.persistence import MemoryStore

door = create_machine({
    "id": "door", "initial": "closed",
    "states": {"closed": {"on": {"OPEN": "open"}},
               "open": {"on": {"CLOSE": "closed"}}},
})

def authorize(request, *, name, key, event):
    return request.headers.get("x-user") is not None   # your auth here

registry = StatechartRegistry(MemoryStore())
registry.register("door", door, authorize=authorize)

app = Litestar(
    route_handlers=[create_statechart_controller(registry, "door", path="/doors")],
    plugins=[XStatePlugin(registry)],   # lifespan, probes, problem mapping
)

with TestClient(app) as client:
    user = {"x-user": "ann"}
    r = client.post("/doors/1/send", json={"type": "OPEN"}, headers=user)
    assert r.status_code == 200 and r.json()["state"] == "open"
    assert client.post("/doors/1/send", json={"type": "OPNE"},
                       headers=user).status_code == 422
    assert client.get("/doors/1").status_code == 403       # no user
    assert client.get("/_xsm/ready").json()["status"] == "ready"
    assert "/doors/{id}/send" in app.openapi_schema.paths
```

## Owning an event route

A hand-written handler takes the interpreter as a `Provide` dependency and answers with `ReceiptResponse` — the Litestar-native one exported by this package (Starlette's `ReceiptResponse` cannot be returned from a Litestar handler; that is a 500).

Litestar refuses **two handlers on one path** (`ImproperlyConfiguredException`), so unlike FastAPI an app cannot shadow a generated `/events/<EVENT>` route by registering it first. Pass `exclude_events=` instead: the controller skips that route and **refuses the event on `/send` (403)** so your route cannot be bypassed. Still gate the event in `authorize` — the WebSocket route and any second controller go through it; `exclude_events` covers only this controller.

<!-- doc-requires: litestar, httpx -->
```python
from typing import Any

from litestar import Litestar, post
from litestar.testing import TestClient

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.litestar import (
    ReceiptResponse, StatechartRegistry, XStatePlugin,
    create_statechart_controller, get_interpreter,
)
from xstate_statemachine.persistence import MemoryStore

order = create_machine({
    "id": "order", "initial": "open",
    "states": {"open": {"on": {"PAY": "paid"}}, "paid": {}},
})

def authorize(request, *, name, key, event):
    # get_interpreter authorizes with event=None; every generated route
    # and WebSocket frame passes the event type, so PAY never gets through
    return event != "PAY"

registry = StatechartRegistry(MemoryStore())
registry.register("order", order, authorize=authorize)
charged = []

@post("/orders/{id:str}/events/PAY", status_code=200,
      dependencies={"order": get_interpreter(registry, "order")})
async def pay(order: Any, id: str) -> Any:
    receipt = await order.send("PAY", wait=True)
    if receipt.changed:
        charged.append(id)          # real code: an outbox row
    return ReceiptResponse(order, receipt)

app = Litestar(
    route_handlers=[pay, create_statechart_controller(
        registry, "order", path="/orders", exclude_events=("PAY",))],
    plugins=[XStatePlugin(registry)],
)

with TestClient(app) as client:
    assert client.post("/orders/1/events/PAY").json()["state"] == "paid"
    assert client.post("/orders/2/send", json={"type": "PAY"}).status_code == 403
assert charged == ["1"]
```

`get_interpreter` saves when the handler returns and discards when it raises; the [FastAPI Request rules](../integration-fastapi/#request-rules) (persistence, `Idempotency-Key`, guards on `GET /events`, gate on `authorize`) apply unchanged. `guards=` and `dependencies=` attach Litestar guards / `Provide`s to every generated route.

## OpenAPI

Served at `/schema/openapi.json` and deterministic for a given chart and model set (Litestar would otherwise generate random examples for msgspec `Struct` schemas; the controller pins them).

* **operationIds** — the same rule (shared code) as [FastAPI](../integration-fastapi/#openapi): `<prefix>_get|send|events|diagram|stream`, and `<prefix>_<event>` folded to ASCII `[a-z0-9_]`. Plain names (`ORDER_PAID`) keep the unsuffixed id; folded ones (`ORDER.PAID`) or names clashing with a fixed route (`get`) take `_2`, `_3`, … — unique, and stable when you add an event.
* **`/send` body** — one `EventModel`: that model; several: `oneOf` + `discriminator: type` (needs `XStatePlugin`); none: `<Name>Event` = `{type: enum[...], payload: {}}` with unknown top-level keys rejected. Aliased fields are honoured; actions read them under the alias.
* **Responses** — `200` is typed (`StateBody`, `ReceiptBody`, `EventsBody`; `context` is filled only with a `context_serializer`). Failures are `application/problem+json` (`Problem`): `400 401 403 404 409 413 415 422 501 503` on sends, `400 401 403 404 503` on reads, `429` on `/stream`.
* **422 problems** list `{"key", "source"}` per error (an unknown key's *name*, never a value), at most 50, plus `errors_total`.
* **Golden.** The library pins the AdvancePayment controller's served document in `tests/contrib/litestar/openapi_golden.json`; regenerate with `XSM_UPDATE_GOLDEN=1 pytest tests/contrib/litestar -k golden` and review the diff.

### msgspec and pydantic

"Works with both" means: without event models the `/send` body is a **msgspec** `Struct` (no pydantic involved); with `EventModel`s (`[pydantic]`) it is a pydantic `RootModel` over the union, validated by Litestar's own `PydanticPlugin` (auto-registered when pydantic is importable). `XStatePlugin` is needed only so the *document* shows the bare union rather than `{root: …}`. Both produce the same value-free 422 problem.

## Testing streams

`litestar.testing.TestClient.stream()` buffers the response, so a never-ending SSE stream hangs the test. Drive `/stream` with `httpx.AsyncClient(transport=httpx.ASGITransport(app))` inside the app's lifespan, or a raw ASGI driver that reads the first `http.response.body` frames.

## Reference

### `create_statechart_controller(registry, name, *, path=None, key_param="id", tags=None, event_models=None, include_diagram=True, create_if_missing=True, operation_id_prefix=None, exclude_events=(), guards=(), dependencies=None) -> type[Controller]`

A `Controller` subclass for machine *name* with the [FastAPI route table](../integration-fastapi/#reference): `GET /{id}`, `POST /{id}/send`, `POST /{id}/events/<EVENT>` per declared event, `GET /{id}/events`, `GET /{id}/diagram.mmd`, `GET /{id}/stream` (SSE) and `WS /{id}/ws`. Status mapping, `Idempotency-Key` and `authorize` are the registry's (`send_event`). The `/send` body is a Pydantic `RootModel` over the discriminated union of the machine's `EventModel`s (documented in OpenAPI as `oneOf` + `discriminator` by `XStatePlugin`), or a msgspec `Struct` `{type: Literal[<declared>], payload: {...}}` when there are none. Validation failures, non-JSON bodies (415) and oversize bodies (413) are problem responses. `exclude_events=` drops those events' routes and refuses them on `/send` (unknown names are a `ValueError`); `guards=` / `dependencies=` apply to every route.

### `XStatePlugin(registry, *, dependencies=False, key_param="id", dependency_prefix="", health_path="/_xsm/health", ready_path="/_xsm/ready")`

An `InitPluginProtocol` + `OpenAPISchemaPluginProtocol`. On app init it appends `registry.lifespan` to the app's lifespan, mounts the health/ready probes (pass `None` to skip), maps every `XStateMachineError` escaping a handler to a problem response (a save conflict → 409) and, with `dependencies=True`, registers one app-level dependency per machine named `{dependency_prefix}{name}`.

### `get_interpreter(registry, name, *, key="id", create_if_missing=True) -> Provide`

Yields a started interpreter inside `registry.act()` — saved with `expected_version` when the handler returns, discarded when it raises. Runs `authorize` with `event=None`; the idempotency principal is the registry's `principal(conn)`. *key* is a path-parameter name or `(request) -> str`.

### Re-exports

`StatechartRegistry`, `allow_all`, `receipt_to_status`, `problem`, `problem_for_exception` — the same objects as in `xstate_statemachine.contrib.starlette`. `ReceiptResponse(interp, receipt, *, context_serializer=None, status=None)` is **Litestar-native** (same body and status mapping as Starlette's).

## Guarantees

> **What this does:** the same multi-worker model as [Starlette](../integration-starlette/#guarantees): **create → act → persist → discard** with an optimistic version check — racing requests give one winner and a `409`, never a lost update (tested with 50 concurrent `POST /send` to one key on `SQLiteStore`). The OpenAPI document lists every declared event. SSE subscribers see one `transition` per committed changed receipt. The registry's lifespan (timer scanner, resident drain) runs under Litestar's.
>
> **What this does not do:** SSE/WebSocket fan-out and residents are per-process. Nothing retries a `409` for you. The controller is generated from the chart at startup.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can reach the controller. `register(authorize=)` is **required** (X0.1) and runs on every route, per instance and per event; add Litestar guards on the controller for framework-native checks.
>
> **What it exposes:** `GET` returns state, state ids and available events — **not** `context` unless you pass a `context_serializer` (X0.1). Problems carry a fixed title and the exception class name; validation problems list field keys only, never input values (X0.7).
>
> **You must configure:** an `authorize=` callable, and a registry `principal=` derived from your authenticated identity when using `inbox=` — `Idempotency-Key` is scoped to it (X0.2). Bodies are JSON-only and size-capped. **CSRF:** with cookie authentication, add Litestar's `CSRFConfig` or `SameSite` cookies; a cross-site form cannot send `application/json` without a CORS preflight, but do not rely on that alone.

## Compatibility

| Litestar | Python | Tested in CI |
|:--|:--|:--|
| 2.0 – 2.x | 3.9 – 3.14 | ✅ |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[litestar]"` | extra not installed | run the command |
| `/send` body is `{type, payload}` | no `events_union()` models on the machine | pass `event_schemas=events_union(...)` or `event_models=` |
| OpenAPI shows `{root: ...}` for `/send` | `XStatePlugin` not registered | add `plugins=[XStatePlugin(registry)]` |
| `500` from a `Provide` route | returned Starlette's `ReceiptResponse` | import `ReceiptResponse` from `contrib.litestar` |
| `ImproperlyConfiguredException` naming an `/events/<EVENT>` path | your route and the controller's share it | `exclude_events=("<EVENT>",)` |
| `403` on `/send` for one event | the event is in `exclude_events` | send it on your dedicated route |
| OpenAPI `examples` differ per start | a msgspec `Struct` of your own in a response | `ResponseSpec(generate_examples=False)` or explicit `examples=` |
| SSE test hangs | `TestClient.stream` buffers | see [Testing streams](#testing-streams) |
| `LitestarDeprecationWarning: Inferred dependency field` | Litestar ≥ 2.18 on a `get_interpreter` parameter | annotate the parameter with `NamedDependency[Any]` on new Litestar |
