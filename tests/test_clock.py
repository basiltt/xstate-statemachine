# tests/test_clock.py
# -----------------------------------------------------------------------------
# 🏛️ #49 (LC-27) + #48 (LC-26): time is an injectable dependency
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `after` delays and delayed sends called
# `asyncio.sleep` / `threading.Event.wait` directly, so a test of a
# 30-second timeout burned 30 real seconds and a timer's accuracy was
# whatever the event loop's backlog allowed. XState v5 makes the clock a
# constructor option (`createActor(m, {clock})`) and ships `SimulatedClock`.
# This mirrors that: a `Clock` protocol, a `RealClock` default that preserves
# today's behaviour byte-for-byte, and a `SimulatedClock` for deterministic
# tests. Invoked children inherit the parent's clock so a whole actor tree
# runs on one timeline. Both engines route EVERY timing path through it.
# -----------------------------------------------------------------------------
"""Clock injection and virtual time (#49); timer priority and drift (#48)."""

import asyncio
import inspect
import logging
import time
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    Clock,
    Interpreter,
    MachineLogic,
    RealClock,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


async def _until(pred, turns: int = 2000) -> None:
    """Yield to the loop until *pred* holds (bounded)."""
    for _ in range(turns):
        if pred():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition not met")


# The filer's shape: a 30 s order timeout that must be testable in < 100 ms.
ORDER: Dict[str, Any] = {
    "id": "order",
    "initial": "submitting",
    "states": {
        "submitting": {
            "after": {"30000": "timed_out"},
            "on": {"ACK": "live"},
        },
        "live": {},
        "timed_out": {},
    },
}


class TestPublicSurface(_Quiet):
    def test_clock_types_are_exported(self) -> None:
        self.assertTrue(isinstance(RealClock(), Clock))
        self.assertTrue(isinstance(SimulatedClock(), Clock))

    def test_both_constructors_accept_clock(self) -> None:
        for cls in (Interpreter, SyncInterpreter):
            with self.subTest(cls=cls.__name__):
                self.assertIn(
                    "clock", inspect.signature(cls.__init__).parameters
                )

    def test_default_clock_is_real(self) -> None:
        i = SyncInterpreter(create_machine(ORDER))
        self.assertIsInstance(i.clock, RealClock)


class TestSimulatedClockAsync(_Quiet):
    def test_after_fires_on_simulated_clock_increment(self) -> None:
        async def main():
            clock = SimulatedClock()
            t0 = time.perf_counter()
            i = await Interpreter(create_machine(ORDER), clock=clock).start()
            await clock.increment(29_999)
            still = set(i.current_state_ids)
            await clock.increment(1)
            fired = set(i.current_state_ids)
            await i.stop()
            return still, fired, (time.perf_counter() - t0) * 1000

        still, fired, wall_ms = asyncio.run(main())
        self.assertEqual(still, {"order.submitting"})
        self.assertEqual(fired, {"order.timed_out"})
        self.assertLess(wall_ms, 100, f"took {wall_ms:.0f} ms of wall time")

    def test_two_timers_fire_in_delay_order_under_simulated_clock(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "type": "parallel",
            "context": {"log": []},
            "states": {
                "a": {
                    "initial": "w",
                    "states": {
                        "w": {
                            "after": {
                                "200": {"target": "d", "actions": ["la"]}
                            }
                        },
                        "d": {},
                    },
                },
                "b": {
                    "initial": "w",
                    "states": {
                        "w": {
                            "after": {
                                "100": {"target": "d", "actions": ["lb"]}
                            }
                        },
                        "d": {},
                    },
                },
            },
        }
        logic = MachineLogic(
            actions={
                "la": lambda i, c, e, a: c["log"].append("a200"),
                "lb": lambda i, c, e, a: c["log"].append("b100"),
            }
        )

        async def once():
            clock = SimulatedClock()
            i = await Interpreter(
                create_machine(cfg, logic=logic), clock=clock
            ).start()
            await clock.increment(250)
            out = list(i.context["log"])
            await i.stop()
            return out

        async def many():
            return [await once() for _ in range(100)]

        results = asyncio.run(many())
        self.assertTrue(
            all(r == ["b100", "a200"] for r in results), results[:3]
        )

    def test_after_timer_cancelled_on_state_exit_clears_clock_handle(
        self,
    ) -> None:
        async def main():
            clock = SimulatedClock()
            i = await Interpreter(create_machine(ORDER), clock=clock).start()
            self.assertEqual(clock.pending, 1)
            await i.send("ACK")
            await _until(lambda: i.current_state_ids == {"order.live"})
            pending = clock.pending
            await clock.increment(60_000)
            out = (pending, set(i.current_state_ids))
            await i.stop()
            return out

        pending, state = asyncio.run(main())
        self.assertEqual(pending, 0)
        self.assertEqual(state, {"order.live"})

    def test_child_actor_inherits_parent_clock(self) -> None:
        child = {
            "id": "kid",
            "initial": "w",
            "states": {
                "w": {"after": {"5000": "late"}},
                "late": {"type": "final"},
            },
        }
        parent = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {"invoke": {"src": "kid", "onDone": "b"}},
                "b": {},
            },
        }

        async def main():
            clock = SimulatedClock()
            m = create_machine(
                parent,
                logic=MachineLogic(services={"kid": create_machine(child)}),
            )
            i = await Interpreter(m, clock=clock).start()
            await _until(lambda: bool(i._actors))
            kid = next(iter(i._actors.values()))
            same = kid.clock is clock
            await clock.increment(5000)
            await _until(lambda: i.current_state_ids == {"p.b"})
            out = (same, set(i.current_state_ids))
            await i.stop()
            return out

        same, state = asyncio.run(main())
        self.assertTrue(same)
        self.assertEqual(state, {"p.b"})

    def test_delayed_send_uses_the_clock(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "raise",
                            "params": {"event": "LATER", "delay": 10_000},
                        }
                    ],
                    "on": {"LATER": "b"},
                },
                "b": {},
            },
        }

        async def main():
            clock = SimulatedClock()
            i = await Interpreter(create_machine(cfg), clock=clock).start()
            before = set(i.current_state_ids)
            await clock.increment(10_000)
            out = (before, set(i.current_state_ids))
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), ({"m.a"}, {"m.b"}))

    def test_set_cannot_travel_backwards(self) -> None:
        clock = SimulatedClock()
        clock.set(1000)
        with self.assertRaises(ValueError):
            clock.set(500)


class TestRealClockUnchanged(_Quiet):
    def test_after_still_fires_against_wall_time(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"after": {"30": "b"}}, "b": {}},
        }

        async def main():
            i = await Interpreter(create_machine(cfg)).start()
            for _ in range(200):
                if i.current_state_ids == {"m.b"}:
                    break
                await asyncio.sleep(0.005)
            out = set(i.current_state_ids)
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), {"m.b"})


# -----------------------------------------------------------------------------
# #48 -- a due timer is not queued behind a deep external backlog
# -----------------------------------------------------------------------------
class TestTimerPriority(_Quiet):
    def test_after_event_is_not_queued_behind_external_events(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"order": []},
            "states": {
                "a": {
                    "after": {"20": {"target": "b", "actions": ["fired"]}},
                    "on": {"TICK": {"actions": ["tick"]}},
                },
                "b": {"on": {"TICK": {"actions": ["tick"]}}},
            },
        }

        def tick(i, c, e, a):
            c["order"].append("T")

        def fired(i, c, e, a):
            c["order"].append("AFTER")

        async def main():
            i = await Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(actions={"tick": tick, "fired": fired}),
                )
            ).start()
            # Flood the inbox with work, then wait past the deadline.
            for _ in range(2000):
                i.send("TICK")
            await asyncio.sleep(0.05)
            for _ in range(400):
                if "AFTER" in i.context["order"]:
                    break
                await asyncio.sleep(0.005)
            pos = i.context["order"].index("AFTER")
            await i.stop()
            return pos

        pos = asyncio.run(main())
        # The timer fired while ~2000 TICKs were still queued: it must land
        # well before the tail of that backlog, not after all of it.
        self.assertLess(
            pos, 1900, f"AFTER processed at position {pos} of 2000+"
        )

    def test_timer_drift_is_reported_on_after_event(self) -> None:
        got: Dict[str, Any] = {}
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"after": {"10": {"target": "b", "actions": ["rec"]}}},
                "b": {},
            },
        }

        def rec(i, c, e, a):
            got["event"] = e

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"rec": rec}))
            ).start()
            for _ in range(200):
                if got:
                    break
                await asyncio.sleep(0.005)
            await i.stop()

        asyncio.run(main())
        e = got["event"]
        # `fired_at` may read a hair BEFORE `scheduled_for` on a platform
        # whose monotonic clock is coarse (Windows + py3.9: 15.6 ms
        # resolution; asyncio rounds the deadline to it). That is why
        # `lateness_ms` clamps at zero -- assert the contract, not the raw
        # stamps.
        self.assertGreater(e.scheduled_for, 0.0)
        self.assertGreater(e.fired_at, 0.0)
        self.assertGreaterEqual(e.lateness_ms, 0.0)
        self.assertLess(e.lateness_ms, 500.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
