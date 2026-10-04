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

With SQLite, create the schema **once** before starting the workers, for example with an `init` step or your migration job. Switching an empty file to WAL mode is a write, and N processes racing to do it see `database is locked`.

**Optimistic vs pessimistic under load.** The default `OptimisticLock` takes no lock. The second writer's save fails its version check, and the API answers `409`. Nothing retries a `409` for you, because the client decides whether to retry. This is the right choice when conflicts on one key are rare, which is the usual case with one order per customer. When one key is hot and every request should be *applied* in turn rather than refused, use `StatechartRegistry(store, lock=PessimisticLock())`: requests to that key queue on the store's lock instead of failing. Measured in the example, 200 concurrent `PAY`s to one order under four workers produce **exactly one** changed receipt and 54 `409`s without a key. With a shared `Idempotency-Key` the result is still one changed receipt, and the replays come back as duplicates.

**Timers run in exactly one process.** `after` deadlines are saved with the snapshot. A `DueTimerScanner` wakes the orders whose deadlines have passed. Do **not** pass `run_timers=True` to a registry that runs in every web worker, because each worker would scan the same keys. Run the scanner in its own process instead:

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

The scanner re-checks each deadline under the lock strategy and saves with the version check, so a second scanner would not fire a timer twice. It would only waste work and produce conflicts.

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

# PAY is refused on /send (403), so the email hook cannot be bypassed
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

## Sessions & wizards

A multi-step form (shipping → payment → review) is a chart with one instance per *visitor*. Take the instance key from a session cookie rather than a path parameter, and let `authorize` compare the two:

<!-- doc-fragment -->
```python
def wizard_key(request: Request) -> str:
    return request.cookies["session"]            # set by your session middleware

@app.post("/checkout/next")
async def next_step(wizard=get_interpreter(registry, "checkout", key=wizard_key)):
    return ReceiptResponse(wizard, await wizard.send("NEXT", wait=True))
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

Drive timers with `DueTimerScanner(store, ...).scan(now=time.time() + 901)`, which passes an explicit `now`, instead of sleeping. Ready-made pytest fixtures arrive with the `[testing]` extra ([#268](https://github.com/basiltt/xstate-statemachine/issues/268)).

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
| `GET /{id}/diagram.mmd` | — | Mermaid, `text/plain` (omit with `include_diagram=False`) |
| `GET /{id}/stream` | — | SSE, via [`transition_stream`](../integration-starlette/#reference) |
| `WS /{id}/ws` | — | [`websocket_endpoint`](../integration-starlette/#reference) protocol |

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
| Every POST is `409` under load | optimistic conflicts on a hot key | retry on 409, or `lock=PessimisticLock()` |
| A `get_interpreter` save conflict is logged, response already 200 | FastAPI older than 0.121 (no dependency `scope`) | upgrade FastAPI, or use `registry.act()` inside the handler |

### 409 storms

A burst of `409 Conflict` responses on one key means many requests loaded the same version and only one could save. This is the lock working as designed, not a fault. Things to check:

* **Clients retrying immediately.** Each retry lands in the same race again. Retry with jittered backoff, and send an `Idempotency-Key` so a retry of a request that actually succeeded returns the original receipt (`duplicate`) instead of running again.
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
* **Multiple workers:** SSE fan-out is per process. A client connected to worker A does not see a change committed on worker B. Use sticky sessions, or reconnect and read the `snapshot` event. `EventSource` reconnects automatically.

### Cookie authentication and CSRF

`EventSource` cannot send an `Authorization` header, so SSE pages usually authenticate with a cookie. Set that cookie `SameSite=Lax` or `SameSite=Strict`, and `HttpOnly`. The POST routes accept only `application/json`, which a cross-site HTML form cannot send without a CORS preflight. Still keep CORS origins explicit (never `*` with credentials) and add a CSRF token for cookie-authenticated writes. The SSE and WebSocket endpoints check that `Origin` is same-origin; use `allowed_origins=` for the exceptions.
