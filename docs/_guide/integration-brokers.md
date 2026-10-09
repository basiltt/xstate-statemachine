---
title: "Broker adapters"
description: "Redis Streams, Kafka, RabbitMQ, NATS JetStream and Amazon SQS adapters for the EDA core: at-least-once delivery, per-subject order, poison to the dead-letter queue."
---

# Brokers

The [EDA core](../integration-eda/) defines one small `BrokerAdapter` contract (`publish`, `subscribe`, `ack`, `nack`) and an in-memory fake. The adapters on this page put it on a real broker. Each adapter stays **thin over its own client**: no new consistency model, no lowest common denominator. What they add is the part the research found missing from broker clients (*reconnect-but-never-resume*, *silent stall/duplicate*): redelivery counts become envelope attempts, so poison is dead-lettered even across restarts; health callbacks; and a size cap enforced before parsing. The same `InboundDispatcher`, inbox and outbox work unchanged on every broker.

## Choosing a broker

| Broker | Extra | Ordering key → | Redelivery signal | Pick it when |
|:--|:--|:--|:--|:--|
| Redis Streams | `[redis]` | one stream (or `crc32(subject) % shards`) | PEL delivery count | you already run Redis for the store |
| Kafka | `[kafka]` | message key → partition | committed offset | high volume, replay, many consumer groups |
| RabbitMQ | `[rabbitmq]` | queue order (or consistent-hash exchange on `subject`) | `x-delivery-count` / `redelivered` | work queues, routing, an existing AMQP estate |
| NATS JetStream | `[nats]` | `<topic>.<subject>` in one stream | `num_delivered` | lightweight, edge, many small services |
| Amazon SQS | `[sqs]` | FIFO `MessageGroupId` | `ApproximateReceiveCount` | serverless / AWS, nothing to operate |

## Install

```bash
pip install "xstate-statemachine[redis]"     # Redis Streams
pip install "xstate-statemachine[kafka]"     # aiokafka>=0.10
pip install "xstate-statemachine[rabbitmq]"  # aio-pika>=9
pip install "xstate-statemachine[nats]"      # nats-py>=2
pip install "xstate-statemachine[sqs]"       # boto3>=1.28
```

Tested versions are in the [compatibility table](#compatibility). The contract suite runs in CI against fakeredis, moto, and in-memory stand-ins for the aiokafka, aio-pika and nats-py client objects. An opt-in job (`XSM_CONTAINERS=1`, manually triggered) runs it against real brokers in testcontainers.

For a complete, runnable app -- the same choreography on the fake broker and on **all five adapters** (Redis Streams, Kafka, RabbitMQ, NATS JetStream, SQS), offline over in-process stand-ins (fakeredis, fake client objects, moto) or against a live server via an environment variable (`python -m eda_fulfilment --broker kafka`), a crashed consumer's messages redelivered with their attempt count through each broker's own redelivery path, an oversize message dead-lettered as `corrupt`, and a parametrised test suite -- see the [`eda_fulfilment` example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/eda_fulfilment).

## Quick start

<!-- doc-requires: redis, fakeredis -->
```python
import asyncio

import fakeredis                                   # stand-in for redis.Redis.from_url(...)
from xstate_statemachine import MachineLogic, create_machine
from xstate_statemachine.contrib.brokers.redis_streams import RedisStreamsBroker
from xstate_statemachine.eda import Envelope, InboundDispatcher
from xstate_statemachine.persistence import MemoryStore
from xstate_statemachine.persistence.idempotency import MemoryInbox

order = create_machine(
    {"id": "order", "initial": "open", "context": {"total": 0},
     "states": {"open": {"on": {"PAY": {"target": "paid", "actions": "setTotal"}}},
                "paid": {"type": "final"}}},
    logic=MachineLogic(actions={
        "setTotal": lambda i, ctx, e, a: ctx.update(total=e.payload["total"])}))

broker = RedisStreamsBroker(fakeredis.FakeRedis(), prefix="shop", group="orders-svc")
store = MemoryStore()
dispatcher = InboundDispatcher(store, {"xsm.order.PAY": order}, inbox=MemoryInbox())


async def main() -> None:
    cmd = Envelope.new(type="xsm.order.PAY", subject="o-42", data={"total": 99})
    await broker.publish("orders", cmd)
    await broker.publish("orders", cmd)            # a redelivery / double publish
    result = await dispatcher.run_once(broker, "orders", timeout=0.1)
    assert (result.processed, result.duplicates) == (1, 1)


asyncio.run(main())
assert '"total": 99' in store.load("o-42").snapshot
```

Replace the constructor to change brokers. The rest of the code stays the same:

```text
KafkaBroker(bootstrap_servers="kafka:9092", group_id="orders-svc")
RabbitMQBroker(url="amqps://user:pw@rabbit/")
NatsBroker(servers="nats://nats:4222", durable="orders-svc")
SqsBroker(region_name="eu-west-1")               # topic = queue name, e.g. "orders.fifo"
```

## Reference

Every adapter module is `xstate_statemachine.contrib.brokers.<name>` and raises `MissingExtraError` for its own extra only. Every adapter accepts these keyword arguments:

| Argument | Default | Meaning |
|:--|:--|:--|
| `max_bytes` | 1 MiB | Inbound envelopes larger than this are rejected **before** JSON parsing (X0.4); outbound ones raise `EnvelopeTooLargeError`. |
| `on_disconnect(exc)` | `None` | Called once when a broker call starts failing (`healthy` becomes `False`). |
| `on_reconnect()` | `None` | Called once when a call succeeds again. The client's own reconnect logic does the reconnecting; this makes it observable. |
| `on_undecodable(topic, raw, exc)` | log a warning | A message that is not a valid envelope. It is then dropped (acked) and never redelivered in a loop. The body is never logged. |
| `dead_letters` | `None` | A `DeadLetterStore`. Undecodable and oversized messages are recorded here (`reason="corrupt"`, size and error only, **never the body**) before they are dropped (X0.8). Pass the same store as `InboundDispatcher(dead_letters=)`. |

Shared semantics (`contrib.brokers._base`):

- **Local requeue.** `nack(d, requeue=True)` puts the delivery back at the head of a local buffer with `attempt + 1`, so it is redelivered before anything fetched after it. The broker message stays un-acked, so a crash still means native redelivery.
- **Attempts.** A broker's own redelivery count is stamped with `Envelope.with_attempt`, so `InboundDispatcher` dead-letters a poison message at `max_attempts` even after a consumer restart (X0.8).
- **Local hold window.** Each adapter fetches a small batch (`batch`, default 10; Kafka 50) and keeps what is not yet handed out in a local buffer. The broker's redelivery clock keeps running meanwhile (JetStream `ack_wait`, SQS visibility timeout, Redis `min_idle_ms`). A buffered message older than **half** that window is released without an ack, and the broker redelivers it with a correct count. It is never handed out late with an inflated attempt number, which would dead-letter a healthy message. Keep `batch` near your `max_in_flight`.
- **Settle once.** The second `ack` / `nack` of a delivery is a no-op.
- **`nack(requeue=False)`** settles the message on the broker for good. Dead-lettering is the dispatcher's job (`DeadLetterStore` / `BrokerDeadLetterSink`).
- `in_flight`, `held(topic)`, `healthy`, `close()`.

Lower-level names, for writing an adapter of your own or testing one: each module also exports its transport (`RedisStreamsTransport`, `KafkaTransport`, `RabbitMQTransport`, `NatsTransport`, `SqsTransport`: the four native operations `send` / `fetch` / `ack` / `drop`, and nothing else), and `nats` exports `subject_token(subject)` (the NATS-safe token an envelope subject is published under). `contrib.brokers._base` exports `SyncBroker` and `AsyncBroker` (the shared bookkeeping over a blocking or an async transport), `Raw(body, native, attempts)` (one message as a transport fetched it), `ThreadedTransport` (runs a blocking transport on a worker thread) and `default_on_undecodable` (logs the topic and error type, never the body).

### Redis Streams: `RedisStreamsBroker` / `SyncRedisStreamsBroker`

`(client=None, *, url=None, prefix, group="xsm", consumer=hostname-pid, shards=1, min_idle_ms=60_000, maxlen=None, batch=10)`. Module `contrib.brokers.redis_streams`, extra `[redis]`. The key namespace follows [`contrib.redis`](../integration-redis/) (a mandatory `prefix`): `{prefix}:stream:{topic}`, or `…:{topic}:{n}` with `shards > 1`, where a subject always hashes (crc32) to the same shard. The consumer group is created lazily from id `0` (`MKSTREAM`). `ack` is `XACK`. Before reading new entries, a consumer claims entries a **dead** consumer left pending for at least `min_idle_ms` (`XAUTOCLAIM`). Their delivery count becomes the attempt, and entries the consumer holds itself are never re-claimed. `maxlen` trims approximately on `XADD`. The sync class calls redis-py directly; the async class runs the same calls on a worker thread, so one thread-safe client can back both.

Every consumer name ever used stays registered in the group until it is removed, and a crashed pod (default name `hostname-pid`) leaves one behind each time. Its pending entries are reclaimed, but the name accumulates, so run `XGROUP DELCONSUMER <stream> <group> <name>` for names with no pending entries (`XINFO CONSUMERS`), or pass a stable `consumer=` per replica.

### Kafka: `KafkaBroker`

`(*, bootstrap_servers, group_id="xsm", producer=None, consumer_factory=None, batch=50, client_kw=None)`. The message **key is `envelope.subject`**, so per-subject order is partition order. The body is structured-mode CloudEvents with `content-type`, `ce_id` and `ce_type` headers, and the producer is idempotent with `acks="all"`. Kafka has no per-message ack, so the adapter tracks the offsets it handed out and **commits only the contiguous settled prefix** per partition. After a crash, the group resumes from the first unsettled offset, and the messages after it are redelivered and deduped by the inbox. Kafka keeps no delivery count, and the adapters no longer trust a producer-supplied `xsmattempt` (a forged count could dead-letter a healthy message), so after a consumer restart a Kafka envelope starts again at attempt 0 -- poison detection there relies on `InboundDispatcher`'s own in-process counter. Pass TLS / SASL through `client_kw` (`security_protocol`, `ssl_context`, `sasl_*`).

### RabbitMQ: `RabbitMQBroker`

`(*, url=None, channel=None, exchange=None, prefetch=20, batch=10, connect_kw=None)`. Each topic is a durable queue of the same name, published through the default exchange as **persistent** messages (with `message_id`, `type`, and the CloudEvents content type). `ack` is `basic.ack`. `nack(requeue=False)` is `basic.reject(requeue=False)`, which a broker-side DLX would see. Attempts come from `x-delivery-count` (quorum queues) or `redelivered`. `basic.qos` only limits `basic.consume`, and the adapter polls with `basic.get`, so the adapter enforces `prefetch` itself: at most `prefetch` messages are un-acked (buffered plus handed out) at any time. To scale out and keep per-subject order, use the **consistent-hash exchange** recipe: pass `exchange="orders-hash"`, and the adapter publishes with `routing_key = subject`. Bind one queue per consumer yourself. `url` uses `connect_robust`, which reconnects.

### NATS JetStream: `NatsBroker`

`(*, servers=None, js=None, durable="xsm", ack_wait_s=30.0, batch=10, connect_kw=None)`. JetStream only: core NATS is at-most-once and is not supported. Topic `orders` is a stream capturing `orders.>`. An envelope is published on `orders.<subject>`, where `.`, `*`, `>` and whitespace in the subject become `_`, and `Nats-Msg-Id = envelope.id` (the server-side duplicate window drops a re-published outbox row). A durable pull consumer reads the stream in order. `ack` is +ACK, drop is +TERM, and attempts are `num_delivered - 1`. `ack_wait_s` is the redelivery timeout.

### Amazon SQS: `SqsBroker` / `SyncSqsBroker`

`(client=None, *, region_name=None, visibility_timeout_s=None, batch=10)`. The topic is a queue **name**. **FIFO queues** (`*.fifo`) get `MessageGroupId = subject` and `MessageDeduplicationId = envelope.id`. **Standard queues do not preserve order**, so use them only for charts that tolerate reordering. `ack` and drop both call `DeleteMessage`. Long polling waits up to 20 s. Attempts are `ApproximateReceiveCount - 1`. `extend_visibility(delivery, seconds)` keeps a slow delivery hidden (`await` it on the async class). A batch of up to 10 messages is received at once, and messages still waiting in the local buffer are subject to the same visibility clock. Size `visibility_timeout_s` for a whole batch: if it expires, SQS hands the message to another consumer (at-least-once; the inbox dedups). Credentials come only from boto3's own chain. For fan-out, publish to SNS and subscribe FIFO queues to it. **Deduplication window versus replay:** SQS drops a FIFO message whose `MessageDeduplicationId` was seen in the last **5 minutes**. `xsm dlq replay` re-publishes with the *same* envelope id (so the inbox dedups a double replay), so a replay within 5 minutes of the original publish is silently dropped by SQS. Wait out the window, or replay to a standard queue.

## Operations

**Reconnects.** The client reconnects; the adapter makes it observable. The first broker call that raises sets `healthy` to `False` and calls `on_disconnect(exc)` once (one `WARNING` log line with the exception *type* only, since client errors can embed a URL with credentials). The call's exception still reaches you: `publish` raises, and `OutboxRelay` keeps the outbox row for the next tick, so nothing is lost. The first call that succeeds again sets `healthy` back to `True` and calls `on_reconnect()` once. Wire `healthy` into your readiness probe.

**What to alert on.** `healthy` staying `False` (or `on_disconnect` without a matching `on_reconnect` within a few minutes); a growing dead-letter store (`xsm dlq list`), especially `reason="corrupt"` (someone is publishing non-envelopes); outbox rows older than a few relay intervals; the broker's own consumer lag (Kafka group lag, Redis `XPENDING`, JetStream `num_pending`, SQS `ApproximateAgeOfOldestMessage`, RabbitMQ queue depth).

| Broker | Redelivery window knob | Sizing | Watch |
|:--|:--|:--|:--|
| Redis Streams | `min_idle_ms` (default 60 s): a dead consumer's pending entries are reclaimed after this | above your slowest handler; `batch` near `max_in_flight`; `maxlen` for retention | `XPENDING`, `XINFO CONSUMERS` (stale names) |
| Kafka | none per message: a crash rewinds to the first unsettled offset of the group | partitions ≥ consumers in the group (`group_id`); `batch` (50) | consumer-group lag |
| RabbitMQ | channel close / connection loss returns un-acked messages | `prefetch` (20) bounds un-acked per consumer | queue depth, unacked count |
| NATS JetStream | `ack_wait_s` (30 s) | above your slowest handler; `batch` (10) | `num_pending`, `num_redelivered` |
| SQS | `visibility_timeout_s` (queue default 30 s); `extend_visibility()` for a slow one | above the time to handle a whole `batch` (≤ 10) | `ApproximateAgeOfOldestMessage`, the queue's redrive DLQ |

A message fetched into the local buffer and not handed out within **half** the window is released (not acked) so the broker redelivers it; see *Local hold window* above.

## Guarantees

> **What this does:** at-least-once delivery on every broker, and effectively-once *processing* when you pass an inbox to `InboundDispatcher` (redeliveries are answered, not re-run). Order is per subject: publish order is kept for one `subject` on one topic **as long as one consumer handles that subject**. Kafka (one partition per consumer in the group) and SQS FIFO (a message group is locked to one receiver) do this for you. On Redis Streams (one stream), RabbitMQ (one queue) and NATS (one durable), consumers that compete on the same topic each get the next batch, so two of them can handle one subject's messages concurrently and out of order. Run one consumer per stream, or use Redis `shards` with one consumer per shard, the RabbitMQ consistent-hash exchange with one queue per consumer, or NATS subject filters. Poison envelopes are dead-lettered after `max_attempts`, counting the broker's own redeliveries, and acked (X0.8). An oversized or undecodable message is dropped, never looped. On all five brokers, a consumer that stops or crashes mid-batch resumes without losing an envelope; this is tested with a container restart.
>
> **Deduplication at the broker.** NATS JetStream (`Nats-Msg-Id = envelope.id`, default 2-minute window) and SQS FIFO (`MessageDeduplicationId = envelope.id`, 5 minutes) drop a re-published envelope **at publish**, so the inbox never sees that duplicate and `InboundDispatcher` reports `duplicates == 0` for it. Redis Streams, Kafka and RabbitMQ deliver it again, and the inbox answers it (`duplicates == 1`). Either way the machine runs once. Do not alert on the duplicate counter being zero on NATS or SQS.
>
> **What this does not do:** no exactly-once delivery, and no global ordering across subjects. Standard SQS queues have no order at all. Kafka carries no broker-side delivery count. Broker-level retention, replication and DLX policy stay your broker's configuration.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can publish to a topic can drive your machines. Forging an event, or a [Celery](../integration-celery/) task completion, therefore requires **write access to the broker**. That is the boundary to protect. Treat **bus messages as untrusted input**, and authenticate producers with the broker's own ACLs (Kafka ACLs, RabbitMQ vhost/user permissions, NATS accounts, SQS queue policies, Redis ACL users). Envelope extensions that look like credentials are refused or dropped (X0.8), and `type` → machine mapping is an explicit allow-list (`machine_for_type`).
>
> **What it exposes:** envelopes travel as structured CloudEvents JSON. `data` is visible to anyone who can read the topic. `repr()` of an adapter never shows URLs or credentials.
>
> **You must configure:** broker credentials and **TLS** (`rediss://`, `security_protocol="SSL"`, `amqps://`, NATS `tls=`, HTTPS for SQS, which is the default); per-topic ACLs; `max_bytes` (X0.4) at or below your broker's message size limit; a `DeadLetterStore` you monitor (X0.8); `max_in_flight` / `prefetch` for backpressure.

## Compatibility

| Broker client | Python | Tested in CI |
|:--|:--|:--|
| redis 5 – latest (Streams) | 3.9 – 3.14 | ✅ fakeredis; live opt-in |
| aiokafka 0.10 – latest | 3.9 – 3.14 | ✅ in-memory stand-in; Redpanda opt-in |
| aio-pika 9 – latest | 3.9 – 3.14 | ✅ in-memory stand-in; RabbitMQ opt-in |
| nats-py 2 – latest | 3.9 – 3.14 | ✅ in-memory stand-in; NATS opt-in |
| boto3 1.28 – latest | 3.9 – 3.14 | ✅ moto; LocalStack opt-in |

Live broker suite: `XSM_CONTAINERS=1 pytest tests/contrib/brokers -m containers` (Docker required; images pinned by digest).

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[kafka]"` | extra not installed | run the command |
| Envelopes of one subject arrive out of order on SQS | a standard queue | use a `.fifo` queue |
| The same envelope is processed twice | at-least-once redelivery | pass `inbox=` to `InboundDispatcher` |
| A poison message loops on Kafka after restarts | Kafka has no delivery count and the adapter does not trust a producer's `xsmattempt` | keep the consumer up long enough for `max_attempts` in-process deliveries, or lower `max_attempts`; `xsm dlq` the message by hand |
| Redis entries of a crashed consumer are never processed | `min_idle_ms` not reached yet | wait, or lower `min_idle_ms` (never below your handler time) |
| "dropping undecodable message" warnings | non-CloudEvents producers on the topic | fix the producer, or use a separate topic |
| `MissingExtraError: … pip install "xstate-statemachine[redis]"` (or `[rabbitmq]`, `[nats]`, `[sqs]`) | importing `contrib.brokers.<name>` without its extra | install the extra the message names |
| `BUSYGROUP Consumer Group name already exists` in a Redis log | another process created the group first | nothing: the adapter treats it as success |
| `ResponseError: NOGROUP` / no such stream (Redis) | the stream or group was deleted under a running consumer | restart the consumer: it recreates both (`MKSTREAM`) |
| `QueueDoesNotExist` (SQS) on publish or subscribe | the topic is a queue **name** that does not exist in this region/account | create the queue (FIFO names end in `.fifo`); the adapter never creates queues |
| `healthy` is `False`, `on_disconnect` fired, one `broker call failed: <Type>` warning | the broker is unreachable | nothing to do in the app: the client reconnects, `on_reconnect` fires, the outbox keeps unsent rows. Alert if it lasts |
| A message is processed later than expected and arrives with a higher attempt | the local hold window released it to the broker (it waited longer than half the redelivery window) | lower `batch`, or raise `ack_wait_s` / `visibility_timeout_s` / `min_idle_ms` |
| A replayed or re-published envelope is never processed on SQS FIFO or NATS | the broker's dedup window dropped the same envelope id (SQS 5 min, NATS 2 min default) | wait out the window; or publish a new envelope |
| Two *different* messages collapse into one on an SQS FIFO queue | the queue has content-based deduplication and a non-xsm producer sends identical bodies | the adapter always sets `MessageDeduplicationId`; give other producers their own id |
| After a Kafka consumer crash, already-processed messages come back | offsets after the first unsettled one were never committed | expected: the inbox answers them (`duplicates`) |
| `TypeError: _Core.__init__() got an unexpected keyword argument 'sasl_…'` | client options passed as adapter keywords | pass them in `client_kw=` (Kafka) or `connect_kw=` (RabbitMQ, NATS) |
