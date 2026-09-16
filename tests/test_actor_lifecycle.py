# tests/test_actor_lifecycle.py
# -----------------------------------------------------------------------------
# 🏛️ #43 (LC-28) + #57 (LC-32): actor completion is a SIGNAL, and it REAPS
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the parent used to learn that a child finished
# by polling `child.status` every 5 ms in a second task -- so every idle
# child cost two tasks and 200 wake-ups a second, and `onDone` had a 5 ms
# floor. And a machine that reached its final state kept its children,
# timers and registry entry alive until someone remembered to call stop().
# Both fixed by one primitive: a per-interpreter completion future that
# `_complete()` / `_fail()` resolve, which the parent awaits and which
# triggers teardown of everything except `status`, `output` and `context`.
# -----------------------------------------------------------------------------
"""Actor completion signal (#43) and terminal-machine reaping (#57)."""

import asyncio
import gc
import logging
import time
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.plugins import PluginBase


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


async def _until(pred, timeout: float = 2.0) -> None:
    """Poll *pred* until true. Fixed sleeps flake on a loaded host; a
    bounded wait on the actual condition does not."""
    for _ in range(int(timeout / 0.002)):
        if pred():
            return
        await asyncio.sleep(0.002)
    raise AssertionError("condition not met in time")


# A child that finishes when told to.
CHILD: Dict[str, Any] = {
    "id": "kid",
    "initial": "work",
    "states": {"work": {"on": {"FINISH": "done"}}, "done": {"type": "final"}},
}
# A child that runs "forever" (long timer) -- what a leaked actor looks like.
SLOW_CHILD: Dict[str, Any] = {
    "id": "slow",
    "initial": "wait",
    "states": {"wait": {"after": {"60000": "late"}}, "late": {}},
}


def _parent_invoking(child_src: str = "kid") -> Dict[str, Any]:
    return {
        "id": "p",
        "initial": "a",
        "context": {"done": 0, "err": 0},
        "states": {
            "a": {
                "invoke": {
                    "src": child_src,
                    "id": "k",
                    "onDone": {"target": "b", "actions": ["mark_done"]},
                    "onError": {"target": "c", "actions": ["mark_err"]},
                },
                "on": {"LEAVE": "b"},
            },
            "b": {},
            "c": {},
        },
    }


def _logic(**services: Any) -> MachineLogic:
    def mark_done(i, c, e, a):
        c["done"] += 1

    def mark_err(i, c, e, a):
        c["err"] += 1

    return MachineLogic(
        actions={"mark_done": mark_done, "mark_err": mark_err},
        services=services,
    )


# -----------------------------------------------------------------------------
# #43 — completion is awaited, not polled
# -----------------------------------------------------------------------------
class TestActorCompletionSignal(_Quiet):
    def test_poll_interval_constant_is_gone(self) -> None:
        import src.xstate_statemachine.interpreter as mod

        self.assertFalse(hasattr(mod, "_ACTOR_POLL_INTERVAL"))

    def test_idle_child_actors_cost_one_task_each(self) -> None:
        N = 50

        async def main():
            base = len(asyncio.all_tasks())
            children = [
                {
                    "id": f"c{n}",
                    "initial": "w",
                    "states": {
                        "w": {"on": {"FINISH": "d"}},
                        "d": {"type": "final"},
                    },
                }
                for n in range(N)
            ]
            parent = {
                "id": "p",
                "type": "parallel",
                "states": {
                    f"r{n}": {
                        "initial": "a",
                        "states": {"a": {"invoke": {"src": f"c{n}"}}},
                    }
                    for n in range(N)
                },
            }
            logic = MachineLogic(
                services={
                    f"c{n}": create_machine(children[n]) for n in range(N)
                }
            )
            i = await Interpreter(create_machine(parent, logic=logic)).start()
            await asyncio.sleep(0.1)
            extra = len(asyncio.all_tasks()) - base
            await i.stop()
            return extra

        extra = asyncio.run(main())
        # 1 parent run loop + (1 manager + 1 child run loop) per child. The
        # *polling* task is gone; the child's own loop is not "overhead".
        self.assertLessEqual(extra, 1 + 2 * N, extra)

    def test_on_done_latency_is_immediate(self) -> None:
        async def main():
            samples: List[float] = []
            for _ in range(20):
                kid = create_machine(CHILD)
                i = await Interpreter(
                    create_machine(_parent_invoking(), logic=_logic(kid=kid))
                ).start()
                for _ in range(200):
                    if "p:k" in i._actors:
                        break
                    await asyncio.sleep(0.001)
                child = i._actors["p:k"]
                t0 = time.perf_counter()
                await child.send("FINISH")
                while i.context["done"] == 0:
                    await asyncio.sleep(0)
                samples.append((time.perf_counter() - t0) * 1000)
                await i.stop()
            return samples

        samples = asyncio.run(main())
        samples.sort()
        median = samples[len(samples) // 2]
        self.assertLess(median, 2.0, f"median onDone latency {median:.2f} ms")

    def test_child_error_still_fires_on_error(self) -> None:
        bad = {
            "id": "bad",
            "initial": "s",
            "actionErrorPolicy": "fail",
            "states": {"s": {"entry": ["boom"]}},
        }

        def boom(i, c, e, a):
            raise RuntimeError("child exploded")

        async def main():
            kid = create_machine(
                bad, logic=MachineLogic(actions={"boom": boom})
            )
            i = await Interpreter(
                create_machine(_parent_invoking(), logic=_logic(kid=kid))
            ).start()
            await asyncio.sleep(0.05)
            out = (set(i.current_state_ids), i.context["err"])
            await i.stop()
            return out

        state, err = asyncio.run(main())
        self.assertEqual(state, {"p.c"})
        self.assertEqual(err, 1)

    def test_child_completing_during_start_fires_on_done_once(self) -> None:
        instant = {
            "id": "now",
            "initial": "f",
            "states": {"f": {"type": "final"}},
        }

        async def main():
            kid = create_machine(instant)
            i = await Interpreter(
                create_machine(_parent_invoking(), logic=_logic(kid=kid))
            ).start()
            await asyncio.sleep(0.05)
            out = (set(i.current_state_ids), i.context["done"])
            await i.stop()
            return out

        state, done = asyncio.run(main())
        self.assertEqual(state, {"p.b"})
        self.assertEqual(done, 1)

    def test_actor_cancelled_on_parent_state_exit(self) -> None:
        async def main():
            kid = create_machine(SLOW_CHILD)
            i = await Interpreter(
                create_machine(_parent_invoking(), logic=_logic(kid=kid))
            ).start()
            for _ in range(200):
                if "p:k" in i._actors:
                    break
                await asyncio.sleep(0.001)
            child = i._actors["p:k"]
            await i.send("LEAVE")
            # Wait for ALL three observable outcomes. Their relative order is
            # not part of the contract and genuinely differs between Python
            # versions: on 3.9 the cancelled child's manager task runs its
            # `finally` (stop + pop from `_actors`) BEFORE the parent's
            # `_enter_states` returns; on 3.14 after. Polling only two of
            # the three read `p.a` on 3.9 -- a test bug, not an engine one.
            await _until(
                lambda: i.current_state_ids == {"p.b"}
                and child.status == "stopped"
                and not i._actors
            )
            out = (set(i.current_state_ids), child.status, list(i._actors))
            await i.stop()
            return out

        state, child_status, actors = asyncio.run(main())
        self.assertEqual(state, {"p.b"})
        self.assertEqual(child_status, "stopped")
        self.assertEqual(actors, [])


# -----------------------------------------------------------------------------
# #57 — reaching a final state reaps
# -----------------------------------------------------------------------------
COMPLETING_PARENT: Dict[str, Any] = {
    "id": "order",
    "initial": "live",
    "context": {"blob": "x" * 1000},
    "states": {
        "live": {
            "entry": [
                {
                    "type": "spawnChild",
                    "params": {
                        "src": "leg",
                        "id": "legA",
                        "systemId": "legsys",
                    },
                }
            ],
            "after": {"60000": "never"},
            "on": {"FILL": "filled"},
        },
        "never": {},
        "filled": {"type": "final"},
    },
    "output": {"ok": True},
}


class TestReapingAsync(_Quiet):
    def _start(self) -> Any:
        leg = create_machine(SLOW_CHILD)
        return Interpreter(
            create_machine(
                COMPLETING_PARENT, logic=MachineLogic(services={"leg": leg})
            )
        )

    def test_child_actors_stopped_when_parent_reaches_final_state(
        self,
    ) -> None:
        async def main():
            i = await self._start().start()
            await _until(lambda: "order:legA" in i._actors)
            child = i._actors["order:legA"]
            await i.send("FILL")
            await _until(lambda: i.status == "done" and not i._actors)
            return i.status, child.status, dict(i._actors)

        status, child_status, actors = asyncio.run(main())
        self.assertEqual(status, "done")
        self.assertEqual(child_status, "stopped")
        self.assertEqual(actors, {})

    def test_timers_and_service_tasks_cancelled_on_completion(self) -> None:
        async def main():
            base = len(asyncio.all_tasks())
            i = await self._start().start()
            await _until(lambda: "order:legA" in i._actors)
            await i.send("FILL")
            await _until(lambda: len(asyncio.all_tasks()) - base == 0)
            return len(asyncio.all_tasks()) - base

        self.assertEqual(asyncio.run(main()), 0)

    def test_system_registry_empty_after_completion(self) -> None:
        async def main():
            i = await self._start().start()
            await _until(lambda: "order:legA" in i._actors)
            before = dict(i.system.get_all())
            await i.send("FILL")
            await _until(lambda: not i.system.get_all())
            return before, dict(i.system.get_all())

        before, after = asyncio.run(main())
        self.assertIn("legsys", before)
        self.assertEqual(after, {})

    def test_system_registry_empty_after_explicit_stop(self) -> None:
        async def main():
            i = await self._start().start()
            await _until(lambda: "order:legA" in i._actors)
            await i.stop()
            return dict(i.system.get_all())

        self.assertEqual(asyncio.run(main()), {})

    def test_output_and_context_readable_after_completion(self) -> None:
        async def main():
            i = await self._start().start()
            await _until(lambda: "order:legA" in i._actors)
            await i.send("FILL")
            await _until(lambda: i.status == "done")
            return i.status, i.output, len(i.context["blob"])

        self.assertEqual(asyncio.run(main()), ("done", {"ok": True}, 1000))

    def test_on_done_plugin_hook_runs_before_teardown(self) -> None:
        class Spy(PluginBase):
            def __init__(self):
                self.seen_children = None

            def on_done(self, interp, output):
                self.seen_children = list(interp._actors)

        async def main():
            spy = Spy()
            i = self._start()
            i.use(spy)
            await i.start()
            await _until(lambda: "order:legA" in i._actors)
            await i.send("FILL")
            await _until(lambda: spy.seen_children is not None)
            return spy.seen_children

        self.assertEqual(asyncio.run(main()), ["order:legA"])

    def test_stop_after_done_is_noop(self) -> None:
        async def main():
            i = await self._start().start()
            await _until(lambda: "order:legA" in i._actors)
            await i.send("FILL")
            await _until(lambda: i.status == "done" and not i._actors)
            # `assertNoLogs` is 3.10+; capture by hand for the 3.9 floor.
            logging.disable(logging.NOTSET)
            records = []
            handler = logging.Handler()
            handler.emit = records.append  # type: ignore[assignment]
            handler.setLevel(logging.WARNING)
            logging.getLogger().addHandler(handler)
            try:
                await i.stop()
            finally:
                logging.getLogger().removeHandler(handler)
            self.assertEqual(records, [], [r.getMessage() for r in records])
            return i.status

        self.assertEqual(asyncio.run(main()), "done")

    def test_fleet_of_completed_machines_releases_references(self) -> None:
        """1,000 spawn/complete cycles leave no live child Interpreters.

        Teardown is deferred by one loop turn and each child's stop awaits
        its run-loop cancellation, so 1,000 of them take real wall time;
        wait for the loop to go quiet rather than a magic sleep.
        """
        leg = create_machine(SLOW_CHILD)

        async def main():
            for _ in range(1000):
                i = await Interpreter(
                    create_machine(
                        COMPLETING_PARENT,
                        logic=MachineLogic(services={"leg": leg}),
                    )
                ).start()
                await i.send("FILL")
            # ⏳ Quiesce: wait until only this task remains.
            for _ in range(2000):
                if len(asyncio.all_tasks()) <= 1:
                    break
                await asyncio.sleep(0.005)
            gc.collect()
            return sum(
                1
                for o in gc.get_objects()
                if isinstance(o, Interpreter)
                and o.machine.id == "slow"
                and o.status != "stopped"
            )

        self.assertEqual(asyncio.run(main()), 0)


class TestReapingSync(_Quiet):
    def _start(self) -> SyncInterpreter:
        leg = create_machine(SLOW_CHILD)
        return SyncInterpreter(
            create_machine(
                COMPLETING_PARENT, logic=MachineLogic(services={"leg": leg})
            )
        ).start()

    def test_child_actors_stopped_when_parent_reaches_final_state(
        self,
    ) -> None:
        i = self._start()
        child = i._actors["order:legA"]
        i.send("FILL")
        self.assertEqual(i.status, "done")
        self.assertEqual(child.status, "stopped")
        self.assertEqual(i._actors, {})

    def test_after_timers_cancelled_on_completion(self) -> None:
        i = self._start()
        self.assertTrue(i._timer_handles)  # #50: clock handles, not threads
        i.send("FILL")
        self.assertEqual(i._timer_handles, {})
        self.assertEqual(i.clock.pending, 0)

    def test_system_registry_empty_after_completion_and_stop(self) -> None:
        i = self._start()
        self.assertIn("legsys", i.system.get_all())
        i.send("FILL")
        self.assertEqual(dict(i.system.get_all()), {})
        j = self._start()
        j.stop()
        self.assertEqual(dict(j.system.get_all()), {})

    def test_output_and_context_readable_after_completion(self) -> None:
        i = self._start()
        i.send("FILL")
        self.assertEqual((i.status, i.output), ("done", {"ok": True}))
        self.assertEqual(len(i.context["blob"]), 1000)

    def test_stop_after_done_is_noop(self) -> None:
        i = self._start()
        i.send("FILL")
        i.stop()
        self.assertEqual(i.status, "done")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
