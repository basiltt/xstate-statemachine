---
title: "Flask integration"
description: "An init_app extension, a statechart blueprint, session-keyed wizards and a flask xsm CLI — plus a Quart shim — over any StateStore."
---

# Flask

Flask has a very large install base, and (as of October 2026) PyPI has no Flask extension for statecharts -- no `flask-fsm`, `flask-statemachine` or `flask-transitions`. This extra follows the canonical `init_app` pattern. You get an `XState` extension that keeps its state in `app.extensions`, so the application-factory pattern is safe. `act()` gives you *create → act → persist → discard* on any `StateStore`. There is a blueprint with the same route table as the FastAPI router, a cookie-backed `SessionStore` for small multi-step wizards, and `flask xsm` commands for the machines your app registers. Quart, Flask's async twin, is served by a shim built on the same core.

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

A context manager that yields a started `SyncInterpreter` and saves on a clean exit. Nothing is written if the block raises. It is `persistence.persisted()` using the app's lock, plugins and inbox. Under the default optimistic lock, a concurrent writer causes `ConflictError` at exit. `init_app` registers error handlers for every exception the library maps to a status, so in the blueprint **and in your own views** a lost race is a **409** RFC 9457 problem (see [Concurrent writers](#concurrent-writers-409-and-how-to-avoid-it) for how to avoid it altogether). `act()` **refuses to run inside a GET/HEAD/OPTIONS/TRACE request** and raises `MethodNotAllowedError`, answered as a **405** problem; an oversized `SessionStore` save is a **413** problem. The handlers are app-level and catch these classes wherever they are raised (a `KeyNotFoundError` from your own code is a 404 problem too); a handler your app registered for one of them -- before or after `init_app` -- is left in place. Pass `init_app(..., error_handlers=False)` to register none (the exceptions then propagate and Flask answers 500 unless you catch them).

`g.xsm` (set before every request) exposes `act`, `peek`, `skip_save` and `registry`. `g.xsm.skip_save()` (or `xsm.skip_save()`) leaves the enclosing `act()` block **without saving** -- the version is not bumped and nothing is published to SSE. The `flask_wizard` example uses it to refuse a stale form under the lock.

### Concurrent writers: 409, and how to avoid it

Two requests on one key at once: under the default `OptimisticLock` the second to save loses with `ConflictError`. Nothing retries for you. Pick one of two patterns.

**Serialise writers** -- `PessimisticLock()` holds the store's per-key lock for the whole `act()` block, so no request loses (needs a store with `lock()`: `SQLiteStore`, `SQLAlchemyStore`, `RedisStore`, not `SessionStore`):

<!-- doc-requires: flask -->
```python
import os, tempfile, threading
from flask import Flask
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.flask import XState, allow_all, receipt_response
from xstate_statemachine.persistence import PessimisticLock, SQLiteStore

def inc(i, ctx, e, a):
    ctx["n"] += 1

counter = create_machine(
    {"id": "counter", "initial": "on", "context": {"n": 0},
     "states": {"on": {"on": {"INC": {"actions": "inc"}}}}},
    logic=MachineLogic(actions={"inc": inc}))
xsm = XState()
xsm.register("counter", counter, authorize=allow_all, context_serializer=dict)
app = Flask(__name__)
db = os.path.join(tempfile.mkdtemp(), "c.db")
xsm.init_app(app, store=SQLiteStore(db), lock=PessimisticLock())

@app.post("/c/<k>/inc")
def bump(k):
    with xsm.act("counter", k) as i:
        return receipt_response(i, i.send("INC", wait=True))

codes = []
def hit():
    codes.append(app.test_client().post("/c/1/inc").status_code)
threads = [threading.Thread(target=hit) for _ in range(20)]
for t in threads: t.start()
for t in threads: t.join()
assert codes == [200] * 20
with app.test_request_context(method="POST"):
    assert xsm.peek("counter", "1")["context"] == {"n": 20}
```

**Retry the work** -- keep the optimistic lock and run the block through `persisted_retry` (or `OptimisticLock(retries=...).run(...)`), which reloads and re-applies your function on a conflict. The function may run more than once, so it must only send events:

<!-- doc-requires: flask -->
```python
import os, tempfile, threading
from flask import Flask
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.flask import XState, allow_all
from xstate_statemachine.persistence import (
    OptimisticLock, SQLiteStore, persisted_retry)

def inc(i, ctx, e, a):
    ctx["n"] += 1

counter = create_machine(
    {"id": "counter", "initial": "on", "context": {"n": 0},
     "states": {"on": {"on": {"INC": {"actions": "inc"}}}}},
    logic=MachineLogic(actions={"inc": inc}))
xsm = XState()
xsm.register("counter", counter, authorize=allow_all, context_serializer=dict)
app = Flask(__name__)
store = SQLiteStore(os.path.join(tempfile.mkdtemp(), "c.db"))
xsm.init_app(app, store=store)

@app.post("/c/<k>/inc")
def bump(k):
    r = xsm.registry()
    n = persisted_retry(
        store, r.store_key("counter", k), counter,
        lambda i: (i.send("INC", wait=True), i.context["n"])[1],
        lock=OptimisticLock(retries=50))
    return {"n": n}

codes = []
def hit():
    codes.append(app.test_client().post("/c/1/inc").status_code)
threads = [threading.Thread(target=hit) for _ in range(20)]
for t in threads: t.start()
for t in threads: t.join()
assert codes == [200] * 20
with app.test_request_context(method="POST"):
    assert xsm.peek("counter", "1")["context"] == {"n": 20}
```

`persisted_retry` bypasses `act()`'s extras -- the app's plugins, inbox and SSE fan-out are not applied; pass `plugins=` yourself if you need them. Use `PessimisticLock` when you need those.

### `receipt_response(interp, receipt, *, status=None, context_serializer=None)`

A JSON response whose status comes from the **core** table, `xstate_statemachine.receipts.receipt_to_status`: 200 for a transition or a no-op, 202 for deferred, 409 when a guard denies, 422 when an idempotency key is reused with a different body, 500 for an action error (class name only). An idempotency refusal comes back as an RFC 9457 problem. `problem_response(exc)` builds a problem for any exception, containing a fixed title and the class name, **never** `str(exc)`. A `StoreUnavailableError` (the store's backend is down) is a **503** problem logged as one WARNING line per request, not a traceback (#306 battle).

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

A `StateStore` over `flask.session`, which puts the snapshot in the **signed** cookie. It is meant for small wizard-style state that belongs to one browser. There is a hard cap on save and on load, and it covers **every machine stored in one session together** (all of them ride in the same cookie). The default is 3 KiB, which keeps the whole signed cookie under the roughly 4 KiB browsers allow (measured: a snapshot at the cap makes a `Set-Cookie` of about 3.4 KB); two wizards each at 2.5 KiB would have produced a cookie browsers silently drop. Going over it raises `SessionStoreTooLargeError`, a `SnapshotTooLargeError` whose message tells you to shrink the context or move to a server-side store.

```python
xsm.register("wizard", wizard_machine, authorize=allow_all,
             key=lambda: session.setdefault("wizard_id", uuid4().hex))
xsm.init_app(app, store=SessionStore())
```

### `DEFAULT_SESSION_LIMIT`

An `int`, `3 * 1024` (3072 bytes). It is the default `max_snapshot_bytes` of `SessionStore`: the cap on the snapshot size, applied on save and on load, that keeps the signed cookie under the browsers' limit.

### `UnprocessableBodyError`

An `HTTPProblemError` with `status = 422` and title `Request body must be a JSON object`. The body reader raises it when a non-empty `application/json` body is not valid JSON (the message is `Request body is not valid JSON`) or is valid JSON but not an object. The error handler turns it into a 422 problem response. An empty body is read as `{}` and does not raise.

### `flask xsm inspect|diagram|docs|simulate <name>`

Runs the `xsm` command of the same name on the registered machine's JSON source. `flask xsm inspect order --plain` prints exactly what `xsm inspect order.json --plain` prints. The flags match: `--json`, `--no-events`, `-f/--format`, `-o/--output`, `-e/--events`, `--plain`, `--no-color`.

### CSRF (Flask-WTF)

`CSRFProtect` rejects a POST that has no token, including JSON POSTs. There are two supported setups, and a test covers each one:

- **Token auth** (bearer / API key, no cookies): exempt the blueprint with `csrf.exempt(app.blueprints["xsm_order"])`.
- **Cookie-session auth:** keep CSRF on. The browser must send **both** the session cookie that `generate_csrf()` set (fetch's default `credentials: "same-origin"` does) **and** the token in the `X-CSRFToken` header (or `X-CSRF-Token`). The header alone, without the cookie session it was issued in, is a 400. Without either, Flask-WTF answers 400 `The CSRF token is missing.` -- an HTML error page, not a problem+json body.

<!-- doc-requires: flask, flask_wtf -->
```python
from flask import Flask
from flask_wtf.csrf import CSRFProtect, generate_csrf
from xstate_statemachine import create_machine
from xstate_statemachine.contrib.flask import XState, allow_all, create_statechart_blueprint
from xstate_statemachine.persistence import MemoryStore

xsm = XState()
xsm.register("o", create_machine({"id": "o", "initial": "a",
             "states": {"a": {"on": {"GO": "b"}}, "b": {}}}), authorize=allow_all)
app = Flask(__name__)
app.secret_key = "dev"
CSRFProtect(app)
xsm.init_app(app, store=MemoryStore())
app.register_blueprint(create_statechart_blueprint(xsm, "o", "/o"))
app.add_url_rule("/token", "token", generate_csrf)   # your page embeds this

browser = app.test_client()
assert browser.post("/o/1/send", json={"type": "GO"}).status_code == 400
token = browser.get("/token").get_data(as_text=True)
ok = browser.post("/o/1/send", json={"type": "GO"}, headers={"X-CSRFToken": token})
assert ok.status_code == 200 and ok.get_json()["state"] == "b"
stranger = app.test_client()                          # token, but not its session
assert stranger.post("/o/2/send", json={"type": "GO"},
                     headers={"X-CSRFToken": token}).status_code == 400
```

### Quart: `xstate_statemachine.contrib.quart`

`QuartXState` offers the same `init_app` / `register`, with the same `init_app` options as Flask (`lock`, `plugins`, `inbox`/`principal`, `log`, `clock`, `migrator`, `allowed_origins`, `max_connections_per_key`, `error_handlers`); its `/stream` checks `Origin` the same way. Its `act` is **`async with xsm.act(name, key) as i: await i.send(...)`** and yields an async `Interpreter` through `apersisted()`. `create_quart_statechart_blueprint(xsm, name, url_prefix)` exposes the same route table, and authorizers may be `async`. Quart is a soft import, not a separate extra: install `[flask]` plus `quart`. The shim is best-effort, and the same tests run under Quart in CI.

## Guarantees

> **What this does:** `act()` saves only on a clean exit, with `expected_version`, so concurrent requests on one key never lose an update: every request either commits on top of the latest version or is refused (409 in the blueprint, `ConflictError` in your own view) with nothing saved. With `PessimisticLock()`, 50 threads posting to one `SQLiteStore` key produce exactly 50 increments and fifty 200s; under the default optimistic lock most of them get 409 and the count equals the number of 200s. An idempotent replay returns the original receipt and does not bump the version. SSE subscribers see a transition only after its save committed. Two apps built from one extension share nothing.
>
> **What this does not do:** it does not retry a 409 for you; the client retries (idempotency keys make that safe), or the server avoids it with `PessimisticLock` / `persisted_retry` ([patterns](#concurrent-writers-409-and-how-to-avoid-it)). It does not push transitions across processes over SSE. It does not make `SessionStore` replay-proof: a client can resend an older signed cookie, so use a server-side store for anything that matters. It does not run async authorizers under Flask (use Quart).
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
| 405 problem `State-changing request must not use a safe method` | `act()` called from a GET view | make the route POST; use `peek()` for reads |
| 409 problem `Conflict` from your own view | two writers on one key, optimistic lock | `PessimisticLock()` or `persisted_retry`; the client may simply retry |
| 413 problem `Snapshot too large` | the session cookie's cap (3 KiB across every machine in the session) | shrink the context, add a compression `codec`, or move to a server-side store |
| 500 for one of the above | `init_app(error_handlers=False)` | register `app.register_error_handler(HTTPProblemError, problem_response)` yourself |
| 400 `The CSRF token is missing.` | Flask-WTF `CSRFProtect` on a JSON route | exempt the blueprint, or send `X-CSRFToken` |
| `SessionStoreTooLargeError` | the wizard's context outgrew the cookie | shrink the context or switch to `SQLiteStore` / `SQLAlchemyStore` |
| The stream blocks other requests | single-threaded dev server | run a threaded/gevent server, or Quart |
