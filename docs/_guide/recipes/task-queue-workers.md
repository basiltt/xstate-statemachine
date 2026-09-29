---
title: "Recipe: RQ, arq and Dramatiq workers"
permalink: /guide/task-queue-workers/
description: "Drive a persisted statechart from background jobs: load, send one event, save under an optimistic version check, retry on ConflictError. Written by hand for RQ, arq and Dramatiq."
---

# Recipe: RQ, arq and Dramatiq workers

A background job that advances a statechart has one shape, whatever the queue: **load the snapshot, send one event, save it**. The job carries only `(key, event, payload)`. It never carries a pickled interpreter. When two jobs for the same key race, one save raises `ConflictError`. The loser reloads and re-applies its event, so no update is lost. This page writes that loop once and hands it to three queues.

Files: [`examples/recipes/task_queue_workers/`](https://github.com/basiltt/xstate-statemachine/tree/main/examples/recipes/task_queue_workers).

```bash
xsm simulate examples/recipes/task_queue_workers/machine.json --events LABEL_PRINTED,PICKED_UP,SCANNED,SCANNED,DELIVERED
# -> shipment.delivered
```

## The loop

```python
import threading
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.persistence import ConflictError, MemoryStore, persisted

chart = {"id": "shipment", "initial": "pending", "context": {"scans": 0}, "states": {
    "pending": {"on": {"LABEL_PRINTED": "labelled"}},
    "labelled": {"on": {"PICKED_UP": "in_transit"}},
    "in_transit": {"on": {"SCANNED": {"actions": "countScan"}, "DELIVERED": "delivered"}},
    "delivered": {"type": "final"}}}
def count_scan(i, ctx, e, a): ctx["scans"] += 1
MACHINE = create_machine(chart, logic=MachineLogic(actions={"countScan": count_scan}))
STORE = MemoryStore()                      # SQLiteStore / RedisStore / SQLAlchemyStore in production

def apply_event(key: str, event: str, retries: int = 50) -> str:
    """The job body: load -> send -> save; reload and re-apply on a conflict."""
    for attempt in range(retries + 1):
        try:
            with persisted(STORE, key, MACHINE) as inst:
                inst.send(event)
                return inst.value
        except ConflictError:
            if attempt == retries:
                raise                      # the queue's retry / dead-letter takes over

apply_event("shipment.42", "LABEL_PRINTED")
apply_event("shipment.42", "PICKED_UP")
workers = [threading.Thread(target=apply_event, args=("shipment.42", "SCANNED")) for _ in range(8)]
[w.start() for w in workers]; [w.join() for w in workers]
import json
assert json.loads(STORE.load("shipment.42").snapshot)["context"]["scans"] == 8   # no lost update
```

`persisted_retry(store, key, machine, fn)` is the library's built-in form of the same loop, if you prefer not to write it yourself.

## Three queues, one function

<!-- doc-fragment -->
```python
# RQ -- a plain function; the worker imports it by dotted path
from rq import Queue
Queue(connection=redis).enqueue(queue_workers.rq_job, "shipment.42", "PICKED_UP")

# arq -- `async def job(ctx, ...)`, using `apersisted` on the async engine
class WorkerSettings:
    functions = [queue_workers.arq_job]
    on_startup = lambda ctx: queue_workers.configure(SQLiteStore("ship.db"))
await pool.enqueue_job("arq_job", "shipment.42", "PICKED_UP")

# Dramatiq -- wrap the function as an actor (done lazily, so importing the module needs no dramatiq)
send_event = queue_workers.dramatiq_actor()
send_event.send("shipment.42", "PICKED_UP")
```

(Sketch: it needs a Redis/RabbitMQ broker. The tested module is `queue_workers.py`.) Three things matter here, whatever the queue:

- **Configure the store once per worker process** (`configure(store)` at start-up). Do not open a connection per job.
- **Retry conflicts inside the job** and let the queue's retry policy handle everything else. A `ConflictError` is expected under concurrency. It is not a failure.
- **Keep payloads JSON.** The job arguments cross a broker, and the event payload ends up in the snapshot.

## Guarantees

> **What this does:** each job is one `persisted()` block. The load, the send and a save guarded by `expected_version` form one unit, so a concurrent job for the same key causes a `ConflictError` and a re-apply, never a lost update (tested: 8 threads, one key, 8 scans counted). An exception inside the block writes nothing.
>
> **What this does not do:** queues deliver **at least once**. A job retried after a successful save sends its event again. Give each event an id and attach `IdempotencyPlugin` (as in the [Stripe recipe](../stripe-webhooks/)) when a duplicate must be a no-op. Ordering between jobs for one key is whatever order the queue delivers them in. Nothing here is a distributed lock. Use `PessimisticLock()` if the work inside the block is slow and conflicts are frequent.

Related: [Persistence → locking](../persistence/), [all recipes](../recipes/).
