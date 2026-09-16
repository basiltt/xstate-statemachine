# tests/test_sync_interpreter_threading.py
# -----------------------------------------------------------------------------
# 🏛️ #50 (LC-38): the SyncInterpreter is single-threaded -- for real
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `after` timers and delayed sends each started a
# daemon OS thread that called `send()` when the delay elapsed -- so actions
# ran on timer threads and mutated `context` under no lock, while the class
# advertised itself as "single-threaded". The threads are gone. A deadline
# is now a record in the interpreter's clock; due deadlines are delivered
# on the CALLER's thread at the top of the next `send()` / `tick()`, in
# queue order, with existing macrostep semantics unchanged. `tick()` lets a
# caller with no traffic advance deadlines deliberately, and is the natural
# seam for the `SimulatedClock` (#49).
# -----------------------------------------------------------------------------
"""SyncInterpreter threading contract (#50)."""

import logging
import threading
import time
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


DELAY_MS = 40
CFG: Dict[str, Any] = {
    "id": "t",
    "initial": "waiting",
    "context": {"n": 0, "threads": []},
    "states": {
        "waiting": {
            "after": {
                str(DELAY_MS): {"target": "timed_out", "actions": ["bump"]}
            },
            "on": {"POKE": {"actions": ["bump"]}},
        },
        "timed_out": {"on": {"POKE": {"actions": ["bump"]}}},
    },
}


def _logic() -> MachineLogic:
    def bump(i, c, e, a):
        c["n"] += 1
        c["threads"].append(threading.current_thread().name)

    return MachineLogic(actions={"bump": bump})


def _threads() -> set:
    return {t.name for t in threading.enumerate()}


class TestNoThreads(_Quiet):
    def test_after_creates_no_background_threads(self) -> None:
        before = _threads()
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        self.assertEqual(_threads() - before, set())
        i.stop()

    def test_scheduled_send_uses_no_thread(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "raise",
                            "params": {"event": "LATER", "delay": 50},
                        }
                    ],
                    "on": {"LATER": "b"},
                },
                "b": {},
            },
        }
        before = _threads()
        i = SyncInterpreter(create_machine(cfg)).start()
        self.assertEqual(_threads() - before, set())
        time.sleep(0.07)
        i.tick()
        self.assertEqual(i.current_state_ids, {"m.b"})
        i.stop()


class TestDeliveryOnCallerThread(_Quiet):
    def test_actions_run_on_calling_thread(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        time.sleep(DELAY_MS / 1000 + 0.02)
        i.tick()
        self.assertEqual(i.current_state_ids, {"t.timed_out"})
        self.assertEqual(
            set(i.context["threads"]), {threading.current_thread().name}
        )
        i.stop()

    def test_after_fires_only_on_pump_not_on_bare_sleep(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        time.sleep(DELAY_MS / 1000 + 0.05)
        # No send/tick yet: the deadline has elapsed but nothing delivered it.
        self.assertEqual(i.current_state_ids, {"t.waiting"})
        self.assertEqual(i.context["n"], 0)
        i.stop()

    def test_elapsed_timer_delivered_on_next_send(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        time.sleep(DELAY_MS / 1000 + 0.02)
        i.send("POKE")  # the pump: due timer first, then POKE
        self.assertEqual(i.current_state_ids, {"t.timed_out"})
        self.assertEqual(i.context["n"], 2)  # timer bump + POKE bump
        i.stop()

    def test_tick_advances_due_timers_without_events(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        i.tick()  # not due yet
        self.assertEqual(i.current_state_ids, {"t.waiting"})
        time.sleep(DELAY_MS / 1000 + 0.02)
        i.tick()
        self.assertEqual(i.current_state_ids, {"t.timed_out"})
        i.stop()

    def test_timer_event_not_dropped_when_queue_is_busy(self) -> None:
        """A due timer is queued and drained in the same macrostep loop."""
        seen: List[str] = []
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {},
            "states": {
                "a": {
                    "after": {"20": {"target": "b", "actions": ["fired"]}},
                    "on": {"BUSY": {"actions": ["busy"]}},
                },
                "b": {"on": {"BUSY": {"actions": ["busy"]}}},
            },
        }

        def busy(i, c, e, a):
            seen.append("BUSY")
            time.sleep(0.005)

        def fired(i, c, e, a):
            seen.append("FIRED")

        i = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(actions={"busy": busy, "fired": fired})
            )
        ).start()
        i.send_events(
            ["BUSY"] * 10
        )  # ~50 ms of work; the 20 ms deadline passes inside
        self.assertIn("FIRED", seen)
        self.assertEqual(i.current_state_ids, {"m.b"})
        i.stop()

    def test_cancelled_timer_never_fires(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"after": {"20": "late"}, "on": {"GO": "b"}},
                "b": {},
                "late": {},
            },
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        i.send("GO")  # exits `a`; its timer must be cancelled
        time.sleep(0.05)
        i.tick()
        self.assertEqual(i.current_state_ids, {"m.b"})
        i.stop()


class TestSimulatedClockSync(_Quiet):
    def test_after_fires_on_increment(self) -> None:
        clock = SimulatedClock()
        i = SyncInterpreter(
            create_machine(CFG, logic=_logic()), clock=clock
        ).start()
        clock.increment(DELAY_MS - 1)
        self.assertEqual(i.current_state_ids, {"t.waiting"})
        clock.increment(1)
        self.assertEqual(i.current_state_ids, {"t.timed_out"})
        i.stop()

    def test_cancel_clears_clock_handle(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"after": {"20": "late"}, "on": {"GO": "b"}},
                "b": {},
                "late": {},
            },
        }
        clock = SimulatedClock()
        i = SyncInterpreter(create_machine(cfg), clock=clock).start()
        self.assertEqual(clock.pending, 1)
        i.send("GO")
        self.assertEqual(clock.pending, 0)
        i.stop()


class TestStress(_Quiet):
    def test_no_lost_updates_under_many_concurrent_timers(self) -> None:
        """Many `after` regions + a hot send() loop: every increment lands."""
        N = 20
        cfg: Dict[str, Any] = {
            "id": "s",
            "type": "parallel",
            "context": {"n": 0},
            "states": {
                f"r{k}": {
                    "initial": "w",
                    "states": {
                        "w": {
                            "after": {
                                "1": {"target": "d", "actions": ["bump"]}
                            }
                        },
                        "d": {},
                    },
                }
                for k in range(N)
            },
        }
        cfg["on"] = {"HOT": {"actions": ["bump"]}}

        def bump(i, c, e, a):
            c["n"] += 1

        i = SyncInterpreter(
            create_machine(cfg, logic=MachineLogic(actions={"bump": bump}))
        ).start()
        for _ in range(1000):
            i.send("HOT")
        time.sleep(0.01)
        i.tick()
        # 1000 HOTs + N timer bumps, each applied exactly once.
        self.assertEqual(i.context["n"], 1000 + N)
        i.stop()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
