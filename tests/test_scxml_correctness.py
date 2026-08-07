# /tests/test_scxml_correctness.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: SCXML Algorithm Correctness (Regression)
# -----------------------------------------------------------------------------
# This module is the regression harness for a family of defects in the core
# transition algorithm that were shipped prior to v0.5.1. Each test class maps
# to exactly one defect and encodes the *observable* symptom, so a regression
# reintroduces a failing test rather than a silent behavioural drift.
#
# 🏛️ Architecture decision: these tests deliberately exercise BOTH the
# `Interpreter` (async) and the `SyncInterpreter` (sync). The two classes
# re-implement `_process_event` / `_enter_states` / `_exit_states`
# independently, so a fix applied to only one is a latent bug in the other.
# Every defect below is therefore asserted twice — once per execution mode.
#
# Defects covered:
#   1. Compound re-entry wiped the active configuration (dead machine).
#   2. Transition selection used `len(state.id)` as a depth proxy.
#   3. Parallel regions took only one transition per event.
#   4. Guard exceptions propagated instead of evaluating to `False`.
#   5. Action exceptions aborted the run loop and silently killed the machine.
# -----------------------------------------------------------------------------
"""
Regression tests pinning the SCXML transition algorithm's correctness.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import unittest
from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    Event,
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Test Helpers
# -----------------------------------------------------------------------------
def build(config: Dict[str, Any], **logic_kwargs: Any) -> Any:
    """Builds a machine from a raw config plus inline logic.

    Args:
        config (Dict[str, Any]): The XState-style machine configuration.
        **logic_kwargs (Any): Forwarded to `MachineLogic` (actions/guards/
            services).

    Returns:
        Any: A fully constructed `MachineNode` ready for interpretation.
    """
    return create_machine(config, logic=MachineLogic(**logic_kwargs))


async def send_and_settle(interpreter: Interpreter, event: str) -> None:
    """Sends an event and waits for the async run loop to drain it.

    `Interpreter.send` is fire-and-forget: it enqueues the event and returns
    before the run loop has processed it. Assertions made immediately after
    `send` would therefore race the interpreter. This helper joins the
    internal queue so tests observe a settled configuration.

    Args:
        interpreter (Interpreter): The running async interpreter.
        event (str): The event type to dispatch.
    """
    await interpreter.send(event)
    # 🕰️ Yield repeatedly so the run loop can drain the queue and any
    #    transient ("always") transitions can stabilise.
    for _ in range(10):
        await asyncio.sleep(0)
    if (
        interpreter._event_queue.empty()
    ):  # noqa: SLF001 — test-only introspection
        return
    await asyncio.wait_for(
        interpreter._event_queue.join(), timeout=2.0
    )  # noqa: SLF001


# -----------------------------------------------------------------------------
# 🔁 Defect 1 — Compound Re-entry Wiped The Active Configuration
# -----------------------------------------------------------------------------
class TestCompoundReentryKeepsLeafState(unittest.IsolatedAsyncioTestCase):
    """Pins that entering a compound state always lands on an atomic leaf.

    🐛 Regression: `_process_event` finalised the active set with
    `difference_update(states_to_exit)` *after* `_enter_states` had already
    inserted the recursively-entered initial children. Because those children
    were themselves members of `states_to_exit`, the finalisation step removed
    the states that had just been entered. The machine was left holding only
    non-atomic ancestors, so `current_state_ids` returned an empty set and no
    further leaf-level event could ever match.
    """

    # 📐 A compound state that re-enters itself via `reenter: True`.
    REENTER_CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "initial": "c1",
                "on": {"RE": {"target": "p", "reenter": True}},
                "states": {"c1": {}, "c2": {}},
            }
        },
    }

    # 📐 A child transitioning up to its own compound parent.
    UP_CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "initial": "c1",
                "states": {"c1": {"on": {"UP": "#m.p"}}, "c2": {}},
            }
        },
    }

    def test_reenter_self_transition_sync(self) -> None:
        """A `reenter` self-transition must return to the initial child."""
        # Arrange
        interpreter = SyncInterpreter(build(self.REENTER_CONFIG)).start()
        self.assertEqual({"m.p.c1"}, interpreter.current_state_ids)

        # Act
        interpreter.send("RE")

        # Assert
        self.assertEqual({"m.p.c1"}, interpreter.current_state_ids)

    async def test_reenter_self_transition_async(self) -> None:
        """The async engine must match the sync engine on re-entry."""
        # Arrange
        interpreter = await Interpreter(build(self.REENTER_CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await send_and_settle(interpreter, "RE")

        # Assert
        self.assertEqual({"m.p.c1"}, interpreter.current_state_ids)

    def test_transition_to_own_compound_parent_sync(self) -> None:
        """Targeting an ancestor must re-enter down to its initial child."""
        # Arrange
        interpreter = SyncInterpreter(build(self.UP_CONFIG)).start()

        # Act
        interpreter.send("UP")

        # Assert
        self.assertEqual({"m.p.c1"}, interpreter.current_state_ids)

    async def test_transition_to_own_compound_parent_async(self) -> None:
        """The async engine must match the sync engine on ancestor targets."""
        # Arrange
        interpreter = await Interpreter(build(self.UP_CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await send_and_settle(interpreter, "UP")

        # Assert
        self.assertEqual({"m.p.c1"}, interpreter.current_state_ids)

    def test_machine_remains_responsive_after_reentry(self) -> None:
        """The machine must still accept leaf-level events after re-entry.

        The original defect's most damaging consequence was not the empty
        snapshot but the permanent deadlock that followed it.
        """
        # Arrange
        config = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "c1",
                    "on": {"RE": {"target": "p", "reenter": True}},
                    "states": {"c1": {"on": {"NEXT": "c2"}}, "c2": {}},
                }
            },
        }
        interpreter = SyncInterpreter(build(config)).start()

        # Act
        interpreter.send("RE")
        interpreter.send("NEXT")

        # Assert
        self.assertEqual({"m.p.c2"}, interpreter.current_state_ids)

    def test_entry_actions_run_once_per_reentry(self) -> None:
        """Re-entry must run entry actions exactly once, not twice.

        Guards against an over-correction where the active-set bookkeeping is
        fixed by entering states twice.
        """
        # Arrange
        calls: List[str] = []

        def track(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            calls.append("entry")

        config = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "c1",
                    "on": {"RE": {"target": "p", "reenter": True}},
                    "states": {"c1": {"entry": ["track"]}, "c2": {}},
                }
            },
        }
        interpreter = SyncInterpreter(
            build(config, actions={"track": track})
        ).start()
        self.assertEqual(1, len(calls))

        # Act
        interpreter.send("RE")

        # Assert
        self.assertEqual(2, len(calls))


# -----------------------------------------------------------------------------
# 📏 Defect 2 — `len(state.id)` Used As A Depth Proxy
# -----------------------------------------------------------------------------
class TestTransitionSelectionUsesTrueDepth(unittest.IsolatedAsyncioTestCase):
    """Pins that the deepest state wins, regardless of its name length.

    🐛 Regression: transition selection sorted by `len(state.id)`. A shallow
    state with a verbose name outranked a genuinely deeper state with a terse
    one, so the wrong transition was taken. SCXML requires selection by tree
    depth (segment count), which name length only accidentally approximates.
    """

    # 📐 Region "aVeryLongRegionNameHere" is at depth 2 but has a 27-char id;
    #    region "b" nests to depth 3 but its id is only 7 chars long.
    CONFIG: Dict[str, Any] = {
        "id": "m",
        "type": "parallel",
        "states": {
            "aVeryLongRegionNameHere": {
                "initial": "s",
                "states": {"s": {"on": {"E": "t"}}, "t": {}},
            },
            "b": {
                "initial": "x",
                "states": {
                    "x": {
                        "initial": "y",
                        "states": {"y": {"on": {"E": "#m.b.z"}}},
                    },
                    "z": {},
                },
            },
        },
    }

    def test_deeper_state_wins_despite_shorter_id_sync(self) -> None:
        """The depth-3 state's transition must beat the depth-2 state's."""
        # Arrange
        interpreter = SyncInterpreter(build(self.CONFIG)).start()

        # Act
        interpreter.send("E")

        # Assert — the deeper region 'b' must have transitioned.
        self.assertIn("m.b.z", interpreter.current_state_ids)

    async def test_deeper_state_wins_despite_shorter_id_async(self) -> None:
        """The async engine must select by depth identically."""
        # Arrange
        interpreter = await Interpreter(build(self.CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await send_and_settle(interpreter, "E")

        # Assert
        self.assertIn("m.b.z", interpreter.current_state_ids)

    def test_child_overrides_parent_transition(self) -> None:
        """The canonical SCXML specificity rule must still hold."""
        # Arrange
        config = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "c",
                    "on": {"E": "#m.parentTarget"},
                    "states": {"c": {"on": {"E": "#m.childTarget"}}},
                },
                "parentTarget": {},
                "childTarget": {},
            },
        }
        interpreter = SyncInterpreter(build(config)).start()

        # Act
        interpreter.send("E")

        # Assert — the child's transition must win over the parent's.
        self.assertEqual({"m.childTarget"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# ⇉ Defect 3 — Parallel Regions Took Only One Transition Per Event
# -----------------------------------------------------------------------------
class TestParallelRegionsTransitionSimultaneously(
    unittest.IsolatedAsyncioTestCase
):
    """Pins that one event fires at most one transition *per parallel region*.

    🐛 Regression: `_find_optimal_transition` returned a single `max(...)`
    winner across the whole configuration. When two active parallel regions
    both handled the same event, only one of them moved. SCXML requires each
    orthogonal region to take its own transition independently.
    """

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "type": "parallel",
        "states": {
            "r1": {
                "initial": "s",
                "states": {"s": {"on": {"E": "t"}}, "t": {}},
            },
            "r2": {
                "initial": "s",
                "states": {"s": {"on": {"E": "t"}}, "t": {}},
            },
        },
    }

    def test_both_regions_transition_sync(self) -> None:
        """Both orthogonal regions must advance on a single event."""
        # Arrange
        interpreter = SyncInterpreter(build(self.CONFIG)).start()
        self.assertEqual({"m.r1.s", "m.r2.s"}, interpreter.current_state_ids)

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.r1.t", "m.r2.t"}, interpreter.current_state_ids)

    async def test_both_regions_transition_async(self) -> None:
        """The async engine must advance both regions too."""
        # Arrange
        interpreter = await Interpreter(build(self.CONFIG)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await send_and_settle(interpreter, "E")

        # Assert
        self.assertEqual({"m.r1.t", "m.r2.t"}, interpreter.current_state_ids)

    def test_only_matching_region_transitions(self) -> None:
        """A region that does not handle the event must stay put."""
        # Arrange
        config = {
            "id": "m",
            "type": "parallel",
            "states": {
                "r1": {
                    "initial": "s",
                    "states": {"s": {"on": {"E": "t"}}, "t": {}},
                },
                "r2": {
                    "initial": "s",
                    "states": {"s": {"on": {"OTHER": "t"}}, "t": {}},
                },
            },
        }
        interpreter = SyncInterpreter(build(config)).start()

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.r1.t", "m.r2.s"}, interpreter.current_state_ids)

    def test_each_region_runs_its_own_actions(self) -> None:
        """Every region's transition actions must fire, not just the winner's."""
        # Arrange
        fired: List[str] = []

        def a1(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            fired.append("r1")

        def a2(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            fired.append("r2")

        config = {
            "id": "m",
            "type": "parallel",
            "states": {
                "r1": {
                    "initial": "s",
                    "states": {
                        "s": {"on": {"E": {"target": "t", "actions": "a1"}}},
                        "t": {},
                    },
                },
                "r2": {
                    "initial": "s",
                    "states": {
                        "s": {"on": {"E": {"target": "t", "actions": "a2"}}},
                        "t": {},
                    },
                },
            },
        }
        interpreter = SyncInterpreter(
            build(config, actions={"a1": a1, "a2": a2})
        ).start()

        # Act
        interpreter.send("E")

        # Assert
        self.assertCountEqual(["r1", "r2"], fired)

    def test_single_transition_when_ancestor_handles_event(self) -> None:
        """An event handled above the regions must fire exactly once.

        Guards against an over-correction that would fire an ancestor's
        transition once per active region.
        """
        # Arrange
        fired: List[str] = []

        def once(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            fired.append("x")

        config = {
            "id": "m",
            "initial": "par",
            "states": {
                "par": {
                    "type": "parallel",
                    "on": {"E": {"target": "#m.done", "actions": "once"}},
                    "states": {
                        "r1": {"initial": "s", "states": {"s": {}}},
                        "r2": {"initial": "s", "states": {"s": {}}},
                    },
                },
                "done": {},
            },
        }
        interpreter = SyncInterpreter(
            build(config, actions={"once": once})
        ).start()

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual(1, len(fired))
        self.assertEqual({"m.done"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🛡️ Defect 4 — Guard Exceptions Propagated
# -----------------------------------------------------------------------------
class TestGuardExceptionsTreatedAsFalse(unittest.IsolatedAsyncioTestCase):
    """Pins the documented contract: a raising guard evaluates to `False`.

    🐛 Regression: `_is_guard_satisfied` invoked the guard with no exception
    handling, so a buggy predicate escaped through `send()` and, in async mode,
    tore down the run loop. AGENTS.md documents guards as "if guard raises
    exception, it's treated as `False`".
    """

    @staticmethod
    def _boom(_ctx: Dict[str, Any], _event: Event) -> bool:
        """A deliberately faulty guard used to simulate user error."""
        raise ValueError("boom")

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {"on": {"E": {"target": "b", "guard": "g"}}},
            "b": {},
        },
    }

    def test_raising_guard_blocks_transition_sync(self) -> None:
        """A raising guard must block the transition, not crash `send`."""
        # Arrange
        interpreter = SyncInterpreter(
            build(self.CONFIG, guards={"g": self._boom})
        ).start()

        # Act
        interpreter.send("E")

        # Assert — transition blocked, machine still alive.
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    async def test_raising_guard_blocks_transition_async(self) -> None:
        """The async engine must survive a raising guard identically."""
        # Arrange
        interpreter = await Interpreter(
            build(self.CONFIG, guards={"g": self._boom})
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await send_and_settle(interpreter, "E")

        # Assert
        self.assertEqual({"m.a"}, interpreter.current_state_ids)
        self.assertEqual("running", interpreter.status)

    def test_fallback_transition_taken_when_guard_raises(self) -> None:
        """A raising guard must let a later unguarded transition win."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": [
                            {"target": "b", "guard": "g"},
                            {"target": "c"},
                        ]
                    }
                },
                "b": {},
                "c": {},
            },
        }
        interpreter = SyncInterpreter(
            build(config, guards={"g": self._boom})
        ).start()

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.c"}, interpreter.current_state_ids)

    def test_missing_guard_still_raises(self) -> None:
        """An *unimplemented* guard must still fail loudly.

        Swallowing runtime errors must not degrade into swallowing
        configuration errors — those are a developer mistake, not a runtime
        condition.
        """
        # Arrange / Act / Assert
        from src.xstate_statemachine import ImplementationMissingError

        interpreter = SyncInterpreter(build(self.CONFIG, guards={})).start()
        with self.assertRaises(ImplementationMissingError):
            interpreter.send("E")


# -----------------------------------------------------------------------------
# 💥 Defect 5 — Action Exceptions Killed The Machine Silently
# -----------------------------------------------------------------------------
class TestActionExceptionsAreContained(unittest.IsolatedAsyncioTestCase):
    """Pins the documented contract for faulty actions.

    🐛 Regression: an action raising mid-list propagated out of
    `_execute_actions`. In async mode `send()` is fire-and-forget, so the
    exception killed `_run_event_loop` while the caller still observed
    `status == "running"` — a silently dead machine. AGENTS.md documents
    actions as "log errors, skip remaining actions in list, continue
    processing".
    """

    @staticmethod
    def _boom(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
        """A deliberately faulty action used to simulate user error."""
        raise ValueError("boom-action")

    def test_transition_completes_despite_faulty_action_sync(self) -> None:
        """A raising action must not abort the state change."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "actions": "boom"}}},
                "b": {},
            },
        }
        interpreter = SyncInterpreter(
            build(config, actions={"boom": self._boom})
        ).start()

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    async def test_machine_survives_faulty_action_async(self) -> None:
        """The async run loop must survive a raising action."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "actions": "boom"}}},
                "b": {"on": {"NEXT": "c"}},
                "c": {},
            },
        }
        interpreter = await Interpreter(
            build(config, actions={"boom": self._boom})
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await send_and_settle(interpreter, "E")
        await send_and_settle(interpreter, "NEXT")

        # Assert — the loop stayed alive and kept processing.
        self.assertEqual("running", interpreter.status)
        self.assertEqual({"m.c"}, interpreter.current_state_ids)

    def test_remaining_actions_are_skipped(self) -> None:
        """Per the contract, actions after the faulty one are skipped."""
        # Arrange
        fired: List[str] = []

        def before(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            fired.append("before")

        def after(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            fired.append("after")

        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "actions": ["before", "boom", "after"],
                        }
                    }
                },
                "b": {},
            },
        }
        interpreter = SyncInterpreter(
            build(
                config,
                actions={
                    "before": before,
                    "boom": self._boom,
                    "after": after,
                },
            )
        ).start()

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual(["before"], fired)
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_faulty_entry_action_does_not_block_start(self) -> None:
        """A raising entry action must not prevent the machine from starting."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"entry": ["boom"]}},
        }

        # Act
        interpreter = SyncInterpreter(
            build(config, actions={"boom": self._boom})
        ).start()

        # Assert
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_missing_action_still_raises(self) -> None:
        """An *unimplemented* action must still fail loudly."""
        # Arrange
        from src.xstate_statemachine import ImplementationMissingError

        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "actions": "ghost"}}},
                "b": {},
            },
        }
        interpreter = SyncInterpreter(build(config, actions={})).start()

        # Act / Assert
        with self.assertRaises(ImplementationMissingError):
            interpreter.send("E")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
