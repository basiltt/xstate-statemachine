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

For a complete, runnable service — Docker Compose with four workers, a scheduler and Redis, a load test, SSE and a test suite — see the [`fastapi_orders` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/fastapi_orders).

## Multi-worker deployments

**Why an interpreter cannot live in a worker.** `uvicorn --workers 4` starts four processes that share no memory, and a load balancer may send each request for order 7 to a different one. If worker A kept order 7's interpreter in memory, worker B would hold a second copy, and the two copies would diverge. Keeping the object in memory does not work here, so the registry never does it: each request runs **create → act → persist → discard**. It loads the snapshot, runs one `Interpreter`, saves with the version it loaded, and drops the interpreter. The store is the only place where the order's state lives. ([`resident()`](../integration-starlette/) is the opt-in exception for one process in development.)

**Choosing the store.**

| Deployment | Store | Idempotency inbox |
|:--|:--|:--|
| One host, any number of workers | `SQLiteStore(path)` — WAL, one file | `SQLiteInbox(store)` — shares the connection, so a mark commits with the snapshot |
| Several hosts | `RedisStore(url, prefix=...)` ([#306](../persistence/)) | `RedisInbox(url, prefix=...)` |
| An existing SQL database | `SQLAlchemyStore` ([SQLAlchemy](../integration-sqlalchemy/)) | — see that guide |

The `fastapi_orders` example's `build_store()` supports only the first two rows: SQLite by default, Redis when `XSM_REDIS_URL` is set. Its Docker Compose file uses a real Redis; the example's Redis tests use `fakeredis` unless you point `XSM_REDIS_URL` at a live server. `SQLAlchemyStore` works with the same registry but is not wired into the example.

With SQLite, create the schema **once** before starting the workers, for example with an `init` step or your migration job. Switching an empty file to WAL mode is a write, and N processes racing to do it see `database is locked`.

**Optimistic vs pessimistic under load.** The default `OptimisticLock` takes no lock, and it is what the `fastapi_orders` example uses (`build_registry()` passes no `lock=`). The second writer's save fails its version check, and the API answers `409`. Nothing retries a `409` for you, because the client decides whether to retry. This is the right choice when conflicts on one key are rare, which is the usual case with one order per customer. When one key is hot and every request should be *applied* in turn rather than refused, use `StatechartRegistry(store, lock=PessimisticLock())`: requests to that key queue on the store's lock instead of failing. In the example's load test, 200 concurrent `PAY`s to one order under four workers produce **exactly one** changed receipt, with or without a shared `Idempotency-Key`. That is the invariant. How many of the other 199 come back as `409` rather than `200 unchanged` / `duplicate` depends on timing and hardware: on one Windows 11 laptop it was 0 in 11 runs at 1, 2 and 4 workers, while earlier runs on the same machine saw dozens. Treat it as a measured range, not a constant. The [example README](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/fastapi_orders#load-test) has the numbers, and `python loadtest.py --json` regenerates them.

**Timers run in exactly one process.** `after` deadlines are saved with the snapshot. A `DueTimerScanner` wakes the orders whose deadlines have passed. Web workers **never** fire a timer: a registry runs a scanner only with `run_timers=True`, and the example's web workers do not pass it. Its fleet test runs real worker processes without a scheduler and no deadline fires. Do **not** pass `run_timers=True` to a registry that runs in every web worker, because each worker would scan the same keys. Run the scanner in its own process instead:

<!-- doc-fragment -->
```python
# app.py -- `python app.py --role scheduler`, started exactly once
def run_scheduler(interval_s: float = 1.0) -> None:
    registry = build_registry()          # same store, same machines
    scanner = DueTimerScanner(
        registry.store, registry.machine_for_store_key,
        lock=registry.lock, prefix="order.",
    )
    scanner.run_forever(interval_s)      # stop() from a signal handler
```

The contract is **exactly one** scheduler. Two by accident are safe but wasteful: the scanner re-checks each deadline under the lock strategy and saves with the version check, so each deadline fires once, and the second scheduler only wastes scans and produces conflicts. In Docker Compose, give the scheduler service `deploy: replicas: 1` and never scale it.

## Side effects

**Actions must be fast and idempotent.** An action runs *inside* `act()`, before the save. If the save then loses a race (`409`), the action has already run, but its result is discarded. So an action should only change `context`. Never send an email or charge a card from an action.

**Prefer `invoke` + `onError` for anything that can fail.** A payment gateway is a *service*. Its failure becomes an `error.platform` event that the chart models, for example `onError → retrying → after(retryDelay) → paying` with [`RetryPolicy`](../patterns/), and the scanner wakes the retry. The failure is then part of the state you can see in the API, not an exception in a log.

**Use `BackgroundTasks` for work that should run *after* the response.** Schedule it only when the receipt shows a committed, first-time change:

<!-- doc-requires: fastapi, httpx -->
```python
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.testclient import TestClient

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.fastapi import (
    StatechartRegistry, StatechartRouter, allow_all, instrument_app,
)
from xstate_statemachine.contrib.pydantic import EventModel, events_union
from xstate_statemachine.persistence import MemoryInbox, MemoryStore

class Pay(EventModel):
    type: Literal["PAY"] = "PAY"

order = create_machine(
    {"id": "order", "initial": "open",
     "states": {"open": {"on": {"PAY": "paid"}}, "paid": {}}},
    event_schemas=events_union(Pay),
)
registry = StatechartRegistry(MemoryStore(), inbox=MemoryInbox(),
                              principal=lambda conn: "ann")
registry.register("order", order, authorize=allow_all)
sent = []

app = FastAPI()

@app.post("/orders/{id}/events/PAY")          # registered first: shadows the router's
async def pay(id: str, request: Request, background: BackgroundTasks):
    response = await registry.send_event(request, "order", id, "PAY", {})
    if response.status_code == 200:
        import json
        body = json.loads(response.body)
        if body["changed"] and not body["duplicate"] and body["error"] is None:
            background.add_task(sent.append, id)   # after the response, once
    return response

# PAY is refused on /send (403); in a real service ALSO gate it in
# `authorize` (see "Request rules") so another router cannot bypass it
app.include_router(StatechartRouter(registry, "order", prefix="/orders",
                                    per_event_dependencies={"PAY": []}))
instrument_app(app, registry)

with TestClient(app) as client:
    key = {"Idempotency-Key": "p1"}
    assert client.post("/orders/1/events/PAY", headers=key).json()["changed"]
    again = client.post("/orders/1/events/PAY", headers=key).json()
    assert again["duplicate"] is True
    assert client.post("/orders/1/send", json={"type": "PAY"}).status_code == 403
assert sent == ["1"]
```

`send_event` returns only after the save has committed. A `409`, a guard denial or an `Idempotency-Key` replay therefore never schedules the task. `BackgroundTasks` still runs *in the web worker*, and a crash after the response loses the task. When the side effect must happen, write it to an **outbox** in the same transaction and deliver it from a separate process. See the event-driven architecture guide (arriving with the Phase F integrations).

## Request rules

**`get_interpreter` persistence.** The interpreter lives inside `registry.act()` for the request. It is **saved** when the handler *returns*, **discarded** (nothing saved) when the handler *raises*, and **stopped** once the response is produced. A `BackgroundTasks` closure that captured it acts on a dead interpreter — the task must open its own `async with registry.act(name, key) as interp:`.

**Idempotency.** An `Idempotency-Key` header needs a registry built with `inbox=`. Without one the request is refused with `501` (`IdempotencyNotConfiguredError`) — never silently ignored; a malformed key is `400`. `get_interpreter` validates the header too and hands it to `act(idempotency_key=)`, which stamps it on your handler's **first** `send` -- the replay is deduped with no handler code. A handler that sends more than once and wants to choose which send carries the key reads `request.state.xsm_idempotency_key` and passes `idempotency_key=` itself.

**Gate sensitive events on `authorize`, not only on a router.** `per_event_dependencies` guards *that router's* `/events/EVENT` route. A second router on another prefix (an admin API), the WebSocket route or a custom route does not inherit it. Put the real rule in `register(authorize=)` — it sees every send with the event type, including WebSocket frames (refused with close code `1008`). The orders example marks the one allowed route on `request.state` and lets `authorize` check the mark.

**`GET /{id}/events` runs your guards.** `available` is computed with `can()`, which evaluates guards against the live context on every GET. Guards must therefore be pure: no counters, no I/O. A guard that raises is logged and its event is simply absent from `available`.

## OpenAPI

The document is generated from the chart, so it is deterministic for a given chart and model set.

* **operationIds** — `<prefix>_get`, `<prefix>_send`, `<prefix>_events`, `<prefix>_diagram`, `<prefix>_stream`, and `<prefix>_<event>` for each event route. Event names are folded to ASCII `[a-z0-9_]` (`ORDER.PAID` → `order_paid`, `éclair` → `eclair`); when two names fold to the same id, or an event is called `GET`/`send`, the later one (in sorted order) gets `_2`, `_3`, … so every id is unique.
* **`/send` body** — one model: that model; two or more: a `oneOf` with `discriminator: type`; none: `<Name>Event` = `{type: Literal[...], payload: {}}`. Field aliases are honoured on every send path; note that actions then read an aliased field under its **alias** in `event.payload` (the body's key), not the Python field name. Event-route `operationId`s are stable when you add an event later: names that are already plain identifiers (`ORDER_PAID`) keep the unsuffixed id; a name that had to be folded (`ORDER.PAID`, `pay-now`) takes `_2` only when the plain id is taken.
* **Statuses** — every route documents its failures as `application/problem+json` with the `Problem` schema: `400 401 403 404 409 413 415 422 500 501 503` on sends, `400 401 403 404 500 503` on reads, `429` on `/stream`.
* **Schemas are public.** `/events` and `/openapi.json` publish each model's JSON Schema, *including field defaults* — never put a secret in an `EventModel` default.
* **Golden.** The library pins the AdvancePayment router's document in `tests/contrib/fastapi/openapi_golden.json`; after an intended change run `XSM_UPDATE_GOLDEN=1 pytest tests/contrib/fastapi -k golden` and review the diff. Do the same in your service: commit `app.openapi()` and compare it in a test.

## Sessions & wizards

A multi-step form (shipping → payment → review) is a chart with one instance per *visitor*. Take the instance key from a session cookie rather than a path parameter, and let `authorize` compare the two:

<!-- doc-requires: fastapi, httpx -->
```python
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.fastapi import (
    ReceiptResponse, StatechartRegistry, allow_all, get_interpreter,
    instrument_app,
)
from xstate_statemachine.persistence import MemoryStore

registry = StatechartRegistry(MemoryStore(),
                              principal=lambda conn: conn.cookies["session"])
registry.register("checkout", create_machine(
    {"id": "checkout", "initial": "shipping", "states": {
        "shipping": {"on": {"NEXT": "payment"}},
        "payment": {"on": {"NEXT": "review"}}, "review": {}}}),
    authorize=allow_all)
app = instrument_app(FastAPI(), registry)

def wizard_key(request: Request) -> str:
    return request.cookies["session"]            # set by your session middleware

@app.post("/checkout/next")
async def next_step(wizard=get_interpreter(registry, "checkout", key=wizard_key)):
    return ReceiptResponse(wizard, await wizard.send("NEXT", wait=True))

with TestClient(app) as ann, TestClient(app) as bob:
    ann.cookies.set("session", "s-ann")
    bob.cookies.set("session", "s-bob")
    ann.post("/checkout/next")
    assert ann.post("/checkout/next").json()["state"] == "review"
    assert bob.post("/checkout/next").json()["state"] == "payment"
```

The key never appears in the URL, so one visitor cannot drive another visitor's wizard by editing a path. Use a session id that you signed or that is stored server-side, not a raw user id. Expired wizards stay in the store until you delete them. Give the store a `ttl_s=` (Redis), or delete finished keys in a scheduled job.

## Testing

Use `fastapi.testclient.TestClient` for request-by-request tests. Use `httpx.ASGITransport` with `asyncio.gather` for concurrency tests. Both run in-process with no server:

<!-- doc-requires: fastapi, httpx -->
```python
import asyncio

import httpx
from fastapi import FastAPI

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.fastapi import (
    StatechartRegistry, StatechartRouter, allow_all, instrument_app,
)
from xstate_statemachine.persistence import MemoryStore

registry = StatechartRegistry(MemoryStore())
registry.register("t", create_machine(
    {"id": "t", "initial": "a", "states": {"a": {"on": {"GO": "b"}}, "b": {}}}),
    authorize=allow_all)
app = instrument_app(FastAPI(), registry)
app.include_router(StatechartRouter(registry, "t"))

async def race():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        return await asyncio.gather(
            *(c.post("/t/k/send", json={"type": "GO", "payload": {}})
              for _ in range(20)))

results = asyncio.run(race())
winners = [r for r in results if r.status_code == 200 and r.json()["changed"]]
assert len(winners) == 1                         # the rest: 409 or unchanged
```

Drive timers with `DueTimerScanner(store, ...).scan(now=time.time() + 901)`, which passes an explicit `now`, instead of sleeping. The `[testing]` extra's pytest plugin ([#268](https://github.com/basiltt/xstate-statemachine/issues/268)) provides machine-level fixtures (`xsm_machine`, `xsm_interp`, `xsm_store`, `xsm_clock`, …). It has no `TestClient` fixture, so build the client yourself as above; the example's `tests/test_orders_app.py` wraps one in a fixture over a per-test SQLite file.

### Generate a router you own

`StatechartRouter` builds the API at runtime. When you would rather check in an editable router (custom auth, extra routes), generate one:

```bash
xsm gt order.json -t pydantic-models --with-api -o app/
```

This writes `order_models.py` (one `EventModel` per event) and `order_api.py`: an `APIRouter` with `GET /{id}` and one typed `POST /{id}/events/<EVENT>` per event, through `get_interpreter` and `ReceiptResponse`. Its `authorize` stub raises `NotImplementedError` until you implement it, so nothing is served before you decide who may do what (X0.1). `xsm gt ... --check` in CI reports drift when the chart changes. See [CLI templates](../cli-templates/#companion-templates).

## Reference

### `StatechartRouter(registry, name, *, prefix=None, tags=None, key_param="id", event_models=None, include_diagram=True, create_if_missing=True, operation_id_prefix=None, dependencies=(), per_event_dependencies=None, actor=None) -> APIRouter`

Returns an `APIRouter` for machine *name* (already registered on *registry*). `prefix` defaults to `/<name>`; `{id}` below is `key_param`.

| Route | Body | Response |
|:--|:--|:--|
| `GET /{id}` | — | `{state, state_ids, available_events, machine_version}` (+ `context` only with a `context_serializer`) |
| `POST /{id}/send` | discriminated union of the event models on `type` | receipt: 200 changed/unchanged/duplicate, 202 deferred, 409 guard denied or conflict, 422 invalid |
| `POST /{id}/events/<EVENT>` | that event's model, optional | same as `/send` — one route per declared event |
| `GET /{id}/events` | — | `{available: [...], declared: [{type, schema}]}` — `available` is what `can()` accepts now |
| `GET /{id}/diagram.mmd` | — | Mermaid, `text/plain` (omit with `include_diagram=False`); runs `authorize` |
| `GET /{id}/stream` | — | SSE, via [`transition_stream`](../integration-starlette/#reference) |
| `WS /{id}/ws` | — | [`websocket_endpoint`](../integration-starlette/#reference) protocol |

📝 **Not generated (deferred from #276):** `GET /{id}/history` needs a transition-log store wired into the registry, which `StatechartRegistry` does not take yet; the chart-level `/schema/diagram.mmd`, `/schema/machine.json`, `/schema/events.json` routes are replaced by the per-instance `/{id}/diagram.mmd` and `/{id}/events` plus `/openapi.json`. Use [`machine_json_schema`](../integration-pydantic/) in your own route if you need the events schema without an instance.

* **`event_models`** — `EventModel` subclasses. Defaults to the models behind the machine's `events_union()` schemas. Without any, the `/send` body is `{type: Literal[<declared events>], payload: {...}}`, so the schema is still deterministic.
* **`create_if_missing=False`** — reads and sends on an unknown key are `404` instead of starting a new instance.
* **`dependencies`** — FastAPI dependencies on every route (your auth). **`per_event_dependencies={EVENT: [Depends(...)]}`** adds dependencies to that event's `/events/EVENT` route; such an event is refused on `/send` (403) so the extra check cannot be bypassed.
* **`actor`** — a dependency returning the authenticated principal, which scopes `Idempotency-Key`. Defaults to the registry's `principal(conn)`. The principal never comes from the body.
* **`operation_id_prefix`** — operation ids are `<prefix>_get`, `<prefix>_send`, `<prefix>_<event>`, `<prefix>_events`, `<prefix>_diagram`, `<prefix>_stream` (prefix defaults to *name*).

Both POSTs delegate to `registry.send_event`: authorize (with the event type) → `Idempotency-Key` → `act()` → receipt. Bodies must be `application/json` (415) and at most `max_body_bytes` (413); request validation failures are `422` problems listing each error's `loc` and `type` only.

A route you add **beside** the router (a custom `PAY` with `BackgroundTasks`) is outside that envelope unless it uses the same route class: `APIRouter(route_class=bounded_route_class(registry))`. Without it FastAPI parses a 1 MB body and answers `422` rather than `413`, and accepts a `text/plain` body.

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
| `501` with `error: IdempotencyNotConfiguredError` | `Idempotency-Key` sent, registry has no `inbox=` | pass `inbox=SQLiteInbox(store)` (or drop the header) |
| Background task fails with `InterpreterStoppedError` | it used the `get_interpreter` interpreter after the response | open `registry.act()` inside the task |
| Event reachable through another router despite `per_event_dependencies` | the gate is per router | enforce it in `authorize` |
| `UserWarning: Duplicate Operation ID` on an older release | two event names folded to the same id | upgrade; ids are now suffixed `_2`, `_3` |
| A guard's side effect fires on `GET /{id}/events` | `available` runs guards | keep guards pure |
| Every POST is `409` under load | optimistic conflicts on a hot key | retry on 409 with jitter (below), or `lock=PessimisticLock()` |
| One request in a burst stalls for the whole client timeout under `uvicorn --workers N` **on Windows**, p95 is normal | uvicorn's shared listening socket: a worker's loop freezes inside `accept()` until the *next* connection arrives (reproduced with a do-nothing ASGI app, 7 of 25 fleets; never with one process). Not the library, SQLite or the lock -- no server-side timeout can bound it, the worker runs no code | multi-worker on Linux / Docker; on Windows run N single-worker processes on separate ports behind a proxy |
| A client sends headers then stalls; a handler waits forever for the body | no body read timeout | `StatechartRegistry(body_timeout_s=30)` (the example: `XSM_BODY_TIMEOUT_S`) → `408` `RequestTimeoutError` |
| `database is locked` at startup without `--role init`; a worker silently keeps rollback-journal mode | N workers racing an empty SQLite file to switch it to WAL -- the loser's lock error is instant (SQLite's busy handler does not wait for it) | fixed in 0.11.0: `SQLiteStore` retries the switch for `busy_timeout` and re-reads the mode another process set; `--role init` is still the recommended one-time step |
| A `get_interpreter` save conflict is logged, response already 200 | FastAPI older than 0.121 (no dependency `scope`) | upgrade FastAPI, or use `registry.act()` inside the handler |

### 409 storms

A burst of `409 Conflict` responses on one key means many requests loaded the same version and only one could save. This is the lock working as designed, not a fault. Things to check:

* **Clients retrying immediately.** Each retry lands in the same race again. Retry with jittered backoff, and send an `Idempotency-Key` so a retry of a request that actually succeeded returns the original receipt (`duplicate`) instead of running again:

<!-- doc-requires: httpx -->
```python
import asyncio
import random

import httpx

from xstate_statemachine import __version__  # noqa: F401 (client: httpx only)

async def post_with_retry(client, url, json, *, key, attempts=5, base_s=0.05):
    """Retry 409s with full jitter; the same Idempotency-Key every time."""
    for attempt in range(attempts):
        r = await client.post(url, json=json, headers={"Idempotency-Key": key})
        if r.status_code != 409:
            return r
        await asyncio.sleep(random.uniform(0, base_s * 2 ** attempt))
    return r

calls = []

def handler(request):                            # stands in for the API
    calls.append(request.headers["Idempotency-Key"])
    return httpx.Response(409 if len(calls) < 3 else 200, json={})

async def main():
    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
        r = await post_with_retry(c, "/orders/1/events/PAY", {}, key="pay-1")
    assert r.status_code == 200 and calls == ["pay-1"] * 3

asyncio.run(main())
```

* **`409` with `error: IdempotencyInFlightError`.** The same key is still being processed by another worker. Retry after a short delay. It is a different condition from a version conflict (`ConflictError`).
* **A key that is always hot**, such as a shared counter or a flash-sale inventory item. Use `lock=PessimisticLock()` so requests queue instead of failing, or split the key.

### `409`/`500` with `MachineVersionMismatchError` after a deploy

The new code ships a chart with a new `"version"`, and the snapshots saved by the old version no longer match it. The problem body carries `machine_version`, the version the running code expects. Register a migration and pass it to the registry:

<!-- doc-fragment -->
```python
migrator = SnapshotMigrator()
@migrator.register("1", "2")
def split_address(snapshot):
    ...
registry = StatechartRegistry(store, migrator=migrator)   # also used by the scanner
```

During a rolling deploy, old and new workers serve the same keys. Make the new chart able to read old snapshots *before* you deploy it. See [Versioning in-flight instances](../persistence/#versioning-in-flight-instances).

### SSE stops or arrives in bursts behind a proxy

Buffering proxies hold the stream back. `transition_stream` already sends `X-Accel-Buffering: no` (for nginx) and `Cache-Control: no-store`, but check the following:

* **nginx:** `proxy_buffering off;` if your config overrides the header, and `proxy_read_timeout` above `registry.heartbeat_s` (default 15 s).
* **Load balancers** with an idle timeout shorter than the heartbeat close the stream. Lower `heartbeat_s`.
* **Compression** (for example `GZipMiddleware`) buffers the stream. Exclude `text/event-stream`.
* **Wire format** (frames, reconnect, close codes): see [Starlette → Wire contract](../integration-starlette/#wire-contract). Reconnect gives a fresh `snapshot`; nothing is replayed from `Last-Event-ID`.
* **Multiple workers:** SSE fan-out is per process. A client connected to worker A does not see a change committed on worker B. Use sticky sessions, or reconnect and read the `snapshot` event. `EventSource` reconnects automatically.

### Cookie authentication and CSRF

`EventSource` cannot send an `Authorization` header, so SSE pages usually authenticate with a cookie. Set that cookie `SameSite=Lax` or `SameSite=Strict`, and `HttpOnly`. The POST routes accept only `application/json`, which a cross-site HTML form cannot send without a CORS preflight. Still keep CORS origins explicit (never `*` with credentials) and add a CSRF token for cookie-authenticated writes. The SSE and WebSocket endpoints check that `Origin` is same-origin; use `allowed_origins=` for the exceptions.
