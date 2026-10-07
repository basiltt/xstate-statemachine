"""``manage.py relay_outbox``: drain the outbox to a broker.

The example has no broker, so the default "broker" prints one CloudEvents
JSON line per envelope on stdout. Swap `StdoutBroker` for your adapter
(Kafka, NATS, SQS, ...) -- anything with ``publish(topic, envelope)``.
Delivery is at-least-once: a row is marked sent only after ``publish``
returned, so a crash re-sends the SAME envelope id; consumers dedup on it.
"""

import json
import time

from django.core.management.base import BaseCommand

from xstate_statemachine.contrib.django import DjangoOutboxStore
from xstate_statemachine.eda import OutboxRelay


class StdoutBroker:
    """``publish(topic, envelope)`` -> one JSON line on stdout."""

    def __init__(self, write):
        self.write = write

    def publish(self, topic, envelope):
        line = {"topic": topic, **envelope.to_dict()}
        self.write(json.dumps(line, sort_keys=True, default=str))


class Command(BaseCommand):
    help = "Publish pending outbox rows (one pass, or --forever)."

    def add_arguments(self, parser):
        parser.add_argument("--forever", action="store_true")
        parser.add_argument("--interval", type=float, default=1.0)
        parser.add_argument("--batch", type=int, default=100)

    def handle(self, *args, forever=False, interval=1.0, batch=100, **kw):
        relay = OutboxRelay(
            DjangoOutboxStore(),
            StdoutBroker(self.stdout.write),
            batch=batch,
        )
        while True:
            n = relay.relay_once_sync()
            self.stderr.write(f"relayed {n}")
            if not forever:
                return
            try:
                time.sleep(interval)
            except KeyboardInterrupt:  # pragma: no cover
                return
