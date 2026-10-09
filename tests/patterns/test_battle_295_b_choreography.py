# tests/patterns/test_battle_295_b_choreography.py
"""#295 battle (adversary B): a ping-pong choreography ends in ONE
documented `RuntimeError` (the same text from both engines), and a
nonsensical ``max_rounds`` is a `ValueError`, not "did not settle in 0
rounds"."""

from __future__ import annotations

import asyncio
import unittest

from xstate_statemachine import create_machine
from xstate_statemachine.eda import (
    Envelope,
    FakeBrokerAdapter,
    OutboxPlugin,
    SyncFakeBrokerAdapter,
)
from xstate_statemachine.patterns import ChoreographyRouter
from xstate_statemachine.persistence import MemoryInbox, MemoryStore


def _echo(mid: str, on: str, publish: str):
    return create_machine(
        {
            "id": mid,
            "initial": "x",
            "states": {
                "x": {
                    "on": {
                        on: {
                            "target": "x",
                            "reenter": True,
                            "meta": {"publish": publish},
                        }
                    }
                }
            },
        }
    )


def _router(bus):
    a = _echo("a", "PONG", "a.ping")
    b = _echo("b", "PING", "b.pong")
    return ChoreographyRouter(
        MemoryStore(),
        {"a.ping": (b, "PING"), "b.pong": (a, "PONG"), "go": (a, "PONG")},
        plugins=[OutboxPlugin(bus, topic="events")],
        inbox=MemoryInbox(),
    )


class TestPingPong(unittest.TestCase):
    def test_sync_ping_pong_is_a_runtime_error(self) -> None:
        bus = SyncFakeBrokerAdapter()
        router = _router(bus)
        bus.publish("events", Envelope.new(type="go", subject="s"))
        with self.assertRaisesRegex(RuntimeError, "event loop between"):
            router.run_until_quiet_sync(bus, max_rounds=10)

    def test_async_ping_pong_is_the_same_error(self) -> None:
        async def main() -> None:
            bus = FakeBrokerAdapter()
            router = _router(bus)
            await bus.deliver("events", Envelope.new(type="go", subject="s"))
            with self.assertRaisesRegex(RuntimeError, "event loop between"):
                await router.run_until_quiet(bus, max_rounds=10)

        asyncio.run(main())

    def test_bad_max_rounds_is_a_value_error(self) -> None:
        bus = SyncFakeBrokerAdapter()
        router = _router(bus)
        for bad in (0, -1, True, 2.5):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "max_rounds"):
                    router.run_until_quiet_sync(bus, max_rounds=bad)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
