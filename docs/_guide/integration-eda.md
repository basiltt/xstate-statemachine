---
title: "Event-driven architecture"
description: "CloudEvents envelopes, a consumer loop with dedup and per-subject ordering, a transactional outbox, dead letters with safe replay, sagas, choreography and AsyncAPI -- generated from your charts."
---

# Event-driven architecture

Event-driven services built on state machines keep re-writing the same plumbing: a message envelope, a consumer loop that loads the right instance and survives redelivery, an outbox so a published event and the state change it describes cannot disagree, a dead-letter queue that is safe to replay, and sagas with compensation. `xstate_statemachine.eda` ships that plumbing in **core, with zero dependencies**, and the chart itself declares what is published, so the AsyncAPI document of your service is generated from the same JSON that runs it.

The real brokers (Kafka, RabbitMQ, NATS, SQS, Redis Streams) arrive with [#294](https://github.com/basiltt/xstate-statemachine/issues/294) and implement the `BrokerAdapter` protocol defined here. Until then, `FakeBrokerAdapter` lets you build and test the whole flow in-process.

## Install

Nothing to install for the core: `from xstate_statemachine.eda import ...`. The `[cloudevents]` extra only adds interop with the official CloudEvents SDK and its HTTP binary / structured helpers:

```bash
pip install "xstate-statemachine[cloudevents]"
```

Requires `cloudevents>=1.10` (1.x and 2.x layouts are both supported). Tested versions are in the [compatibility table](#compatibility).

## Quick start

A chart that publishes `order.paid` when it is paid, a consumer that turns inbound commands into events on the right persisted instance, and an outbox that stamps the causation chain:

```python
import asyncio

from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.eda import (
    Envelope,
    FakeBrokerAdapter,
    InboundDispatcher,
    OutboxPlugin,
)
from xstate_statemachine.persistence import MemoryInbox, MemoryStore

order = create_machine({
    "id": "order",
    "initial": "open",
    "context": {"total": 0},
    "states": {
        "open": {"on": {"PAY": {
            "target": "paid",
            "actions": "setTotal",
            "meta": {"publish": {"type": "order.paid", "data": ["total"]}},
        }}},
        "paid": {"type": "final"},
    },
}, logic=MachineLogic(actions={
    "setTotal": lambda i, ctx, e, a: ctx.update(total=e.payload["total"]),
}))

broker = FakeBrokerAdapter()
dispatcher = InboundDispatcher(
    MemoryStore(),                      # instances keyed by envelope.subject
    {"xsm.order.PAY": order},           # CloudEvents type -> machine
    inbox=MemoryInbox(),                # redeliveries are answered, not re-run
    plugins=[OutboxPlugin(broker, topic="order-events")],
)


async def main() -> None:
    cmd = Envelope.new(type="xsm.order.PAY", subject="o-42", data={"total": 99})
    await broker.deliver("orders", cmd)
    await broker.deliver("orders", cmd)  # the broker redelivers
    result = await dispatcher.run_once(broker, "orders")
    assert (result.processed, result.duplicates) == (1, 1)

    [paid] = broker.published_on("order-events")
    assert paid.type == "order.paid" and paid.data == {"total": 99}
    assert paid.causationid == cmd.id and paid.subject == "o-42"


asyncio.run(main())
```

## Reference

### Envelope

`Envelope` is a frozen CloudEvents 1.0 event: `specversion`, `id`, `type`, `source`, `subject`, `time`, `datacontenttype`, `data`, plus the extensions `correlationid`, `causationid`, `machineid`, `machineversion` and any further validated `extensions`.

- **`subject` is the machine instance key and the partition key.** Adapters preserve order per subject, never globally.
- **`id` is sortable** (`new_id()`: a UUIDv7-style value, 48-bit millisecond timestamp plus randomness, strictly increasing within a process). It is also the idempotency key.
- `Envelope.new(type=..., subject=..., data=...)` fills `id` and `time`. `Envelope.from_transition(interpreter, type=..., cause=inbound)` builds an outbound event whose `causationid` is the cause's id and whose `correlationid` is inherited, so a whole conversation shares one correlation id.
- `to_event()` validates first, then returns the `Event` the machine receives: `xsm.<machine>.<EVENT>` becomes `EVENT` and `data` (which must be a JSON object) becomes the payload.
- `to_json()` / `from_json()` use CloudEvents structured mode. `from_json` checks the byte size **before** parsing (the same 1 MiB default as snapshots), then the shape. A wrong shape raises `EnvelopeCorruptError`; an oversized one raises `EnvelopeTooLargeError`. Both are `XStateMachineError`s.
- Extension names that carry credentials (`authorization`, `cookie`, `*token*`, `*secret*`, `apikey`, `password`) are refused, and `traceparent` must match the W3C Trace Context grammar.
- `with_attempt(n)` / `.attempt` carry the delivery-attempt counter (`xsmattempt`) used for poison handling.

With the extra, `xstate_statemachine.contrib.cloudevents` adds `to_cloudevent()` / `from_cloudevent()` (SDK objects) and `to_binary()` / `to_structured()` / `from_http(headers, body)` (HTTP modes). `from_http` only reads `ce-*` headers and drops credential-bearing ones, so an `Authorization` header can never become an extension.

### Broker adapters

```text
BrokerAdapter (async)            SyncBrokerAdapter (threads, Celery, Django)
  await publish(topic, env)        publish(topic, env)
  async for d in subscribe(topic)  for d in subscribe(topic)
  await ack(d)                     ack(d)
  await nack(d, requeue=bool)      nack(d, requeue=bool)
```

A `Delivery` is `(envelope, topic, ack, nack)`. The contract is FIFO per subject, explicit settlement, requeue to the **head**, settling twice is a no-op, and a failed publish raises. `tests/eda/contract.py` is the suite every adapter runs.

`FakeBrokerAdapter` / `SyncFakeBrokerAdapter` are in-memory implementations for tests. Beyond the contract they record `published`, accept inbound traffic with `deliver()`, inject failures with `fail_next_publish()`, and run handlers synchronously with `on(topic, handler)` + `drain()`. `from xstate_statemachine.contrib.testing import FakeBrokerAdapter` also works (the `[testing]` extra re-exports it next to `replay()` and `assert_replay_consistent()`).

### Inbound dispatcher

`InboundDispatcher(store, machine_for_type, *, lock=OptimisticLock(), plugins=(), inbox=None, max_in_flight=16, max_attempts=5, dead_letters=None, ...)` is the consumer loop every adapter reuses: validate the envelope, find the machine for its `type`, then `lock.run(store, key=subject, machine, send(envelope.to_event()))`, then ack.

| Concern | Behaviour |
|:--|:--|
| Dedup | With an `inbox`, an `IdempotencyPlugin` keyed on `envelope.id` (principal = `envelope.source`) answers a redelivery with the original receipt. `dedup_key=` changes the key (sagas dedup on `causationid`). |
| Order | One subject is processed at a time; different subjects run concurrently up to `max_in_flight`. When a delivery is requeued, the later deliveries of the same subject in the batch are requeued behind it. |
| Poison | Attempts are the larger of the envelope's `xsmattempt` and the dispatcher's own count. At `max_attempts` the envelope is dead-lettered (`reason="max_attempts"`) and **acked**: never an infinite redelivery loop. The dispatcher's own count lives in the process (bounded LRU): with several consumers or a restart, a message can cycle up to `consumers × max_attempts` times unless the broker adapter republishes with `with_attempt(n + 1)` or reports its own delivery count, which the #294 adapters do. |
| Failure | An exception, or a receipt carrying an error, is **not committed** (`persisted()` skips the save) and the delivery is requeued. An infrastructure error outside the machine (dead-letter store or inbox down, a raising `machine_for_type`) is logged and requeued too; it never escapes into the loop. |
| Unknown / corrupt | An unknown `type` is dead-lettered as `unknown_event` (or acked with `on_unknown="ignore"`), a malformed envelope as `corrupt`, on the first attempt. Neither is raised into the loop. |
| Causation | The inbound envelope is attached to the interpreter so `OutboxPlugin` stamps `causationid` / `correlationid`. |

`run_once(broker, topic)` drains what is there now; `run_forever(broker, topic, stop_event)` loops; `run_once_sync(...)` is the sync twin; `handle(envelope)` processes one.

### Outbox

What is published is declared **in the chart**:

- `"meta": {"publish": {"type": "order.paid", "data": ["total"]}}` on a transition: `data` copies those context fields. `"publish": "order.paid"` (type only) and `"publish": true` (type `xsm.<machine>.transition.<target>`) also work. A malformed value fails loudly.
- `"tags": ["publish"]` on a state: entering it publishes `xsm.<machine>.transition.<state>` with the whole context, **redacted**.

`OutboxPlugin(sink, topic="events")` builds the envelopes during the step and hands them to the sink once the event has settled. The sink is either:

- an **`OutboxStore`**, which is transactional when it shares the state store's transaction: `SQLiteOutboxStore(sqlite_store)` (zero-dep) or `SQLAlchemyOutboxStore(sqlalchemy_store)` (`[sqlalchemy]`). `persisted()` writes the rows right after the snapshot save; under `PessimisticLock` the lock **is** the transaction, so a rollback drops the rows with the snapshot. `OutboxRelay(store, broker).relay_once()` then publishes pending rows in order and marks them sent only after the broker accepted them (at-least-once);
- a **`BrokerAdapter`** directly. Inside `persisted()` the publish is held until the block, including a `PessimisticLock` transaction, has exited cleanly, so a rolled-back state is never announced. It is still outside any transaction: a crash between the commit and the publish loses the message, so it is at-most-once-ish. Use it for tests and non-critical notifications.

`publish_specs(machine)` lists every publication a chart declares.

### Dead letters

Dead letters from both sources share one record, `DeadLetter`:

- **chart-driven**: `patterns.DeadLetterPlugin` captures entry into a `dead-letter`-tagged state (see [Patterns](../patterns/)), with the error chain and a redacted snapshot;
- **envelope-driven**: the dispatcher's `max_attempts`, `unknown_event` and `corrupt` cases, with the redacted envelope.

Every record carries the machine's `structure_hash` and `version` so a replay can refuse a different machine. Stores implement `DeadLetterStore` (`put`, `get`, `list`, `mark_resolved`, `delete`, `purge_older_than`): `MemoryDeadLetterStore` and `SQLiteDeadLetterStore` (the default; it redacts again on write and keeps an audit table). `BrokerDeadLetterSink(broker, "orders", store=...)` publishes each record to `orders.dlq` as `xsm.deadletter` and can also keep it in a store; pass it as the plugin's sink.

Operate them with the CLI:

```bash
xsm dlq --dlq sqlite:///dlq.db list [--all] [--json]
xsm dlq --dlq sqlite:///dlq.db show <id>
xsm dlq --dlq sqlite:///dlq.db replay <id> --store sqlite:///state.db \
    --machine order.json --logic myapp.order_logic --reason "fixed in 1.4.2"          # dry run
xsm dlq --dlq sqlite:///dlq.db replay <id> ... --no-dry-run --yes --reason "..."      # for real
xsm dlq --dlq sqlite:///dlq.db purge --older-than 30d --yes --reason "retention"
```

`replay` is a **dry run by default**. A real replay needs `--no-dry-run --yes --reason`. It reuses the envelope id, so the inbox deduplicates a double replay. It refuses when the machine's structure or version changed since capture unless you pass `--force`, marks the record resolved on success, and writes an audit row (who, why, when, outcome). `replay_dead_letter()` is the same operation from Python.

### Sagas

`patterns.SagaBuilder` turns an orchestrated saga into **plain chart JSON**: nothing is interpreted at runtime, the result is editable in Stately, and it is `strictConfig`-clean.

```python
from xstate_statemachine import MachineLogic, SimulatedClock, SyncInterpreter, create_machine
from xstate_statemachine.patterns import RetryPolicy, SagaBuilder

saga = (
    SagaBuilder("fulfil")
    .step("reserve", invoke="reserveStock", compensate="releaseStock",
          timeout_ms=5000, retry=RetryPolicy(max_attempts=3, jitter="none"))
    .step("charge", invoke="chargeCard", compensate="refundCard")
    .step("ship", invoke="ship")
    .on_failure("notifyOps")
)
config = saga.build()            # a dict you can json.dump and open in Stately

calls = []


def service(name, fail=False):
    def run(i, ctx, e):
        calls.append(name)
        if fail:
            raise RuntimeError(name)
        return f"{name}-ok"
    return run


logic = saga.logic().merge(MachineLogic(
    services={
        "reserveStock": service("reserve"), "releaseStock": service("release"),
        "chargeCard": service("charge"), "refundCard": service("refund"),
        "ship": service("ship", fail=True),
    },
    actions={"notifyOps": lambda i, ctx, e, a: None},
))
interp = SyncInterpreter(create_machine(config, logic=logic), clock=SimulatedClock()).start()
assert interp.current_state_ids == {"fulfil.failed"}
assert calls == ["reserve", "charge", "ship", "refund", "release"]   # reverse, once each
assert interp.context["compensated"] == ["charge", "reserve"]
```

The generated shape: `steps.<name>` invokes the step's service, with an `after` timeout and `onError` both leading to failure. A failure at step *k* enters `compensating.<k-1>`, then walks back to `compensating.<first>` and on to `failed`. Success leads to `completed`. A step with `retry=` fails into `steps.<name>Retrying`, which waits the policy's delay and re-enters the step while retries remain. A compensation that fails ends in `compensationFailed`, tagged `dead-letter` so `DeadLetterPlugin` captures it. Results are in `context.results`, compensated steps in `context.compensated` and the failure in `context.error`. Every step transition carries `meta.publish` (`fulfil.charge.completed`, `.failed`, `.compensated`), so with an `OutboxPlugin` the saga emits its own integration events.

To make completion idempotent when the upstream event may be re-minted with a new id, give the dispatcher `inbox=` and `dedup_key=lambda e: e.causationid or e.id`.

### Choreography

In choreography there is no orchestrator: each machine reacts to the integration events it cares about. `patterns.ChoreographyRouter` is an `InboundDispatcher` with a `type → (machine, EVENT)` mapping, instances stored as `<machine id>:<subject>` so several machines can share one business key, and unrouted types acked (a shared bus carries other services' events).

```python
import asyncio

from xstate_statemachine import create_machine
from xstate_statemachine.eda import Envelope, FakeBrokerAdapter, OutboxPlugin
from xstate_statemachine.patterns import ChoreographyRouter
from xstate_statemachine.persistence import MemoryInbox, MemoryStore

order = create_machine({"id": "order", "initial": "new", "states": {
    "new": {"on": {"PLACE": {"target": "awaiting", "meta": {"publish": "order.placed"}}}},
    "awaiting": {"on": {"PAID": {"target": "completed", "meta": {"publish": "order.completed"}}}},
    "completed": {"type": "final"},
}})
payment = create_machine({"id": "payment", "initial": "idle", "states": {
    "idle": {"on": {"CHARGE": {"target": "paid", "meta": {"publish": "payment.captured"}}}},
    "paid": {"type": "final"},
}})

bus, store = FakeBrokerAdapter(), MemoryStore()
router = ChoreographyRouter(
    store,
    {
        "xsm.order.PLACE": order,
        "order.placed": (payment, "CHARGE"),
        "payment.captured": (order, "PAID"),
    },
    plugins=[OutboxPlugin(bus, topic="events")],
    inbox=MemoryInbox(),
)


async def main() -> None:
    cmd = Envelope.new(type="xsm.order.PLACE", subject="o-1", correlationid="c-1")
    await bus.deliver("events", cmd)
    await router.run_until_quiet(bus)
    chain = {e.type: e for e in bus.published}
    assert chain["order.placed"].causationid == cmd.id
    assert chain["payment.captured"].causationid == chain["order.placed"].id
    assert chain["order.completed"].causationid == chain["payment.captured"].id
    assert {e.correlationid for e in bus.published} == {"c-1"}


asyncio.run(main())
```

**Orchestration or choreography?** Use a saga when one business process owns the steps, needs compensation in a defined order, and someone must be able to answer "where is order 42?" by looking at one instance. Use choreography when services are owned by different teams and each only needs to react to facts, not to a plan. Choreography scales organisationally but spreads the process across machines, so the causation chain is the only thing that ties it together. Keep `correlationid` on every envelope.

### AsyncAPI

`asyncapi_document(machine, server={"host": ..., "protocol": ...}, inbound_topic=..., outbound_topic="events")` returns an **AsyncAPI 3.0.0** document. It lists the events the chart consumes (its `on` keys, as `xsm.<machine>.<EVENT>` CloudEvents) and the events it publishes (from `publish_specs`), with CloudEvents message payloads. `validate_asyncapi(doc)` checks it against the AsyncAPI 3.0.0 JSON Schema, which is **vendored** in the package so validation works offline (it needs `jsonschema`). From the CLI:

```bash
xsm asyncapi order.json -o asyncapi.json --server localhost:9092 --protocol kafka --validate
xsm docs order.json      # the generated page now has an "Integration events" section
```

## Guarantees

> **What this does:** at-least-once delivery plus the inbox gives **effectively-once transitions**: a redelivered envelope is answered with the original receipt and never re-runs actions. Per-subject order is preserved within a consumer. A failed delivery is not committed and is retried, then dead-lettered and acked after `max_attempts`. With an `OutboxStore` sharing the state store's transaction under `PessimisticLock`, the outbox rows commit or roll back **with** the snapshot (`tests/eda/test_outbox.py::TestSQLiteTransactional::test_forced_failure_after_the_write_leaves_no_row`, `tests/contrib/sqlalchemy/test_sqlalchemy_outbox.py::TestSQLAlchemyOutbox::test_forced_rollback_leaves_no_row`). This fills steps 4–5 of the [order of operations](../guarantees/#the-order-of-operations).
>
> **What this does not do:** no exactly-once **publish**. The relay publishes then marks sent, so a crash in between publishes twice; consumers must dedup on the envelope id (the dispatcher does). The direct-broker sink is at-most-once-ish. There is no global order across subjects, and an `OptimisticLock` outbox is only transactional on stores whose save and outbox write share one transaction.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can publish to your topics. An envelope is untrusted input.
>
> **What it exposes:** envelopes are size-capped **before** parsing and shape-validated before `to_event()` (X0.4); a malformed or unknown envelope is dead-lettered, never raised. Credential-bearing extension names are refused, transport headers other than `ce-*` never become extensions, and `traceparent` is validated (X0.8). Poison messages cannot loop: an attempt counter dead-letters and acks after `max_attempts`, and `max_in_flight` bounds concurrency (X0.8). Dead letters, state-tag `data` and audit details are `redact()`ed before they are written; `SQLiteDeadLetterStore` / `SQLiteOutboxStore` files are created `0600` (X0.5).
>
> **You must configure:** an `inbox` in production (without one, redeliveries re-run); broker-level authentication and ACLs on who may publish which `type`; a `source` your consumers trust as the idempotency principal; DLQ replay only through `--no-dry-run --yes --reason` by an operator with access to the audit table; retention (`xsm dlq purge --older-than`, `SQLiteOutboxStore.purge_sent`).

## Compatibility

| Component | Python | Tested in CI |
|:--|:--|:--|
| Core `eda` (no extra) | 3.9 – 3.14 | ✅ (default test matrix) |
| `[cloudevents]` `cloudevents` 1.10 – 2.x | 3.9 – 3.14 | ✅ (see the [compatibility table](../compatibility/)) |
| `SQLAlchemyOutboxStore` (`[sqlalchemy]`) | 3.9 – 3.14 | ✅ |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[cloudevents]"` | SDK interop without the extra | run the command (the core envelope needs nothing) |
| Every message ends in the DLQ as `unknown_event` | the dispatcher's `machine_for_type` does not know the CloudEvents `type` | map the type, or use `on_unknown="ignore"` on a shared bus |
| `EnvelopeCorruptError: extension 'authorization' looks credential-bearing` | a producer copied an auth header into the event | send credentials on the transport, never in the event |
| The same message is processed twice | no `inbox=` on the dispatcher | pass `SQLiteInbox(store)` / `MemoryInbox()` |
| `xsm dlq replay` exits 2 with "use --force" | the chart changed since the message failed | check the change is compatible, then add `--force` |
| Outbox row present after a failed request | the outbox is not sharing the store's transaction, or `OptimisticLock` is used | `SQLiteOutboxStore(same_store)` + `PessimisticLock()` |
