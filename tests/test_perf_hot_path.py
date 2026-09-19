"""Pins for the 0.8.1 hot-path performance work.

Every optimisation here changes *how* the engine computes something it
already computed; none may change *what* it observes. These tests pin the
invariants each shortcut relies on, so a later refactor that breaks one
fails loudly instead of silently returning stale geometry or a wrong
`Receipt.changed`.

    1. `create_machine` builds the tree ONCE (auto-discovery reuses it).
    2. `_accepts_kwarg` is memoised per underlying function.
    3. Transition geometry memo is keyed on the resolved target's identity.
    4. `MachineNode.context_is_immutable` is exactly "no action anywhere".
    5. `Receipt.changed` is unchanged by the deepcopy shortcut.
    6. The async inbox still yields to the event loop under a backlog.
    7. `Clock.pump()` fast path fires due timers exactly as before.
"""

from __future__ import annotations

import asyncio
import logging
import unittest
from typing import Any, Dict
from unittest import mock

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    RealClock,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine import base_interpreter as bi
from src.xstate_statemachine import models


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


TOGGLE: Dict[str, Any] = {
    "id": "t",
    "initial": "A",
    "states": {"A": {"on": {"NEXT": "B"}}, "B": {"on": {"NEXT": "A"}}},
}


# =============================================================================
# 1. Single build in create_machine
# =============================================================================
class TestSingleBuild(_Quiet):
    def test_auto_discovery_builds_the_tree_once(self) -> None:
        class P:
            def bump(self, i, c, e, a) -> None:
                c["n"] += 1

        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {"a": {"entry": "bump"}},
        }
        with mock.patch.object(
            models.MachineNode,
            "__init__",
            autospec=True,
            side_effect=models.MachineNode.__init__,
        ) as ctor:
            m = create_machine(cfg, logic_providers=[P()])
        self.assertEqual(1, ctor.call_count)
        # Discovery still bound the implementation and it runs.
        self.assertIn("bump", m.logic.actions)
        self.assertEqual(1, SyncInterpreter(m).start().context["n"])

    def test_front_door_validation_messages_survive(self) -> None:
        from src.xstate_statemachine import InvalidConfigError

        with self.assertRaisesRegex(InvalidConfigError, "must be a dict"):
            create_machine([])  # type: ignore[arg-type]
        with self.assertRaisesRegex(InvalidConfigError, "root 'id'"):
            create_machine({"states": {"a": {}}})


# =============================================================================
# 2. _accepts_kwarg memo
# =============================================================================
class TestAcceptsKwargMemo(_Quiet):
    def test_signature_inspected_once_per_function(self) -> None:
        bi._ACCEPTS_KWARG_CACHE.clear()
        clock = RealClock()
        with mock.patch.object(
            bi.inspect, "signature", wraps=bi.inspect.signature
        ) as sig:
            for _ in range(5):
                SyncInterpreter(create_machine(TOGGLE), clock=clock)
        self.assertEqual(1, sig.call_count)

    def test_memo_distinguishes_functions_with_same_name(self) -> None:
        def with_sync(fn, delay, *, sync=None):  # noqa: ARG001
            return None

        def without_sync(fn, delay, **kw):  # noqa: ARG001
            return None

        self.assertTrue(bi._accepts_kwarg(with_sync, "sync"))
        self.assertFalse(bi._accepts_kwarg(without_sync, "sync"))
        # Second look-ups come from the memo and agree.
        self.assertTrue(bi._accepts_kwarg(with_sync, "sync"))
        self.assertFalse(bi._accepts_kwarg(without_sync, "sync"))


# =============================================================================
# 3. Geometry memo
# =============================================================================
class TestGeometryMemo(_Quiet):
    def test_memo_is_populated_and_returns_fresh_lists(self) -> None:
        i = SyncInterpreter(create_machine(TOGGLE)).start()
        t = i.machine.states["A"].on["NEXT"][0]
        self.assertIsNone(t._geometry)
        i.send("NEXT")
        self.assertIsNotNone(t._geometry)
        d1, p1 = i._transition_geometry(t, t.resolved_target)
        d2, p2 = i._transition_geometry(t, t.resolved_target)
        self.assertIsNot(p1, p2)  # callers may mutate their copy
        self.assertEqual(p1, p2)
        self.assertIs(d1, d2)

    def test_memo_is_not_served_for_a_different_target(self) -> None:
        """A live-resolved target (strict_targets=False) may change."""
        i = SyncInterpreter(create_machine(TOGGLE)).start()
        t = i.machine.states["A"].on["NEXT"][0]
        b = i.machine.states["B"]
        a = i.machine.states["A"]
        _, path_b = i._transition_geometry(t, b)
        _, path_a = i._transition_geometry(t, a)
        self.assertEqual([b], path_b)
        self.assertEqual([a], path_a)

    def test_nested_and_parallel_traces_unchanged(self) -> None:
        """Same event script, geometry memo warm vs cold: identical trace."""
        cfg = {
            "id": "p",
            "type": "parallel",
            "states": {
                "X": {
                    "initial": "a",
                    "states": {
                        "a": {"on": {"TX": "b"}},
                        "b": {
                            "initial": "b1",
                            "states": {"b1": {"on": {"TX": "#p.X.a"}}},
                        },
                    },
                },
                "Y": {
                    "initial": "a",
                    "states": {
                        "a": {"on": {"TY": "b"}},
                        "b": {"on": {"TY": "a"}},
                    },
                },
            },
        }
        script = ["TX", "TY", "TX", "TX", "TY", "TX"]

        def run() -> list:
            i = SyncInterpreter(create_machine(cfg)).start()
            out = []
            for ev in script:
                i.send(ev)
                out.append(sorted(i.current_state_ids))
            return out

        self.assertEqual(run(), run())
        expected_last = ["p.X.a", "p.Y.a"]  # verified against pre-memo main
        self.assertEqual(expected_last, run()[-1])


# =============================================================================
# 4 / 5. context_is_immutable and Receipt.changed
# =============================================================================
class TestContextImmutableFlag(_Quiet):
    def _flag(self, cfg: Dict[str, Any], **logic: Any) -> bool:
        return create_machine(
            cfg, logic=MachineLogic(**logic)
        ).context_is_immutable

    def test_no_actions_anywhere_is_immutable(self) -> None:
        self.assertTrue(self._flag(TOGGLE))

    def test_every_action_site_flips_it(self) -> None:
        noop = {"n": lambda i, c, e, a: None}
        sites = [
            {"id": "m", "initial": "a", "states": {"a": {"entry": "n"}}},
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"exit": "n", "on": {"T": "b"}}, "b": {}},
            },
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"T": {"target": "a", "actions": "n"}}}
                },
            },
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"after": {"10": {"target": "a", "actions": "n"}}}
                },
            },
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"always": {"target": "b", "actions": "n"}},
                    "b": {},
                },
            },
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "initial": "x",
                        "states": {"x": {"type": "final"}},
                        "onDone": {"target": "b", "actions": "n"},
                    },
                    "b": {},
                },
            },
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "T": {
                                "target": "a",
                                "actions": {
                                    "type": "assign",
                                    "params": {"k": 1},
                                },
                            }
                        }
                    }
                },
            },
        ]
        for cfg in sites:
            with self.subTest(cfg=cfg):
                self.assertFalse(self._flag(cfg, actions=noop))

    def test_invoke_ondone_actions_flip_it(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {
                        "src": "s",
                        "onDone": {"target": "a", "actions": "n"},
                    }
                }
            },
        }
        self.assertFalse(
            self._flag(
                cfg,
                actions={"n": lambda *a: None},
                services={"s": lambda *a: 1},
            )
        )


class TestReceiptChangedUnaffected(_Quiet):
    def test_sync_changed_semantics(self) -> None:
        # Immutable-context machine: changed follows the configuration.
        i = SyncInterpreter(create_machine(TOGGLE)).start()
        self.assertTrue(i.send("NEXT", wait=True).changed)
        self.assertFalse(i.send("NOPE", wait=True).changed)
        # Context-mutating self-transition with no config change: changed.
        cfg = {
            "id": "c",
            "initial": "a",
            "context": {"n": 0},
            "states": {"a": {"on": {"INC": {"actions": "inc"}}}},
        }
        j = SyncInterpreter(
            create_machine(
                cfg,
                logic=MachineLogic(
                    actions={
                        "inc": lambda i, c, e, a: c.__setitem__(
                            "n", c["n"] + 1
                        )
                    }
                ),
            )
        ).start()
        self.assertTrue(j.send("INC", wait=True).changed)

    def test_async_changed_semantics(self) -> None:
        async def main() -> tuple:
            i = await Interpreter(create_machine(TOGGLE)).start()
            r1 = await i.send("NEXT", wait=True)
            r2 = await i.send("NOPE", wait=True)
            await i.stop()
            return r1.changed, r2.changed

        self.assertEqual((True, False), asyncio.run(main()))


# =============================================================================
# 6. Async inbox fairness under a backlog
# =============================================================================
class TestInboxStillYields(_Quiet):
    def test_a_timer_fires_while_a_backlog_is_drained(self) -> None:
        """`call_later` work must run before a 2,000-event backlog empties."""
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {"a": {"on": {"T": {"actions": "inc"}}}},
        }
        fired_at: list = []

        async def main() -> int:
            i = await Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        actions={
                            "inc": lambda i, c, e, a: c.__setitem__(
                                "n", c["n"] + 1
                            )
                        }
                    ),
                )
            ).start()
            loop = asyncio.get_running_loop()
            loop.call_soon(lambda: fired_at.append(i.context["n"]))
            for _ in range(2000):
                await i.send("T")
            await i.send("T", wait=True)
            n = i.context["n"]
            await i.stop()
            return n

        n = asyncio.run(main())
        self.assertEqual(2001, n)
        self.assertEqual(1, len(fired_at))
        # The callback ran mid-backlog, not after everything was processed.
        self.assertLess(fired_at[0], 2001)
        self.assertLessEqual(fired_at[0], Interpreter._INBOX_YIELD_EVERY + 1)


# =============================================================================
# 7. Clock pump fast path
# =============================================================================
class TestPumpFastPath(_Quiet):
    def test_empty_heap_returns_zero_without_touching_now(self) -> None:
        clock = RealClock()
        with mock.patch.object(clock, "now", side_effect=AssertionError):
            self.assertEqual(0, clock.pump())

    def test_due_timers_still_fire(self) -> None:
        clock = SimulatedClock()
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"after": {"10": "b"}}, "b": {}},
        }
        i = SyncInterpreter(create_machine(cfg), clock=clock).start()
        clock.increment(10)
        self.assertEqual({"m.b"}, i.current_state_ids)


# =============================================================================
# 8. __slots__ on the interpreters
# =============================================================================
class TestInterpreterSlots(_Quiet):
    """Every attribute an interpreter sets must be declared in a `__slots__`
    somewhere on its MRO, or it silently falls into the kept `__dict__` and
    the locality win is lost for that attribute. `__dict__` itself is kept
    so subclasses and ad-hoc attributes keep working."""

    CFG = {
        "id": "t",
        "initial": "A",
        "context": {"n": 0},
        "states": {
            "A": {"on": {"NEXT": "B"}, "after": {"1000": "B"}},
            "B": {"on": {"NEXT": "A"}},
        },
    }

    @staticmethod
    def _declared(cls) -> set:
        return {n for c in cls.__mro__ for n in getattr(c, "__slots__", ())}

    def test_sync_sets_only_declared_attributes(self) -> None:
        i = SyncInterpreter(create_machine(self.CFG)).start()
        i.send("NEXT")
        i.stop()
        self.assertEqual({}, vars(i), "attributes fell through to __dict__")
        self.assertTrue(
            self._declared(SyncInterpreter) >= {"status", "_held_replays"}
        )

    def test_async_sets_only_declared_attributes(self) -> None:
        async def main():
            i = await Interpreter(create_machine(self.CFG)).start()
            await i.send("NEXT", wait=True)
            await i.stop()
            return dict(vars(i))

        self.assertEqual({}, asyncio.run(main()))

    def test_subclasses_and_adhoc_attributes_still_work(self) -> None:
        class Spy(SyncInterpreter):
            def __init__(self, m):
                super().__init__(m)
                self.seen = []

        s = Spy(create_machine(self.CFG)).start()
        s.seen.append(1)
        s.anything = "ok"  # type: ignore[attr-defined]
        self.assertEqual("ok", s.anything)  # type: ignore[attr-defined]


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
