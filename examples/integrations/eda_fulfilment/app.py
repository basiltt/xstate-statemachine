"""EDA fulfilment -- two statecharts that talk only through events.

`build_app()` wires the whole pipeline; `run_demo()` drives it end to end:

    command (xsm.order.PAY) --broker--> order chart --outbox--> OrderPaid
    OrderPaid   --broker--> warehouse chart (PACK) --outbox--> OrderPacked
    OrderPacked --broker--> order chart (PACKED) --invoke shipOrder-->
                shipped --outbox--> OrderShipped

Nothing here needs a running service: SQLite files in a temp directory,
`SyncFakeBrokerAdapter` (or Redis Streams on fakeredis), Celery in eager
mode and in-memory Prometheus / OpenTelemetry / inspector sinks.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

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
BROKERS = ("fake", "redis-streams")


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


def select_broker(
    name: Optional[str] = None,
    *,
    dead_letters: Any = None,
    client: Any = None,
    consumer: str = "fulfilment-1",
) -> Any:
    """``"fake"`` (default) or ``"redis-streams"``.

    ``EDA_BROKER`` picks the default. ``redis-streams`` uses *client*, else
    ``REDIS_URL`` when set, else an in-process ``fakeredis`` server.
    """
    name = name or os.environ.get("EDA_BROKER", "fake")
    if name == "fake":
        return SyncFakeBrokerAdapter()
    if name != "redis-streams":
        raise ValueError(f"unknown broker {name!r}; choose from {BROKERS}")
    from xstate_statemachine.contrib.brokers.redis_streams import (
        SyncRedisStreamsBroker,
    )

    url = os.environ.get("REDIS_URL")
    if client is None and not url:
        import fakeredis

        client = fakeredis.FakeRedis()
    return SyncRedisStreamsBroker(
        client,
        url=None if client is not None else url,
        prefix="fulfilment",
        consumer=consumer,
        min_idle_ms=0,
        max_bytes=MAX_ENVELOPE_BYTES,
        dead_letters=dead_letters,
    )


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
            client=redis_client,
            consumer=consumer,
        )
        self.relay = OutboxRelay(self.outbox, self.broker)
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
