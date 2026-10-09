---
title: "Celery integration"
description: "A Celery task as an invoke service, a worker-side persisted act-loop, Celery Beat as the durable after-timer scheduler, and an outbox relay task."
---

# Celery

Celery has no notion of state: long flows get stitched together with `chain` / `chord`, and a retry, a timeout or a cancellation all end up as ad-hoc bookkeeping. With the `[celery]` extra, the statechart holds the flow and Celery does the work. A task becomes an **`invoke` service** (its result drives `onDone`, its failure or timeout drives `onError`, and leaving the state revokes it). A worker task runs the **load → send → persist** act-loop, with Celery retrying optimistic conflicts. **Celery Beat** is the durable `after` scheduler, and the transactional outbox drains through an ordinary Celery task.

## Install

```bash
pip install "xstate-statemachine[celery]"
```

Requires `celery>=5.3`. Tested versions are in the [compatibility table](#compatibility). The tests use `task_always_eager` plus an in-memory result backend (no broker), and a real in-process worker on the `memory://` transport. A live broker test runs when `CELERY_BROKER_URL` is set.

For a complete, runnable app -- `celery_service` as an `invoke`, `@statechart_task`, `DurableTimerScheduler` firing an `after` escalation once, `outbox_relay_task`, a forged task id ignored, pickle refused, and a test suite -- see the [`eda_fulfilment` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/eda_fulfilment).

## Quick start

<!-- doc-requires: celery -->
```python
from celery import Celery
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.celery import celery_service
from xstate_statemachine.persistence import MemoryStore, persisted

app = Celery(broker="memory://", backend="cache+memory://")
app.conf.task_always_eager = True          # a docs run needs no worker

@app.task
def charge(amount):
    return {"ok": True, "amount": amount}

cfg = {"id": "o", "initial": "paying", "states": {
    "paying": {"invoke": {"src": "charge", "onDone": "paid", "onError": "failed"}},
    "paid": {"type": "final"}, "failed": {}}}
machine = create_machine(cfg, logic=MachineLogic(services={
    "charge": celery_service(charge, args_from=lambda ctx, e: ((42,), {}))}))

store = MemoryStore()
with persisted(store, "o1", machine):
    pass
with persisted(store, "o1", machine) as order:
    assert order.matches("o.paid")
```

## Reference

### `celery_service(task, *, args_from=..., timeout_s=None, queue=None, poll_s=0.05, watch=True)`

Returns an `invoke` service. On entry to the state it calls `task.apply_async(args, kwargs, headers=..., queue=...)` and returns **without blocking**:

- **Result already available** (eager mode): it behaves exactly like a plain service, so `onDone` / `onError` fire in the same step.
- **Live interpreter**: a daemon watcher polls the result backend and completes the invocation through the engine's own actor-logic path. The engine mints the events, so a user `send("done.invoke.x")` is still refused. If `timeout_s` elapses first, the task is revoked and `onError` fires with a `TimeoutError`.
- **Durable** (create → act → persist → discard): the task id is recorded in the snapshot under `context["_xsm_celery"][<invoke id>]`, and the headers `xsm_store_key` and `xsm_invocation_id` travel with the task. The completion arrives later through `deliver_result`. **`poll_results` is the durable path**, and the signal handlers are a low-latency shortcut.

**Exiting the state** calls `AsyncResult.revoke(terminate=False)`, which is best effort. **`stop()`** (for example, the end of a `persisted()` block) only stops the watcher and never revokes.

### `deliver_result(store, machine_for_key, key, invocation_id, task_id, *, result=None, error=None, lock=None, plugins=())`

Completes an invocation on a persisted instance and saves it, retrying `ConflictError`. The header values count as **trusted only after this check**: the instance must exist, the invocation must still be active, and it must record `task_id`. Anything else is a stale completion: it is ignored, logged, and reported to `on_event_dropped(..., "stale_invocation")`. Returns whether the completion was applied.

### `connect_signals(store, machine_for_key, *, app, lock=None, plugins=(), pending=None) -> disconnect`

Installs `task_success` / `task_failure` handlers in the **worker** process that call `deliver_result` for `celery_service` tasks. Eager tasks and tasks without the headers are ignored. A worker can finish **before** the caller's `persisted()` block has saved the `_xsm_celery` record. That completion is not stale: it is parked in `pending` (a `MemoryPendingResults`), and `poll_results(pending=...)` applies it once the record exists. Pass the same table to both. Without a table, the completion is left to `poll_results`, which reads it from the result backend.

### `poll_results(store, machine_for_key, *, app, prefix="", now=None, lock=None, plugins=(), pending=None) -> int`

A fallback that polls the result backend, for when signals are not available (the worker runs in another process and cannot reach the store). It delivers every finished task and fails and revokes every invocation past its `timeout_s` deadline. Schedule it with Beat.

### `@statechart_task(app, store, machine_for_key, *, lock=None, plugins=(), name=None, max_retries=10, **task_options)`

Registers `fn(interp, *args, **kwargs)` as a task whose first argument is the instance key. The body runs inside `persisted(store, key, machine)`. `ConflictError` is retried through Celery's own `autoretry_for`, with exponential backoff from 1 s (Celery rounds `retry_backoff` up to whole seconds) to 2 s, with jitter. A retry **re-runs `fn` from the start**, including any side effect it performed outside the machine, so keep side effects in machine actions or make them idempotent.

```python
@statechart_task(app, store, order_machine)
def pay(order, amount):
    order.send("PAY", amount=amount)

pay.delay("order-1", 42)
```

### `DurableTimerScheduler(app, store, machine_for_key, *, name="xsm.deadlines.scan", fire_name="xsm.deadlines.fire", **scanner_kw)`

Wraps [`DueTimerScanner`](../persistence/) in two tasks:

- `scheduler.task` runs `DueTimerScanner.run_once()`. This is the **safety net**, so schedule it with `app.conf.beat_schedule = xsm_deadlines_every(scheduler, seconds=10)`.
- `scheduler.schedule_exact(key)` gives exact timing. It enqueues one `eta` job per persisted deadline, and each job carries its **state-entry generation** (`state_id`, `entry_seq`, per X0.9). When it runs, it wakes the instance only if that same deadline is still recorded. A machine that left the state, or re-entered it and so got a new generation, is skipped.

Double firing (the `eta` job plus the scan) is idempotent: the scanner re-checks under the lock, and `fire_due` fires a deadline once.

> ⚠️ **Run exactly one Beat process.** Two Beats are still correct, but they double the scan traffic. With zero Beats, the `after` timers of discarded instances never fire.

### `outbox_relay_task(app, outbox, broker, *, name="xsm.outbox.relay", batch=100, owner=None, lease_s=None)`

A task that runs `OutboxRelay.relay_once` (the async form for an async broker, the sync form otherwise). Schedule it with Beat. Several workers may run it against one outbox: each run **leases** the rows it publishes (`owner` names this worker's relay -- pass a stable name such as the hostname so a restarted worker reclaims its own rows at once; `lease_s` defaults to `DEFAULT_CLAIM_LEASE_S`, 30 s; see the [EDA guide](../integration-eda/)). An async broker is driven from **one private event loop per worker process**, never a new loop per tick. Call `task.close_relay_loop()` from `worker_process_shutdown` to close the broker and the loop.

Every worker process gets its own `OutboxRelay`, so several workers draining one outbox is safe. On the bundled outbox stores the relays [lease their rows](../integration-eda/#several-relays-on-one-outbox-leases) (default lease 30 s, owner `host:pid:id`). A worker killed mid-batch leaves its rows to another worker when the lease expires, and consumers dedup the rare re-publication on the envelope id.

### `assert_json_serializer(app)`

Raises `InvalidConfigError` unless `task_serializer` and `result_serializer` are `"json"` and neither `accept_content` nor `result_accept_content` admits pickle or YAML, by name or by MIME type (`application/x-python-serialize`, `application/x-yaml`; see `UNSAFE_CONTENT`). `result.get()` deserialises with the *result* settings, so both matter. `celery_service`, `@statechart_task`, `connect_signals` and `poll_results` all call it. See [Event-driven architecture](../integration-eda/).

### Every other public name

The rest of `xstate_statemachine.contrib.celery.__all__`:

| Name | Kind | What it is / when you use it |
|:--|:--|:--|
| `HEADER_KEY` = `"xsm_store_key"`, `HEADER_INVOCATION` = `"xsm_invocation_id"` | constants | The two task headers `celery_service` attaches so a worker can find the persisted instance and the invocation. `deliver_result` trusts them only after the instance itself confirms the task id. |
| `register_task(app, fn, **options)` | function | What every task here is registered through: ``shared=False`` (a Celery task is `shared=True` by default and is RE-CREATED on every app built later, with the FIRST app's closure -- a second app's Beat scan ran against the first app's store, #292 battle) and a taken name is refused with `InvalidConfigError` instead of silently returning the existing task. Pass `name=` to register two schedulers / relays / statechart tasks on one app. |
| `UNSAFE_CONTENT` | constant | The serializer names and MIME types `assert_json_serializer` refuses (`pickle`, `application/x-python-serialize`, `yaml`, `application/x-yaml`, …). |
| `CeleryInvocation` | dataclass | What `poll_results` found for one pending invocation: `key`, `invocation_id`, `task_id`, `deadline`. Useful when you write your own poller or dashboard. |
| `PendingResult` | dataclass | A completion that arrived before its `_xsm_celery` record was saved: `key`, `invocation_id`, `task_id`, `result` / `error`, `parked_at`. |
| `MemoryPendingResults(ttl_s=...)` | class | The per-process table `connect_signals` parks a `PendingResult` in and `poll_results(pending=...)` drains; entries older than `ttl_s` are given up and logged. Completions that must survive a worker restart rely on `poll_results` reading the result backend. |
| `xsm_deadlines_every(scheduler, seconds=10.0)` | function | Builds the `beat_schedule` entry for `DurableTimerScheduler.task`: `app.conf.beat_schedule = xsm_deadlines_every(scheduler, 10)`. |

## Guarantees

> **What this does:** at-least-once completion delivery for `celery_service` (signals, `poll_results` and the live watcher are all idempotent, because a completion for a finished or replaced invocation is ignored); no lost update for `@statechart_task` under concurrent workers (an optimistic save and a Celery retry); matured `after` deadlines fire exactly once per state-entry generation while a Beat process runs; JSON-only task messages.
>
> **What this does not do:** it does not make your task idempotent (with `acks_late=True` a worker crash re-runs it, so make `fn` safe to repeat or dedup with an inbox). `revoke()` is best effort: a task that has already started keeps running, and its late result is discarded as stale. There is no exactly-once delivery, and no ordering between two different instances.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can publish to your Celery broker can run your tasks. The `xsm_*` headers are **not** trusted as delivered: `deliver_result` checks them against the persisted instance (key exists, invocation active, task id matches) before any completion is applied.
>
> **What it exposes:** task arguments and results travel through the broker and the result backend in clear JSON. Keep secrets out of `args_from` and task results, and use TLS on the broker (`rediss://`, `amqps://`).
>
> **You must configure:** JSON-only task **and** result serialisation (`task_serializer`, `result_serializer`, `accept_content`, `result_accept_content` with no pickle or YAML; enforced by every entry point); broker credentials, TLS and ACLs; exactly one Beat process; a result backend for the live watcher and `poll_results`.

## Compatibility

| Celery | Python | Tested in CI |
|:--|:--|:--|
| 5.3 – latest | 3.9 – 3.14 | ✅ (eager + in-process worker; live broker opt-in) |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[celery]"` | extra not installed | run the command |
| `InvalidConfigError: statechart tasks need task_serializer='json'` (or `result_serializer`, or `… allows pickle`) | pickle / YAML configured | JSON for tasks and results; drop pickle / YAML (and their MIME types) from both accept lists |
| The instance never leaves the invoking state after a `persisted()` block | durable mode with no delivery path | schedule `poll_results` (the durable path); `connect_signals` only speeds it up |
| "stale celery completion … ignored" in the logs | the state was left (or re-entered) before the task finished | expected: the late result is discarded |
| `after` timers of stored instances never fire | no Beat process runs the scan task | add `xsm_deadlines_every(scheduler)` to `beat_schedule` |
