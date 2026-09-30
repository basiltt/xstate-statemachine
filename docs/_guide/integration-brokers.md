---
title: "Broker adapters"
description: "Redis Streams, Kafka, RabbitMQ, NATS JetStream and Amazon SQS adapters for the EDA core: at-least-once delivery, per-subject order, poison to the dead-letter queue."
---

# Brokers

The [EDA core](../integration-eda/) defines one small `BrokerAdapter` contract (`publish`, `subscribe`, `ack`, `nack`) and an in-memory fake. The adapters on this page put it on a real broker. Each adapter stays **thin over its own client**: no new consistency model, no lowest common denominator. What they add is the part the research found missing from broker clients (*reconnect-but-never-resume*, *silent stall/duplicate*): redelivery counts become envelope attempts, so poison is dead-lettered even across restarts; health callbacks; and a size cap enforced before parsing. The same `InboundDispatcher`, inbox and outbox work unchanged on every broker.

## Choosing a broker

| Broker | Extra | Ordering key → | Redelivery signal | Pick it when |
|:--|:--|:--|:--|:--|
| Redis Streams | `[redis]` | one stream (or `hash(subject) % shards`) | PEL delivery count | you already run Redis for the store |
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

Shared semantics (`contrib.brokers._base`):

- **Local requeue.** `nack(d, requeue=True)` puts the delivery back at the head of a local buffer with `attempt + 1`, so it is redelivered before anything fetched after it. The broker message stays un-acked, so a crash still means native redelivery.
- **Attempts.** A broker's own redelivery count is stamped with `Envelope.with_attempt`, so `InboundDispatcher` dead-letters a poison message at `max_attempts` even after a consumer restart (X0.8).
- **Settle once.** The second `ack` / `nack` of a delivery is a no-op.
- **`nack(requeue=False)`** settles the message on the broker for good. Dead-lettering is the dispatcher's job (`DeadLetterStore` / `BrokerDeadLetterSink`).
- `in_flight`, `held(topic)`, `healthy`, `close()`.

### Redis Streams: `RedisStreamsBroker` / `SyncRedisStreamsBroker`

`(client=None, *, url=None, prefix, group="xsm", consumer=hostname-pid, shards=1, min_idle_ms=60_000, maxlen=None, batch=100)`. Module `contrib.brokers.redis_streams`, extra `[redis]`. The key namespace follows [`contrib.redis`](../integration-redis/) (a mandatory `prefix`): `{prefix}:stream:{topic}`, or `…:{topic}:{n}` with `shards > 1`, where a subject always hashes (crc32) to the same shard. The consumer group is created lazily from id `0` (`MKSTREAM`). `ack` is `XACK`. Before reading new entries, a consumer claims entries a **dead** consumer left pending for at least `min_idle_ms` (`XAUTOCLAIM`). Their delivery count becomes the attempt, and entries the consumer holds itself are never re-claimed. `maxlen` trims approximately on `XADD`. The sync class calls redis-py directly; the async class runs the same calls on a worker thread, so one thread-safe client can back both.

### Kafka: `KafkaBroker`

`(*, bootstrap_servers, group_id="xsm", producer=None, consumer_factory=None, batch=100, client_kw=None)`. The message **key is `envelope.subject`**, so per-subject order is partition order. The body is structured-mode CloudEvents with `content-type`, `ce_id` and `ce_type` headers, and the producer is idempotent with `acks="all"`. Kafka has no per-message ack, so the adapter tracks the offsets it handed out and **commits only the contiguous settled prefix** per partition. After a crash, the group resumes from the first unsettled offset, and the messages after it are redelivered and deduped by the inbox. Kafka keeps no delivery count, so the attempt carried across a restart is the envelope's own `xsmattempt`. Pass TLS / SASL through `client_kw` (`security_protocol`, `ssl_context`, `sasl_*`).

### RabbitMQ: `RabbitMQBroker`

`(*, url=None, channel=None, exchange=None, prefetch=100, batch=100, connect_kw=None)`. Each topic is a durable queue of the same name, published through the default exchange as **persistent** messages (with `message_id`, `type`, and the CloudEvents content type). `ack` is `basic.ack`. `nack(requeue=False)` is `basic.reject(requeue=False)`, which a broker-side DLX would see. Attempts come from `x-delivery-count` (quorum queues) or `redelivered`. `prefetch` bounds the number of un-acked messages. To scale out and keep per-subject order, use the **consistent-hash exchange** recipe: pass `exchange="orders-hash"`, and the adapter publishes with `routing_key = subject`. Bind one queue per consumer yourself. `url` uses `connect_robust`, which reconnects.

### NATS JetStream: `NatsBroker`

`(*, servers=None, js=None, durable="xsm", ack_wait_s=30.0, batch=100, connect_kw=None)`. JetStream only: core NATS is at-most-once and is not supported. Topic `orders` is a stream capturing `orders.>`. An envelope is published on `orders.<subject>`, where `.`, `*`, `>` and whitespace in the subject become `_`, and `Nats-Msg-Id = envelope.id` (the server-side duplicate window drops a re-published outbox row). A durable pull consumer reads the stream in order. `ack` is +ACK, drop is +TERM, and attempts are `num_delivered - 1`. `ack_wait_s` is the redelivery timeout.

### Amazon SQS: `SqsBroker` / `SyncSqsBroker`

`(client=None, *, region_name=None, visibility_timeout_s=None)`. The topic is a queue **name**. **FIFO queues** (`*.fifo`) get `MessageGroupId = subject` and `MessageDeduplicationId = envelope.id`. **Standard queues do not preserve order**, so use them only for charts that tolerate reordering. `ack` and drop both call `DeleteMessage`. Long polling waits up to 20 s. Attempts are `ApproximateReceiveCount - 1`. `extend_visibility(delivery, seconds)` keeps a slow delivery hidden. A batch of up to 10 messages is received at once, and messages still waiting in the local buffer are subject to the same visibility clock. Size `visibility_timeout_s` for a whole batch: if it expires, SQS hands the message to another consumer (at-least-once; the inbox dedups). Credentials come only from boto3's own chain. For fan-out, publish to SNS and subscribe FIFO queues to it.

## Guarantees

> **What this does:** at-least-once delivery on every broker, and effectively-once *processing* when you pass an inbox to `InboundDispatcher` (redeliveries are answered, not re-run). Order is per subject: publish order is kept for one `subject` on one topic. Poison envelopes are dead-lettered after `max_attempts`, counting the broker's own redeliveries, and acked (X0.8). An oversized or undecodable message is dropped, never looped. On all five brokers, a consumer that stops or crashes mid-batch resumes without losing an envelope; this is tested with a container restart.
>
> **What this does not do:** no exactly-once delivery, and no global ordering across subjects. Standard SQS queues have no order at all. Kafka carries no broker-side delivery count. Broker-level retention, replication and DLX policy stay your broker's configuration.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** anyone who can publish to a topic can drive your machines. Treat **bus messages as untrusted input**, and authenticate producers with the broker's own ACLs (Kafka ACLs, RabbitMQ vhost/user permissions, NATS accounts, SQS queue policies, Redis ACL users). Envelope extensions that look like credentials are refused or dropped (X0.8), and `type` → machine mapping is an explicit allow-list (`machine_for_type`).
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
| A poison message loops on Kafka after restarts | Kafka has no delivery count | republish with `with_attempt(n + 1)`, or lower `max_attempts` |
| Redis entries of a crashed consumer are never processed | `min_idle_ms` not reached yet | wait, or lower `min_idle_ms` (never below your handler time) |
| "dropping undecodable message" warnings | non-CloudEvents producers on the topic | fix the producer, or use a separate topic |
