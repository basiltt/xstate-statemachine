# tests/test_persistence.py
# -----------------------------------------------------------------------------
# 🏛️ #45 (LC-21) + #47 (LC-24): snapshot envelope v1
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: a persisted snapshot used to be a bare dict of
# nine keys with no version and no machine identity. A blob from a newer
# build, or from a machine whose structure has changed since, restored
# without complaint into whatever half-fit -- and events accepted by `send()`
# but not yet processed were simply lost on stop(). Both are fixed in ONE
# envelope bump (version 1): `version`, `machine_id`, `machine_hash`,
# `taken_at`, `pending_events`. Version-0 (unversioned) payloads restore
# exactly as before, which is the whole point of adding a version late.
# -----------------------------------------------------------------------------
"""Snapshot versioning, machine identity and pending-event durability."""

import asyncio
import json
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SnapshotDriftError,
    SnapshotVersionError,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.persistence import SNAPSHOT_VERSION


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


CFG: Dict[str, Any] = {
    "id": "order",
    "initial": "a",
    "context": {"n": 0},
    "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"BACK": "a"}}},
}


def _machine(cfg: Dict[str, Any] = CFG, **logic: Any) -> Any:
    return create_machine(cfg, logic=MachineLogic(**logic))


# -----------------------------------------------------------------------------
# #45 — version + identity
# -----------------------------------------------------------------------------
class TestSnapshotEnvelope(_Quiet):
    def test_persisted_snapshot_includes_version_and_machine_identity(
        self,
    ) -> None:
        i = SyncInterpreter(_machine()).start()
        snap = i.get_persisted_snapshot()
        self.assertEqual(snap["version"], SNAPSHOT_VERSION)
        self.assertEqual(snap["machine_id"], "order")
        self.assertEqual(snap["machine_hash"], i.machine.structure_hash)
        self.assertIsInstance(snap["taken_at"], float)
        self.assertRegex(snap["machine_hash"], r"^[0-9a-f]{16}$")

    def test_from_snapshot_rejects_future_version(self) -> None:
        i = SyncInterpreter(_machine()).start()
        snap = json.loads(i.get_snapshot())
        snap["version"] = SNAPSHOT_VERSION + 1
        with self.assertRaises(SnapshotVersionError) as cm:
            SyncInterpreter.from_snapshot(json.dumps(snap), _machine())
        self.assertIn(str(SNAPSHOT_VERSION + 1), str(cm.exception))

    def test_from_snapshot_accepts_legacy_unversioned_snapshot(self) -> None:
        """A hand-written 0.7.x payload (no envelope keys) still restores."""
        legacy = {
            "status": "running",
            "context": {"n": 7},
            "state_ids": ["order.b"],
            "configuration": ["order", "order.b"],
            "output": None,
            "error": None,
            "history": {},
            "actors": {},
            "system": {},
        }
        j = SyncInterpreter.from_snapshot(json.dumps(legacy), _machine())
        self.assertEqual(j.current_state_ids, {"order.b"})
        self.assertEqual(j.context["n"], 7)

    def test_machine_hash_changes_when_a_guard_is_added(self) -> None:
        i = SyncInterpreter(_machine()).start()
        snap = i.get_snapshot()
        drifted = json.loads(json.dumps(CFG))
        drifted["states"]["a"]["on"]["GO"] = {"target": "b", "guard": "ok"}
        m2 = _machine(drifted, guards={"ok": lambda c, e: True})
        self.assertNotEqual(i.machine.structure_hash, m2.structure_hash)
        with self.assertRaises(SnapshotDriftError) as cm:
            SyncInterpreter.from_snapshot(snap, m2)
        self.assertIn("order", str(cm.exception))

    def test_machine_hash_is_stable_across_cosmetic_edits(self) -> None:
        i = SyncInterpreter(_machine()).start()
        snap = i.get_snapshot()
        cosmetic = json.loads(json.dumps(CFG))
        cosmetic["description"] = "An order lifecycle"
        cosmetic["states"]["a"]["meta"] = {"doc": "waiting"}
        cosmetic["states"]["a"]["description"] = "the a state"
        m2 = _machine(cosmetic)
        self.assertEqual(i.machine.structure_hash, m2.structure_hash)
        SyncInterpreter.from_snapshot(snap, m2)  # must not raise

    def test_machine_hash_is_order_insensitive_for_states(self) -> None:
        a = _machine({"id": "m", "initial": "x", "states": {"x": {}, "y": {}}})
        b = _machine({"id": "m", "initial": "x", "states": {"y": {}, "x": {}}})
        self.assertEqual(a.structure_hash, b.structure_hash)

    def test_verify_machine_hash_false_allows_drifted_restore(self) -> None:
        i = SyncInterpreter(_machine()).start()
        snap = i.get_snapshot()
        drifted = json.loads(json.dumps(CFG))
        drifted["states"]["c"] = {}
        j = SyncInterpreter.from_snapshot(
            snap, _machine(drifted), verify_machine_hash=False
        )
        self.assertEqual(j.current_state_ids, {"order.a"})

    def test_machine_id_mismatch_is_drift(self) -> None:
        i = SyncInterpreter(_machine()).start()
        other = json.loads(json.dumps(CFG))
        other["id"] = "invoice"
        with self.assertRaises(SnapshotDriftError):
            SyncInterpreter.from_snapshot(i.get_snapshot(), _machine(other))

    def test_nested_actor_snapshots_carry_their_own_version(self) -> None:
        child = {"id": "kid", "initial": "i", "states": {"i": {}}}
        parent = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        }
                    ]
                }
            },
        }
        i = SyncInterpreter(
            _machine(parent, services={"kid": create_machine(child)})
        ).start()
        snap = i.get_persisted_snapshot()
        rec = snap["actors"]["p:k"]["snapshot"]
        self.assertEqual(rec["version"], SNAPSHOT_VERSION)
        self.assertEqual(rec["machine_id"], "kid")
        i.stop()


# -----------------------------------------------------------------------------
# #47 — pending events
# -----------------------------------------------------------------------------
class TestPendingEventsSync(_Quiet):
    """`SyncInterpreter` processes inline, so pending events only exist
    while an action is mid-`send()` (re-entrancy) -- but the API must still
    exist, answer the empty case, and round-trip through a snapshot."""

    def test_pending_events_empty_after_synchronous_send(self) -> None:
        i = SyncInterpreter(_machine()).start()
        i.send("GO")
        self.assertEqual(i.pending_events, ())

    def test_pending_events_visible_from_inside_an_action(self) -> None:
        seen: Dict[str, Any] = {}

        def peek(interp, c, e, a):
            interp.send("BACK")  # queued behind the current macrostep
            seen["pending"] = [ev.type for ev in interp.pending_events]

        cfg = json.loads(json.dumps(CFG))
        cfg["states"]["a"]["on"]["GO"] = {"target": "b", "actions": ["peek"]}
        i = SyncInterpreter(_machine(cfg, actions={"peek": peek})).start()
        i.send("GO")
        self.assertEqual(seen["pending"], ["BACK"])
        self.assertEqual(i.current_state_ids, {"order.a"})  # BACK ran

    def test_drain_pending_returns_and_empties_queue(self) -> None:
        drained: Dict[str, Any] = {}

        def drain(interp, c, e, a):
            interp.send("BACK")
            drained["got"] = [ev.type for ev in interp.drain_pending()]
            drained["left"] = interp.pending_events

        cfg = json.loads(json.dumps(CFG))
        cfg["states"]["a"]["on"]["GO"] = {"target": "b", "actions": ["drain"]}
        i = SyncInterpreter(_machine(cfg, actions={"drain": drain})).start()
        i.send("GO")
        self.assertEqual(drained["got"], ["BACK"])
        self.assertEqual(drained["left"], ())
        self.assertEqual(i.current_state_ids, {"order.b"})  # BACK never ran


class TestPendingEventsAsync(_Quiet):
    def _cfg(self) -> Dict[str, Any]:
        cfg = json.loads(json.dumps(CFG))
        cfg["context"]["seen"] = []
        cfg["states"]["b"]["on"]["TICK"] = {"actions": ["rec"]}
        return cfg

    def _logic(self) -> Dict[str, Any]:
        def rec(i, c, e, a):
            c["seen"].append(e.payload.get("n"))

        return {"rec": rec}

    def test_pending_events_reports_unprocessed_in_order(self) -> None:
        async def main():
            i = Interpreter(_machine(self._cfg(), actions=self._logic()))
            # Not started: everything sent sits in the inbox.
            await i.send("GO")
            await i.send("TICK", n=1)
            await i.send("TICK", n=2)
            return [(e.type, e.payload) for e in i.pending_events]

        self.assertEqual(
            asyncio.run(main()),
            [("GO", {}), ("TICK", {"n": 1}), ("TICK", {"n": 2})],
        )

    def test_drain_pending_returns_and_empties_queue(self) -> None:
        async def main():
            i = Interpreter(_machine(self._cfg(), actions=self._logic()))
            await i.send("GO")
            await i.send("TICK", n=1)
            got = [e.type for e in await i.drain_pending()]
            left = i.pending_events
            await i.start()
            await asyncio.sleep(0.03)
            out = (
                got,
                left,
                set(i.current_state_ids),
                list(i.context["seen"]),
            )
            await i.stop()
            return out

        got, left, state, seen = asyncio.run(main())
        self.assertEqual(got, ["GO", "TICK"])
        self.assertEqual(left, ())
        self.assertEqual(state, {"order.a"})  # drained events never ran
        self.assertEqual(seen, [])

    def test_snapshot_round_trip_preserves_pending_events(self) -> None:
        async def main():
            i = Interpreter(_machine(self._cfg(), actions=self._logic()))
            await i.start()
            await asyncio.sleep(0.02)
            await i.send("GO")
            await asyncio.sleep(0.02)
            # Stop the loop so events accumulate without being processed.
            await i.stop()
            snap = json.loads(i.get_snapshot())
            return snap

        # Build the persisted form by hand around a started machine in `b`,
        # then inject pending events -- the equivalent of a crash between
        # `send()` and processing.
        snap = asyncio.run(main())
        snap["status"] = "running"
        snap["pending_events"] = [
            {"type": "TICK", "payload": {"n": 1}},
            {"type": "TICK", "payload": {"n": 2}},
        ]

        async def resume():
            j = Interpreter.from_snapshot(
                json.dumps(snap), _machine(self._cfg(), actions=self._logic())
            )
            self.assertEqual(
                [e.type for e in j.pending_events], ["TICK", "TICK"]
            )
            await j.start()
            await asyncio.sleep(0.05)
            out = list(j.context["seen"])
            await j.stop()
            return out

        self.assertEqual(asyncio.run(resume()), [1, 2])

    def test_persisted_snapshot_lists_pending_events(self) -> None:
        async def main():
            i = Interpreter(_machine(self._cfg(), actions=self._logic()))
            await i.send("GO")
            await i.send("TICK", n=9)
            return i.get_persisted_snapshot()["pending_events"]

        self.assertEqual(
            asyncio.run(main()),
            [
                {"kind": "event", "type": "GO", "payload": {}},
                {"kind": "event", "type": "TICK", "payload": {"n": 9}},
            ],
        )

    def test_stop_with_drain_processes_remaining_events(self) -> None:
        async def main():
            i = Interpreter(_machine(self._cfg(), actions=self._logic()))
            await i.start()
            await i.send("GO")
            for n in range(5):
                await i.send("TICK", n=n)
            # No sleep: the inbox is non-empty when stop() is called.
            await i.stop(drain=True)
            return list(i.context["seen"]), i.pending_events

        seen, left = asyncio.run(main())
        self.assertEqual(seen, [0, 1, 2, 3, 4])
        self.assertEqual(left, ())

    def test_stop_without_drain_warns_when_queue_non_empty(self) -> None:
        async def main():
            i = Interpreter(_machine(self._cfg(), actions=self._logic()))
            await i.start()
            await i.send("GO")
            for n in range(50):
                await i.send("TICK", n=n)
            logging.disable(logging.NOTSET)
            with self.assertLogs(level="WARNING") as logs:
                await i.stop()
            return logs.output

        out = asyncio.run(main())
        self.assertTrue(any("pending event" in line for line in out), out)

    def test_old_snapshot_without_pending_events_restores(self) -> None:
        i = SyncInterpreter(_machine()).start()
        snap = json.loads(i.get_snapshot())
        snap.pop("pending_events", None)
        j = SyncInterpreter.from_snapshot(json.dumps(snap), _machine())
        self.assertEqual(j.pending_events, ())

    def test_child_actor_pending_events_round_trip(self) -> None:
        """A live child's inbox is captured recursively (like `_persist_actors`)
        and re-enqueued on restore."""
        child = {
            "id": "kid",
            "initial": "i",
            "states": {"i": {"on": {"PING": {"actions": ["hit"]}}}},
        }
        parent = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "kid", "id": "k"}}},
        }

        async def main():
            kid = create_machine(
                child, logic=MachineLogic(actions={"hit": lambda *a: None})
            )
            i = Interpreter(_machine(parent, services={"kid": kid}))
            await i.start()
            for _ in range(200):  # wait for the invoke task to register
                if "p:k" in i._actors:
                    break
                await asyncio.sleep(0.005)
            k = i._actors["p:k"]
            # Enqueue WITHOUT yielding: the child's loop has not run yet, so
            # the event is genuinely pending at snapshot time.
            k.send("PING")
            snap = i.get_persisted_snapshot()
            await i.stop()
            return snap

        snap = asyncio.run(main())
        self.assertEqual(
            snap["actors"]["p:k"]["snapshot"]["pending_events"],
            [{"kind": "event", "type": "PING", "payload": {}}],
        )

        async def restore():
            kid = create_machine(
                child, logic=MachineLogic(actions={"hit": lambda *a: None})
            )
            j = Interpreter.from_snapshot(
                json.dumps(snap, default=str),
                _machine(parent, services={"kid": kid}),
            )
            return [e.type for e in j._actors["p:k"].pending_events]

        self.assertEqual(asyncio.run(restore()), ["PING"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
