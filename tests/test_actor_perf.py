"""Acceptance tests for #43: one task per invoked child, push-based
completion, no periodic wake-ups while children are idle.

These pin the RESOURCE contract, not just behaviour: a regression that
reintroduced a per-child waiter task would pass every functional test
and fail here.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    ErrorEvent,
    Interpreter,
    MachineLogic,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


IDLE_CHILD: Dict[str, Any] = {
    "id": "kid",
    "initial": "waiting",
    "states": {
        "waiting": {"on": {"FINISH": "done"}},
        "done": {"type": "final"},
    },
}


def _parent_with_children(n: int) -> Dict[str, Any]:
    """A parallel parent that invokes *n* idle children at once."""
    return {
        "id": "p",
        "type": "parallel",
        "context": {"done": 0},
        "states": {
            f"r{k}": {
                "initial": "run",
                "states": {
                    "run": {
                        "invoke": {
                            "src": "kid",
                            "id": f"kid{k}",
                            "onDone": {"target": "ok", "actions": "bump"},
                        }
                    },
                    "ok": {"type": "final"},
                },
            }
            for k in range(n)
        },
    }


def _logic() -> MachineLogic:
    return MachineLogic(
        actions={
            "bump": lambda i, c, e, a: c.__setitem__("done", c["done"] + 1)
        },
        services={"kid": create_machine(IDLE_CHILD)},
    )


class TestActorTaskBudget(_Quiet):
    def test_idle_child_actors_cost_one_task_each(self) -> None:
        """Invoking 50 children adds ≤ 1 asyncio task per child over a
        0-child baseline (#43 acceptance)."""

        async def main():
            base = await Interpreter(
                create_machine(_parent_with_children(0), logic=_logic())
            ).start()
            await asyncio.sleep(0.02)
            baseline = len(asyncio.all_tasks())
            await base.stop()
            await asyncio.sleep(0.02)

            p = await Interpreter(
                create_machine(_parent_with_children(50), logic=_logic())
            ).start()
            await asyncio.sleep(0.05)  # let bring-up tasks finish
            with_children = len(asyncio.all_tasks())
            live_children = sum(
                1 for a in p._actors.values() if a.status == "running"
            )
            await p.stop()
            return baseline, with_children, live_children

        baseline, with_children, live = asyncio.run(main())
        self.assertEqual(live, 50, "all 50 children should be running")
        # +1 for the parent's own run loop.
        self.assertLessEqual(
            with_children - baseline,
            50 + 1,
            f"{with_children - baseline} tasks for 50 children (+parent)",
        )

    def test_no_polling_wakeups_while_children_idle(self) -> None:
        """With 20 idle children, the loop schedules no timer callbacks
        attributable to actor management over a 200 ms window."""

        async def main():
            p = await Interpreter(
                create_machine(_parent_with_children(20), logic=_logic())
            ).start()
            await asyncio.sleep(0.05)
            loop = asyncio.get_running_loop()
            # Count `call_later` scheduling while idle. The library's own
            # timers are only created by `after` / delayed sends, none of
            # which this machine declares, so any hit is a poll.
            scheduled = []
            orig = loop.call_later

            def spy(delay, cb, *args, **kw):
                scheduled.append(delay)
                return orig(delay, cb, *args, **kw)

            loop.call_later = spy  # type: ignore[method-assign]
            try:
                await asyncio.sleep(0.2)
            finally:
                loop.call_later = orig  # type: ignore[method-assign]
            await p.stop()
            # asyncio.sleep itself uses call_later once for OUR sleep.
            return [d for d in scheduled if d != 0.2]

        self.assertEqual(asyncio.run(main()), [])

    def test_on_done_latency_is_immediate(self) -> None:
        """A child driven to final fires the parent's `onDone` within a
        single loop settle: median < 2 ms over 50 repetitions (was a 5 ms
        floor with the poll)."""

        async def one() -> float:
            p = await Interpreter(
                create_machine(_parent_with_children(1), logic=_logic())
            ).start()
            await asyncio.sleep(0.01)
            kid = next(iter(p._actors.values()))
            t0 = time.perf_counter()
            await kid.send("FINISH")
            for _ in range(2000):
                if p.context["done"] == 1:
                    break
                await asyncio.sleep(0)
            dt = (time.perf_counter() - t0) * 1000
            await p.stop()
            return dt

        async def main():
            return [await one() for _ in range(50)]

        samples = asyncio.run(main())
        self.assertLess(
            statistics.median(samples),
            2.0,
            f"median {statistics.median(samples):.2f} ms",
        )


class TestErrorEvent(_Quiet):
    def test_service_failure_delivers_error_event(self) -> None:
        """#80 acceptance: `error.platform.*` is an `ErrorEvent` exposing
        `.error`; `DoneEvent` is never used for failure delivery."""
        seen: list = []

        async def failing(i, c, e):
            raise ValueError("boom")

        cfg = {
            "id": "svc",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "failing",
                        "id": "failing",
                        "onError": {"target": "b", "actions": "note"},
                    }
                },
                "b": {},
            },
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        actions={"note": lambda i, c, e, a: seen.append(e)},
                        services={"failing": failing},
                    ),
                )
            ).start()
            await asyncio.sleep(0.05)
            await i.stop()

        asyncio.run(main())
        self.assertEqual(len(seen), 1)
        ev = seen[0]
        self.assertIsInstance(ev, ErrorEvent)
        self.assertIsInstance(ev.error, ValueError)
        self.assertEqual(ev.type, "error.platform.failing")
        self.assertEqual(ev.src, "failing")

    def test_child_machine_failure_delivers_error_event(self) -> None:
        seen: list = []
        bad = {
            "id": "bad",
            "initial": "s",
            "actionErrorPolicy": "fail",
            "states": {"s": {"entry": ["boom"]}},
        }

        def boom(i, c, e, a):
            raise RuntimeError("child exploded")

        cfg = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "kid",
                        "onError": {"target": "c", "actions": "note"},
                    }
                },
                "c": {},
            },
        }

        async def main():
            kid = create_machine(
                bad, logic=MachineLogic(actions={"boom": boom})
            )
            i = await Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        actions={"note": lambda i, c, e, a: seen.append(e)},
                        services={"kid": kid},
                    ),
                )
            ).start()
            await asyncio.sleep(0.05)
            out = set(i.current_state_ids)
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), {"p.c"})
        self.assertIsInstance(seen[0], ErrorEvent)
        self.assertIsInstance(seen[0].error, Exception)

    def test_error_event_data_alias_is_deprecated(self) -> None:
        import warnings

        ev = ErrorEvent("error.platform.x", ValueError("v"), "x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertIs(ev.data, ev.error)
        self.assertTrue(any(x.category is DeprecationWarning for x in w))


class TestInvokedActorBringUpEdges(_Quiet):
    """The bring-up coroutine's failure and cancellation paths (#43), plus
    the plugin hooks that fire around a pushed completion."""

    def test_failing_input_resolver_delivers_error_event_and_leaves_no_child(
        self,
    ) -> None:
        seen: list = []

        def bad_input(ctx, ev):
            raise KeyError("no such key")

        cfg = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "kid",
                        "id": "kid",
                        "input": bad_input,
                        "onError": {"target": "c", "actions": "note"},
                    }
                },
                "c": {},
            },
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        actions={"note": lambda i, c, e, a: seen.append(e)},
                        services={"kid": create_machine(IDLE_CHILD)},
                    ),
                )
            ).start()
            await asyncio.sleep(0.05)
            out = (set(i.current_state_ids), dict(i._invoked_children))
            await i.stop()
            return out

        state, children = asyncio.run(main())
        self.assertEqual(state, {"p.c"})
        self.assertEqual(children, {}, "failed bring-up must not leak a child")
        self.assertIsInstance(seen[0], ErrorEvent)
        self.assertIsInstance(seen[0].error, KeyError)

    def test_exit_during_bring_up_cancels_cleanly(self) -> None:
        """Leave the invoking state on the very next tick after entering it:
        the bring-up task is cancelled, the child is stopped, nothing is
        orphaned and no `onDone` fires into the state we left."""
        cfg = {
            "id": "p",
            "initial": "a",
            "context": {"done": 0},
            "states": {
                "a": {
                    "invoke": {
                        "src": "kid",
                        "id": "kid",
                        "onDone": {"actions": "bump"},
                    },
                    "on": {"LEAVE": "b"},
                },
                "b": {},
            },
        }

        async def main():
            i = await Interpreter(create_machine(cfg, logic=_logic())).start()
            # No sleep: the bring-up task has been created but may not have
            # run `child.start()` yet.
            await i.send("LEAVE")
            await asyncio.sleep(0.05)
            live = [a for a in i._actors.values() if a.status == "running"]
            out = (
                set(i.current_state_ids),
                i.context["done"],
                len(live),
                dict(i._invoked_children),
            )
            await i.stop()
            return out

        state, done, live, children = asyncio.run(main())
        self.assertEqual(state, {"p.b"})
        self.assertEqual(done, 0)
        self.assertEqual(live, 0)
        self.assertEqual(children, {})

    def test_plugin_hooks_fire_around_pushed_completion(self) -> None:
        from src.xstate_statemachine import PluginBase

        class Spy(PluginBase):
            def __init__(self):
                self.calls = []

            def on_service_start(self, interp, inv):
                self.calls.append(("start", inv.id))

            def on_service_done(self, interp, inv, result):
                self.calls.append(("done", inv.id))

            def on_service_error(self, interp, inv, err):
                self.calls.append(("error", inv.id, type(err).__name__))

        bad = {
            "id": "bad",
            "initial": "s",
            "actionErrorPolicy": "fail",
            "states": {"s": {"entry": ["boom"]}},
        }

        def boom(i, c, e, a):
            raise RuntimeError("x")

        cfg = {
            "id": "p",
            "type": "parallel",
            "states": {
                "ok": {
                    "initial": "run",
                    "states": {
                        "run": {
                            "invoke": {
                                "src": "good",
                                "id": "good",
                                "onDone": "fin",
                            }
                        },
                        "fin": {"type": "final"},
                    },
                },
                "ko": {
                    "initial": "run",
                    "states": {
                        "run": {
                            "invoke": {
                                "src": "bad",
                                "id": "bad",
                                "onError": "fin",
                            }
                        },
                        "fin": {"type": "final"},
                    },
                },
            },
        }
        instant = {
            "id": "now",
            "initial": "f",
            "states": {"f": {"type": "final"}},
        }

        async def main():
            spy = Spy()
            i = Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        services={
                            "good": create_machine(instant),
                            "bad": create_machine(
                                bad, logic=MachineLogic(actions={"boom": boom})
                            ),
                        }
                    ),
                )
            ).use(spy)
            await i.start()
            await asyncio.sleep(0.05)
            await i.stop()
            return sorted(spy.calls)

        calls = asyncio.run(main())
        self.assertIn(("start", "good"), calls)
        self.assertIn(("done", "good"), calls)
        self.assertIn(("start", "bad"), calls)
        self.assertTrue(any(c[:2] == ("error", "bad") for c in calls), calls)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
