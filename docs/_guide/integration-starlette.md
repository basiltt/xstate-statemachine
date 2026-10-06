---
title: "Starlette integration"
description: "A store-backed statechart registry for Starlette (and everything built on it): Receipt → HTTP status, Idempotency-Key, SSE and WebSocket transition streams, timers under lifespan."
---

# Starlette

A web app that drives a statechart has to answer the same questions every time: where does the instance live between requests, how does "the guard refused" become an HTTP status, what happens when a client retries a POST, and how does a browser hear about a transition another request made? The `[starlette]` extra answers all four once, framework-neutrally — FastAPI and Litestar integrations reuse it. Each request loads the snapshot, runs one async `Interpreter`, saves with an optimistic version check and discards it (**create → act → persist → discard**), which is the only model that is honest under several workers.

## Install

```bash
pip install "xstate-statemachine[starlette]"
```

Requires Starlette `>=0.27`. Tested versions are in the [compatibility table](#compatibility). The tests (and the sample below) also use `httpx`, which `starlette.testclient` needs.

## Quick start

<!-- doc-requires: starlette, httpx -->
```python
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.starlette import StatechartRegistry
from xstate_statemachine.persistence import MemoryStore

machine = create_machine({
    "id": "door", "initial": "closed",
    "states": {"closed": {"on": {"OPEN": "open"}},
               "open": {"on": {"CLOSE": "closed"}}},
})

def authorize(request, *, name, key, event):
    return request.headers.get("x-user") is not None   # your auth here

registry = StatechartRegistry(MemoryStore())
registry.register("door", machine, authorize=authorize, strict=True)

async def send(request):
    p = request.path_params
    return await registry.send_event(request, "door", p["id"], p["event"])

app = Starlette(
    routes=[Route("/doors/{id}/events/{event}", send, methods=["POST"]),
            registry.health_route(), registry.ready_route()],
    lifespan=registry.lifespan,
)

with TestClient(app) as client:
    ok = client.post("/doors/1/events/OPEN", headers={"x-user": "ann"})
    assert ok.status_code == 200 and ok.json()["state"] == "open"
    assert client.post("/doors/1/events/OPEN").status_code == 403
    typo = client.post("/doors/1/events/OPNE", headers={"x-user": "ann"})
    assert typo.status_code == 422     # strict: undeclared event
    assert client.get("/_xsm/ready").json()["status"] == "ready"
```

For full control, use `act()` directly — it is an async context manager yielding a started interpreter:

<!-- doc-fragment -->
```python
async def submit(request):
    await registry.authorize(request, "payment", request.path_params["id"], "SUBMIT")
    async with registry.act("payment", request.path_params["id"]) as interp:
        return ReceiptResponse(interp, await interp.send("SUBMIT", wait=True))
```

## Reference

### `StatechartRegistry(store, *, lock=None, clock=None, plugins=(), migrator=None, inbox=None, principal=None, max_residents=1000, resident_idle_ttl_s=300.0, max_connections_per_key=16, drain_timeout_s=10.0, run_timers=False, scanner_interval_s=1.0, scanner_now=None, heartbeat_s=15.0, allowed_origins=(), max_body_bytes=None)`

Named machines over one store. *store* is a sync `StateStore` (wrapped with `as_async()` so the event loop never blocks) or an `AsyncStateStore`. An instance lives under the store key `"<name>.<key>"`. `inbox=` enables principal-scoped idempotency; `principal=(conn) -> str` names the authenticated caller for the HTTP/WS helpers. `run_timers=True` needs a **sync** store (the scanner runs in a thread).

### `register(name, machine, *, authorize, context_serializer=None, strict=None)`

`authorize(conn, *, name, key, event) -> bool | Awaitable[bool]` is **required**; `event` is `None` for reads and stream connects, and the event type for sends — so authorization is per object **and** per event. `context_serializer=(context) -> JSON` opts into `context` in responses; without it responses carry state only. `strict=True` turns an undeclared event into 422 instead of 200-unchanged. Raises `TypeError` without a callable `authorize`, `ValueError` for a duplicate name or one containing `.`.

### `allow_all`

An authorizer that admits everything and logs one `WARNING` the first time it is used. For demos and tests.

### `async with registry.act(name, key, *, principal=None) as interp`

Builds an async `Interpreter` via `persistence.apersisted` over `as_async(store)` with the registry's plugins (plus an `IdempotencyPlugin` when `inbox=` was given — `principal=` is then required), yields it started, and saves with `expected_version` on exit. A lost race raises `ConflictError` (→ 409; the client retries). After the save commits, each **changed** receipt is published to this process's SSE/WebSocket subscribers.

### `await registry.send_event(request, name, key, event_type, payload=None)`

The one-call route body: authorize → `json_body()` (unless *payload* is given) → copy `Idempotency-Key` into `payload["idempotency_key"]` → `act()` → `send(wait=True)` → `ReceiptResponse`. Every failure becomes an RFC 9457 problem; it never raises for request-level errors.

### `await registry.resident(name, key)` / `release_resident(name, key)` / `residents` / `evict_idle()`

An opt-in long-lived in-process actor. Loaded from the store on first use, LRU-evicted beyond `max_residents`, evicted after `resident_idle_ttl_s` of idleness, and saved + stopped on eviction, release and shutdown. Single-process only.

### `registry.lifespan`

`Starlette(lifespan=registry.lifespan)`. Startup: starts `DueTimerScanner` in a daemon thread when `run_timers=True`. Shutdown: refuses new streams, closes subscribers, saves and stops residents and stops the scanner, all bounded by `drain_timeout_s`.

### `health_route(path="/_xsm/health")` / `ready_route(path="/_xsm/ready")`

Liveness is always 200. Readiness is 200 once `lifespan` has started, the store's `health()` reports ok and the registry is not draining; otherwise a 503 problem.

### `receipt_to_status(receipt, *, changed=200, unchanged=200, denied=409, deferred=202, duplicate=200, error=500)`

| Receipt | Status |
|:--|:--|
| `error` is `IdempotencyMismatchError` (same key, different body) | 422 |
| `error` is `IdempotencyInFlightError` (first delivery still running) | 409 |
| `duplicate=True` | `duplicate` (200) |
| `error` is `InterpreterStoppedError` (the instance already finished or was stopped) | `denied` (409) — refused, like a guard |
| `error` set | `error` (500) |
| `deferred=True` | `deferred` (202) |
| `denied=True` (a guard refused) | `denied` (409) |
| `changed` / not | `changed` / `unchanged` (200) |

### `ReceiptResponse(interp, receipt, *, context_serializer=None, status=None)`

A `JSONResponse` with `{state, state_ids, changed, denied, deferred, duplicate, available_events, error}` (+ `context` only with a serializer). `error` is the exception **class name**, never its message.

### `problem(status, title, detail=None, **ext)` / `problem_for_exception(exc)` / `status_for_exception(exc)`

RFC 9457 `application/problem+json`. The exception mapping: `UnknownEventError`, `InvalidEventPayloadError`, `InvalidEventError`, `IdempotencyMismatchError` → 422; `SnapshotDriftError` / `MachineVersionMismatchError` → 409 with a `machine_version` hint; `ConflictError`, `LockTimeoutError`, `IdempotencyInFlightError` → 409; `KeyNotFoundError` → 404; `ForbiddenError` → 403; `UnsupportedMediaTypeError` → 415; `PayloadTooLargeError` → 413; `StoreUnavailableError` → **503** (the store's backend is down -- retryable, one WARNING line per request, #306 battle); anything else → 500. Problems carry a fixed title and `error` class name only.

### `HTTPProblemError(title=None)` / `BadRequestError`

`HTTPProblemError` is the base class (an `XStateMachineError`) for an error that already knows its HTTP `status` (default 400) and public `title`. `status_for_exception` returns its `status`, and `problem_for_exception` turns it into a problem document with that `title` and the `error` class name, so raising a subclass from your own code yields the answer you chose. The library raises subclasses internally (`ForbiddenError` 403, `PayloadTooLargeError` 413, `UnsupportedMediaTypeError` 415, `UnprocessableBodyError` 422). `BadRequestError` is the 400 subclass (title `"Bad Request"`); the library itself does not raise it, so it is there for your handlers. Pass a string to override the title; keep it fixed, never put user data in it.

<!-- doc-fragment -->
```python
from xstate_statemachine.contrib.starlette import (
    BadRequestError,
    HTTPProblemError,
    problem_for_exception,
    status_for_exception,
)


class TeapotError(HTTPProblemError):
    status = 418
    title = "I'm a teapot"


assert status_for_exception(BadRequestError()) == 400
assert status_for_exception(TeapotError()) == 418
response = problem_for_exception(BadRequestError("Missing order id"))
assert response.status_code == 400
```

### `receipt_body(interp, receipt, *, context_serializer=None)`

The plain `dict` that `ReceiptResponse` serialises (the WebSocket endpoint reuses it for its `receipt` messages): the state body for `interp`, plus the sorted `state_ids` and the receipt's `changed`, `denied`, `deferred`, `duplicate` flags and `error`, which is the exception *class name* or `None`, never its text. Use it when you need the JSON shape without a `JSONResponse`, for example to embed the receipt in your own envelope. Unlike `ReceiptResponse` it does not fall back to the serializer given to `register`; pass `context_serializer` explicitly if you need one.

<!-- doc-fragment -->
```python
async with registry.act("order", key) as interp:
    receipt = await interp.send("PAY")
    body = receipt_body(interp, receipt)
return JSONResponse({"result": body}, status_code=receipt_to_status(receipt))
```
### `idempotency_key_from(conn)` / `await json_body(request, *, max_body_bytes=DEFAULT_MAX_SNAPSHOT_BYTES)`

The `Idempotency-Key` header or `None`. `json_body` requires `Content-Type: application/json` (415), caps the size (413, checked on `Content-Length` and while streaming), and requires a JSON object (422). An empty body is `{}`.

### `await transition_stream(registry, name, key, request)`

A `text/event-stream` response: `event: snapshot` on connect, then one `event: transition` per changed receipt committed in this process, `id:` a per-instance increasing sequence, and a `: heartbeat` comment every `heartbeat_s`. Refuses with 403 (Origin / authorize), 429 (`max_connections_per_key`) or 503 (server shutting down). The subscriber and its connection slot are released when the client disconnects — detected immediately, even while frames are flowing. See [Wire contract](#wire-contract).

### `websocket_endpoint(registry, name, *, key_param="key")`

Returns a `WebSocketEndpoint` subclass for `WebSocketRoute("/ws/{key}", ...)`. On connect sends `{"kind": "snapshot", ...}`; a client message `{"type": "EVENT", "payload": {...}}` is authorized, run through `act()`, and answered with `{"kind": "receipt", ...}` or `{"kind": "error", "status", "title", ...}`; committed transitions arrive as `{"kind": "transition", "seq": n, ...}`; `{"kind": "ping"}` every `heartbeat_s`. Close codes and frame shapes: see [Wire contract](#wire-contract). Holds no resident.

### `mount_inspector(app, registry, path="/_xsm/inspect", *, debug=False)`

Raises `RuntimeError` unless `debug=True`. Mounts the live inspector over WebSocket (`WebSocketSink`, one Stately Inspector protocol message per frame) and appends an `InspectorPlugin` to `registry.plugins`; token, loopback `Host` and `Origin` checks per X0.7. Keyword options `token`, `context_allowlist`, `include_payloads`, `allow_remote`; returns the sink. See [Live inspector](../integration-inspector/) ([#274](https://github.com/basiltt/xstate-statemachine/issues/274)).

## Wire contract

**SSE** (`transition_stream`):

| Frame | When | `id:` |
|:--|:--|:--|
| `event: snapshot` + `data: {state, state_ids, available_events[, context]}` | first frame of every connection | the current sequence (`0` if nobody was listening) |
| `event: transition` + `data:` the receipt body | each CHANGED receipt committed in **this process** — by a request *or* by the timer scanner | per-instance sequence, +1 per frame |
| `: heartbeat` (comment) | after `heartbeat_s` of silence | — |

**Reconnect = fresh snapshot, no replay.** No history is kept. A browser's `EventSource` sends `Last-Event-ID` on reconnect; the server ignores it and starts with a new `snapshot`, which already contains everything the missed frames would have told you. The sequence is forgotten when the last subscriber of an instance leaves, so do not compare `id:` values across connections. The stream ends (and the client reconnects) on shutdown, when the client falls `MAX_BACKLOG` (256) frames behind, and if a frame cannot be encoded as JSON (logged).

**WebSocket** (`websocket_endpoint`) — every frame is a JSON object with `kind`:

| Direction | Frame | Notes |
|:--|:--|:--|
| server → client | `{"kind": "snapshot", ...}` | once, after accept |
| client → server | `{"type": "EVENT", "payload": {...}}` | text or UTF-8 binary; `payload` optional |
| server → client | `{"kind": "receipt", ...}` | the answer to *your* event |
| server → client | `{"kind": "transition", "seq": n, ...}` | every committed change, yours included |
| server → client | `{"kind": "error", "status": 400}` | frame is not JSON — session stays open |
| server → client | `{"kind": "error", "status": 422, ...}` | not an object, `type` not a string, `payload` not an object, a reserved key (`wait`, `priority`) in `payload`, or an undeclared event under `strict` |
| server → client | `{"kind": "error", "status": 409/404/..., ...}` | the same problem body HTTP would return |
| server → client | `{"kind": "ping"}` | after `heartbeat_s` of silence |

Events from one socket are processed one at a time, in order.

| Close code | Meaning |
|:--|:--|
| 1001 | server shutting down (on connect or mid-session) — reconnect elsewhere |
| 1008 | `Origin` refused, or `authorize` refused on connect or for an event |
| 1009 | inbound frame larger than `max_body_bytes` |
| 1011 | internal error (connect failed, or a frame could not be encoded) — logged |
| 1013 | over `max_connections_per_key`, or cut for falling `MAX_BACKLOG` frames behind |

## Guarantees

> **What this does:** Multi-worker model is **create → act → persist → discard**: each request builds one async `Interpreter` from the stored snapshot and saves it with `expected_version`, so two workers racing on one key produce one winner and one `409` — never a lost update (tested with 50 concurrent requests on `MemoryStore` and `SQLiteStore`). Subscribers hear a transition only after its save commits. Persisted `after` deadlines fire under `lifespan` via `DueTimerScanner` when `run_timers=True`. Shutdown is bounded by `drain_timeout_s`; residents, connections per key and per-subscriber backlog are all capped.
>
> **Fan-out is PER PROCESS.** With `--workers 4`, a `POST` handled by worker 2 is invisible to a stream held open on worker 1 — it only shows up after that client reconnects and gets a fresh `snapshot`. Use one worker, sticky routing for both the stream and the writes, or a broker.
>
> **What this does not do:** Residents are **single-process** — two workers holding the same key as residents will conflict on save. SSE/WebSocket fan-out is **per-process**: a client only hears transitions made by the worker it is connected to; cross-worker fan-out needs a broker layer, which is out of scope here. `act()` does not retry a `ConflictError` for you.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can reach your routes. The registry authenticates nobody; your `authorize=` callable decides, per instance and per event, and it is **required** (closed by default, X0.1). `allow_all` is an explicit, logged opt-out.
>
> **What it exposes:** state value, active state ids and available events — **not** `context`, unless you pass a `context_serializer` (X0.1). Errors are RFC 9457 problems with a fixed title and the exception class name, never exception text (X0.7). `Idempotency-Key` is scoped to `principal / machine / instance`, so one tenant cannot replay another's receipt (X0.2 / X0.7 in [Security](../security/)); a reused key with a different body is 422, an in-flight key 409.
>
> **You must configure:** an `authorize=` callable; `principal=` derived from your authenticated identity (never the payload) when using `inbox=`; `allowed_origins=` for cross-origin SSE/WebSocket clients (otherwise only same-origin `Origin` vs `Host` is accepted). Bodies are JSON-only (415) and size-capped (413). **CSRF:** if you authenticate with cookies, a cross-site form cannot send `application/json` without a CORS preflight, but add a CSRF token or `SameSite` cookies anyway. `max_residents`, `resident_idle_ttl_s`, `max_connections_per_key` and `drain_timeout_s` bound resource use and shutdown time (X0.11 / X0.12 of the issue's review amendments).

## Compatibility

| Starlette | Python | Tested in CI |
|:--|:--|:--|
| 0.27 – 1.x | 3.9 – 3.14 | ✅ |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[starlette]"` | extra not installed | run the command |
| `TypeError: register(authorize=) is required` | no authorizer | pass a callable, or `allow_all` for demos |
| Every POST is `409` under load | optimistic conflicts on a hot key | retry on 409, or `lock=PessimisticLock()` |
| `ValueError: act(principal=) is required` | `inbox=` without a principal | pass `principal=` to the registry (HTTP helpers) or to `act()` |
| SSE client never sees transitions from other workers | fan-out is per-process | pin the stream to one worker, or add a broker |
| Stream shows a stale state after an `after` timer | the timer fired in a scanner in **another process** (or `run_timers=False`) — only the registry that owns the scanner pushes timer transitions | run the scanner in the web process (`run_timers=True`, single worker), or have clients re-read on a timer of their own |
| `429` on the stream | `max_connections_per_key` reached — tabs left open, or a client reconnecting in a loop | raise the cap; disconnected clients release their slot immediately |
| `503` on the stream / WebSocket close `1001` | the server is draining (shutdown) | reconnect; the balancer sends you to a live worker |
| A resident lost an update | residents are single-process; another writer saved first | see `registry.resident()` above — prefer `act()` per request |
| `409 Conflict` storms | optimistic retries on one hot key | retry with jitter, or `lock=PessimisticLock()` |
| `RuntimeError: run_timers=True needs a sync StateStore` | registry built on an `AsyncStateStore` | pass the sync store; the scanner runs in a thread |
