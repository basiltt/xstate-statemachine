# tests/test_restore_services.py
# -----------------------------------------------------------------------------
# 🏛️ #44 (LC-19): a restored machine with dormant invokes can be re-driven
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `from_snapshot` is a STATIC restore -- it puts
# the configuration back but starts no service, so a machine snapshotted
# mid-`invoke` came back "running" in a state whose work would never
# complete. That default is kept (restarting a non-idempotent placement is
# worse than parking), but it is no longer silent: `pending_invocations()`
# lists every invoke in the restored configuration with no live task, and
# `from_snapshot(..., restart_services=True)` re-invokes them from scratch
# through the SAME path `_enter_states` uses, owner-registered so leaving
# the state still cancels them.
# -----------------------------------------------------------------------------
"""Restore-time service restart and inspection (#44)."""

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


# The filer's OMS: snapshotted while `place` is in flight.
OMS: Dict[str, Any] = {
    "id": "oms",
    "initial": "submitting",
    "context": {"acked": False},
    "states": {
        "submitting": {
            "invoke": {"src": "place", "id": "place", "onDone": "live"},
            "on": {"LEAVE": "idle"},
        },
        "live": {"entry": ["ack"]},
        "idle": {},
    },
}


def _logic(calls: List[str], slow: float = 0.02) -> MachineLogic:
    async def place(i, c, e):
        calls.append("place")
        await asyncio.sleep(slow)
        return "ok"

    def place_sync(i, c, e):
        calls.append("place")
        return "ok"

    def ack(i, c, e, a):
        c["acked"] = True

    return MachineLogic(
        actions={"ack": ack},
        services={"place": place, "place_sync": place_sync},
    )


async def _snapshot_mid_invoke(calls: List[str]) -> str:
    """Start the OMS, snapshot while `place` is still running, stop."""
    i = await Interpreter(
        create_machine(OMS, logic=_logic(calls, slow=5.0))
    ).start()
    await asyncio.sleep(0.01)  # invoke task started, far from done
    snap = i.get_snapshot()
    await i.stop()
    return snap


class TestPendingInvocations(_Quiet):
    def test_pending_invocations_lists_dormant_invokes_after_static_restore(
        self,
    ) -> None:
        async def main():
            snap = await _snapshot_mid_invoke([])
            r = Interpreter.from_snapshot(
                snap, create_machine(OMS, logic=_logic([]))
            )
            return [
                (p.state_id, p.invoke_id, p.src)
                for p in r.pending_invocations()
            ]

        self.assertEqual(
            asyncio.run(main()), [("oms.submitting", "place", "place")]
        )

    def test_pending_invocations_is_empty_on_a_live_machine(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(OMS, logic=_logic([]))
            ).start()
            await asyncio.sleep(0.005)
            out = i.pending_invocations()
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), [])

    def test_pending_invocations_is_empty_after_restart_services(self) -> None:
        async def main():
            snap = await _snapshot_mid_invoke([])
            r = Interpreter.from_snapshot(
                snap,
                create_machine(OMS, logic=_logic([])),
                restart_services=True,
            )
            await r.start()
            out = r.pending_invocations()
            await r.stop()
            return out

        self.assertEqual(asyncio.run(main()), [])


class TestRestartServices(_Quiet):
    def test_default_does_not_restart_services(self) -> None:
        calls: List[str] = []

        async def main():
            snap = await _snapshot_mid_invoke(calls)
            calls.clear()
            r = Interpreter.from_snapshot(
                snap, create_machine(OMS, logic=_logic(calls))
            )
            await r.start()
            await asyncio.sleep(0.05)
            out = (list(calls), set(r.current_state_ids), r.status)
            await r.stop()
            return out

        calls_after, state, status = asyncio.run(main())
        self.assertEqual(calls_after, [])  # parked, as before
        self.assertEqual(state, {"oms.submitting"})
        self.assertEqual(status, "running")

    def test_restart_services_reinvokes_active_invocations(self) -> None:
        calls: List[str] = []

        async def main():
            snap = await _snapshot_mid_invoke(calls)
            calls.clear()
            r = Interpreter.from_snapshot(
                snap,
                create_machine(OMS, logic=_logic(calls)),
                restart_services=True,
            )
            await r.start()
            for _ in range(200):
                if r.current_state_ids == {"oms.live"}:
                    break
                await asyncio.sleep(0.005)
            out = (list(calls), set(r.current_state_ids), r.context["acked"])
            await r.stop()
            return out

        calls_after, state, acked = asyncio.run(main())
        self.assertEqual(
            calls_after, ["place"]
        )  # re-invoked from scratch, once
        self.assertEqual(state, {"oms.live"})
        self.assertTrue(acked)

    def test_restarted_invoke_is_cancelled_on_state_exit(self) -> None:
        calls: List[str] = []

        async def main():
            snap = await _snapshot_mid_invoke(calls)
            r = Interpreter.from_snapshot(
                snap,
                create_machine(OMS, logic=_logic(calls, slow=5.0)),
                restart_services=True,
            )
            await r.start()
            await asyncio.sleep(0.005)
            before = len(r.task_manager.get_tasks_by_owner("oms.submitting"))
            await r.send("LEAVE")
            for _ in range(100):
                if r.current_state_ids == {"oms.idle"}:
                    break
                await asyncio.sleep(0.005)
            after = len(r.task_manager.get_tasks_by_owner("oms.submitting"))
            pending = len(asyncio.all_tasks())
            await r.stop()
            return before, after, pending

        before, after, _ = asyncio.run(main())
        self.assertGreater(before, 0)
        self.assertEqual(after, 0)  # owner-registered, so exit cancelled it

    def test_restart_services_behaves_identically_on_both_engines(
        self,
    ) -> None:
        cfg = dict(OMS)
        cfg["states"] = {
            **OMS["states"],
            "submitting": {
                "invoke": {
                    "src": "place_sync",
                    "id": "place",
                    "onDone": "live",
                },
                "on": {"LEAVE": "idle"},
            },
        }
        calls: List[str] = []
        # Build a static snapshot by hand: the persisted shape of a machine
        # parked in `submitting`.
        base = SyncInterpreter(
            create_machine(cfg, logic=_logic(calls))
        ).start()
        # sync invoke completed inline -> base is in `live`; force the shape
        snap = base.get_persisted_snapshot()
        snap["state_ids"] = ["oms.submitting"]
        snap["configuration"] = ["oms", "oms.submitting"]
        snap["value"] = "submitting"
        base.stop()
        import json

        calls.clear()
        s = SyncInterpreter.from_snapshot(
            json.dumps(snap),
            create_machine(cfg, logic=_logic(calls)),
            restart_services=True,
        )
        self.assertEqual(
            [(p.invoke_id, p.src) for p in s.pending_invocations()],
            [("place", "place_sync")],
        )
        s.start()
        self.assertEqual(calls, ["place"])
        self.assertEqual(s.current_state_ids, {"oms.live"})
        self.assertEqual(s.pending_invocations(), [])
        s.stop()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
