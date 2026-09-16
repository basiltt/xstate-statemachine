# tests/test_macrostep.py
# -----------------------------------------------------------------------------
# 🏛️ #36 (LC-05): `raise` is a MICROSTEP event, not a queued external one
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: SCXML and XState distinguish the internal event
# queue (events the machine raised for itself, drained to completion as
# part of the current macrostep) from the external queue (events from the
# outside world, one per macrostep). The library had one queue, so an event
# a transition raised for itself was processed AFTER any external event
# that had already arrived -- the machine observed the outside world in the
# middle of its own step. Both engines now hold raised events in a separate
# internal queue that is drained before the next external event is taken.
# -----------------------------------------------------------------------------
"""Macrostep / microstep ordering (#36)."""

import asyncio
import logging
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


def _raise(event: str) -> Dict[str, Any]:
    return {"type": "raise", "params": {"event": event}}


# The filer's shape: entering `b` raises RAISED; an EXTERNAL event was
# already queued behind the GO that caused the entry.
CFG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"trace": []},
    "states": {
        "a": {"on": {"GO": "b"}},
        "b": {
            "entry": ["log_entry", _raise("RAISED")],
            "on": {
                "RAISED": {"actions": ["log_raised"]},
                "EXTERNAL": {"actions": ["log_external"]},
            },
        },
    },
}


def _logic() -> MachineLogic:
    def rec(name):
        return lambda i, c, e, a: c["trace"].append(name)

    return MachineLogic(
        actions={
            "log_entry": rec("entry"),
            "log_raised": rec("RAISED"),
            "log_external": rec("EXTERNAL"),
        }
    )


class TestAsyncMacrostep(_Quiet):
    def test_raised_event_precedes_pending_external(self) -> None:
        async def main():
            i = await Interpreter(create_machine(CFG, logic=_logic())).start()
            i.send("GO")
            i.send("EXTERNAL")  # queued BEFORE GO is processed
            for _ in range(500):
                if len(i.context["trace"]) == 3:
                    break
                await asyncio.sleep(0.002)
            out = list(i.context["trace"])
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), ["entry", "RAISED", "EXTERNAL"])

    def test_raise_chain_settles_before_external(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"trace": []},
            "states": {
                "a": {
                    "on": {
                        "GO": {"actions": [_raise("A")]},
                        "A": {"actions": ["la", _raise("B")]},
                        "B": {"actions": ["lb", _raise("C")]},
                        "C": {"actions": ["lc"]},
                        "EXT": {"actions": ["le"]},
                    }
                }
            },
        }

        def rec(name):
            return lambda i, c, e, a: c["trace"].append(name)

        logic = MachineLogic(
            actions={
                "la": rec("A"),
                "lb": rec("B"),
                "lc": rec("C"),
                "le": rec("EXT"),
            }
        )

        async def main():
            i = await Interpreter(create_machine(cfg, logic=logic)).start()
            i.send("GO")
            i.send("EXT")
            for _ in range(500):
                if len(i.context["trace"]) == 4:
                    break
                await asyncio.sleep(0.002)
            out = list(i.context["trace"])
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), ["A", "B", "C", "EXT"])

    def test_raise_interleaves_with_always(self) -> None:
        """Eventless transitions are taken before the internal queue drains."""
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"trace": []},
            "states": {
                "a": {"on": {"GO": {"target": "b", "actions": [_raise("R")]}}},
                "b": {
                    "always": {"target": "c", "actions": ["lb_always"]},
                    "on": {"R": {"actions": ["lr_in_b"]}},
                },
                "c": {"on": {"R": {"actions": ["lr_in_c"]}}},
            },
        }

        def rec(name):
            return lambda i, c, e, a: c["trace"].append(name)

        logic = MachineLogic(
            actions={
                "lb_always": rec("always"),
                "lr_in_b": rec("R@b"),
                "lr_in_c": rec("R@c"),
            }
        )

        async def main():
            i = await Interpreter(create_machine(cfg, logic=logic)).start()
            await i.send("GO")
            for _ in range(500):
                if len(i.context["trace"]) == 2:
                    break
                await asyncio.sleep(0.002)
            out = (list(i.context["trace"]), set(i.current_state_ids))
            await i.stop()
            return out

        trace, state = asyncio.run(main())
        # SCXML: the `always` from b runs first (microstep), so R is
        # handled in c, not b.
        self.assertEqual(trace, ["always", "R@c"])
        self.assertEqual(state, {"m.c"})

    def test_raise_guard_still_bounds_self_feeding_chain(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "maxIterations": 50,
            "context": {"n": 0},
            "states": {
                "a": {"on": {"LOOP": {"actions": ["inc", _raise("LOOP")]}}}
            },
        }

        def inc(i, c, e, a):
            c["n"] += 1

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"inc": inc}))
            ).start()
            await i.send("LOOP")
            await asyncio.sleep(0.1)
            out = (i.context["n"], i.status)
            await i.stop()
            return out

        n, status = asyncio.run(main())
        self.assertEqual(status, "running")
        self.assertLessEqual(n, 60)  # bounded, not infinite

    def test_high_volume_external_traffic_is_never_throttled(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "maxIterations": 50,
            "context": {"n": 0},
            "states": {"a": {"on": {"T": {"actions": ["inc"]}}}},
        }

        def inc(i, c, e, a):
            c["n"] += 1

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(actions={"inc": inc}))
            ).start()
            for _ in range(3000):
                i.send("T")
            for _ in range(2000):
                if i.context["n"] == 3000:
                    break
                await asyncio.sleep(0.002)
            out = i.context["n"]
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), 3000)


class TestSyncMacrostep(_Quiet):
    def test_sync_raise_precedes_external(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        i.send_events(["GO", "EXTERNAL"])
        self.assertEqual(i.context["trace"], ["entry", "RAISED", "EXTERNAL"])
        i.stop()

    def test_sync_raise_chain_settles_before_external(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"trace": []},
            "states": {
                "a": {
                    "on": {
                        "GO": {"actions": [_raise("A")]},
                        "A": {"actions": ["la", _raise("B")]},
                        "B": {"actions": ["lb"]},
                        "EXT": {"actions": ["le"]},
                    }
                }
            },
        }

        def rec(name):
            return lambda i, c, e, a: c["trace"].append(name)

        logic = MachineLogic(
            actions={"la": rec("A"), "lb": rec("B"), "le": rec("EXT")}
        )
        i = SyncInterpreter(create_machine(cfg, logic=logic)).start()
        i.send_events(["GO", "EXT"])
        self.assertEqual(i.context["trace"], ["A", "B", "EXT"])
        i.stop()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
