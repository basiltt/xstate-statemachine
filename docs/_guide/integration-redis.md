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

Implements `StateStore`. `client_or_url` is a `redis.Redis` or a URL. Keys under `{prefix}:` — `snap:{key}` (hash), `dl:{key}` (deadline hash), `deadlines` (sorted set indexed by `due_at_wall`, read by `DueTimerScanner`), `keys` (set, for `list_keys`), `lock:{key}`, `schema`.

- `save(..., expected_version=)` is **one Lua script**: compare the stored version, write the hash, replace the deadline index — atomically. A mismatch is `ConflictError` with the actual version; nothing is written.
- `lock(key, timeout=)` is `SET NX PX lock_ttl_ms` with a random token, released only by that token (Lua compare-and-delete). `LockTimeoutError` when not acquired in time.
- `forget(key)` deletes snapshot + deadlines + lock **+ the instance's log stream** atomically and reports counts (X0.5: everything the namespace holds about one instance); inbox rows are per tenant scope — use `RedisInbox.forget(scope)`. `delete(key)` removes only the record and leaves a held lock alone.
- `list_keys(prefix=)` escapes `*?[]\` so a user prefix matches literally.
- `ttl_s` expires idle instances; `health()` pings.
- `due_keys(until_wall, limit=)` reads the deadline index directly — the scanner uses it instead of loading every record.

### `AsyncRedisStore(...)`

The same layout and scripts on `redis.asyncio` — `AsyncStateStore`, so `async with apersisted(astore, key, machine)` works natively. A sync and an async store may share one prefix.

### `RedisInbox(client_or_url, *, prefix)`

Implements `InboxStore`: one hash per scope (`inbox:{scope}`, field = idempotency key, value = JSON entry) plus a sorted-set TTL index (`inbox_exp`) so `purge_expired()` is a range query. `claim` is atomic first-wins (Lua). `forget(scope)` erases a tenant.

### `RedisLog(client_or_url, *, prefix, maxlen=10_000)`

Implements `TransitionLogStore` as one Redis Stream per machine id (`log:{machine_id}`), `XADD MAXLEN ~ maxlen`. `read(after_seq=)`, `purge_older_than`, `forget`.

### `escape_glob(text)`

The SCAN-pattern escaper `list_keys` uses; exported for your own `SCAN`s.

## Guarantees

> **What this does:** optimistic saves are atomic (no read-then-write window); the pessimistic lock is token-owned and **fenced** — `persisted(..., lock=PessimisticLock())` still saves with `expected_version`, so a lock that **expired** under a slow holder produces `ConflictError`, never a lost update; `forget()` is atomic; two applications cannot share a namespace by accident (`prefix` is mandatory).
>
> **What this does not do:** durability beyond what your Redis persistence (AOF / RDB) provides; multi-key transactions across prefixes; broker semantics (see the Streams integration). A lock is advisory: a writer that bypasses `persisted()` and calls `save()` without `expected_version` is not stopped.
>
> See the programme-wide [guarantees](https://github.com/basiltt/xstate-statemachine/issues/303).

## Threat model

> **Who can call this:** anyone with network access to the Redis and its credentials — the store trusts the connection you hand it. Use `requirepass` / ACLs and TLS (`rediss://`).
>
> **What it exposes:** snapshots contain `context` in clear text unless you pass a `codec=` that encrypts. Idempotency entries contain cached receipts (state ids, no payloads). Log streams contain redacted payloads (the shared `redact()` denylist).
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
