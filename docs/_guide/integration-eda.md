---
title: "Event-driven architecture"
description: "CloudEvents envelopes, a consumer loop with dedup and per-subject ordering, a transactional outbox, dead letters with safe replay, sagas, choreography and AsyncAPI -- generated from your charts."
---

# Event-driven architecture

Event-driven services built on state machines keep re-writing the same plumbing: a message envelope, a consumer loop that loads the right instance and survives redelivery, an outbox so a published event and the state change it describes cannot disagree, a dead-letter queue that is safe to replay, and sagas with compensation. `xstate_statemachine.eda` ships that plumbing in **core, with zero dependencies**, and the chart itself declares what is published, so the AsyncAPI document of your service is generated from the same JSON that runs it.

The real brokers (Redis Streams, Kafka, RabbitMQ, NATS JetStream and Amazon SQS) implement the `BrokerAdapter` protocol defined here. They are documented on [Brokers](../integration-brokers/), which includes a **choosing a broker** table. `FakeBrokerAdapter` lets you build and test the whole flow in-process with no broker at all. For Celery workers, Beat-driven `after` timers and an outbox relay task, see [Celery](../integration-celery/).

## Install

Nothing to install for the core: `from xstate_statemachine.eda import ...`. The `[cloudevents]` extra only adds interop with the official CloudEvents SDK and its HTTP binary / structured helpers:

```bash
pip install "xstate-statemachine[cloudevents]"
```

Requires `cloudevents>=1.10` (1.x and 2.x layouts are both supported). Tested versions are in the [compatibility table](#compatibility).

For a complete, runnable app -- an order chart and a warehouse chart in choreography, the SQLite outbox committed with the snapshot, inbox dedup, poison messages dead-lettered and listed with `xsm dlq`, and a test suite -- see the [`eda_fulfilment` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/eda_fulfilment).

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
| Poison | Attempts are the larger of the envelope's `xsmattempt` and the dispatcher's own count. At `max_attempts` the envelope is dead-lettered (`reason="max_attempts"`) and **acked**: never an infinite redelivery loop. The dispatcher's own count lives in the process (bounded LRU): with several consumers or a restart, a message can cycle up to `consumers × max_attempts` times unless the broker adapter reports its own delivery count, which the #294 adapters do on Redis Streams, RabbitMQ, NATS and SQS (not Kafka, which has none). The adapters do not trust a producer-supplied `xsmattempt`. |
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

#### Several relays on one outbox (leases)

You can run one relay per replica. `OutboxRelay(store, broker, *, batch=100, owner=None, lease_s=DEFAULT_CLAIM_LEASE_S)` does not read `pending()` when the store offers `claim()`. `SQLiteOutboxStore`, `SQLAlchemyOutboxStore` and `MemoryOutboxStore` all do. Instead, each run **leases** up to `batch` pending rows to its `owner` for `lease_s` seconds (default `30.0`), using the `claimed_by` / `claimed_until` columns. A second relay skips rows under a live lease, so two relays never publish the same row at the same time. A relay whose broker raises hands its unsent rows back at once with `release()`. A relay that **dies** cannot release, so its rows are picked up again when the lease expires. `owner` defaults to `host:pid:id(relay)`.

```python
from xstate_statemachine.eda import (
    Envelope, MemoryOutboxStore, OutboxRelay, SyncFakeBrokerAdapter,
)

outbox, broker = MemoryOutboxStore(), SyncFakeBrokerAdapter()
for n in range(10):
    outbox.add("orders", Envelope.new(type="order.paid", subject=f"o-{n}"))

# relay A claimed 4 rows and is still publishing them (or just died)
held = outbox.claim(limit=4, owner="relay-a", lease_s=30)

relay_b = OutboxRelay(outbox, broker, owner="relay-b", lease_s=30)
assert relay_b.relay_once_sync() == 6              # B skips A's leased rows
assert {e.subject for e in broker.published_on("orders")}.isdisjoint(
    {r.envelope.subject for r in held}
)
outbox.release([r.seq for r in held], owner="relay-a")   # A failed: hands back
assert relay_b.relay_once_sync() == 4               # nothing published twice
assert len(broker.published_on("orders")) == 10
```

Set `lease_s` well above the time one batch takes to publish (`batch` × the broker's worst publish latency). If a lease expires while its owner is still publishing, a second relay publishes the same rows too. That is a duplicate, not a loss, and the consumer's inbox dedups it. A store without `claim()` (your own `OutboxStore`) falls back to `pending()`, so run **one** relay per outbox there.

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

**A saga driven from the bus.** In production a saga is one persisted instance per business key, started by a command. Build it with `start_event=`, map `xsm.<saga>.<START>` to it in an `InboundDispatcher`, and give it the four stores. Two rules a newcomer trips over:

* **START's payload lives in `context["input"]`.** Each step's service receives its own `invoke.<step>` event, not the command -- read the data the saga was started with from `ctx["input"]` (the start event's payload, copied by the generated `sagaStart` action; `None` until START). The instance's identity is the envelope `subject`, which the dispatcher sets as `interp.store_key`.
* **`compensationFailed` is final.** A failing compensation parks the instance there, and `DeadLetterPlugin` writes a chart-state dead letter. That record is the operator's ticket: fix the cause by hand. A redelivered START does nothing (the instance is done).

```python
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.eda import (
    DeadLetterPlugin, Envelope, InboundDispatcher, MemoryDeadLetterStore,
    MemoryOutboxStore, OutboxPlugin, SyncFakeBrokerAdapter,
)
from xstate_statemachine.patterns import SagaBuilder
from xstate_statemachine.persistence import MemoryInbox, MemoryStore

saga = (
    SagaBuilder("fulfil", start_event="START")
    .step("reserve", invoke="reserveStock", compensate="releaseStock")
    .step("charge", invoke="chargeCard")
)
seen = []


def reserve(i, ctx, e):
    seen.append(i.store_key)          # the order id comes from the subject
    return {"hold": f"h-{i.store_key}"}


def charge(i, ctx, e):
    raise RuntimeError("card declined")


def release(i, ctx, e):               # idempotent: a restart may re-run it
    raise RuntimeError("warehouse API down")


machine = create_machine(saga.build(), logic=saga.logic().merge(MachineLogic(
    services={"reserveStock": reserve, "chargeCard": charge,
              "releaseStock": release},
)), strict_config=True)
store, bus, dlq = MemoryStore(), SyncFakeBrokerAdapter(), MemoryDeadLetterStore()
dispatcher = InboundDispatcher(
    store, {"xsm.fulfil.START": machine}, inbox=MemoryInbox(),
    plugins=[OutboxPlugin(MemoryOutboxStore(), topic="sagas"),
             DeadLetterPlugin(dlq)],
    dead_letters=dlq, on_unknown="ignore",
)
start = Envelope.new(type="xsm.fulfil.START", subject="o-42")
bus.publish("commands", start)
dispatcher.run_once_sync(bus, "commands")

assert seen == ["o-42"]
[letter] = dlq.list()                             # the operator's ticket
assert letter.state_id == "fulfil.compensationFailed"
assert [e["message"] for e in letter.errors] == [
    "card declined", "warehouse API down",        # cause, then the stuck undo
]
bus.publish("commands", start)                    # redelivered: a no-op
assert dispatcher.run_once_sync(bus, "commands").duplicates == 1
assert len(dlq.list()) == 1
```

`context.error` holds the **last** failure (here the compensation's); the dead letter's `errors` keeps the whole sequence.

`examples/integrations/eda_fulfilment/tests/test_battle_295_scenario.py` runs the same shape at scale (`SagaApp`): 90 SQLite-persisted sagas, a third failing at a different step, plus a `kill -9` in the middle of a compensation.

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

**Orchestration or choreography?** Use a saga when one business process owns the steps, needs compensation in a defined order, and someone must be able to answer "where is order 42?" by looking at one instance. Use choreography when services are owned by different teams and each only needs to react to facts, not to a plan. Choreography scales organisationally but spreads the process across machines, so the causation chain is the only thing that ties it together. Keep `correlationid` on every envelope. Choreography has no compensation of its own: an undo is just another event each service must handle, and nothing guarantees the order. A cycle between two routes is not caught by the engine's `RunawayChainError` (that guards one machine's internal chain); `run_until_quiet` stops it after `max_rounds` with a `RuntimeError`, and in production it simply loops on the bus.

| `xstate_statemachine.patterns` name | What it is |
|:--|:--|
| `SagaBuilder` | Fluent builder: `.step()`, `.on_failure()`, `.build()` → chart JSON, `.logic()` → the generic actions. |
| `SagaStep` | Frozen dataclass of one declared step (`name`, `invoke`, `compensate`, `timeout_ms`, `retry`); `SagaBuilder.steps` returns them. |
| `ChoreographyRouter` | `InboundDispatcher` over a `type → machine` map; `run_once`, `run_until_quiet`, `run_until_quiet_sync`. |
| `Route` | `NamedTuple(machine, event=None)`; the explicit form of a route value. |

### AsyncAPI

`asyncapi_document(machine, server={"host": ..., "protocol": ...}, inbound_topic=..., outbound_topic="events")` returns an **AsyncAPI 3.0.0** document. It lists the events the chart consumes (its `on` keys, as `xsm.<machine>.<EVENT>` CloudEvents) and the events it publishes (from `publish_specs`), with CloudEvents message payloads. `validate_asyncapi(doc)` checks it against the AsyncAPI 3.0.0 JSON Schema, which is **vendored** in the package so validation works offline (it needs `jsonschema`). From the CLI:

```bash
xsm asyncapi order.json -o asyncapi.json --server localhost:9092 --protocol kafka --validate
xsm docs order.json      # the generated page now has an "Integration events" section
```

### Every other public name

The rest of `xstate_statemachine.eda.__all__`, for readers who grep. Everything below imports from `xstate_statemachine.eda`.

| Name | Kind | What it is / when you use it |
|:--|:--|:--|
| `DispatchResult` | dataclass | What one `InboundDispatcher.run_once()` / `handle()` did: `processed`, `duplicates`, `dead_lettered`, `retried`, `ignored` counts plus per-envelope `outcomes`. Assert on it in tests; log it in a worker loop. |
| `Delivery` | NamedTuple | One received envelope plus the callables that settle it (`ack()` / `nack(requeue)`; settling twice is a no-op). Adapters yield these; you only touch them when writing your own `BrokerAdapter`. |
| `OutboxRecord` | NamedTuple | One pending outbox row: `seq`, `topic`, `envelope`. What `OutboxStore.pending()` returns and `OutboxRelay` publishes. |
| `MemoryOutboxStore` | class | In-memory `OutboxStore` for tests; pairs with `MemoryStore`. Production uses `SQLiteOutboxStore` / `SQLAlchemyOutboxStore` / `DjangoOutboxStore`. |
| `MemoryDeadLetterStore` | class | Thread-safe in-memory dead-letter store and the reference store shape; production uses `SQLiteDeadLetterStore` or a `BrokerDeadLetterSink`. |
| `ReplayResult` | dataclass | Returned by `replay_dead_letter` and `xsm dlq replay`: `record_id`, `dry_run`, `outcome`, `warnings`. |
| `ReplayRefusedError` | exception | A dead-letter replay was refused: the record has no envelope, its `machine_hash` / `machine_version` differ from the dispatcher's machine (pass `force=True` to override), or no `reason` was given. |
| `BrokerPublishError` | exception | The failure `FakeBrokerAdapter.fail_next_publish()` injects by default; catch it in tests that assert the outbox keeps the row on a failed publish. |
| `replay_dead_letter(dead_letters, record_id, dispatcher, *, reason, dry_run=True, force=False, actor=None)` | function | Re-send one dead-lettered envelope through a dispatcher, reusing its `id` so an inbox dedups a double replay; audited with *reason* / *actor*. Dry-run by default; `xsm dlq replay` wraps it. |
| `redact_record(record, keys=...)` | function | A `DeadLetter` with payload, snapshot and envelope data redacted (default key list covers passwords, tokens, secrets) before it is shown or exported (X0.5). |
| `consumed_events(machine)` | function | Every caller-sendable event the chart handles, sorted; feeds AsyncAPI and `xsm docs`. |
| `publish_specs(machine)` | function | Every publication the chart declares (`meta.publish` and `publish`-tagged states); feeds AsyncAPI and the `OutboxPlugin`. |
| `default_event_name(envelope_type)` | function | The dispatcher's default type→event mapping: `xsm.<machine>.<EVENT>` → `EVENT`; anything else unchanged. Pass `InboundDispatcher(event_type=...)` to override. |
| `dlq_topic(topic)` | function | `orders` → `orders.dlq`: the topic `BrokerDeadLetterSink` publishes to. |
| `SyncBrokerAdapter` | protocol | The blocking twin of `BrokerAdapter` (threads, Celery, Django): `publish`, `subscribe`, `ack`, `nack` without `await`. `SyncFakeBrokerAdapter` implements it. |
| `DEFAULT_CLAIM_LEASE_S` = `30.0` | constant | `OutboxRelay(lease_s=)` default: seconds a relay owns the rows it claimed before another relay may take them ([leases](#several-relays-on-one-outbox-leases)). |
| `new_id(now_ms=None)` | function | A UUIDv7-style id, lexicographically sortable by creation time; used for envelope ids. |
| `load_asyncapi_schema()` | function | The vendored AsyncAPI 3.0.0 JSON Schema as a dict (offline). |
| `PUBLISH_TAG` = `"publish"` | constant | The state tag that makes `OutboxPlugin` publish on entry. |
| `ATTEMPT_EXTENSION` = `"xsmattempt"` | constant | The CloudEvents extension carrying the delivery attempt (`Envelope.with_attempt`); adapters stamp the broker's redelivery count here (X0.8). |
| `DEFAULT_MAX_ATTEMPTS` = `5` | constant | `InboundDispatcher(max_attempts=)` default before an envelope is dead-lettered. |
| `DEFAULT_MAX_IN_FLIGHT` = `16` | constant | `InboundDispatcher(max_in_flight=)` default: concurrent subjects in flight. |
| `ASYNCAPI_VERSION` = `"3.0.0"`, `SPECVERSION` = `"1.0"` | constants | The AsyncAPI and CloudEvents spec versions the module emits. |

## Guarantees

> **What this does:** at-least-once delivery plus the inbox gives **effectively-once transitions**: a redelivered envelope is answered with the original receipt and never re-runs actions. Per-subject order is preserved within a consumer. A failed delivery is not committed and is retried, then dead-lettered and acked after `max_attempts`. With an `OutboxStore` sharing the state store's transaction under `PessimisticLock`, the outbox rows commit or roll back **with** the snapshot (`tests/eda/test_outbox.py::TestSQLiteTransactional::test_forced_failure_after_the_write_leaves_no_row`, `tests/contrib/sqlalchemy/test_sqlalchemy_outbox.py::TestSQLAlchemyOutbox::test_forced_rollback_leaves_no_row`). This fills steps 4–5 of the [order of operations](../guarantees/#the-order-of-operations).
>
> **What this does not do:** no exactly-once **publish**. The relay publishes then marks sent, so a crash in between publishes twice; consumers must dedup on the envelope id (the dispatcher does). Several relays may drain one outbox: row leases (`claim()` / `lease_s`) stop two live relays publishing the same row at once, but they do not make publishing exactly-once. A relay that dies mid-batch, or one that is still publishing when its lease expires, leaves rows another relay publishes again -- the duplicate window is **one batch per expired lease**, so size `lease_s` above the slowest batch you expect (`batch` × the broker's worst publish latency). A custom `OutboxStore` without `claim()` still needs **one** relay per outbox. The direct-broker sink is at-most-once-ish. There is no global order across subjects, and the leases do not order rows *across* relays. An `OptimisticLock` outbox is only transactional on stores whose save and outbox write share one transaction.
>
> **Sagas (`SagaBuilder`):** when step *k* fails (its service raises, or its `timeout_ms` fires), the compensations of the completed steps run in reverse, **once each per run**: entering a compensating state runs its invoke once. Step results are in `context.results[<step>]`, compensated steps in `context.compensated`, the last failure in `context.error`. A step with `retry=` re-runs after the policy's delay up to `max_attempts`, then compensates; a timeout counts as a failed attempt. The timeout **does not cancel** the service's work in an external system: the invoke is abandoned, so a late success is lost and the compensation must cope with a step that may have half-happened. **Compensations must be idempotent**: a process killed mid-compensation restarts the saga from its last snapshot and runs that compensation again. A failing compensation ends in `compensationFailed`, which is **final**: no retry, and a chart-state dead letter is written for a human. Services receive their own `invoke.<step>` event; the START event's payload is in `context.input` and identity comes from the instance key (`interp.store_key`). Under `OptimisticLock` a replica that loses the save race has already run the step's service (at-least-once): use `PessimisticLock` or idempotent services.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can publish to your topics. An envelope is untrusted input.
>
> **What it exposes:** envelopes are size-capped **before** parsing and shape-validated before `to_event()` (X0.4); a malformed or unknown envelope is dead-lettered, never raised. Credential-bearing extension names are refused, transport headers other than `ce-*` never become extensions, and `traceparent` is validated (X0.8). Poison messages cannot loop: an attempt counter dead-letters and acks after `max_attempts`, and `max_in_flight` bounds concurrency (X0.8). Dead letters, state-tag `data` and audit details are `redact()`ed before they are written; `SQLiteDeadLetterStore` / `SQLiteOutboxStore` files are created `0600` (X0.5).
>
> **You must configure:** an `inbox` in production (without one, redeliveries re-run); broker-level authentication and ACLs on who may publish which `type`; a `source` your consumers trust as the idempotency principal; DLQ replay only through `--no-dry-run --yes --reason` by an operator with access to the audit table; retention (`xsm dlq purge --older-than`, `SQLiteOutboxStore.purge_sent`).
>
> **Sagas and choreography on a shared bus:** a forged `done.invoke.<step>` / `error.platform.<step>` envelope cannot complete or fail a saga step. With the usual `{type: machine}` mapping such a type is unknown (acked or dead-lettered per `on_unknown`). Even a catch-all mapping that turns `xsm.fulfil.done.invoke.reserve` into the event `done.invoke.reserve` only delivers **user** traffic, and the engine drives `onDone` / `onError` / `after` from engine-minted events alone (provenance, #195/#203) — `tests/patterns/test_battle_295_b_saga_input.py::TestForgedCompletions`. Event *names* are a namespace, not a secret: anyone allowed to publish `xsm.fulfil.START` can start a saga, so the ACL on that type is the authorisation. Prefix saga and choreography types with your service (`fulfil.*`, `order.*`) so two teams on one bus cannot collide, and keep `on_unknown="ignore"` only on topics that really are shared.

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
| DLQ reason `corrupt` (`EnvelopeCorruptError`: `envelope attribute 'x' missing` / `must be a non-empty string` / `exceeds … characters`, `invalid CloudEvents extension name`, `… is an envelope attribute, not an extension`, `must be a string, integer or boolean`, `invalid W3C traceparent extension`, `xsmattempt must be a non-negative integer`, `envelope has no subject`, `envelope is not JSON`, `data` not a JSON object) | a producer sends a malformed envelope | fix the producer; the record keeps the redacted envelope for `xsm dlq show` |
| `EnvelopeCorruptError: extension 'authorization' looks credential-bearing` | a producer copied an auth header into the event | send credentials on the transport, never in the event |
| `EnvelopeTooLargeError` (DLQ reason `corrupt`) | the body is over the size cap (1 MiB default), checked before parsing | send a reference (object-store key) instead of the payload, or raise `max_bytes` deliberately |
| DLQ reason `max_attempts` | the machine's step kept failing (an action/service error) on every delivery, or a user hook (`machine_for_type` / `key_for` / `dedup_key`) raised for this envelope on every delivery | fix the cause, then `xsm dlq replay` |
| A message is redelivered again and again but never dead-lettered | the state store / inbox is DOWN (`StoreError`): an outage is not the message's fault, so it is requeued, never counted as poison | restore the store; the broker's own redelivery policy bounds the loop |
| DLQ reason `corrupt`: `envelope data is nested deeper than 64` | `data` nests past `MAX_DATA_DEPTH` -- it parses, but nothing downstream (redaction, the dead-letter writer) could walk it, so it used to be redelivered forever | flatten the payload (no real event is 64 levels deep) |
| DLQ reason `instance_done` | the subject's instance already reached a final state | usually correct (a late event); purge it, or route the type to a new instance key |
| DLQ reason `idempotency_mismatch` | the same envelope `id` arrived with a different event / payload than the one first processed | a producer reuses ids: mint a new id per event (`Envelope.new`) |
| The same message is processed twice | no `inbox=` on the dispatcher | pass `SQLiteInbox(store)` / `MemoryInbox()` |
| `xsm dlq replay` exits 2 with "use --force" | the chart changed since the message failed (`ReplayRefusedError`) | check the change is compatible, then add `--force` |
| `xsm dlq replay` exits 2: "no machine handles type …" | none of the `--machine` charts has the record's machine id | pass the right `--machine` (repeatable) |
| `xsm dlq replay` exits 2: "captured from a chart state, not an envelope" | a chart-driven (`DeadLetterPlugin`) record | restore its snapshot instead; only envelope dead letters replay |
| `xsm dlq replay` exits 2: "cannot import --logic" | `--logic` is not an importable dotted module | run from the project root or set `PYTHONPATH`; pass `myapp.order_logic`, not a file path |
| `xsm dlq replay` exits 1 | the replay ran and the machine failed again (outcome is not `processed` / `duplicate`) | the record stays unresolved; read `--json` output and the logs |
| `xsm dlq … ` exits 2: "no such … file" | the `--dlq` / `--store` path is wrong (the CLI never creates a database) -- or the application has not started yet: `SQLiteDeadLetterStore(...)` creates the file on first open, so a fresh deployment has no DLQ file until the service ran once | check the path (`sqlite:///rel.db` is relative, `sqlite:////abs.db` absolute); treat exit 2 before the first start as "not deployed", not "no dead letters" |
| Outbox row present after a failed request | the outbox is not sharing the store's transaction, or `OptimisticLock` is used | `SQLiteOutboxStore(same_store)` + `PessimisticLock()` |
| `sqlite3.OperationalError: no such column: claimed_by` | never on `SQLiteOutboxStore`: it adds the lease columns to a 0.11.0 `xsm_outbox` table on open | if you see it, a raw query ran before any store was opened; open the store first |
| SQLAlchemy: `StoreError: xsm_outbox lacks claimed_by, claimed_until` at startup (`create_table=False`) | the `xsm_outbox` table was created before the relay leases; with `create_table=True` the store adds the columns itself | add a migration with `claimed_by VARCHAR(128) NULL` and `claimed_until FLOAT NULL` (see `examples/integrations/sqlalchemy_orders` migration `0003`) |
| Pending outbox rows stay pending for `lease_s` after a relay crash | a dead relay cannot release its lease | expected; lower `lease_s` if that delay matters (not below one batch's publish time) |
| `ValueError: step name … must be an identifier` / `duplicate step` / `collides with step '<x>Retrying'` | `SagaBuilder.step()` names are state keys; a `retry=` step owns a generated `<step>Retrying` state | rename the step (`reserve_stock`, not `reserve-stock`) |
| `ValueError: timeout_ms must be a positive int` / `retry must be a RetryPolicy` / `invoke must be a non-empty string` / `start_event … is an engine-reserved event name` | a declaration the builder refuses up front rather than emit JSON that fails later | pass `timeout_ms=5000`, `retry=RetryPolicy(...)`, a service key, a plain event name such as `START` |
| `ValueError: a saga needs at least one step` | `build()` before any `.step()` | declare the steps first |
| A saga instance sits in `compensationFailed` and a dead letter (`reason` `dead_letter_state`) appeared | a compensation raised; the state is final by design | fix the external system by hand, then resolve the record (`xsm dlq … purge`); never "retry" by resending START (the instance is done) |
| A compensation ran twice for one saga | the process died mid-compensation and the saga restarted from its snapshot | expected: compensations must be idempotent (key them by `interp.store_key`) |
| A step service raises `KeyError` looking for the order id in `e.data` | services receive `invoke.<step>`, not the command | read `ctx["input"]` (START's payload) or `interp.store_key` (the envelope `subject`) |
| Two replicas under `OptimisticLock` ran a step's service twice | the replica that lost the save race had already run the service in memory (at-least-once, as the persistence guide says) | drive sagas under `PessimisticLock`, or make step services idempotent |
| `RuntimeError: choreography did not settle in N rounds (an event loop between machines?)` | two routes publish at each other forever (A's event routes to B, B's back to A), or a test bus never drains | break the cycle (a final state, a guard), or raise `max_rounds` for a genuinely long conversation |
| `ValueError: max_rounds must be >= 1` | `run_until_quiet(max_rounds=0)` | pass a positive count |
| A saga START is acked but nothing happens, `DispatchResult.ignored` grows | the shared bus dispatcher has no route for `xsm.<saga>.START` and `on_unknown="ignore"` (with `"dead_letter"` it is DLQ reason `unknown_event`) | add the type to the dispatcher's mapping |
| `MissingExtraError: jsonschema is not installed` (`validate_asyncapi`) / `xsm asyncapi: error: --validate needs jsonschema` | schema validation is optional | `pip install jsonschema` (the message also names an `[asyncapi]` extra that this release does not ship; install `jsonschema` directly); generation itself needs nothing |
| `jsonschema.ValidationError` from `validate_asyncapi` / `xsm asyncapi: error: document is not valid AsyncAPI 3.0: …` | a hand-edited document, or a `server=` dict missing `host` / `protocol` | fix the named field; `asyncapi_document` output itself always validates |
| `xsm asyncapi` exits 2: `cannot load machine` / `cannot write` / `--server must not be empty` | a missing or invalid machine file, an unwritable `-o`, an empty option | fix the path or option (exit codes in the [CLI reference](../cli/)) |

## Operations

**Sizing.** One dispatcher handles one subject at a time and up to `max_in_flight` (16) subjects concurrently. Scale out with more consumers on a partitioned topic: the broker keeps per-subject order, the inbox keeps redeliveries effectively-once. Run one `OutboxRelay` per replica if you like. With `batch=100`, a relay publishes at most 100 rows per `relay_once`, so schedule it often enough that `batch / interval` exceeds your peak publish rate.

**Lease tuning.** Use `lease_s` ≥ 3 × the slowest batch you have seen (`batch` × p99 publish latency). If it is too short, a slow relay's rows are published twice (duplicates, which the consumers dedup). If it is too long, rows held by a crashed relay wait that long. Give every relay a stable `owner` (e.g. the pod name), so a restarted pod reclaims its own rows at once (`claim()` also returns rows already leased to the same owner).

**Metrics to alert on.**

| Signal | How to read it | Alert when |
|:--|:--|:--|
| DLQ growth | `len(SQLiteDeadLetterStore.list(limit=…))` or `xsm dlq --dlq … list --json` → `count` | any new record (it is a human's job), or growth over N per hour |
| Outbox backlog | `outbox.count(pending_only=True)` | it rises for several relay intervals |
| Outbox pending age | `SELECT MIN(created_at) FROM xsm_outbox WHERE sent_at IS NULL` | older than a few `lease_s` (the relays are stuck or the broker is down) |
| Leased (`locked`) rows | `SELECT COUNT(*) FROM xsm_outbox WHERE sent_at IS NULL AND claimed_until > <now>` | stays above `batch` × relays (leases are not being released) |
| Dispatcher outcomes | `DispatchResult.retried` / `.dead_lettered` per `run_once` | `retried` keeps rising (an infrastructure fault) |

**Sagas in production.** A saga is a normal dispatcher-driven machine, so it scales like one: **one dispatcher per topic partition, not one per saga key**. Every instance lives in the shared store under its `subject`, the broker keeps per-subject order, and the `PessimisticLock` serialises the rare overlap. Run as many replicas as the topic has partitions. Step services run inside the dispatcher's delivery, so a slow step holds that subject's slot (one of `max_in_flight`) until it finishes or its `timeout_ms` fires. Give every step that calls a remote system a `timeout_ms`. Choreography is the same: one `ChoreographyRouter` per consumer group; its instances are keyed `<machine id>:<subject>`.

| Saga signal | How to read it | Alert when |
|:--|:--|:--|
| Stuck compensations | dead letters with `state_id` ending `.compensationFailed` (`xsm dlq … list --json`) | **any** — each one is money or stock in an inconsistent state, and only a human can close it |
| Compensation rate | `fulfil.*.compensated` events on the outbox topic vs `fulfil.*.completed` | the ratio jumps (a downstream outage is turning orders into refunds) |
| Saga age | instances not in a final state whose `StoredSnapshot` save time is older than the sum of the step timeouts plus retry delays | any — a saga that outlives its own timeouts is not being driven (no consumer, or a lost START) |
| Retry pressure | `context.attempt_<step>` above 1 at completion | sustained — the step is flaky, not failing |

**Retention.** Purge sent outbox rows with `SQLiteOutboxStore.purge_sent(older_than_s=86400)`. Purge resolved dead letters with `xsm dlq --dlq … purge --older-than 30d --yes --reason retention` (the purge is audited).

**`xsm dlq` exit codes.** `0` success. `1` a real replay ran and the outcome was not `processed` / `duplicate`. `2` refused input: a missing or non-SQLite `--dlq` / `--store` file (never created), an unsupported URL scheme, an unknown id, a bad `--older-than` / `--limit`, an unloadable `--machine` or `--logic`, a missing guard-rail flag (`--yes`, `--reason`), or a refused replay. Errors are one line on stderr, so `--json` stdout stays parseable.
