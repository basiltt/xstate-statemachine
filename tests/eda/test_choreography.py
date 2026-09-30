# tests/eda/test_choreography.py
"""#295: Order + Payment machines react to each other over
`FakeBrokerAdapter` and reach ``completed`` / ``paid`` from a SINGLE inbound
envelope; the causation chain and shared correlation id are asserted."""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any, List

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.eda import (
    Envelope,
    FakeBrokerAdapter,
    OutboxPlugin,
    SyncFakeBrokerAdapter,
)
from src.xstate_statemachine.patterns import ChoreographyRouter, Route
from src.xstate_statemachine.persistence import MemoryInbox, MemoryStore

ORDER = {
    "id": "order",
    "initial": "new",
    "states": {
        "new": {
            "on": {
                "PLACE": {
                    "target": "awaitingPayment",
                    "meta": {"publish": "order.placed"},
                }
            }
        },
        "awaitingPayment": {
            "on": {
                "PAID": {
                    "target": "completed",
                    "meta": {"publish": "order.completed"},
                }
            }
        },
        "completed": {"type": "final"},
    },
}
PAYMENT = {
    "id": "payment",
    "initial": "idle",
    "states": {
        "idle": {
            "on": {
                "CHARGE": {
                    "target": "paid",
                    "meta": {"publish": "payment.captured"},
                }
            }
        },
        "paid": {"type": "final"},
    },
}


def _router(broker: Any, store: Any) -> ChoreographyRouter:
    order, payment = create_machine(ORDER), create_machine(PAYMENT)
    return ChoreographyRouter(
        store,
        {
            "xsm.order.PLACE": order,
            "order.placed": (payment, "CHARGE"),
            "payment.captured": Route(order, "PAID"),
        },
        topics=("events",),
        plugins=[OutboxPlugin(broker, topic="events")],
        inbox=MemoryInbox(),
    )


def _state(store: Any, key: str) -> List[str]:
    return json.loads(store.load(key).snapshot)["state_ids"]


class TestOrderPayment(unittest.TestCase):
    def test_single_inbound_envelope_drives_both_machines(self) -> None:
        broker, store = FakeBrokerAdapter(), MemoryStore()
        router = _router(broker, store)
        cmd = Envelope.new(
            type="xsm.order.PLACE", subject="o-42", correlationid="corr-42"
        )

        async def go() -> Any:
            await broker.deliver("events", cmd)
            return await router.run_until_quiet(broker)

        res = asyncio.run(go())
        self.assertEqual(res.processed, 3)
        self.assertEqual(res.dead_lettered, 0)
        self.assertEqual(res.ignored, 1)  # order.completed: nobody routes it
        self.assertEqual(_state(store, "order:o-42"), ["order.completed"])
        self.assertEqual(_state(store, "payment:o-42"), ["payment.paid"])

        chain = {e.type: e for e in broker.published}
        placed = chain["order.placed"]
        captured = chain["payment.captured"]
        completed = chain["order.completed"]
        # causation: cmd → placed → captured → completed
        self.assertEqual(placed.causationid, cmd.id)
        self.assertEqual(captured.causationid, placed.id)
        self.assertEqual(completed.causationid, captured.id)
        # one conversation: one correlation id, one business key
        for e in (placed, captured, completed):
            self.assertEqual(e.correlationid, "corr-42")
            self.assertEqual(e.subject, "o-42")
        self.assertEqual(captured.machineid, "payment")

    def test_redelivered_command_is_deduplicated(self) -> None:
        broker, store = FakeBrokerAdapter(), MemoryStore()
        router = _router(broker, store)
        cmd = Envelope.new(type="xsm.order.PLACE", subject="o-1")

        async def go() -> Any:
            await broker.deliver("events", cmd)
            await broker.deliver("events", cmd)
            return await router.run_until_quiet(broker)

        res = asyncio.run(go())
        self.assertEqual(res.duplicates, 1)
        self.assertEqual(
            len([e for e in broker.published if e.type == "order.placed"]), 1
        )

    def test_sync_twin_and_unrouted_types(self) -> None:
        broker, store = SyncFakeBrokerAdapter(), MemoryStore()
        router = _router(broker, store)
        broker.deliver(
            "events", Envelope.new(type="xsm.order.PLACE", subject="o-7")
        )
        broker.deliver(
            "events", Envelope.new(type="nobody.cares", subject="o-7")
        )
        res = router.run_until_quiet_sync(broker)
        self.assertEqual(_state(store, "order:o-7"), ["order.completed"])
        self.assertEqual(res.dead_lettered, 0)  # others' events: ignored
        self.assertEqual(res.ignored, 2)  # nobody.cares + order.completed
        self.assertIsNone(router.machine_for("nobody.cares"))

    def test_a_ping_pong_loop_is_bounded(self) -> None:
        ping = create_machine(
            {
                "id": "ping",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "GO": {
                                "target": "a",
                                "reenter": True,
                                "meta": {"publish": "go"},
                            }
                        }
                    }
                },
            }
        )
        broker, store = SyncFakeBrokerAdapter(), MemoryStore()
        router = ChoreographyRouter(
            store,
            {"go": (ping, "GO")},
            plugins=[OutboxPlugin(broker, topic="events")],
        )
        broker.deliver("events", Envelope.new(type="go", subject="k"))
        with self.assertRaises(RuntimeError):
            router.run_until_quiet_sync(broker, max_rounds=5)

        async def go() -> None:
            ab = FakeBrokerAdapter()
            r2 = ChoreographyRouter(
                MemoryStore(),
                {"go": (ping, "GO")},
                plugins=[OutboxPlugin(ab, topic="events")],
            )
            await ab.deliver("events", Envelope.new(type="go", subject="k"))
            await r2.run_until_quiet(ab, max_rounds=3)

        with self.assertRaises(RuntimeError):
            asyncio.run(go())


if __name__ == "__main__":
    unittest.main()
