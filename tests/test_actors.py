# tests/test_actors.py
# -----------------------------------------------------------------------------
# 🏛️ #41 (LC-12): `spawn_blocking_<key>` means the same on both engines
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the sync engine gave `spawn_blocking_` a distinct
# meaning -- the child runs to completion before the parent's NEXT action --
# while the async engine dispatched on `startswith("spawn_")` and discarded
# the marker. One action string, two behaviours, no warning: exactly the
# divergence class #60 exists to prevent. The async engine now honours it:
# after `start()` it awaits the child's completion future (#43) before
# returning to the action list.
# -----------------------------------------------------------------------------
"""`spawn_blocking_` parity on the async `Interpreter` (#41)."""

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


# A child whose work happens in entry actions and ends in a final state --
# the filer's shape. "Blocking" means the child's start() runs to completion
# before the parent's next action; on the sync engine that has always been
# the guarantee (entry actions run inline in start()), and the async engine
# now matches it by awaiting the child's completion future.
WORKER: Dict[str, Any] = {
    "id": "worker",
    "initial": "busy",
    "context": {"n": 0},
    "states": {
        "busy": {"entry": ["work"], "always": "finished"},
        "finished": {"type": "final"},
    },
}


def _parent(spawn_action: str) -> Dict[str, Any]:
    return {
        "id": "p",
        "initial": "a",
        "context": {"log": []},
        "states": {
            "a": {"entry": [spawn_action, "after_spawn"]},
        },
    }


def _logic(seen: List[Any]) -> MachineLogic:
    def after_spawn(interp, ctx, event, action_def):
        # What does the parent's NEXT action observe about the child?
        children = list(interp._actors.values())
        seen.append([c.status for c in children])

    def work(interp, ctx, event, action_def):
        ctx["n"] += 1

    return MachineLogic(
        actions={"after_spawn": after_spawn},
        services={
            "worker": create_machine(
                WORKER, logic=MachineLogic(actions={"work": work})
            )
        },
    )


class TestAsyncSpawnBlocking(_Quiet):
    def test_async_spawn_blocking_waits_for_child_final_state(self) -> None:
        seen: List[Any] = []

        async def main():
            i = await Interpreter(
                create_machine(
                    _parent("spawn_blocking_worker"), logic=_logic(seen)
                )
            ).start()
            await asyncio.sleep(0.02)
            await i.stop()

        asyncio.run(main())
        self.assertEqual(seen, [["done"]])

    def test_async_spawn_non_blocking_does_not_wait(self) -> None:
        """Pins the contrast so the two modes cannot re-converge.

        Uses a child that finishes on an `after` timer, so its completion
        is strictly later than `start()`; the non-blocking parent's next
        action therefore observes it still running, while (see the blocking
        test below) `spawn_blocking_` would wait it out.
        """
        seen: List[Any] = []
        slow = {
            "id": "slow",
            "initial": "busy",
            "states": {
                "busy": {"after": {"40": "finished"}},
                "finished": {"type": "final"},
            },
        }

        def after_spawn(interp, ctx, event, action_def):
            seen.append([c.status for c in interp._actors.values()])

        logic = MachineLogic(
            actions={"after_spawn": after_spawn},
            services={"worker": create_machine(slow)},
        )

        async def main():
            i = await Interpreter(
                create_machine(_parent("spawn_worker"), logic=logic)
            ).start()
            await asyncio.sleep(0.1)
            await i.stop()

        asyncio.run(main())
        self.assertEqual(seen, [["running"]])

    def test_async_spawn_blocking_waits_out_a_timer_child(self) -> None:
        """Same timer child as above, blocking: parent sees it finished."""
        seen: List[Any] = []
        slow = {
            "id": "slow",
            "initial": "busy",
            "states": {
                "busy": {"after": {"40": "finished"}},
                "finished": {"type": "final"},
            },
        }

        def after_spawn(interp, ctx, event, action_def):
            seen.append([c.status for c in interp._actors.values()])

        logic = MachineLogic(
            actions={"after_spawn": after_spawn},
            services={"worker": create_machine(slow)},
        )

        async def main():
            i = await Interpreter(
                create_machine(_parent("spawn_blocking_worker"), logic=logic)
            ).start()
            await i.stop()

        asyncio.run(main())
        self.assertEqual(seen, [["done"]])

    def test_blocking_child_with_no_final_state_does_not_hang_forever(
        self,
    ) -> None:
        """A blocking spawn of a never-ending child must be bounded."""
        forever = {"id": "f", "initial": "x", "states": {"x": {}}}
        cfg = _parent("spawn_blocking_f")
        cfg["spawnBlockingTimeout"] = 50  # ms

        async def main():
            logic = MachineLogic(
                actions={"after_spawn": lambda *a: None},
                services={"f": create_machine(forever)},
            )
            i = Interpreter(create_machine(cfg, logic=logic))
            await asyncio.wait_for(i.start(), timeout=2.0)
            out = i.status
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), "running")


class TestSpawnBlockingParity(_Quiet):
    def test_spawn_blocking_prefix_means_the_same_on_both_engines(
        self,
    ) -> None:
        sync_seen: List[Any] = []
        i = SyncInterpreter(
            create_machine(
                _parent("spawn_blocking_worker"), logic=_logic(sync_seen)
            )
        ).start()
        i.stop()

        async_seen: List[Any] = []

        async def main():
            j = await Interpreter(
                create_machine(
                    _parent("spawn_blocking_worker"), logic=_logic(async_seen)
                )
            ).start()
            await j.stop()

        asyncio.run(main())
        self.assertEqual(sync_seen, async_seen)
        self.assertEqual(sync_seen, [["done"]])


class TestNoBareLiteral(_Quiet):
    def test_spawn_blocking_prefix_constant_is_the_only_spelling(self) -> None:
        import pathlib

        src = pathlib.Path("src/xstate_statemachine")
        offenders = [
            str(f)
            for f in src.rglob("*.py")
            if f.name != "models.py"
            and '"spawn_blocking_"' in f.read_text(encoding="utf-8")
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
