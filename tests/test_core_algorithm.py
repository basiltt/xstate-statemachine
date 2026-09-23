# tests/test_core_algorithm.py
# -----------------------------------------------------------------------------
# 🏛️ #60 (LC-57): ONE algorithm, two execution strategies
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the SyncInterpreter used to re-implement the
# core steps -- transition execution, entry/exit, event processing -- as
# plain-def forks of the base's `async def`s (some under different names,
# so no override check could catch drift). Every wave of this effort found
# a bug that existed on one engine only. The base algorithm awaits NOTHING
# but its own methods; the sync engine now inherits it unchanged and drives
# each coroutine to completion with `_drive()`, which raises if any leaf
# ever truly suspends. The only sync-specific code left is the LEAVES
# (`_execute_actions`, `_cancel_state_tasks`, `send`, spawning, timers),
# each returning an already-finished awaitable. The filer's repro asserts
# this structurally; so does this suite.
# -----------------------------------------------------------------------------
"""Engine unification: no core step exists twice (#60)."""

import asyncio
import functools
import inspect
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    NotSupportedError,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.base_interpreter import BaseInterpreter


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


CORE_STEPS = (
    "_process_event",
    "_execute_transition",
    "_execute_internal_transition",
    "_execute_lifecycle_actions",
    "_enter_states",
    "_exit_states",
    "_check_and_fire_on_done",
)


class TestOneAlgorithm(_Quiet):
    def test_both_engines_share_one_algorithm_implementation(self) -> None:
        """Neither engine defines its own copy of a core step."""
        for name in CORE_STEPS:
            with self.subTest(step=name):
                base = getattr(BaseInterpreter, name)
                self.assertIs(getattr(SyncInterpreter, name), base, name)
                self.assertIs(getattr(Interpreter, name), base, name)

    def test_no_base_coroutine_is_shadowed_by_a_plain_def(self) -> None:
        for name, member in vars(BaseInterpreter).items():
            if not inspect.iscoroutinefunction(member):
                continue
            override = vars(SyncInterpreter).get(name)
            if override is None:
                continue
            with self.subTest(step=name):
                # A sync override of a base coroutine must itself return an
                # awaitable (a leaf), never be a plain fork of the algorithm.
                self.assertNotIn(
                    name, CORE_STEPS, f"{name} forked in SyncInterpreter"
                )

    def test_renamed_forks_are_gone(self) -> None:
        for renamed in (
            "_execute_transition_sync",
            "_process_single_transition",
        ):
            self.assertFalse(
                hasattr(SyncInterpreter, renamed), f"{renamed} still exists"
            )


class TestSyncStrategyRejectsAsyncLogic(_Quiet):
    """LC-58: the sync engine must refuse EVERY async-callable shape."""

    CFG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {"on": {"GO": {"target": "b", "actions": ["act"]}}},
            "b": {},
        },
    }

    def _expect_not_supported(self, action: Any) -> None:
        i = SyncInterpreter(
            create_machine(
                self.CFG, logic=MachineLogic(actions={"act": action})
            )
        ).start()
        with self.assertRaises(NotSupportedError):
            i.send("GO")
        i.stop()

    def test_partial_wrapped_async_action_raises_not_supported(self) -> None:
        async def act(i, c, e, a):
            pass

        self._expect_not_supported(functools.partial(act))

    def test_async_call_object_raises_not_supported(self) -> None:
        class Act:
            async def __call__(self, i, c, e, a):
                pass

        self._expect_not_supported(Act())

    def test_async_generator_action_raises_not_supported(self) -> None:
        async def act(i, c, e, a):
            yield 1

        self._expect_not_supported(act)

    def test_plain_sync_action_still_runs(self) -> None:
        hits = []
        i = SyncInterpreter(
            create_machine(
                self.CFG,
                logic=MachineLogic(actions={"act": lambda *a: hits.append(1)}),
            )
        ).start()
        i.send("GO")
        self.assertEqual(hits, [1])
        self.assertEqual(i.current_state_ids, {"m.b"})


class TestDriveNeverSuspends(_Quiet):
    def test_sync_engine_raises_if_a_leaf_truly_suspends(self) -> None:
        """`_drive` is the safety net: a leaf that awaits real I/O is a bug."""

        class Bad(SyncInterpreter):
            def _execute_actions(self, actions, event):  # type: ignore[override]
                async def suspends():
                    await asyncio.sleep(0)
                    return []

                return suspends()

        # The entry action is what routes `start()` through the leaf: an
        # empty action list never creates the coroutine (perf, 0.9.0).
        i = Bad(
            create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {"entry": "noop", "on": {"G": "b"}},
                        "b": {},
                    },
                },
                logic=MachineLogic(actions={"noop": lambda i, c, e, a: None}),
            )
        )
        with self.assertRaises(RuntimeError) as cm:
            i.start()
        self.assertIn("suspend", str(cm.exception).lower())


class TestParityOnSharedAlgorithm(_Quiet):
    """The same machine, both engines, byte-identical observable trace."""

    CFG: Dict[str, Any] = {
        "id": "p",
        "initial": "a",
        "context": {"trace": []},
        "states": {
            "a": {
                "entry": ["ea"],
                "exit": ["xa"],
                "on": {"GO": {"target": "b", "actions": ["t"]}},
            },
            "b": {
                "entry": ["eb"],
                "initial": "b1",
                "states": {
                    "b1": {
                        "entry": ["eb1"],
                        "always": {"target": "b2", "actions": ["al"]},
                    },
                    "b2": {"entry": ["eb2"], "type": "final"},
                },
                "onDone": {"target": "c", "actions": ["od"]},
            },
            "c": {"entry": ["ec"], "type": "final"},
        },
    }

    def _logic(self) -> MachineLogic:
        names = ("ea", "xa", "t", "eb", "eb1", "al", "eb2", "od", "ec")
        return MachineLogic(
            actions={
                n: (lambda i, c, e, a, n=n: c["trace"].append(n))
                for n in names
            }
        )

    def test_trace_identical_on_both_engines(self) -> None:
        s = SyncInterpreter(
            create_machine(self.CFG, logic=self._logic())
        ).start()
        s.send("GO")
        sync_trace = list(s.context["trace"])

        async def main():
            i = await Interpreter(
                create_machine(self.CFG, logic=self._logic())
            ).start()
            await i.send("GO")
            for _ in range(200):
                if i.status == "done":
                    break
                await asyncio.sleep(0.002)
            out = list(i.context["trace"])
            await i.stop()
            return out

        self.assertEqual(sync_trace, asyncio.run(main()))
        self.assertEqual(
            sync_trace, ["ea", "xa", "t", "eb", "eb1", "al", "eb2", "od", "ec"]
        )


# -----------------------------------------------------------------------------
# #77 -- the sync macrostep budget bounds the RAISE CHAIN, not throughput
# -----------------------------------------------------------------------------
class TestSyncMacrostepBudget(_Quiet):
    """External batches of any size are processed in full; only a
    self-feeding `raise` chain trips `maxIterations`, and tripping it
    never discards events the caller was told were accepted."""

    @staticmethod
    def _counter(extra_actions=None, **cfg_extra) -> Dict[str, Any]:
        return {
            "id": "bud",
            "initial": "a",
            "context": {"seen": 0},
            **cfg_extra,
            "states": {
                "a": {
                    "on": {
                        "T": {
                            "target": "a",
                            "reenter": True,
                            "actions": ["bump", *(extra_actions or [])],
                        }
                    }
                }
            },
        }

    @staticmethod
    def _logic(trace=None) -> MachineLogic:
        def bump(i, c, e, a):
            c["seen"] += 1
            if trace is not None:
                trace.append(e.type)

        return MachineLogic(actions={"bump": bump})

    def test_sync_large_batch_is_not_truncated(self) -> None:
        i = SyncInterpreter(
            create_machine(self._counter(), logic=self._logic())
        )
        i.start()
        i.send_events(["T"] * 5000)
        self.assertEqual(i.context["seen"], 5000)
        self.assertEqual(i.queue_depth, 0)
        i.stop()

    def test_sync_runaway_raise_chain_is_still_bounded(self) -> None:
        cfg = self._counter(
            [{"type": "raise", "params": {"event": "T"}}], maxIterations=50
        )
        i = SyncInterpreter(create_machine(cfg, logic=self._logic()))
        i.start()
        i.send("T")  # must return, not spin forever
        self.assertLessEqual(i.context["seen"], 60)
        self.assertEqual(i.status, "running")
        i.stop()

    def test_sync_runaway_does_not_discard_external_events(self) -> None:
        """The chain is broken; the inbox behind it is preserved."""
        cfg = {
            "id": "bud",
            "initial": "a",
            "maxIterations": 20,
            "context": {"seen": 0, "ok": 0},
            "states": {
                "a": {
                    "on": {
                        "LOOP": {
                            "actions": [
                                "bump",
                                {"type": "raise", "params": {"event": "LOOP"}},
                            ]
                        },
                        "OK": {"actions": ["ok"]},
                    }
                }
            },
        }

        def bump(i, c, e, a):
            c["seen"] += 1

        def ok(i, c, e, a):
            c["ok"] += 1

        i = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(actions={"bump": bump, "ok": ok})
            )
        )
        i.start()
        i.send_events(["LOOP"] + ["OK"] * 30)
        self.assertLessEqual(i.context["seen"], 25)
        self.assertEqual(i.context["ok"], 30)
        i.stop()

    def test_sync_external_self_send_loop_is_still_bounded(self) -> None:
        """Review finding: a loop via `interp.send()` from an action (an
        EXTERNAL self-send, not a `raise`) must also terminate."""
        cfg = {
            "id": "pp",
            "initial": "a",
            "maxIterations": 40,
            "context": {"n": 0},
            "states": {
                "a": {"on": {"P": {"target": "b", "actions": ["bounce"]}}},
                "b": {"on": {"P": {"target": "a", "actions": ["bounce"]}}},
            },
        }

        def bounce(i, c, e, a):
            c["n"] += 1
            i.send("P")

        i = SyncInterpreter(
            create_machine(cfg, logic=MachineLogic(actions={"bounce": bounce}))
        )
        i.start()
        i.send("P")  # must return
        self.assertLessEqual(i.context["n"], 45)
        self.assertEqual(i.queue_depth, 0)
        i.stop()

    def test_sync_rollback_rearming_invoke_does_not_hang(self) -> None:
        """Review finding: `onDone` action fails -> rollback re-arms the
        invoke -> fresh `done.invoke` -> repeat. The generated-event budget
        must break this cycle; `send()` must return."""
        cfg = {
            "id": "rl",
            "initial": "A",
            "maxIterations": 30,
            "actionErrorPolicy": "rollback",
            "states": {
                "A": {"on": {"GO": "B"}},
                "B": {
                    "invoke": {
                        "src": "svc",
                        "onDone": {"target": "C", "actions": ["boom"]},
                    }
                },
                "C": {},
            },
        }

        def svc(i, c, e):
            return 1

        def boom(i, c, e, a):
            raise RuntimeError("x")

        i = SyncInterpreter(
            create_machine(
                cfg,
                logic=MachineLogic(
                    services={"svc": svc}, actions={"boom": boom}
                ),
            )
        )
        i.start()
        i.send("GO")  # must return
        self.assertEqual(sorted(i.current_state_ids), ["rl.B"])
        i.stop()

    # -- chain accounting (review of #77) ----------------------------------

    @staticmethod
    def _one_deep_raise() -> Dict[str, Any]:
        """Every `T` raises exactly one `R`: independent one-deep chains,
        no loop anywhere. N of them must NEVER trip the runaway guard."""
        return {
            "id": "chain",
            "initial": "a",
            "context": {"t": 0, "r": 0},
            "states": {
                "a": {
                    "on": {
                        "T": {
                            "actions": [
                                "bump_t",
                                {"type": "raise", "params": {"event": "R"}},
                            ]
                        },
                        "R": {"actions": "bump_r"},
                    }
                }
            },
        }

    @staticmethod
    def _tr_logic() -> MachineLogic:
        return MachineLogic(
            actions={
                "bump_t": lambda i, c, e, a: c.__setitem__("t", c["t"] + 1),
                "bump_r": lambda i, c, e, a: c.__setitem__("r", c["r"] + 1),
            }
        )

    def test_sync_independent_raises_in_one_batch_are_not_budgeted(
        self,
    ) -> None:
        """3,000 one-deep raises in a single `send_events()` must all be
        delivered. Before the chain reset only the first 1,000 were, on
        this engine only -- `send()` one at a time processed all 3,000."""
        i = SyncInterpreter(
            create_machine(self._one_deep_raise(), logic=self._tr_logic())
        )
        i.start()
        i.send_events(["T"] * 3000)
        self.assertEqual((i.context["t"], i.context["r"]), (3000, 3000))
        i.stop()

    def test_engine_parity_independent_raises_in_one_batch(self) -> None:
        """Both engines deliver every self-raised event of a batch of
        independent one-deep chains. The 0.8.0 changelog claimed parity
        here; this pins it."""
        s = SyncInterpreter(
            create_machine(self._one_deep_raise(), logic=self._tr_logic())
        )
        s.start()
        s.send_events(["T"] * 3000)
        sync_counts = (s.context["t"], s.context["r"])
        s.stop()

        async def main():
            i = await Interpreter(
                create_machine(self._one_deep_raise(), logic=self._tr_logic())
            ).start()
            await i.send_events(["T"] * 3000)
            for _ in range(4000):
                if i.context["r"] == 3000:
                    break
                await asyncio.sleep(0.002)
            out = (i.context["t"], i.context["r"])
            await i.stop()
            return out

        self.assertEqual(sync_counts, (3000, 3000))
        self.assertEqual(asyncio.run(main()), sync_counts)

    def test_sync_chain_reset_does_not_unbound_a_real_loop(self) -> None:
        """The reset fires only when a step generated NOTHING. A step that
        keeps regenerating never resets, so a genuine loop still trips
        at `maxIterations` and returns promptly."""
        cfg = self._counter(
            extra_actions=[{"type": "raise", "params": {"event": "T"}}],
            maxIterations=200,
        )
        i = SyncInterpreter(create_machine(cfg, logic=self._logic()))
        i.start()
        i.send("T")
        # 1 external + 200 generated before the trip.
        self.assertEqual(i.context["seen"], 201)
        self.assertEqual(i.queue_depth, 0)
        i.stop()

    def test_sync_overflow_discards_generated_tail_larger_than_one(
        self,
    ) -> None:
        """When the guard trips with several self-generated events already
        appended BEHIND the user's remaining events, the whole generated
        tail is discarded and every user event still runs (covers the
        multi-pop branch of the overflow handler)."""
        cfg = {
            "id": "tail",
            "initial": "a",
            "context": {"t": 0, "r": 0, "u": 0},
            "maxIterations": 50,
            "states": {
                "a": {
                    "on": {
                        # Each T / R sends THREE R's to itself via send(),
                        # so the inbox tail grows faster than it drains.
                        "T": {"actions": ["bump_t", "fan_out"]},
                        "R": {"actions": ["bump_r", "fan_out"]},
                        "U": {"actions": "bump_u"},
                    }
                }
            },
        }

        def fan_out(i, c, e, a):
            for _ in range(3):
                i.send("R")

        logic = MachineLogic(
            actions={
                "bump_t": lambda i, c, e, a: c.__setitem__("t", c["t"] + 1),
                "bump_r": lambda i, c, e, a: c.__setitem__("r", c["r"] + 1),
                "bump_u": lambda i, c, e, a: c.__setitem__("u", c["u"] + 1),
                "fan_out": fan_out,
            }
        )
        i = SyncInterpreter(create_machine(cfg, logic=logic))
        i.start()
        i.send_events(["T"] + ["U"] * 25)
        # Every user event ran; generated work was capped, not unbounded.
        self.assertEqual(i.context["t"], 1)
        self.assertEqual(i.context["u"], 25)
        self.assertEqual(i.context["r"], 50)
        self.assertEqual(i.queue_depth, 0)
        i.stop()

    def test_engine_trace_parity_large_batch(self) -> None:
        sync_trace: list = []
        s = SyncInterpreter(
            create_machine(self._counter(), logic=self._logic(sync_trace))
        )
        s.start()
        s.send_events(["T"] * 2000)
        s.stop()

        async_trace: list = []

        async def main():
            i = await Interpreter(
                create_machine(self._counter(), logic=self._logic(async_trace))
            ).start()
            await i.send_events(["T"] * 2000)
            for _ in range(2000):
                if i.context["seen"] == 2000:
                    break
                await asyncio.sleep(0.002)
            await i.stop()

        asyncio.run(main())
        self.assertEqual(len(sync_trace), 2000)
        self.assertEqual(sync_trace, async_trace)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
