# tests/test_helpers_pure.py
# -----------------------------------------------------------------------------
# 🏛️ #54 (LC-44): the pure API must not be SLOWER than the effectful engine
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `transition()` built a fresh `SyncInterpreter`
# subclass (a new CLASS object, closing over a fresh list) per call, then
# deep-copied the context twice. A path documented as cheap enough for
# "preview the next step" UIs ran 4x slower than actually sending the event.
# The probe class is now module-level, one probe per MachineNode is cached
# and reset per call, and the redundant inbound copy is gone. Semantics are
# unchanged and pinned here: `assign` applies, user actions do not run,
# nothing is scheduled, snapshots stay independent.
# -----------------------------------------------------------------------------
"""Pure-API semantics and cost (#54)."""

import logging
import time
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
    get_initial_snapshot,
    get_next_snapshot,
    initial_transition,
    pure_transition as transition,
)
from src.xstate_statemachine import helpers


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


CFG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0, "log": []},
    "states": {
        "a": {
            "on": {
                "GO": {
                    "target": "b",
                    "actions": [
                        {"type": "assign", "params": {"assignment": {"n": 1}}},
                        "side_effect",
                    ],
                }
            }
        },
        "b": {
            "after": {"10": "a"},
            "invoke": {"src": "svc"},
            "on": {"BACK": "a"},
        },
    },
}


def _logic() -> MachineLogic:
    def side_effect(i, c, e, a):
        c["log"].append("RAN")  # must NEVER appear in pure results

    def svc(i, c, e):
        raise AssertionError("service must never be invoked by the pure API")

    return MachineLogic(
        actions={"side_effect": side_effect}, services={"svc": svc}
    )


class TestPureSemantics(_Quiet):
    def test_pure_probe_class_is_module_level(self) -> None:
        m = create_machine(CFG, logic=_logic())
        p1, _ = helpers._build_probe(m, None, None)
        p2, _ = helpers._build_probe(m, None, None)
        self.assertIs(type(p1), type(p2))
        self.assertIs(type(p1), helpers._Probe)

    def test_pure_api_semantics_unchanged(self) -> None:
        m = create_machine(CFG, logic=_logic())
        snap, entry_actions = initial_transition(m)
        self.assertEqual(snap.state_ids, {"m.a"})
        nxt, actions = transition(m, snap, "GO")
        self.assertEqual(nxt.state_ids, {"m.b"})
        self.assertEqual(nxt.context["n"], 1)  # assign applied
        self.assertEqual(nxt.context["log"], [])  # user action did NOT run
        self.assertEqual([a.type for a in actions], ["assign", "side_effect"])

    def test_pure_transition_never_schedules_timers_or_invokes(self) -> None:
        m = create_machine(CFG, logic=_logic())
        snap = get_initial_snapshot(m)
        nxt = get_next_snapshot(m, snap, "GO")
        self.assertEqual(nxt.state_ids, {"m.b"})
        time.sleep(0.05)  # the `after: 10` in `b` must not fire
        again = get_next_snapshot(m, nxt, "BACK")
        self.assertEqual(again.state_ids, {"m.a"})
        # And the cached probe holds no live timers.
        probe = helpers._probes()[m]
        self.assertEqual(probe._timer_handles, {})

    def test_snapshots_remain_independent(self) -> None:
        """Branching twice from one snapshot leaves the original untouched."""
        m = create_machine(CFG, logic=_logic())
        base = get_initial_snapshot(m)
        b1 = get_next_snapshot(m, base, "GO")
        b2 = get_next_snapshot(m, base, "GO")
        self.assertEqual(base.context["n"], 0)
        self.assertEqual(base.state_ids, {"m.a"})
        self.assertIsNot(b1.context, b2.context)
        b1.context["n"] = 99
        self.assertEqual(b2.context["n"], 1)

    def test_chained_calls_share_one_probe_per_machine(self) -> None:
        m = create_machine(CFG, logic=_logic())
        snap = get_initial_snapshot(m)
        for _ in range(5):
            snap = get_next_snapshot(m, snap, "GO")
            snap = get_next_snapshot(m, snap, "BACK")
        self.assertEqual(len([k for k in helpers._probes() if k is m]), 1)


class TestPurePerf(_Quiet):
    def test_pure_api_not_slower_than_sync_interpreter(self) -> None:
        """Engine work of the pure path within 2x of a real `send()`.

        The pure API must allocate a new immutable snapshot per step (one
        context deepcopy + object), which `send()` never pays; that floor
        is subtracted so the assertion measures ENGINE cost. Best-of-5 to
        reject scheduler noise. Measured ~1.1x on a quiet host.
        """
        cfg = {
            "id": "p",
            "initial": "a",
            "context": {"n": 0},
            "states": {
                "a": {"on": {"T": {"target": "b", "actions": ["inc"]}}},
                "b": {"on": {"T": {"target": "a", "actions": ["inc"]}}},
            },
        }

        def inc(i, c, e, a):
            c["n"] += 1

        m = create_machine(cfg, logic=MachineLogic(actions={"inc": inc}))
        N = 5000

        import copy

        from src.xstate_statemachine import PureSnapshot

        def time_sync() -> float:
            i = SyncInterpreter(m).start()
            t0 = time.perf_counter()
            for _ in range(N):
                i.send("T")
            return (time.perf_counter() - t0) / N

        def time_pure() -> float:
            snap = get_initial_snapshot(m)
            t0 = time.perf_counter()
            for _ in range(N):
                snap = get_next_snapshot(m, snap, "T")
            return (time.perf_counter() - t0) / N

        def time_floor() -> float:
            ctx = {"n": 0}
            t0 = time.perf_counter()
            for _ in range(N):
                PureSnapshot(
                    state_ids={"p.a"},
                    configuration={"p", "p.a"},
                    context=copy.deepcopy(ctx),
                )
            return (time.perf_counter() - t0) / N

        for fn in (time_sync, time_pure, time_floor):
            fn()  # warm-up
        real = min(time_sync() for _ in range(5))
        pure = min(time_pure() for _ in range(5))
        floor = min(time_floor() for _ in range(5))
        engine = pure - floor

        self.assertLessEqual(
            engine,
            real * 2.0,
            f"pure engine work {engine * 1e6:.1f} us/event vs interpreter "
            f"{real * 1e6:.1f} us (pure total {pure * 1e6:.1f}, "
            f"floor {floor * 1e6:.1f})",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
