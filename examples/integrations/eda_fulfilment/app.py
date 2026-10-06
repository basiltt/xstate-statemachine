"""EDA fulfilment -- two statecharts that talk only through events.

`build_app()` wires the whole pipeline; `run_demo()` drives it end to end:

    command (xsm.order.PAY) --broker--> order chart --outbox--> OrderPaid
    OrderPaid   --broker--> warehouse chart (PACK) --outbox--> OrderPacked
    OrderPacked --broker--> order chart (PACKED) --invoke shipOrder-->
                shipped --outbox--> OrderShipped

Nothing here needs a running service: SQLite files in a temp directory,
`SyncFakeBrokerAdapter` or one of the five real broker adapters on an
in-process stand-in (`brokers_local`: fakeredis, fake Kafka / AMQP /
JetStream clients, moto SQS), Celery in eager mode and in-memory
Prometheus / OpenTelemetry / inspector sinks. Set a broker's `LIVE_ENV`
variable to run the same demo against a real server.
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from xstate_statemachine import create_machine
from xstate_statemachine.eda import (
    Envelope,
    OutboxPlugin,
    OutboxRelay,
    SQLiteDeadLetterStore,
    SQLiteOutboxStore,
    SyncFakeBrokerAdapter,
)
from xstate_statemachine.patterns import ChoreographyRouter
from xstate_statemachine.persistence import (
    AuditPlugin,
    PessimisticLock,
    SQLiteInbox,
    SQLiteLog,
    SQLiteStore,
)

import logic

HERE = Path(__file__).resolve().parent
TOPIC = "events"
#: X0.8: a failing envelope is retried this many times, then dead-lettered.
MAX_ATTEMPTS = 3
#: X0.4: inbound size cap for the real-broker adapters (bytes).
MAX_ENVELOPE_BYTES = 64 * 1024
MAX_ROUNDS = 100
BROKERS = ("fake", "redis-streams", "kafka", "rabbitmq", "nats", "sqs")


def load_chart(name: str) -> Dict[str, Any]:
    return json.loads((HERE / name).read_text("utf-8"))


def order_machine(ship_service: Any = None) -> Any:
    return create_machine(
        load_chart("machine.json"),
        logic=logic.order_logic(ship_service),
        strict_config=True,
    )


def warehouse_machine() -> Any:
    return create_machine(load_chart("warehouse.json"), strict_config=True)


# -------------------------------------------------------------------------
# 📡 Broker selection
# -------------------------------------------------------------------------


#: The environment variable that points each real broker at a live
#: server. Unset = the in-process stand-in from `brokers_local`.
LIVE_ENV = {
    "redis-streams": "REDIS_URL",
    "kafka": "XSM_KAFKA_BOOTSTRAP",
    "rabbitmq": "XSM_RABBITMQ_URL",
    "nats": "XSM_NATS_URL",
    "sqs": "XSM_SQS_ENDPOINT",
}
#: The consumer group / durable name the live adapters share.
GROUP = "fulfilment"


def is_live(name: str) -> bool:
    env = LIVE_ENV.get(name)
    return bool(env and os.environ.get(env))


def select_broker(
    name: Optional[str] = None,
    *,
    dead_letters: Any = None,
    client: Any = None,
    consumer: str = "fulfilment-1",
) -> Any:
    """A broker adapter by name: one of `BROKERS`.

    ``EDA_BROKER`` picks the default (``fake``). Every other name builds
    the REAL adapter from ``xstate_statemachine.contrib.brokers``:

    * against a live server when its `LIVE_ENV` variable is set;
    * else against *client* -- the in-process stand-in shared by several
      app instances (see `brokers_local.new_stand_in`);
    * else against a fresh stand-in this adapter owns (closed with it).

    Async-only adapters (Kafka, RabbitMQ, NATS) come back wrapped in
    `SyncBridge`, so the app's publish / dispatch code is one code path.
    """
    name = name or os.environ.get("EDA_BROKER", "fake")
    if name == "fake":
        return SyncFakeBrokerAdapter()
    if name not in BROKERS:
        raise ValueError(f"unknown broker {name!r}; choose from {BROKERS}")
    import brokers_local

    owned = None
    if client is None and not is_live(name):
        client = owned = brokers_local.new_stand_in(name)
    kw: Dict[str, Any] = {
        "max_bytes": MAX_ENVELOPE_BYTES,
        "dead_letters": dead_letters,
    }
    broker = _BUILDERS[name](client, consumer, kw)
    broker.owned_stand_in = owned
    return broker


def _redis_streams(client: Any, consumer: str, kw: Dict[str, Any]) -> Any:
    from xstate_statemachine.contrib.brokers.redis_streams import (
        SyncRedisStreamsBroker,
    )

    url = None if client is not None else os.environ["REDIS_URL"]
    return SyncRedisStreamsBroker(
        client,
        url=url,
        prefix="fulfilment",
        consumer=consumer,
        min_idle_ms=0,
        **kw,
    )


def _kafka(cluster: Any, consumer: str, kw: Dict[str, Any]) -> Any:
    from xstate_statemachine.contrib.brokers.kafka import KafkaBroker

    if cluster is None:
        adapter = KafkaBroker(
            bootstrap_servers=os.environ["XSM_KAFKA_BOOTSTRAP"],
            group_id=GROUP,
            **kw,
        )
    else:
        adapter = KafkaBroker(
            producer=cluster.producer(),
            consumer_factory=cluster.consumer_factory(GROUP),
            group_id=GROUP,
            **kw,
        )
    return SyncBridge(adapter)


def _rabbitmq(amqp: Any, consumer: str, kw: Dict[str, Any]) -> Any:
    from xstate_statemachine.contrib.brokers.rabbitmq import RabbitMQBroker

    if amqp is None:
        adapter = RabbitMQBroker(url=os.environ["XSM_RABBITMQ_URL"], **kw)
    else:
        adapter = RabbitMQBroker(channel=amqp.channel(), **kw)
    return SyncBridge(adapter)


def _nats(js: Any, consumer: str, kw: Dict[str, Any]) -> Any:
    from xstate_statemachine.contrib.brokers.nats import NatsBroker

    if js is None:
        adapter = NatsBroker(
            servers=os.environ["XSM_NATS_URL"], durable=GROUP, **kw
        )
    else:
        adapter = NatsBroker(js=js, durable=GROUP, **kw)
    return SyncBridge(adapter)


def _sqs(moto_sqs: Any, consumer: str, kw: Dict[str, Any]) -> Any:
    import brokers_local
    from xstate_statemachine.contrib.brokers.sqs import SyncSqsBroker

    if moto_sqs is None:
        import boto3

        client = boto3.client(
            "sqs",
            endpoint_url=os.environ["XSM_SQS_ENDPOINT"],
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        )
        brokers_local.ensure_queue(client)
    else:
        client = moto_sqs.client
    return SqsTopic(SyncSqsBroker(client, **kw), brokers_local.SQS_QUEUE)


_BUILDERS = {
    "redis-streams": _redis_streams,
    "kafka": _kafka,
    "rabbitmq": _rabbitmq,
    "nats": _nats,
    "sqs": _sqs,
}


class SqsTopic:
    """Maps the app's logical topic onto the SQS FIFO queue name (SQS
    needs the ``.fifo`` suffix; the router and outbox keep ``events``)."""

    def __init__(self, broker: Any, queue: str) -> None:
        self.inner = broker
        self.queue = queue

    def publish(self, topic: str, envelope: Envelope) -> None:
        self.inner.publish(self.queue, envelope)

    def subscribe(self, topic: str, *, timeout: Optional[float] = None):
        return self.inner.subscribe(self.queue, timeout=timeout)

    def ack(self, delivery: Any) -> None:
        self.inner.ack(delivery)

    def nack(self, delivery: Any, *, requeue: bool) -> None:
        self.inner.nack(delivery, requeue=requeue)

    def extend_visibility(self, delivery: Any, seconds: int) -> None:
        self.inner.extend_visibility(delivery, seconds)

    def close(self) -> None:
        self.inner.close()


class SyncBridge:
    """The blocking face of an async adapter: every call runs on ONE
    private event loop (aiokafka / aio-pika / nats-py connections belong
    to the loop that opened them, so a fresh ``asyncio.run`` per call
    would reconnect every time). Subscribing is lazy -- one delivery per
    step -- so a dispatcher that stops early never strands deliveries."""

    def __init__(self, adapter: Any) -> None:
        self.inner = adapter
        self.loop = asyncio.new_event_loop()

    def _run(self, awaitable: Any) -> Any:
        return self.loop.run_until_complete(awaitable)

    def publish(self, topic: str, envelope: Envelope) -> None:
        self._run(self.inner.publish(topic, envelope))

    def subscribe(
        self, topic: str, *, timeout: Optional[float] = None
    ) -> Iterator[Any]:
        agen = self.inner.subscribe(topic, timeout=timeout)
        try:
            while True:
                try:
                    yield self._run(agen.__anext__())
                except StopAsyncIteration:
                    return
        finally:
            self._run(agen.aclose())

    def ack(self, delivery: Any) -> None:
        self._run(self.inner.ack(delivery))

    def nack(self, delivery: Any, *, requeue: bool) -> None:
        self._run(self.inner.nack(delivery, requeue=requeue))

    def close(self) -> None:
        if self.loop.is_closed():
            return
        try:
            self._run(self.inner.close())
        finally:
            self.loop.close()


# -------------------------------------------------------------------------
# 🔭 Observability (optional extras)
# -------------------------------------------------------------------------


class Instruments:
    """Prometheus registry, OTel span exporter and inspector sink."""

    def __init__(self) -> None:
        self.plugins: List[Any] = []
        self.registry: Any = None
        self.spans: Any = None
        self.inspector: Any = None

    def metrics_text(self) -> str:
        if self.registry is None:
            return ""
        from prometheus_client import generate_latest

        return generate_latest(self.registry).decode("utf-8")

    def transitions_total(self) -> int:
        total = 0.0
        for line in self.metrics_text().splitlines():
            if line.startswith("xstatemachine_transitions_total{"):
                total += float(line.rsplit(" ", 1)[1])
        return int(total)

    def span_names(self) -> List[str]:
        if self.spans is None:
            return []
        return [s.name for s in self.spans.get_finished_spans()]


def instrument() -> Instruments:
    """Attach whatever observability extras are installed."""
    out = Instruments()
    try:
        from prometheus_client import CollectorRegistry

        from xstate_statemachine.contrib.observability import (
            PrometheusPlugin,
        )

        out.registry = CollectorRegistry()
        out.plugins.append(PrometheusPlugin(registry=out.registry))
    except ImportError:
        pass
    try:
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        from xstate_statemachine.contrib.observability import (
            OpenTelemetryPlugin,
        )

        out.spans = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(out.spans))
        tracer = provider.get_tracer("eda_fulfilment")
        out.plugins.append(OpenTelemetryPlugin(tracer))
    except ImportError:
        pass
    from xstate_statemachine.inspect import InspectorPlugin, MemorySink

    out.inspector = MemorySink()
    # 🔐 Only these context keys / payload fields may leave the process;
    #    none of them is personal data. Payloads are redacted anyway.
    out.plugins.append(
        InspectorPlugin(
            out.inspector,
            context_allowlist=("orderId", "total", "trackingId"),
            include_payloads=True,
            # 🔐 battle #274: `PAYMENT_FAILED.reason` is free text from the
            #    gateway -- it carried a card number past key redaction
            payload_allowlist=("orderId", "total", "trackingId"),
        )
    )
    return out


# -------------------------------------------------------------------------
# 🏗️ The application
# -------------------------------------------------------------------------


class FulfilmentApp:
    """Everything one service process holds."""

    def __init__(
        self,
        workdir: Path,
        broker: str = "fake",
        *,
        celery: bool = True,
        redis_client: Any = None,
        stand_in: Any = None,
        consumer: str = "fulfilment-1",
    ) -> None:
        self.workdir = Path(workdir)
        self.store = SQLiteStore(self.workdir / "state.db")
        self.outbox = SQLiteOutboxStore(self.store)
        self.dead_letters = SQLiteDeadLetterStore(self.store)
        self.inbox = SQLiteInbox(self.store)
        self.log = SQLiteLog(self.store)
        self.lock = PessimisticLock()
        self.broker = select_broker(
            broker,
            dead_letters=self.dead_letters,
            client=stand_in if stand_in is not None else redis_client,
            consumer=consumer,
        )
        #: every envelope the relay put on the broker, in publish order
        self.sent: List[Envelope] = []
        self.relay = OutboxRelay(
            self.outbox, _Recorder(self.broker, self.sent)
        )
        self.instruments = instrument()
        self.outbox_plugin = OutboxPlugin(self.outbox, topic=TOPIC)
        self.plugins = [
            self.outbox_plugin,
            AuditPlugin(self.log),
        ] + self.instruments.plugins
        self.celery: Any = None
        ship = None
        if celery:
            import celery_app

            self.celery = celery_app.make_celery()
            ship = celery_app.ship_service(self.celery)
        self.order = order_machine(ship)
        self.warehouse = warehouse_machine()
        self.router = ChoreographyRouter(
            self.store,
            {
                "xsm.order.PAY": self.order,
                "xsm.order.PAYMENT_FAILED": self.order,
                "xsm.order.CANCEL": self.order,
                "OrderPaid": (self.warehouse, "PACK"),
                "OrderPacked": (self.order, "PACKED"),
            },
            topics=(TOPIC,),
            plugins=self.plugins,
            inbox=self.inbox,
            lock=self.lock,
            max_attempts=MAX_ATTEMPTS,
            dead_letters=self.dead_letters,
        )
        self.commands: List[Envelope] = []
        self.relayed = 0

    # -- keys -------------------------------------------------------------
    def machine_for_key(self, key: str) -> Any:
        return self.warehouse if key.startswith("warehouse:") else self.order

    def state_of(self, key: str) -> Optional[List[str]]:
        rec = self.store.load(key)
        return json.loads(rec.snapshot)["state_ids"] if rec else None

    # -- commands ---------------------------------------------------------
    def command(self, order_id: str, event: str, **data: Any) -> Envelope:
        env = Envelope.new(
            type=f"xsm.order.{event}",
            subject=order_id,
            data=dict(data),
            source="checkout",
        )
        self.publish(env)
        return env

    def publish(self, env: Envelope) -> None:
        self.commands.append(env)
        self.broker.publish(TOPIC, env)

    # -- the loop ---------------------------------------------------------
    def pump(self) -> Dict[str, int]:
        """Relay outbox rows and dispatch until nothing moves."""
        stats = {"processed": 0, "duplicates": 0, "dead_lettered": 0}
        for _ in range(MAX_ROUNDS):
            relayed = self.relay.relay_once_sync()
            self.relayed += relayed
            res = self.router.run_until_quiet_sync(self.broker)
            stats["processed"] += res.processed
            stats["duplicates"] += res.duplicates
            stats["dead_lettered"] += res.dead_lettered
            if not relayed and not res.outcomes:
                return stats
        raise RuntimeError("fulfilment did not settle")

    def transitions(self, key: str, event: Optional[str] = None) -> int:
        return sum(
            1
            for r in self.log.read(key)
            if r.disposition == "transition"
            and (event is None or r.event_type == event)
        )

    def close(self) -> None:
        close = getattr(self.broker, "close", None)
        if close is not None:
            close()
        self.store.close()


class _Recorder:
    """The relay's view of the broker: publish, and remember what went."""

    def __init__(self, broker: Any, sent: List[Envelope]) -> None:
        self.broker = broker
        self.sent = sent

    def publish(self, topic: str, envelope: Envelope) -> None:
        self.broker.publish(topic, envelope)
        self.sent.append(envelope)


def build_app(
    broker: str = "fake", workdir: Optional[Path] = None, **kw: Any
) -> FulfilmentApp:
    path = Path(workdir or tempfile.mkdtemp(prefix="eda-fulfilment-"))
    return FulfilmentApp(path, broker, **kw)


def _celery_available() -> bool:
    try:
        import celery  # noqa: F401
    except ImportError:
        return False
    return True


def run_demo(
    broker: str = "fake", workdir: Optional[Path] = None
) -> Dict[str, Any]:
    """Three orders to ``shipped``, one poison message, one duplicate."""
    app = build_app(broker, workdir, celery=_celery_available())
    try:
        orders = ["o-1", "o-2", "o-3"]
        for n, oid in enumerate(orders, start=1):
            app.command(oid, "PAY", orderId=oid, total=10 * n)
        stats = app.pump()
        # 💀 poison: a PAYMENT_FAILED whose reason is not a string.
        app.command("o-4", "PAYMENT_FAILED", reason=12345)
        # 🔁 redelivery: the very same envelope again (same id).
        app.publish(app.commands[0])
        more = app.pump()
        keys = ["order:" + o for o in orders]
        return {
            "broker": broker,
            "celery": app.celery is not None,
            "orders": {k: app.state_of(k) for k in keys},
            "transitions": sum(app.transitions(k) for k in keys),
            "processed": stats["processed"] + more["processed"],
            "duplicates": more["duplicates"],
            "outbox_rows": app.outbox.count(),
            "published": app.relayed,
            "dead_letters": len(app.dead_letters.list()),
            "metrics_transitions": app.instruments.transitions_total(),
            "spans": len(app.instruments.span_names()),
            "inspector_messages": len(app.instruments.inspector.messages),
        }
    finally:
        app.close()
