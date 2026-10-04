---
title: "Redis integration"
description: "RedisStore, RedisInbox and RedisLog — shared state for statecharts across workers and hosts, with fencing locks and atomic Lua operations."
---

# Redis

`SQLiteStore` is single-host. The first real deployment question every web developer asks is *"I have four uvicorn workers on two machines — where does the snapshot live?"* Redis is the lowest-friction shared answer. This extra ships the **store**, the **idempotency inbox**, the **transition log** and a **fencing lock** on Redis — the same protocols as the stdlib backends, so `persisted()`, `IdempotencyPlugin`, `AuditPlugin` and `DueTimerScanner` work unchanged. (Redis Streams as an event *broker* is a separate, later integration.)

## Install

```bash
pip install "xstate-statemachine[redis]"
```

Requires `redis>=5`. Tested versions are in the [compatibility table](#compatibility). Tests run against `fakeredis` by default and against a live server when `XSM_REDIS_URL` is set.

For a complete, runnable app that uses the Redis Streams adapter -- run it on `fakeredis` with `python -m eda_fulfilment --broker redis-streams`, or point it at a real server by setting `REDIS_URL` -- see the [`eda_fulfilment` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/eda_fulfilment).

## Quick start

<!-- doc-requires: redis, fakeredis -->
```python
import fakeredis                                   # stand-in for redis.Redis.from_url("redis://...")
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.redis import RedisInbox, RedisLog, RedisStore
from xstate_statemachine.persistence import AuditPlugin, IdempotencyPlugin, persisted

r = fakeredis.FakeRedis()
store = RedisStore(r, prefix="shop")               # prefix is mandatory: one namespace per app
inbox = RedisInbox(r, prefix="shop")
log = RedisLog(r, prefix="shop")

cfg = {"id": "order", "initial": "cart", "context": {"items": 0},
       "states": {"cart": {"on": {"ADD": {"actions": "add"}, "PAY": "paid"}}, "paid": {"type": "final"}}}
def add(i, ctx, e, a):
    ctx["items"] += 1
machine = create_machine(cfg, logic=MachineLogic(actions={"add": add}))
plugins = [IdempotencyPlugin(inbox, principal=lambda e: "acct_1"), AuditPlugin(log)]

# Any worker on any host:
with persisted(store, "order:42", machine, plugins=plugins) as order:
    order.send("ADD", idempotency_key="evt_1", actor="alice")
with persisted(store, "order:42", machine, plugins=plugins) as order:
    order.send("ADD", idempotency_key="evt_1", actor="alice")   # redelivery: deduplicated
    order.send("PAY", actor="alice", reason="checkout")

record = store.load("order:42")
assert record.version == 2 and record.machine_version == ""
assert [(x.event_type, x.actor) for x in log.read("order:42")] == [("ADD", "alice"), ("PAY", "alice")]
with persisted(store, "order:42", machine) as order:
    assert order.context["items"] == 1 and order.matches("order.paid")
```

## Reference

### `RedisStore(client_or_url, *, prefix, codec=None, max_snapshot_bytes=1 MiB, ttl_s=None, lock_ttl_ms=30_000)`

Implements `StateStore`. `client_or_url` is a `redis.Redis` or a URL. A client built from a URL gets `socket_timeout` / `socket_connect_timeout` of `DEFAULT_SOCKET_TIMEOUT_S` / `DEFAULT_SOCKET_CONNECT_TIMEOUT_S` (5 s each), so a Redis that accepts TCP but never answers raises `StoreUnavailableError` instead of hanging; override in the URL (`?socket_timeout=30`) or pass your own client — a client **you** construct keeps its own settings, so give it `socket_timeout=` yourself (redis-py 8 defaults to 5 s; older releases have none). `ttl_s` and `lock_ttl_ms` must be at least one millisecond (`ValueError` at construction). Keys under `{prefix}:` — `snap:{key}` (hash), `dl:{key}` (deadline hash), `deadlines` (sorted set indexed by `due_at_wall`, read by `DueTimerScanner`), `keys` (set, for `list_keys`), `lock:{key}`, `schema`.

- `save(..., expected_version=)` is **one Lua script**: compare the stored version, write the hash, replace the deadline index — atomically. A mismatch is `ConflictError` with the actual version; nothing is written.
- `lock(key, timeout=)` is `SET NX PX lock_ttl_ms` with a random token, released only by that token (Lua compare-and-delete). `LockTimeoutError` when not acquired in time.
- `forget(key)` deletes snapshot + deadlines + lock **+ the instance's log stream** atomically and reports counts (X0.5: everything the namespace holds about one instance); inbox rows are per tenant scope — use `RedisInbox.forget(scope)`. `delete(key)` removes only the record and leaves a held lock alone.
- `list_keys(prefix=)` escapes `*?[]\` so a user prefix matches literally.
- `ttl_s` expires idle instances; `health()` pings and never raises.
- A damaged record (missing `snapshot` field, non-integer `version`) is `SnapshotCorruptError`; an unreadable `{prefix}:schema` marker is `StoreError` at construction.
- `due_keys(until_wall, limit=)` reads the deadline index directly — the scanner uses it instead of loading every record. Index members whose snapshot expired (`ttl_s`) are pruned as they are met, so they cannot starve live keys.
- **Layout 2** (this release): deadline index members are JSON arrays `[key, state_id, entry_seq, event]`, so a key containing `|` is unambiguous. A namespace written by a pre-release build (layout 1) is upgraded in place on construction and its old members are still read; a process on the older layout then refuses the namespace (`StoreError: … newer`) — upgrade every worker sharing a prefix together. No released version wrote layout 1.

### `AsyncRedisStore(...)`

The same layout, scripts and argument checks on `redis.asyncio` (shared code, not a copy) — `AsyncStateStore`, plus `due_keys`; the schema marker is checked on the first call, so `async with apersisted(astore, key, machine)` works natively. A sync and an async store may share one prefix.

### `RedisInbox(client_or_url, *, prefix)`

Implements `InboxStore`: one hash per scope (`inbox:{scope}`, field = idempotency key, value = JSON entry) plus a sorted-set TTL index (`inbox_exp`) so `purge_expired()` is a range query (cost grows with the number of *expired* entries, not the total). `claim` is atomic first-wins (Lua). `forget(scope)` erases one tenant atomically; a scope containing `*` or `?` never touches another.

- **Expiry uses the Redis server clock** (`TIME` inside the scripts), never the worker's: two hosts with skewed clocks agree on whether a key is still live.
- A worker that dies between `claim` and `mark` leaves the key **in flight** (`409`) until the plugin's `ttl_s` passes, then a retry is admitted — the same rule as `SQLiteInbox`.
- The mark is written right **after** the snapshot save, not in one transaction with it (Redis cannot span both scripts); the in-snapshot `processed_ids` ring covers a crash in between.

### `RedisLog(client_or_url, *, prefix, maxlen=None)`

Implements `TransitionLogStore` as one Redis Stream per machine id (`log:{machine_id}`). The stream entry id **is** the record's `seq` (`"{seq}-0"`) and each append is a compare-and-append script, so two workers can never store the same `seq` and `append_next` (used by `TransitionLogPlugin`) is atomic across hosts. `read(after_seq=, limit=)` is a ranged `XRANGE` — paging a long stream costs the page, not the stream.

- `maxlen` (default **unbounded**, like `SQLiteLog`) trims with `XADD MAXLEN ~` — *approximate*: at least `maxlen` newest records are kept. Trimming drops the **head** of the audit trail: `replay()` then refuses with `ReplayDivergenceError(field="seq")` unless you pass a `snapshot=` taken at the first retained record. It never silently replays from the middle.
- `purge_older_than(cutoff)` walks every stream of the prefix in pages (O(records)); run it from a maintenance job.
- **Not transactional with the snapshot.** `append(..., connection=)` is accepted for protocol parity and ignored. `TransitionLogPlugin` writes records after the `persisted()` block commits, so after a crash the log may **trail** the snapshot, never lead it (#262).

### `escape_glob(text)`

The SCAN-pattern escaper `list_keys` uses; exported for your own `SCAN`s.

## Guarantees

> **What this does:** optimistic saves are atomic (no read-then-write window); the pessimistic lock is token-owned and **fenced** — `persisted(..., lock=PessimisticLock())` still saves with `expected_version`, so a lock that **expired** under a slow holder produces `ConflictError`, never a lost update; `forget()` is atomic; two applications cannot share a namespace by accident (`prefix` is mandatory).
>
> **What this does not do:** durability beyond what your Redis persistence (AOF / RDB) provides; multi-key transactions across prefixes; **one transaction for snapshot + inbox mark + log record** (each is its own atomic script — mark and log are written after the save); SSE/WebSocket fan-out across workers (per process — a stream on host B does not see a commit on host A until it reconnects); broker semantics (see the Streams integration). A lock is advisory: a writer that bypasses `persisted()` and calls `save()` without `expected_version` is not stopped.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone with network access to the Redis and its credentials — the store trusts the connection you hand it. Use `requirepass` / ACLs and TLS (`rediss://`).
>
> **What it exposes:** snapshots contain `context` in clear text unless you pass a `codec=` that encrypts. Idempotency entries contain cached receipts (state ids, flags, no payloads — but a receipt for a step whose action raised also stores that exception's class **and message**, so do not put secrets in exception messages). Log streams contain redacted payloads (the shared `redact()` denylist).
>
> **You must configure:** a unique `prefix` per application; a `lock_ttl_ms` longer than your slowest step (the fence catches the rest); a `maxlen` for logs and `ttl_s` for idle snapshots if the key space is unbounded; Redis persistence if a restart must not lose state.

## Compatibility

| redis-py | Redis server | Python | Tested in CI |
|:--|:--|:--|:--|
| 5.x – 6.x | 7.x (Lua, Streams, `SET NX PX`) | 3.9 – 3.14 | ✅ `fakeredis[lua]` in the `[redis]` cell; live server opt-in via `XSM_REDIS_URL` |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[redis]"` | extra not installed, or `redis` present but failing to import | run the command; the message carries the underlying import error |
| `InvalidConfigError: Redis backends need a non-empty prefix` | `prefix=""` | choose a namespace, e.g. your app name |
| `StoreError: … schema version N, newer than this library supports` | a newer library wrote this namespace | upgrade, or point at a fresh prefix |
| `ConflictError` from a `PessimisticLock` block | the lock expired (`lock_ttl_ms` too short) and another worker saved | raise `lock_ttl_ms`, or shorten the step — the data is intact, retry |
| `list_keys()` returns nothing for a prefix with `*` in it | pre-0.11 pattern injection | fixed: metacharacters are escaped |
| every route answers `503 Store unavailable`; log shows one `🔌 store unavailable` WARNING per request | Redis is unreachable (`StoreUnavailableError`: refused connection, socket timeout, `LOADING` after a restart) | nothing was written -- retry after the failover; `/_xsm/ready` is 503 while `/_xsm/health` stays 200, so route traffic on readiness |
| `StoreUnavailableError` from `RedisStore(url)` at construction | the schema check / script registration ran against a dead server | the store needs Redis at construction; build it lazily or after your readiness gate |
