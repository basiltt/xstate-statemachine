# tests/test_wave2_edge_paths.py
# -----------------------------------------------------------------------------
# 🧪 Wave-2 edge paths -- branches the feature suites did not reach
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: same rationale as test_v080_edge_paths.py. A
# diff-coverage pass over the wave-2 branch found the error/timeout/fallback
# branches below unexercised. Grouped by source line so a red line in a
# coverage run maps straight to its test.
# -----------------------------------------------------------------------------
"""Edge-path coverage for the wave-2 features (#34 #41-#47 #54 #57 #58)."""

import asyncio
import json
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    PureSnapshot,
    SyncInterpreter,
    create_machine,
    get_next_snapshot,
)
from src.xstate_statemachine.helpers import _probes


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


CFG: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"seen": []},
    "states": {
        "a": {"on": {"GO": "b"}},
        "b": {"on": {"TICK": {"actions": ["rec"]}}},
    },
}


def _logic() -> MachineLogic:
    def rec(i, c, e, a):
        c["seen"].append(e.payload.get("n"))

    return MachineLogic(actions={"rec": rec})


# -----------------------------------------------------------------------------
# #47 -- async inbox on a STARTED queue; drain timeout
# -----------------------------------------------------------------------------
class TestAsyncInboxEdges(_Quiet):
    def test_drain_pending_on_started_queue_removes_without_processing(
        self,
    ) -> None:
        async def main():
            i = await Interpreter(create_machine(CFG, logic=_logic())).start()
            await i.send("GO")
            await asyncio.sleep(0.02)
            # Enqueue several without yielding: they sit in the real
            # asyncio.Queue, not the pre-start buffer.
            for n in range(3):
                i.send("TICK", n=n)
            self.assertEqual(len(i.pending_events), 3)
            got = [e.payload["n"] for e in await i.drain_pending()]
            await asyncio.sleep(0.02)
            out = (got, i.pending_events, list(i.context["seen"]))
            await i.stop()
            return out

        got, left, seen = asyncio.run(main())
        self.assertEqual(got, [0, 1, 2])
        self.assertEqual(left, ())
        self.assertEqual(seen, [])  # drained events never ran

    def test_stop_drain_timeout_warns_and_still_stops(self) -> None:
        """A drain that cannot finish in time warns and stops anyway.

        The slow work must be genuinely async (`await asyncio.sleep`) --
        a blocking `time.sleep` in an action stalls the loop, so the
        timeout timer itself could not fire until the queue was already
        empty. That is the loop-stall property documented in Production
        Characteristics, not a defect in `stop()`.
        """

        async def main():
            async def slow(i, c, e, a):
                await asyncio.sleep(0.05)

            logic = MachineLogic(actions={"slow": slow})
            cfg = json.loads(json.dumps(CFG))
            cfg["states"]["b"]["on"]["TICK"] = {"actions": ["slow"]}
            i = await Interpreter(create_machine(cfg, logic=logic)).start()
            await i.send("GO")
            await asyncio.sleep(0.02)
            for _ in range(20):
                i.send("TICK")
            logging.disable(logging.NOTSET)
            with self.assertLogs(level="WARNING") as logs:
                await i.stop(drain=True, timeout=0.01)
            return i.status, logs.output

        status, out = asyncio.run(main())
        self.assertEqual(status, "stopped")
        self.assertTrue(any("timed out" in line for line in out), out)


# -----------------------------------------------------------------------------
# #47 -- sync inbox: drain=True from inside an action; restore path
# -----------------------------------------------------------------------------
class TestSyncInboxEdges(_Quiet):
    def test_stop_drain_processes_queue_when_called_between_sends(
        self,
    ) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        i.send("GO")
        # Poke an event straight into the queue (what a timer thread does
        # between macrosteps) and stop with drain -> it is processed.
        i._enqueue_restored(i._prepare_event("TICK", n=7))
        self.assertEqual(len(i.pending_events), 1)
        i.stop(drain=True)
        self.assertEqual(i.context["seen"], [7])
        self.assertEqual(i.pending_events, ())

    def test_stop_without_drain_warns_on_non_empty_queue(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        i._enqueue_restored(i._prepare_event("TICK", n=1))
        logging.disable(logging.NOTSET)
        with self.assertLogs(level="WARNING") as logs:
            i.stop()
        self.assertTrue(any("pending event" in line for line in logs.output))


# -----------------------------------------------------------------------------
# #57 -- teardown scheduling when the loop is gone
# -----------------------------------------------------------------------------
class TestTeardownWithoutLoop(_Quiet):
    def test_complete_after_loop_closed_does_not_raise(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"E": "f"}}, "f": {"type": "final"}},
        }
        i = Interpreter(create_machine(cfg))

        async def boot():
            await i.start()

        asyncio.run(boot())  # loop closed; interpreter still "running"
        # Driving completion with no live loop must not blow up on the
        # deferred-teardown path.
        i._complete({"ok": True})
        self.assertEqual(i.status, "done")


# -----------------------------------------------------------------------------
# #41 -- sync blocking spawn timeout
# -----------------------------------------------------------------------------
class TestSyncSpawnBlockingTimeout(_Quiet):
    def test_never_ending_timer_child_is_bounded(self) -> None:
        forever = {
            "id": "f",
            "initial": "x",
            "states": {"x": {"after": {"60000": "y"}}, "y": {}},
        }
        cfg = {
            "id": "p",
            "initial": "a",
            "spawnBlockingTimeout": 30,
            "states": {"a": {"entry": ["spawn_blocking_f"]}},
        }
        logic = MachineLogic(services={"f": create_machine(forever)})
        logging.disable(logging.NOTSET)
        with self.assertLogs(level="WARNING") as logs:
            i = SyncInterpreter(create_machine(cfg, logic=logic)).start()
        self.assertEqual(i.status, "running")
        self.assertTrue(any("did not finish" in line for line in logs.output))
        i.stop()


# -----------------------------------------------------------------------------
# #58 -- value on a torn configuration; matches() with an unknown key
# -----------------------------------------------------------------------------
class TestValueEdges(_Quiet):
    def test_value_on_torn_configuration_is_partial_not_exception(
        self,
    ) -> None:
        """Superseded by review F1: `value` must never raise on a live
        machine (mid-transition a compound is momentarily childless). The
        deepest active node is reported as a leaf instead."""
        cfg = {
            "id": "m",
            "initial": "p",
            "states": {"p": {"initial": "q", "states": {"q": {}}}},
        }
        i = SyncInterpreter(create_machine(cfg)).start()
        i._active_state_nodes.discard(i.machine.states["p"].states["q"])
        self.assertEqual(i.value, "p")

    def test_matches_dict_with_unknown_key_is_false(self) -> None:
        i = SyncInterpreter(create_machine(CFG, logic=_logic())).start()
        self.assertFalse(i.matches({"a": "nope"}))
        self.assertFalse(i.matches({"zzz": "a"}))


# -----------------------------------------------------------------------------
# #54 -- hand-built PureSnapshot (no cached nodes) still works
# -----------------------------------------------------------------------------
class TestPureHandBuiltSnapshot(_Quiet):
    def test_snapshot_without_cached_nodes_resolves_by_id(self) -> None:
        m = create_machine(CFG, logic=_logic())
        hand = PureSnapshot(
            state_ids={"m.a"}, configuration={"m", "m.a"}, context={"seen": []}
        )
        self.assertIsNone(hand._nodes)
        nxt = get_next_snapshot(m, hand, "GO")
        self.assertEqual(nxt.state_ids, {"m.b"})

    def test_probe_reaching_done_stays_reusable(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"E": "f"}}, "f": {"type": "final"}},
        }
        m = create_machine(cfg)
        from src.xstate_statemachine import get_initial_snapshot

        s0 = get_initial_snapshot(m)
        done = get_next_snapshot(m, s0, "E")
        self.assertEqual(done.status, "done")
        # The cached probe was not torn down; a second call from s0 works.
        again = get_next_snapshot(m, s0, "E")
        self.assertEqual(again.state_ids, {"m.f"})
        self.assertIn(m, _probes())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
