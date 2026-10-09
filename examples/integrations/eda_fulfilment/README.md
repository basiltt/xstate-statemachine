# EDA fulfilment — two statecharts that talk only through events

Order fulfilment across two charts that never call each other. Every
hand-off is an event on a broker. This is the worked example for three
guide pages that had no app yet: the
[event-driven core](https://basiltt.github.io/xstate-statemachine/guide/integration-eda/),
[brokers](https://basiltt.github.io/xstate-statemachine/guide/integration-brokers/) +
[Celery](https://basiltt.github.io/xstate-statemachine/guide/integration-celery/), and
[observability](https://basiltt.github.io/xstate-statemachine/guide/integration-observability/) +
the [inspector](https://basiltt.github.io/xstate-statemachine/guide/integration-inspector/).

It runs with **no external services**. State, outbox, inbox, dead letters
and audit log live in one SQLite file in a temp directory. The broker is
`SyncFakeBrokerAdapter` or any of the five real adapters (Redis Streams,
Kafka, RabbitMQ, NATS, SQS) on an in-process stand-in. Celery runs in
`task_always_eager` mode. Prometheus, OpenTelemetry and the inspector
write to in-memory sinks.

```
checkout ──xsm.order.PAY──▶ order: placed ─▶ paid ──OrderPaid──▶ warehouse: waiting ─PACK─▶ packed
                                              │                                           │
                                              │ after 60 s ─▶ packingLate (PackingLate)   │
                                              ▼                                           │
                          order: packed ◀──PACKED──────────────────────OrderPacked────────┘
                              │ invoke shipOrder (Celery task)
                              ▼
                          shipped ──OrderShipped──▶
```

| File | What it is |
|:--|:--|
| `machine.json` | The `order` chart: `placed → paid → packed → shipped \| cancelled`, `meta.publish` on the transitions that are integration events, an `after` escalation on `paid`, and `actionErrorPolicy: "fail"` so a poison `PAYMENT_FAILED` is not committed. |
| `warehouse.json` | The `warehouse` chart: `PACK` publishes `OrderPacked`. |
| `logic.py` | Actions, the `hasTotal` guard and the deterministic fake carrier. |
| `app.py` | `build_app()` wires everything; `select_broker()`, `instrument()` and `run_demo()`. `SyncBridge` drives the async-only adapters from one private event loop. |
| `brokers_local.py` | The offline stand-ins for the real adapters: fake aiokafka / aio-pika / nats-py client objects (copies of the library's unit-test fakes), moto SQS, and `crash()`, which triggers each broker's own redelivery path. |
| `celery_app.py` | JSON-only Celery app, `ship_order` via `celery_service`, `@statechart_task` `handle_order_event`, `DurableTimerScheduler`, `outbox_relay_task`. |
| `__main__.py` | `python -m eda_fulfilment [--broker fake\|redis-streams\|kafka\|rabbitmq\|nats\|sqs]`. |
| `tests/` | Plain pytest. The suites for optional extras skip cleanly without them. |

## Run it

```bash
pip install "xstate-statemachine[redis,celery,observability]" "fakeredis[lua]" opentelemetry-sdk
cd examples/integrations
python -m eda_fulfilment                          # fake broker
python -m eda_fulfilment --broker redis-streams   # Redis Streams on fakeredis
python -m pytest eda_fulfilment/tests -q
```

### Run it against each broker

Every broker below uses the **real** adapter class from
`xstate_statemachine.contrib.brokers`. Only the client underneath changes:
offline it is an in-process stand-in; set the env var and it is a live
server. The summary has the same shape for each one.

| Broker | Offline stand-in | Live env var | Command |
|:--|:--|:--|:--|
| Redis Streams | `fakeredis` | `REDIS_URL` | `python -m eda_fulfilment --broker redis-streams` |
| Kafka | fake aiokafka producer/consumer (`brokers_local.FakeKafkaCluster`) | `XSM_KAFKA_BOOTSTRAP` (e.g. `localhost:9092`) | `python -m eda_fulfilment --broker kafka` |
| RabbitMQ | fake aio-pika channel (`brokers_local.FakeAmqpBroker`) | `XSM_RABBITMQ_URL` (e.g. `amqp://guest:guest@localhost/`) | `python -m eda_fulfilment --broker rabbitmq` |
| NATS JetStream | fake JetStream (`brokers_local.FakeJetStream`) | `XSM_NATS_URL` (e.g. `nats://localhost:4222`) | `python -m eda_fulfilment --broker nats` |
| SQS | `moto` (`mock_aws`), FIFO queue `events.fifo` | `XSM_SQS_ENDPOINT` (e.g. LocalStack `http://localhost:4566`) | `python -m eda_fulfilment --broker sqs` |

Install the matching extra first (`[redis]`, `[kafka]`, `[rabbitmq]`,
`[nats]`, `[sqs]`), plus `fakeredis[lua]` or `moto[sqs]` for the offline
Redis and SQS runs. Kafka, RabbitMQ and NATS adapters are async-only. The
app drives them through `SyncBridge`, one private event loop per adapter,
so the order and warehouse dispatch code is the same for every broker.
`tests/test_all_brokers.py` runs the demo on all five. It covers the
3 orders reaching `shipped`, outbox rows equal to published envelopes,
per-subject order, the poison envelope in the DLQ with
`attempts == 3`, and a crashed consumer's messages redelivered with their
attempt count. With `XSM_CONTAINERS=1` and Docker, it also runs the demo
against real containers, using the repository's pinned testcontainers
images.

What is faked, per broker:

- **Redis Streams.** fakeredis runs the real stream commands
  (`XREADGROUP`, `XAUTOCLAIM`) in process. No persistence, no cluster.
- **Kafka.** A partitioned log with committed offsets per group. There is
  **no rebalance**, since one consumer owns every partition. There is no
  replication and no retention, and nothing waits for the group-join
  delay. A restarted consumer re-reads from the last commit, as with real
  Kafka. Kafka keeps no delivery count, so a crash-redelivered envelope
  reports attempt 0 unless the envelope carried one.
- **RabbitMQ.** One in-memory deque per queue. Un-acked messages return
  with `redelivered=True` when their channel closes. There are no
  exchanges beyond the default, no `x-delivery-count` (quorum queues), and
  no QoS enforcement by the fake. The adapter enforces its own prefetch
  window.
- **NATS JetStream.** A stream per topic and a durable pull consumer with
  `num_delivered`. `ack_wait` never elapses on its own. The crash test
  expires it explicitly. The `Nats-Msg-Id` duplicate window never
  expires, so the demo's deliberate redelivery is dropped **at publish**
  and the summary shows `duplicates 0`. Real JetStream does the same
  within its default 2-minute window.
- **SQS.** moto emulates the SQS API in process: `MessageGroupId`
  ordering, `MessageDeduplicationId` dedup, `ApproximateReceiveCount`, and
  visibility timeouts. The FIFO deduplication id is the envelope id, but
  unlike real SQS, moto does not apply the 5-minute dedup interval to the
  redelivered envelope. The inbox absorbs it either way. The logical topic
  `events` maps to the queue `events.fifo`.

The demo places three orders, drives the choreography to `shipped`,
injects one poison message and redelivers one envelope. Then it prints the
counters: 9 transitions, 9 outbox rows = 9 published envelopes, 1 duplicate
answered from the inbox, 1 dead letter, plus the metric, span and
inspector-message counts.

Without Celery installed the app falls back to an in-process `shipOrder`
service. The core flow needs no extra at all.

From Python:

```python
import app

summary = app.run_demo("fake")
assert set(map(tuple, summary["orders"].values())) == {("order.shipped",)}
assert summary["outbox_rows"] == summary["published"] == 9
assert summary["dead_letters"] == 1 and summary["duplicates"] == 1
```

### Operate it: when the broker goes away

Every adapter has a `healthy` flag and two callbacks. The first broker
call that fails sets `healthy` to `False` and calls `on_disconnect(exc)`
once; the first call that succeeds again calls `on_reconnect()` once. The
client library does the reconnecting; the adapter only makes it
observable. While the broker is down, `OutboxRelay` cannot publish, so
the outbox **keeps its rows** and sends them on a later tick: nothing is
lost and nothing is sent twice to the machine (the inbox answers a
redelivery). `tests/test_battle_294_scenario.py` takes each of the five
brokers away mid-run and checks exactly this. Put `healthy` in your
readiness probe and alert when it stays `False`.

## The two charts

`xsm diagram machine.json -f mermaid`, with the `after` and `invoke` edges
(which the diagram export leaves out) added by hand:

```mermaid
stateDiagram-v2
[*] --> placed
placed --> paid : PAY [hasTotal] / publish OrderPaid
placed --> cancelled : PAYMENT_FAILED
placed --> cancelled : CANCEL
paid --> packingLate : after 60 s / publish PackingLate
paid --> packed : PACKED
paid --> cancelled : CANCEL
packingLate --> packed : PACKED
packingLate --> cancelled : CANCEL
packed --> shipped : done.invoke.shipOrder / publish OrderShipped
packed --> shippingFailed : error.platform.shipOrder
shippingFailed --> cancelled : CANCEL
shipped --> [*]
cancelled --> [*]
```

`xsm diagram warehouse.json -f mermaid`:

```mermaid
stateDiagram-v2
[*] --> waiting
waiting --> packed : PACK / publish OrderPacked
packed --> [*]
```

## Operate it

The poison `PAYMENT_FAILED` the demo sends ends up in the dead-letter
table of `state.db`, the same SQLite file as the state, outbox and inbox.
Run the commands from `examples/integrations/eda_fulfilment`, so that
`--logic logic` imports this folder's `logic.py`. Every command below is
run by `tests/test_readme_commands.py`:

```bash
DB=sqlite:///path/to/workdir/state.db   # FulfilmentApp(workdir) -> workdir/state.db
xsm dlq --dlq $DB list                                   # the poison, reason max_attempts
xsm dlq --dlq $DB list --json                            # {"count": 1, "dead_letters": [...]}
xsm dlq --dlq $DB show <id>                              # the redacted envelope + error chain
xsm dlq --dlq $DB replay <id> --store $DB \
    --machine machine.json --logic logic --reason "producer fixed"        # dry run
xsm dlq --dlq $DB replay <id> --store $DB \
    --machine machine.json --logic logic --no-dry-run --yes --reason "producer fixed"
xsm dlq --dlq $DB purge --id <id> --yes --reason "obsolete"              # audited
```

A replay of data that is still poison exits `1` and leaves the record
unresolved. A replay against a changed `machine.json` exits `2` until you
add `--force`. Every refused input is one line on stderr with exit `2`.

**Two replicas.** Run `FulfilmentApp(workdir, consumer="fulfilment-1")`
and `consumer="fulfilment-2"` on the same `state.db` and the same broker.
Each replica has its own `OutboxRelay`. The relays **lease** outbox rows
(`claimed_by` / `claimed_until`, `lease_s=30` by default), so they never
publish the same row at the same time. A relay killed mid-batch leaves
its rows to the other relay once the lease expires. The consumers' inbox
dedups any re-publication.
`tests/test_battle_293_scenario.py` runs 1,000 orders through two
replicas this way, including `kill -9` of a relay and of a consumer.

## Sagas

`tests/test_battle_295_scenario.py` adds a third service, `SagaApp`: an
orchestrated `SagaBuilder` saga (reserve → charge → ship, each with a
compensation) persisted in SQLite and driven by an `InboundDispatcher`
on `xsm.fulfil.START`. The saga's identity is the envelope `subject`
(`interp.store_key`); no step service sees START's payload. Its
compensations are **idempotent**: a `kill -9` mid-compensation restarts
the saga and runs that compensation again. A compensation that fails
parks the saga in the final `compensationFailed` state and writes a
chart-state dead letter, which is the operator's ticket.

Each chart's event contract is an AsyncAPI 3.0 document. Every command
below is run by `tests/test_readme_commands.py`:

```bash
xsm asyncapi machine.json                                # to stdout
xsm asyncapi warehouse.json -o asyncapi.json --server localhost:9092 --protocol kafka
xsm asyncapi machine.json --validate                     # needs jsonschema
```

Handled events appear as `consume.<EVENT>` messages (type
`xsm.order.<EVENT>`), published ones as `publish.<type>`. See
[EDA: sagas](https://basiltt.github.io/xstate-statemachine/guide/integration-eda/#sagas).

## How each piece maps to the guides

| Piece | Where | Guide |
|:--|:--|:--|
| `Envelope`, `ChoreographyRouter` (type → `(machine, EVENT)`, instances keyed `<machine>:<subject>`) | `app.FulfilmentApp` | [EDA: choreography](https://basiltt.github.io/xstate-statemachine/guide/integration-eda/) |
| `OutboxPlugin` → `SQLiteOutboxStore` on the **same** `SQLiteStore`, `PessimisticLock` (the rows commit with the snapshot), `OutboxRelay` | `app.FulfilmentApp`, `pump()` | [EDA: outbox](https://basiltt.github.io/xstate-statemachine/guide/integration-eda/) |
| `SQLiteInbox` dedup on the envelope id, `max_attempts=3`, `SQLiteDeadLetterStore`, `xsm dlq` | `app.FulfilmentApp` | [EDA: dead letters](https://basiltt.github.io/xstate-statemachine/guide/integration-eda/) |
| `AuditPlugin` → `SQLiteLog` | `app.FulfilmentApp.transitions()` | [Persistence](https://basiltt.github.io/xstate-statemachine/guide/persistence/) |
| `SyncRedisStreamsBroker` (`prefix`, consumer group, `min_idle_ms`, `max_bytes`, `dead_letters`) | `app.select_broker()` | [Brokers: Redis Streams](https://basiltt.github.io/xstate-statemachine/guide/integration-brokers/) |
| `celery_service`, `statechart_task`, `DurableTimerScheduler`, `outbox_relay_task`, `assert_json_serializer` | `celery_app.py` | [Celery](https://basiltt.github.io/xstate-statemachine/guide/integration-celery/) |
| `PrometheusPlugin`, `OpenTelemetryPlugin` | `app.instrument()` | [Observability](https://basiltt.github.io/xstate-statemachine/guide/integration-observability/) |
| `InspectorPlugin(MemorySink)` with a context allow-list, `replay_messages` | `app.instrument()` | [Inspector](https://basiltt.github.io/xstate-statemachine/guide/integration-inspector/) |

> **Guarantees**
>
> - **At-least-once delivery plus inbox dedup.** The relay may publish a row
>   twice (crash between publish and `mark_sent`), and a broker may
>   redeliver. The consumer's `SQLiteInbox`, keyed on the envelope id,
>   answers a repeat with the original receipt, so there is one transition
>   (`test_duplicate_envelope_is_a_single_transition`).
> - **The outbox commits with the snapshot.** The outbox rows, inbox mark
>   and audit rows share the snapshot's SQLite transaction under
>   `PessimisticLock`. A failed step writes none of them.
> - **Per-subject order.** One subject (order id) is processed at a time,
>   in delivery order (`test_per_subject_order_is_preserved`).
> - **No exactly-once.** Side effects outside the store (the carrier call)
>   can run more than once. Make them idempotent. Here the tracking id is
>   derived from the order id.

> **Threat model**
>
> - **X0.4 size caps.** The broker adapters check inbound bytes
>   (`max_bytes`) *before* parsing. An oversize or undecodable message is
>   dead-lettered with reason `corrupt`, and its body is **not** stored
>   (`test_oversize_envelope_is_dead_lettered_as_corrupt`).
> - **X0.8 poison → DLQ.** A message that keeps failing is dead-lettered
>   after `max_attempts` and acked, so it never loops forever. The attempt
>   count survives a consumer crash (`test_crashed_consumer_is_reclaimed_with_attempts`).
>   `xsm dlq replay` is a dry run by default.
> - **Serializer refusal.** Every Celery entry point refuses an app that
>   accepts pickle or YAML (`test_pickle_config_is_refused`). A forged or
>   stale task id completing an invoke is ignored and reported through
>   `on_event_dropped`.
> - **Telemetry hygiene.** Metric labels are machine, state and declared
>   event names only, never an order id or a payload value. The inspector
>   sends only the allow-listed context keys.

## Switch to a real broker

`select_broker()` reads `EDA_BROKER` (`fake` or `redis-streams`). For
`redis-streams`, `REDIS_URL` points it at a real server
(`rediss://` for TLS). Without it, the app uses an in-process `fakeredis`:

```bash
EDA_BROKER=redis-streams REDIS_URL=redis://localhost:6379/0 python -m eda_fulfilment
```

Kafka, RabbitMQ, NATS and SQS work the same way. Pick one with
`EDA_BROKER` / `--broker` and point it at a server with its env var (see
*Run it against each broker* above). For a real Celery worker, build the app with
`make_celery(eager=False)`, run a worker plus **exactly one** Beat process
with `xsm_deadlines_every(scheduler)`, and call `connect_signals()` so
completions are delivered durably.

## What is faked here

- **The broker.** `SyncFakeBrokerAdapter`, or a real adapter over an
  in-process stand-in (see the per-broker notes above). The adapter code
  is the real one.
- **Celery.** It runs in `task_always_eager` mode with the `memory://`
  transport. No worker process, no result backend.
- **The carrier.** `ship_order` returns `TRK-<order id>`.
- **Time.** The `after` escalation is driven by `SimulatedClock` and an
  injected `now`. Nothing sleeps.
- **Exporters.** Prometheus scrapes a private `CollectorRegistry`, OTel
  spans go to an `InMemorySpanExporter`, and inspector messages go to a
  `MemorySink` (swap in `SseSink` / `JsonLinesSink` for a live view).
