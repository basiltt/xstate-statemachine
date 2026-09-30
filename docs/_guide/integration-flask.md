---
title: "Flask integration"
description: "An init_app extension, a statechart blueprint, session-keyed wizards and a flask xsm CLI — plus a Quart shim — over any StateStore."
---

# Flask

Flask has a very large install base and no state-machine extension. This extra follows the canonical `init_app` pattern. You get an `XState` extension that keeps its state in `app.extensions`, so the application-factory pattern is safe. `act()` gives you *create → act → persist → discard* on any `StateStore`. There is a blueprint with the same route table as the FastAPI router, a cookie-backed `SessionStore` for small multi-step wizards, and `flask xsm` commands for the machines your app registers. Quart, Flask's async twin, is served by a shim built on the same core.

## Install

```bash
pip install "xstate-statemachine[flask]"
pip install quart          # optional: the Quart shim
```

Requires Flask `>=2.3`. Tested versions are in the [compatibility table](#compatibility).

For a complete, runnable app -- a multi-step wizard on `SessionStore`, CSRF-protected forms, the `flask xsm` CLI and a test suite -- see the [`flask_wizard` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/flask_wizard).

## Quick start

<!-- doc-requires: flask -->
```python
from flask import Flask, request
from xstate_statemachine import create_machine
from xstate_statemachine.contrib.flask import (
    XState, create_statechart_blueprint, receipt_response)
from xstate_statemachine.persistence import MemoryInbox, SQLiteStore

order = create_machine({"id": "order", "initial": "cart", "states": {
    "cart": {"on": {"CHECKOUT": "paying"}},
    "paying": {"on": {"PAY": "paid"}},
    "paid": {"type": "final"}}})

def can_touch(req, *, name, key, event):          # REQUIRED: who may read/drive what
    return req.headers.get("X-User") is not None

xsm = XState()
xsm.register("order", order, authorize=can_touch)

def create_app():
    app = Flask(__name__)
    xsm.init_app(app, store=SQLiteStore("app.db"), inbox=MemoryInbox(),
                 principal=lambda req: req.headers["X-User"])
    app.register_blueprint(create_statechart_blueprint(xsm, "order", "/orders"))

    @app.post("/orders/<oid>/quick-pay")           # your own view, same guarantees
    def quick_pay(oid):
        with xsm.act("order", oid) as o:
            o.send("CHECKOUT")
            return receipt_response(o, o.send("PAY", wait=True))
    return app

c = create_app().test_client()
h = {"X-User": "alice", "Idempotency-Key": "chk-1"}
assert c.post("/orders/42/send", json={"type": "CHECKOUT"}, headers=h).status_code == 200
assert c.post("/orders/42/send", json={"type": "CHECKOUT"}, headers=h).get_json()["duplicate"]
assert c.get("/orders/42", headers=h).get_json()["state"] == "paying"
assert c.get("/orders/42/send", headers=h).status_code == 405   # no state change via GET
assert c.post("/orders/42/send", json={"type": "CHECKOUT"}).status_code == 403
```

## Reference

### `XState(app=None)` and `init_app(app, store, *, lock=None, plugins=(), inbox=None, principal=None, log=None, max_body_bytes=1 MiB, heartbeat_s=15, max_connections_per_key=16, allowed_origins=(), cli=True)`

Binds a store and its policies to *app*. The state lives in `app.extensions["xstate"]`. Nothing is stored on the extension object, so two apps built from one `XState()` never share a store. `lock` is `OptimisticLock()` (the default) or `PessimisticLock()`. `inbox` together with `principal` enables principal-scoped `Idempotency-Key` deduplication (X0.2), and `principal` is **required** whenever `inbox` is set. `log` attaches an `AuditPlugin` and backs `GET /<id>/history`. With `cli=True`, `flask xsm` is registered. The extension also sets `g.xsm` on each request (`g.xsm.act(...)`, `g.xsm.peek(...)`).

### `register(name, machine, *, key=None, authorize=REQUIRED, context_serializer=None, strict=None, source=None, app=None)`

`machine` can be a `MachineNode`, a JSON path or a config dict. `authorize(request, *, name, key, event) -> bool` is **required** (X0.1). Its `event` argument is `None` for reads. Pass `allow_all` to opt out explicitly; it logs a warning the first time it is used. `key` is a `() -> str` used when a view calls `act(name)` without a key, typically read from the session. Responses include `context` **only** when a `context_serializer` is given. `source` is the machine's JSON, which `flask xsm` needs when `machine` is a `MachineNode`. `app=` registers the machine on one app only.

### `act(name, key=None, *, principal=None)`

A context manager that yields a started `SyncInterpreter` and saves on a clean exit. Nothing is written if the block raises. It is `persistence.persisted()` using the app's lock, plugins and inbox. Under the default optimistic lock, a concurrent writer causes `ConflictError` at exit (HTTP 409 in the blueprint). Retry, or configure `PessimisticLock`. `act()` **refuses to run inside a GET/HEAD/OPTIONS request** and raises `MethodNotAllowedError` (405).

### `receipt_response(interp, receipt, *, status=None, context_serializer=None)`

A JSON response whose status comes from the **core** table, `xstate_statemachine.receipts.receipt_to_status`: 200 for a transition or a no-op, 202 for deferred, 409 when a guard denies, 422 when an idempotency key is reused with a different body, 500 for an action error (class name only). An idempotency refusal comes back as an RFC 9457 problem. `problem_response(exc)` builds a problem for any exception, containing a fixed title and the class name, **never** `str(exc)`.

### `create_statechart_blueprint(xsm, name, url_prefix, *, per_event_routes=False, create_if_missing=True)`

| Route | Does |
|:--|:--|
| `GET /<id>` | state, state ids, available events (+ `context` via serializer) |
| `POST /<id>/send` | body `{"type": "EVENT", ...payload}` |
| `POST /<id>/events/<EVENT>` | body = payload; `per_event_routes=True` adds one named endpoint per declared event |
| `GET /<id>/events` | `available` now + every `declared` event |
| `GET /<id>/history` | the transition log (payloads omitted); 404 problem when no `log=` is configured |
| `GET /<id>/stream` | SSE: `snapshot`, then each committed `transition`; `?once=1` ends after the snapshot |
| `GET /schema/diagram.mmd` | Mermaid source |

Every route calls `authorize`. Write routes accept POST only, and a GET to them returns a 405 problem with `Allow: POST`. Bodies must be `application/json` (otherwise 415), within `max_body_bytes` (otherwise 413), and a JSON object (otherwise 422). The `Idempotency-Key` header is honoured, and a replay is **not** re-saved. `create_if_missing=False` makes an unknown id a 404.

⚠️ **SSE and threads:** a stream holds a worker for its whole lifetime. Flask's dev server and a sync gunicorn worker serve one request per thread or worker, so an open stream blocks that worker. Serve streams from a threaded or gevent worker, or use Quart. The fan-out is in-process: a transition committed by another process is not pushed.

### `SessionStore(*, max_snapshot_bytes=3 KiB, codec=None)` and `SessionStoreTooLargeError`

A `StateStore` over `flask.session`, which puts the snapshot in the **signed** cookie. It is meant for small wizard-style state that belongs to one browser. There is a hard cap on save and on load. The default is 3 KiB, which stays under the roughly 4 KiB browsers allow for a whole cookie. Going over it raises `SessionStoreTooLargeError`, a `SnapshotTooLargeError` whose message tells you to shrink the context or move to a server-side store.

```python
xsm.register("wizard", wizard_machine, authorize=allow_all,
             key=lambda: session.setdefault("wizard_id", uuid4().hex))
xsm.init_app(app, store=SessionStore())
```

### `flask xsm inspect|diagram|docs|simulate <name>`

Runs the `xsm` command of the same name on the registered machine's JSON source. `flask xsm inspect order --plain` prints exactly what `xsm inspect order.json --plain` prints. The flags match: `--json`, `--no-events`, `-f/--format`, `-o/--output`, `-e/--events`, `--plain`, `--no-color`.

### CSRF (Flask-WTF)

`CSRFProtect` rejects a POST that has no token, including JSON POSTs. There are two supported setups, and a test covers each one:

- **Token auth** (bearer / API key, no cookies): exempt the blueprint with `csrf.exempt(app.blueprints["xsm_order"])`.
- **Cookie-session auth:** keep CSRF on and send the token in the `X-CSRFToken` header (`generate_csrf()` in your page).

### Quart: `xstate_statemachine.contrib.quart`

`QuartXState` offers the same `init_app` / `register`. Its `act` is **`async with xsm.act(name, key) as i: await i.send(...)`** and yields an async `Interpreter` through `apersisted()`. `create_quart_statechart_blueprint(xsm, name, url_prefix)` exposes the same route table, and authorizers may be `async`. Quart is a soft import, not a separate extra: install `[flask]` plus `quart`. The shim is best-effort, and the same tests run under Quart in CI.

## Guarantees

> **What this does:** `act()` saves only on a clean exit, with `expected_version`, so concurrent requests on one key never lose an update. 50 threads posting to one `SQLiteStore` key produce exactly 50 increments, with the losers getting 409 and retrying. An idempotent replay returns the original receipt and does not bump the version. SSE subscribers see a transition only after its save committed. Two apps built from one extension share nothing.
>
> **What this does not do:** it does not retry a 409 for you; the client retries (idempotency keys make that safe). It does not push transitions across processes over SSE. It does not make `SessionStore` replay-proof: a client can resend an older signed cookie, so use a server-side store for anything that matters. It does not run async authorizers under Flask (use Quart).
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** any HTTP client that can reach the app. Each route calls your `authorize` callable (X0.1) before reading or writing.
>
> **What it exposes:** state ids and available events. `context` is exposed only through `context_serializer`. Error responses are RFC 9457 problems carrying the exception **class** name, never its text (X0.7). `SessionStore` cookies are signed, not encrypted, so the client can read the context.
>
> **You must configure:** an `authorize=` callable for every machine; `principal=` with `inbox=` (X0.2); `SECRET_KEY` (sessions and CSRF); CSRF, either by exempting the blueprint under token auth or with the `X-CSRFToken` header under cookie auth; `max_body_bytes` suited to your payloads; `allowed_origins` if a cross-origin page reads the stream.

## Compatibility

| Flask | Quart | Python | Tested in CI |
|:--|:--|:--|:--|
| 2.3 – 3.1 | 0.19+ (optional) | 3.9 – 3.14 | ✅ `[flask]` cell, Quart + Flask-WTF installed |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[flask]"` | extra not installed | run the command |
| `TypeError: register(authorize=) is required` | no authorizer | pass one, or `allow_all` on purpose |
| `RuntimeError: XState.init_app(app, store=...) was not called` | `act()` in an app that never ran `init_app` | call `init_app` in your factory |
| 405 `State-changing request must not use a safe method` | `act()` called from a GET view | make the route POST |
| 400 `The CSRF token is missing.` | Flask-WTF `CSRFProtect` on a JSON route | exempt the blueprint, or send `X-CSRFToken` |
| `SessionStoreTooLargeError` | the wizard's context outgrew the cookie | shrink the context or switch to `SQLiteStore` / `SQLAlchemyStore` |
| The stream blocks other requests | single-threaded dev server | run a threaded/gevent server, or Quart |
