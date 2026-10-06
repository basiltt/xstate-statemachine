---
title: "Live inspector"
description: "Watch a running Python machine live in the Stately Inspector (or the built-in page): the @statelyai/inspect protocol over SSE, JSON Lines recording and replay, WebSocket under Starlette."
---

# Live inspector

`@xstate/inspect` and the **Stately Inspector** let JavaScript developers watch a running machine in the browser: actors appear, events flow between them, the state highlights as it changes. This module speaks the same wire protocol from Python, so the existing Stately UI — or a small page we ship as a fallback — can follow a Python process. It is also a flight recorder: record a session to JSON Lines, replay it later.

## Install

Nothing to install: the core (`xstate_statemachine.inspect`) is stdlib only — the plugin, JSON Lines, and Server-Sent Events over `http.server`. The WebSocket sink needs the web extra:

```bash
pip install "xstate-statemachine[starlette]"   # only for WebSocketSink / mount_inspector
```

For a complete, runnable app -- `InspectorPlugin` with a context allow-list on two charts in choreography, the recording replayed with `replay_messages`, and a test suite -- see the [`eda_fulfilment` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/eda_fulfilment).

## Quick start

```python
from xstate_statemachine import SyncInterpreter, create_machine
from xstate_statemachine.inspect import InspectorPlugin, MemorySink

machine = create_machine({
    "id": "door", "initial": "closed", "context": {"opens": 0, "pin": "1234"},
    "states": {"closed": {"on": {"OPEN": "open"}}, "open": {"on": {"CLOSE": "closed"}}},
})
sink = MemorySink()                                   # or JsonLinesSink / SseSink
plugin = InspectorPlugin(sink, context_allowlist=["opens"]).install()
door = SyncInterpreter(machine).start()
door.send("OPEN")
door.stop()
plugin.uninstall()

kinds = [m["type"] for m in sink.messages]
assert kinds[0] == "@xstate.actor"
assert ("@xstate.event", "OPEN") in [(m["type"], m.get("event", {}).get("type")) for m in sink.messages]
assert sink.messages[-1]["snapshot"]["context"] == {"opens": 0}   # "pin" never leaves
```

From the terminal:

```bash
xsm inspect machine.json --live --open            # serve + interactive simulator
xsm sim machine.json -e SUBMIT,+2000 --record session.jsonl
xsm replay session.jsonl --live --speed 1         # stream a recording
```

## Reference

### Protocol

Three message kinds, shaped exactly like `@statelyai/inspect`'s `StatelyInspectionEvent` (pinned in tests against fixtures **recorded from the real npm package**, `@statelyai/inspect@0.7.2` + `xstate@5.33.2` — see `tests/inspect/fixtures/`):

| Kind | When | Key fields |
|:--|:--|:--|
| `@xstate.actor` | an interpreter starts | `name`, `sessionId`, `parentId` (children), `rootId`, `definition` (the chart JSON), `snapshot` |
| `@xstate.event` | an event is delivered | `event`, `sessionId` (receiver), `sourceId` (sender, for `sendTo` / `sendParent` / `forwardTo`) |
| `@xstate.snapshot` | the event has been processed | `event`, `snapshot` (`status`, `value`, `context`, `children`, `historyValue`, `tags`) |

Every message also has `_version`, `createdAt` (epoch ms, string) and `id: null`. The startup is reported as `xstate.init`, as in XState.

### `InspectorPlugin(sink, *, context_allowlist=(), include_payloads=False, payload_allowlist=(), redact_keys=DEFAULT_REDACT_KEYS, clock=None)`

`sink` is anything with `send(message)` or a callable. `install()` registers the plugin globally so **child actors** and restored interpreters are followed too (`interp.use(plugin)` sees only that one interpreter); `uninstall()` undoes it. `sourceId` comes from the core hook `on_event_sent(interp, target_id, event)` (see [Plugins](../plugins/)).

### Sinks

| Sink | What |
|:--|:--|
| `MemorySink(maxlen=None)` | `.messages` list; `maxlen` keeps only the newest, `.dropped` counts the rest |
| `JsonLinesSink(path)` | one ASCII-only message per line; the file is created **0600** (POSIX; on Windows the directory ACL applies), an existing file is appended to; `send()` after `close()` raises; context manager |
| `SseSink(host="127.0.0.1", port=0, *, token=None, allowed_origins=(), history=1000, max_queue=10_000)` | stdlib HTTP server: `/` page, `/app.js`, `/events` (SSE, backlog replayed to late clients, 15 s keep-alives), `/messages` (JSON). `.url` is the first-load URL, `.port`, `.token`, `.start()` / `.close()` / context manager. A client `max_queue` frames behind is disconnected; `.dropped`, `.sent`, `.clients` |
| `contrib.starlette.WebSocketSink(*, token=None, history=1000, max_queue=10_000)` | WebSocket fan-out; created by `mount_inspector()`; a lagging client is closed with 1013, `.dropped` |

`read_jsonl(path)` is a generator over a recording (a truncated *last* line is ignored, a corrupt middle line raises). `replay_messages(source, sink, *, speed=0.0)` streams a path (`str` or `os.PathLike`, never loaded whole) or an iterable of dicts into a sink and returns how many it sent; non-protocol lines are skipped (not counted), a negative `speed` raises `ValueError`, a recorded clock that steps backwards never sleeps, and a sink that raises stops the replay with that exception. `session_id_of(interp)` returns the session id the plugin uses for an interpreter (the `store_key` of a persisted instance). The protocol builders `actor_message`, `event_message`, `snapshot_message`, and `PROTOCOL_VERSION`, `MESSAGE_TYPES`, `COOKIE_NAME` are exported for custom sinks.

### The page

`SseSink` serves a small page with two views of the same stream: an iframe on `https://stately.ai/inspect`, driven the way `@statelyai/inspect`'s browser adapter drives it (`postMessage` after the frame reports `@statelyai.connected`), and our own fallback list of actors, values and events that works offline. No build step and no third-party script.

### Starlette / FastAPI: `mount_inspector(app, registry, path="/_xsm/inspect", *, debug=False, token=None, context_allowlist=(), include_payloads=False, allow_remote=False)`

Refuses unless `debug=True`. Appends an `InspectorPlugin` to `registry.plugins` (every interpreter the registry builds is observed) and mounts `WS <path>` (one protocol message per frame — what `@statelyai/inspect`'s `createWebSocketReceiver` parses) plus `GET <path>` (the backlog as JSON; `?token=` sets the cookie once). Returns the `WebSocketSink`; read `.token`.

## Guarantees

> **What this does:** reports every actor start, delivered event and settled snapshot on both engines, in order per actor, with sender provenance for actor-to-actor sends. Plugin failures are contained like any plugin's. Recording and replay round-trip byte-for-byte through JSON.
>
> **What this does not do:** control the machine from the UI (the stream is one-way); guarantee delivery to a slow browser (SSE clients get a bounded backlog on connect, then live messages); follow interpreters created before `install()`; persist anything except what a `JsonLinesSink` writes. The hosted Stately UI is a third-party page whose protocol is not formally documented — the fallback page is why that is acceptable.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can reach the port **and** holds the token. An inspector streams every event of every machine it observes — treat it as a data-exfiltration endpoint and never run it in production.
>
> **What it exposes (X0.7 web hardening):**
> - Binds `127.0.0.1` by default; `--host 0.0.0.0` (any non-loopback host) is refused without an explicit `--token`.
> - The token is `secrets.token_urlsafe(32)` per run, compared with `hmac.compare_digest`. It appears in the URL **only on the first page load**, which answers `303` with an `HttpOnly; SameSite=Strict` cookie, so it does not linger in the address bar, history or `Referer`. API calls use the cookie, `Authorization: Bearer …` or `X-XSM-Token`.
> - On loopback, a non-loopback `Host` header is refused (421, DNS-rebinding defence); any request carrying an `Origin` must be same-origin or in `allowed_origins` (403). The Starlette route uses the registry's own `origin_allowed()` and closes the socket with 1008.
> - Strict CSP (`default-src 'none'`, `script-src 'self'`, `frame-ancestors 'none'`), no inline script, `nosniff`, `no-referrer`, `no-store`.
> - **Context is deny-by-default**: snapshots — and the initial `context` inside the `definition` — carry only keys in `context_allowlist`, and those still go through `redact()`. Event payloads are dropped unless `include_payloads=True` (then redacted).
> - Recordings are created with mode **0600**.
>
> **You must configure:** `context_allowlist` for anything you want to see; a strong `--token` if you ever bind beyond loopback; `debug=True` only in development builds.

## XState parity

| XState / `@statelyai/inspect` | Here |
|:--|:--|
| `createBrowserInspector()` | `SseSink` + the shipped page (Stately iframe + fallback) |
| `createWebSocketInspector()` / `createWebSocketReceiver()` | `mount_inspector()` + `WebSocketSink` (`[starlette]`) |
| `inspect` option on `createActor` | `InspectorPlugin(sink).install()` (or `interp.use(plugin)`) |
| `createSkyInspector()` (hosted relay) | not provided -- nothing leaves your machine |
| Sending events *from* the UI | not provided -- the stream is one-way |

## Compatibility

| Component | Python | Tested in CI |
|:--|:--|:--|
| Core (`xstate_statemachine.inspect`, SSE, JSONL) | 3.9 – 3.14 | ✅ default test job |
| `WebSocketSink` / `mount_inspector` | 3.9 – 3.14 with `[starlette]` | ✅ `starlette` cells |
| Wire protocol | `@statelyai/inspect` 0.7.x | ✅ recorded fixtures |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `401 inspector token required` | opened `/` without the one-time `?token=` URL, or the cookie was cleared | open the URL `xsm` printed again |
| `421 misdirected request (Host)` | reached a loopback server through another host name | use `127.0.0.1` / `localhost` |
| `refusing to serve … non-loopback` | `--host` without `--token` | pass `--token` |
| Child actors missing | plugin attached with `.use()` | use `plugin.install()` |
| Snapshot `context` is `{}` | deny-by-default | add keys with `context_allowlist` / `--context` |
| Stately pane stays blank | the hosted UI is unreachable or changed | the fallback list on the left still works |
| One actor for all my orders | instances share an id | give each a `store_key`; it becomes the session id |
| Browser tab froze and the process grew | a stalled client | bounded by `max_queue`; the client is cut and reconnects |
| Recording stops silently | the sink raised (disk full, closed file) | the plugin logs one warning and disables itself -- check the logs |
| A card number appears in an event | a free-text payload field | `include_payloads=True` with `payload_allowlist` naming only safe fields |
| `xsm sim --record` exits 2 | the file already holds a recording | another path, or `--append` |
