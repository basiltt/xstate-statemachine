# /tests/test_sync_interpreter.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: SyncInterpreter
# -----------------------------------------------------------------------------
# This suite provides comprehensive testing for the `SyncInterpreter`, which
# is the synchronous execution engine for the state machine library. It verifies
# core synchronous functionality including transitions, actions, guards, and
# error handling for unsupported asynchronous features.
#
# The tests cover a wide range of scenarios:
#   - Basic transitions and action execution.
#   - Conditional transitions using guards.
#   - Hierarchical state entry/exit action ordering.
#   - `onDone` transitions for compound and parallel states.
#   - Synchronous service invocations (`invoke`).
#   - Actor model behavior (`spawn`).
#   - State snapshotting and restoration.
#   - Error handling for invalid configurations and unsupported features.
#   - Plugin lifecycle hooks.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import json
import logging
import threading
import time
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    ActionDefinition,
    Event,
    ImplementationMissingError,
    InvalidConfigError,
    MachineLogic,
    NotSupportedError,
    PluginBase,
    StateNotFoundError,
    SyncInterpreter,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestSyncInterpreter
# -----------------------------------------------------------------------------
class TestSyncInterpreter(unittest.TestCase):
    """Test suite for the `SyncInterpreter` class.

    This class contains synchronous test methods to validate all features
    of the `SyncInterpreter`, ensuring it correctly executes state logic
    in a blocking manner across a wide variety of scenarios.
    """

    # -------------------------------------------------------------------------
    # 🛠️ Setup & Teardown Methods
    # -------------------------------------------------------------------------

    def setUp(self) -> None:
        """Set up common machine configurations for reuse in multiple tests.

        This method runs before each test function, providing a fresh instance
        of common data structures to ensure test isolation. Here, it defines a
        nested machine configuration used in hierarchy tests.
        """
        logger.info("🛠️ Setting up common test resources...")
        self.nested_machine_config: Dict[str, Any] = {
            "id": "nester",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "entry": "enterA",
                    "exit": "exitA",
                    "states": {
                        "a1": {
                            "entry": "enterA1",
                            "exit": "exitA1",
                            "on": {"T1": "b", "T2": ".a2"},
                        },
                        "a2": {"entry": "enterA2"},
                    },
                },
                "b": {"entry": "enterB"},
            },
        }

    # -------------------------------------------------------------------------
    # 🧪 Helper Methods for Creating Machines
    # -------------------------------------------------------------------------

    @staticmethod
    def _create_auth_machine_config() -> Dict[str, Any]:
        """Creates the configuration for the authentication machine.

        Returns:
            A dictionary representing the machine's configuration.
        """
        return {
            "id": "auth",
            "initial": "idle",
            "states": {
                "idle": {
                    "on": {"LOGIN": {"target": "success", "guard": "canLogin"}}
                },
                "success": {},
            },
        }

    @staticmethod
    def _create_chooser_machine_config() -> Dict[str, Any]:
        """Creates the configuration for the chooser machine.

        Returns:
            A dictionary representing the machine's configuration.
        """
        return {
            "id": "chooser",
            "initial": "start",
            "context": {"value": 15},
            "states": {
                "start": {
                    "on": {
                        "CHECK": [
                            {"target": "low", "guard": "isLow"},
                            {"target": "med", "guard": "isMed"},
                            {"target": "high"},
                        ]
                    }
                },
                "low": {},
                "med": {},
                "high": {},
            },
        }

    @staticmethod
    def _infinite_child_machine() -> Dict[str, Any]:
        """Creates a configuration for a child machine that never terminates.

        Returns:
            A dictionary representing the machine's configuration.
        """
        return {"id": "infinite", "initial": "loop", "states": {"loop": {}}}

    @staticmethod
    def _alive_child_machine() -> Dict[str, Any]:
        """Creates a config for a child machine that stays alive for >=100ms.

        Returns:
            A dictionary representing the machine's configuration.
        """
        return {
            "id": "alive",
            "initial": "alive",
            "states": {
                "alive": {"after": {100: "done"}},
                "done": {"type": "final"},
            },
        }

    # -------------------------------------------------------------------------
    # ✅ Basic Transition & Action Tests
    # -------------------------------------------------------------------------

    def test_simple_transition(self) -> None:
        """Tests a simple transition from one state to another on an event.

        This test verifies the most fundamental behavior: that the interpreter
        correctly moves from a starting state to a target state when it
        receives the appropriate event.
        """
        logger.info("🧪 Testing a basic state transition on event...")
        # 🤖 Arrange: Create a simple state machine with two states.
        machine_config: Dict[str, Any] = {
            "id": "light",
            "initial": "green",
            "states": {"green": {"on": {"TIMER": "yellow"}}, "yellow": {}},
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"light.green"})

        # ⚡ Act: Send the event that triggers the transition.
        interpreter.send("TIMER")

        # ✨ Assert: Verify the interpreter is in the new state.
        self.assertEqual(interpreter.current_state_ids, {"light.yellow"})
        interpreter.stop()

    def test_context_and_actions(self) -> None:
        """Tests that synchronous actions can modify the machine's context.

        This test ensures that an action, triggered by an event, receives the
        correct context and event payload, and that its modifications to the
        context are persisted in the interpreter.
        """
        logger.info("🧪 Testing action-based context modification...")
        # 🤖 Arrange: Define an action that modifies the context.
        mock_action = MagicMock()

        def increment(
            interpreter: SyncInterpreter,  # noqa
            context: Dict[str, Any],
            event: Event,
            action_definition: ActionDefinition,  # noqa
        ) -> None:
            """Increments a counter in the context."""
            context["count"] += event.payload.get("amount", 1)

        mock_action.side_effect = increment
        machine_config: Dict[str, Any] = {
            "id": "counter",
            "initial": "active",
            "context": {"count": 0},
            "states": {"active": {"on": {"INC": {"actions": ["increment"]}}}},
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(actions={"increment": mock_action}),
        )
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send an event with a payload.
        interpreter.send("INC", amount=5)

        # ✨ Assert: Check that the action was called and context was updated.
        mock_action.assert_called_once()
        self.assertEqual(interpreter.context["count"], 5)
        interpreter.stop()

    def test_multiple_actions_on_transition(self) -> None:
        """Tests that all actions in a list are executed for a transition."""
        logger.info("🧪 Testing execution of multiple actions...")
        # 🤖 Arrange: Define a machine with two mock actions on one transition.
        action1 = MagicMock()
        action2 = MagicMock()
        machine_config: Dict[str, Any] = {
            "id": "multi",
            "initial": "a",
            "states": {
                "a": {"on": {"EVENT": {"actions": ["action1", "action2"]}}}
            },
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(
                actions={"action1": action1, "action2": action2}
            ),
        )
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send the event to trigger the actions.
        interpreter.send("EVENT")

        # ✨ Assert: Verify both actions were called.
        action1.assert_called_once()
        action2.assert_called_once()

    def test_internal_transition_does_not_change_state(self) -> None:
        """Tests an internal transition executes actions without changing state.

        An internal transition is one without a `target`. It should execute
        its actions but not cause any state entry/exit actions to fire.
        """
        logger.info("🧪 Testing internal transitions...")
        # 🤖 Arrange: Create a machine with an internal transition.
        action = MagicMock()
        machine_config: Dict[str, Any] = {
            "id": "internal",
            "initial": "active",
            "states": {"active": {"on": {"EVENT": {"actions": "doIt"}}}},
        }
        machine = create_machine(
            machine_config, logic=MachineLogic(actions={"doIt": action})
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})

        # ⚡ Act: Send the event.
        interpreter.send("EVENT")

        # ✨ Assert: State remains the same, and the action was executed.
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})
        action.assert_called_once()

    def test_event_payload_is_passed_to_actions(self) -> None:
        """Tests that the event payload is correctly passed to actions."""
        logger.info("🧪 Testing event payload passing to actions...")
        # 🤖 Arrange: Create a machine with an action that will receive a payload.
        mock_action = MagicMock()
        machine_config: Dict[str, Any] = {
            "id": "payload_test",
            "initial": "idle",
            "states": {"idle": {"on": {"DATA": {"actions": "process"}}}},
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(actions={"process": mock_action}),
        )
        interpreter = SyncInterpreter(machine).start()
        payload = {"user": "test", "id": 123}

        # ⚡ Act: Send an event with a payload.
        interpreter.send("DATA", **payload)

        # ✨ Assert: The action's received event argument should contain the payload.
        self.assertEqual(mock_action.call_args[0][2].payload, payload)

    def test_reentrant_send_from_action_is_queued(self) -> None:
        """Tests events sent from an action are queued and processed later.

        This ensures that the machine fully completes its current transition
        before processing new events, preventing race conditions and undefined
        behavior.
        """
        logger.info("🧪 Testing reentrant `send` calls are queued...")
        # 🤖 Arrange: Define actions where one sends another event.
        call_order: List[str] = []

        def action_sends_event(
            interp: SyncInterpreter,
            ctx: Dict,  # noqa: F841
            evt: Event,  # noqa: F841
            ad: ActionDefinition,  # noqa: F841
        ) -> None:
            """This action sends a new event during its execution."""
            call_order.append("action_A")
            interp.send("EVENT_B")
            call_order.append("action_A_finished")

        def action_for_b(
            interp: SyncInterpreter,  # noqa: F841
            ctx: Dict,  # noqa: F841
            evt: Event,  # noqa: F841
            ad: ActionDefinition,  # noqa: F841
        ) -> None:
            """This action is triggered by the second event."""
            call_order.append("action_B")

        machine_config: Dict[str, Any] = {
            "id": "reentrant",
            "initial": "a",
            "states": {
                "a": {
                    "on": {"EVENT_A": {"target": "b", "actions": "actionA"}}
                },
                "b": {"on": {"EVENT_B": {"target": "c"}}},
                "c": {"entry": "actionB"},
            },
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(
                actions={
                    "actionA": action_sends_event,
                    "actionB": action_for_b,
                }
            ),
        )
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send the initial event.
        interpreter.send("EVENT_A")

        # ✨ Assert: The first action completes before the second one starts.
        self.assertEqual(
            call_order, ["action_A", "action_A_finished", "action_B"]
        )
        self.assertEqual(interpreter.current_state_ids, {"reentrant.c"})

    def test_context_is_copied_not_referenced(self) -> None:
        """Tests that the interpreter performs a deep copy of initial context.

        This is crucial to prevent mutations within the running interpreter
        from affecting the original machine configuration object.
        """
        logger.info("🧪 Testing that initial context is deep copied...")
        # 🤖 Arrange: Define a machine config with a nested context object.
        config: Dict[str, Any] = {
            "id": "m",
            "initial": "s1",
            "context": {"data": {"nested": "value"}},
            "states": {"s1": {}},
        }
        machine = create_machine(config)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Mutate the context within the interpreter.
        interpreter.context["data"]["nested"] = "changed"

        # ✨ Assert: The original config dictionary remains unchanged.
        self.assertEqual(config["context"]["data"]["nested"], "value")

    def test_self_transition_on_state(self) -> None:
        """Tests an external self-transition re-executes entry/exit actions."""
        logger.info("🧪 Testing external self-transitions re-fire actions...")
        # 🤖 Arrange: Create a machine with a self-transition on state 'a'.
        exit_action = MagicMock()
        entry_action = MagicMock()
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {"LOOP": {"target": "a", "reenter": True}},
                    "entry": "onEnter",
                    "exit": "onExit",
                }
            },
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(
                actions={"onEnter": entry_action, "onExit": exit_action}
            ),
        )
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: Initial entry action is fired once.
        entry_action.assert_called_once()
        exit_action.assert_not_called()

        # ⚡ Act: Send the event that causes the self-transition.
        interpreter.send("LOOP")

        # ✨ Assert: Exit and entry actions were fired again.
        self.assertEqual(entry_action.call_count, 2)
        self.assertEqual(exit_action.call_count, 1)

    # -------------------------------------------------------------------------
    # 🛡️ Guard & Conditional Transition Tests
    # -------------------------------------------------------------------------

    def test_guards_allow_transition(self) -> None:
        """Tests a transition is allowed if its guard condition returns true."""
        logger.info("🧪 Testing that a passing guard allows transition...")
        # 🤖 Arrange: Create a machine with a guarded transition returning true.
        machine_config = self._create_auth_machine_config()
        logic = MachineLogic(guards={"canLogin": lambda ctx, evt: True})
        machine = create_machine(machine_config, logic=logic)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send the triggering event.
        interpreter.send("LOGIN")

        # ✨ Assert: The state transition occurred successfully.
        self.assertEqual(interpreter.current_state_ids, {"auth.success"})

    def test_guards_block_transition(self) -> None:
        """Tests a transition is blocked if its guard condition returns false."""
        logger.info("🧪 Testing that a failing guard blocks transition...")
        # 🤖 Arrange: Create a machine with a guarded transition returning false.
        machine_config = self._create_auth_machine_config()
        logic = MachineLogic(guards={"canLogin": lambda ctx, evt: False})
        machine = create_machine(machine_config, logic=logic)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send the triggering event.
        interpreter.send("LOGIN")

        # ✨ Assert: The state transition did not occur.
        self.assertEqual(interpreter.current_state_ids, {"auth.idle"})

    def test_chooses_first_passing_guarded_transition(self) -> None:
        """Tests that the first transition whose guard passes is selected.

        When multiple transitions are defined for the same event, the interpreter
        should evaluate them in order and take the first one that is not blocked
        by a failing guard.
        """
        logger.info(
            "🧪 Testing selection of the first valid guarded transition..."
        )
        # 🤖 Arrange: A machine where the second of two guards should pass.
        machine_config = self._create_chooser_machine_config()
        machine = create_machine(
            machine_config,
            logic=MachineLogic(
                guards={
                    "isLow": lambda ctx, evt: ctx["value"] < 10,
                    "isMed": lambda ctx, evt: ctx["value"] < 20,
                }
            ),
        )
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send the event.
        interpreter.send("CHECK")

        # ✨ Assert: The interpreter transitioned to the state of the second guard.
        self.assertEqual(interpreter.current_state_ids, {"chooser.med"})

    def test_falls_through_to_unguarded_transition(self) -> None:
        """Tests an unguarded transition is chosen if all guarded ones fail."""
        logger.info("🧪 Testing fallback to an unguarded transition...")
        # 🤖 Arrange: A machine where all guards fail, leaving one option.
        machine_config = self._create_chooser_machine_config()
        machine_config["context"]["value"] = 50  # For this test
        machine = create_machine(
            machine_config,
            logic=MachineLogic(
                guards={
                    "isLow": lambda ctx, evt: ctx["value"] < 10,
                    "isMed": lambda ctx, evt: ctx["value"] < 20,
                }
            ),
        )
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send the event.
        interpreter.send("CHECK")

        # ✨ Assert: The interpreter took the final, unguarded transition.
        self.assertEqual(interpreter.current_state_ids, {"chooser.high"})

    def test_guard_receives_context_and_event_payload_correctly(self) -> None:
        """Tests a guard function receives the correct context and event payload."""
        logger.info("🧪 Testing argument passing to guard functions...")
        # 🤖 Arrange: Create a machine with a mock guard to inspect its args.
        guard = MagicMock(return_value=True)
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "s1",
            "context": {"x": 1},
            "states": {"s1": {"on": {"E": {"guard": "myGuard"}}}},
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(guards={"myGuard": guard}),
        )
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send an event with a payload.
        interpreter.send("E", y=2)

        # ✨ Assert: Verify the guard was called with correct context and event.
        guard.assert_called_once()
        self.assertEqual(guard.call_args[0][0]["x"], 1)
        self.assertEqual(guard.call_args[0][1].payload, {"y": 2})

    def test_eventless_transition_is_taken_immediately(self) -> None:
        """Tests an event-less ("always") transition is taken on state entry."""
        logger.info("🧪 Testing immediate event-less transitions...")
        # 🤖 Arrange: Create a machine with a transient state 'b'.
        machine_config: Dict[str, Any] = {
            "id": "transient",
            "initial": "a",
            "states": {
                "a": {"on": {"NEXT": "b"}},
                "b": {"on": {"": "c"}},
                "c": {},
            },
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Transition to the state that has an event-less transition.
        interpreter.send("NEXT")

        # ✨ Assert: The interpreter should immediately transition again to 'c'.
        self.assertEqual(interpreter.current_state_ids, {"transient.c"})

    def test_guarded_eventless_transitions(self) -> None:
        """Tests that the correct guarded event-less transition is chosen."""
        logger.info("🧪 Testing guarded event-less transitions...")
        # 🤖 Arrange: A machine with two guarded, event-less transitions.
        machine_config: Dict[str, Any] = {
            "id": "transient_guarded",
            "initial": "start",
            "context": {"status": "ok"},
            "states": {
                "start": {"on": {"CHECK": "evaluating"}},
                "evaluating": {
                    "on": {
                        "": [
                            {"target": "success", "guard": "isOk"},
                            {"target": "failure"},
                        ]
                    }
                },
                "success": {},
                "failure": {},
            },
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(
                guards={"isOk": lambda c, e: c["status"] == "ok"}
            ),
        )

        # ⚡ Act (Success Case): Start with context that makes the guard pass.
        interpreter_ok = SyncInterpreter(machine).start()
        interpreter_ok.send("CHECK")

        # ✨ Assert (Success Case): It should transition to the success state.
        self.assertEqual(
            interpreter_ok.current_state_ids, {"transient_guarded.success"}
        )
        interpreter_ok.stop()

        # ⚡ Act (Failure Case): Start with context that makes the guard fail.
        interpreter_err = SyncInterpreter(machine).start()
        interpreter_err.context["status"] = "error"
        interpreter_err.send("CHECK")

        # ✨ Assert (Failure Case): It should fall through to the failure state.
        self.assertEqual(
            interpreter_err.current_state_ids, {"transient_guarded.failure"}
        )

    # -------------------------------------------------------------------------
    # 🏰 State Hierarchy & Lifecycle Tests
    # -------------------------------------------------------------------------

    def test_entry_and_exit_actions_fire_in_order(self) -> None:
        """Tests that exit actions fire before entry actions on transition."""
        logger.info("🧪 Testing exit/entry action ordering...")
        # 🤖 Arrange: Define actions that record their call order.
        call_order: List[str] = []
        logic = MachineLogic(
            actions={
                "exitA": lambda i, c, e, a: call_order.append("exitA"),
                "enterB": lambda i, c, e, a: call_order.append("enterB"),
            }
        )
        machine_config: Dict[str, Any] = {
            "id": "lifecyle",
            "initial": "a",
            "states": {
                "a": {"exit": "exitA", "on": {"NEXT": "b"}},
                "b": {"entry": "enterB"},
            },
        }
        machine = create_machine(machine_config, logic=logic)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Trigger the transition.
        interpreter.send("NEXT")

        # ✨ Assert: The exit action of the old state was called before the new.
        self.assertEqual(call_order, ["exitA", "enterB"])

    def test_nested_entry_exit_actions_fire_correctly(self) -> None:
        """Tests hierarchical entry/exit action ordering.

        Entry actions should fire from parent to child (top-down).
        Exit actions should fire from child to parent (bottom-up).
        """
        logger.info("🧪 Testing hierarchical entry/exit action ordering...")
        # 🤖 Arrange: Use a nested machine and record action calls.
        call_order: List[str] = []
        logic = MachineLogic(
            actions={
                "enterA": lambda i, c, e, a: call_order.append("enterA"),
                "exitA": lambda i, c, e, a: call_order.append("exitA"),
                "enterA1": lambda i, c, e, a: call_order.append("enterA1"),
                "exitA1": lambda i, c, e, a: call_order.append("exitA1"),
                "enterB": lambda i, c, e, a: call_order.append("enterB"),
            }
        )
        machine = create_machine(self.nested_machine_config, logic=logic)

        # ⚡ Act (Initial): Start the interpreter.
        interpreter = SyncInterpreter(machine).start()
        # ✨ Assert (Initial): Entry actions fired top-down.
        self.assertEqual(call_order, ["enterA", "enterA1"])
        call_order.clear()

        # ⚡ Act (Transition): Trigger a transition out of the nested state.
        interpreter.send("T1")
        # ✨ Assert (Transition): Exit actions fired bottom-up, then new entry.
        self.assertEqual(call_order, ["exitA1", "exitA", "enterB"])

    def test_complex_nested_entry_actions(self) -> None:
        """Tests that entry actions fire from the outermost to innermost state."""
        logger.info(
            "🧪 Testing complex nested entry action order (top-down)..."
        )
        # 🤖 Arrange
        call_order: List[str] = []
        logic = MachineLogic(
            actions={
                "enterA": lambda i, c, e, a: call_order.append("A"),
                "enterB": lambda i, c, e, a: call_order.append("B"),
                "enterC": lambda i, c, e, a: call_order.append("C"),
            }
        )
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "entry": "enterA",
                    "initial": "b",
                    "states": {
                        "b": {
                            "entry": "enterB",
                            "initial": "c",
                            "states": {"c": {"entry": "enterC"}},
                        }
                    },
                }
            },
        }
        machine = create_machine(machine_config, logic=logic)

        # ⚡ Act
        SyncInterpreter(machine).start()

        # ✨ Assert
        self.assertEqual(call_order, ["A", "B", "C"])

    def test_complex_nested_exit_actions(self) -> None:
        """Tests that exit actions fire from the innermost to outermost state."""
        logger.info(
            "🧪 Testing complex nested exit action order (bottom-up)..."
        )
        # 🤖 Arrange
        call_order: List[str] = []
        logic = MachineLogic(
            actions={
                "exitA": lambda i, c, e, a: call_order.append("A"),
                "exitB": lambda i, c, e, a: call_order.append("B"),
                "exitC": lambda i, c, e, a: call_order.append("C"),
            }
        )
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "exit": "exitA",
                    "initial": "b",
                    "states": {
                        "b": {
                            "exit": "exitB",
                            "initial": "c",
                            "states": {
                                "c": {
                                    "exit": "exitC",
                                    "on": {"FINISH": "#m.d"},
                                }
                            },
                        }
                    },
                },
                "d": {},
            },
        }
        machine = create_machine(machine_config, logic=logic)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act
        interpreter.send("FINISH")

        # ✨ Assert
        self.assertEqual(call_order, ["C", "B", "A"])

    def test_compound_state_on_done_transition(self) -> None:
        """Tests `onDone` transition from a compound state.

        An `onDone` transition should be taken when a child state reaches
        its final state.
        """
        logger.info("🧪 Testing `onDone` from a compound state...")
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "completer",
            "initial": "working",
            "states": {
                "working": {
                    "initial": "step1",
                    "onDone": "finished",
                    "states": {
                        "step1": {"on": {"NEXT": "step2"}},
                        "step2": {"type": "final"},
                    },
                },
                "finished": {},
            },
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()
        self.assertIn("completer.working.step1", interpreter.current_state_ids)

        # ⚡ Act: Move the child to its final state.
        interpreter.send("NEXT")

        # ✨ Assert: The parent's `onDone` transition was taken.
        self.assertEqual(interpreter.current_state_ids, {"completer.finished"})

    def test_parallel_state_on_done_transition(self) -> None:
        """Tests `onDone` transition from a parallel state.

        An `onDone` transition should only be taken when all child regions
        of the parallel state have reached a final state.
        """
        logger.info("🧪 Testing `onDone` from a parallel state...")
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {  # noqa: DuplicatedCode
            "id": "parallel",
            "initial": "active",
            "states": {
                "active": {
                    "type": "parallel",
                    "onDone": "finished",
                    "states": {
                        "a": {
                            "initial": "a1",
                            "states": {
                                "a1": {"on": {"A_DONE": "a2"}},
                                "a2": {"type": "final"},
                            },
                        },
                        "b": {
                            "initial": "b1",
                            "states": {
                                "b1": {"on": {"B_DONE": "b2"}},
                                "b2": {"type": "final"},
                            },
                        },
                    },
                },
                "finished": {},
            },
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(
            interpreter.current_state_ids,
            {"parallel.active.a.a1", "parallel.active.b.b1"},
        )

        # ⚡ Act: Finish the first region.
        interpreter.send("A_DONE")
        # ✨ Assert: The `onDone` transition is NOT taken yet.
        self.assertNotIn("parallel.finished", interpreter.current_state_ids)

        # ⚡ Act: Finish the second region.
        interpreter.send("B_DONE")
        # ✨ Assert: NOW the `onDone` transition is taken.
        self.assertEqual(interpreter.current_state_ids, {"parallel.finished"})

    def test_transition_from_nested_state_to_ancestor_sibling(self) -> None:
        """Tests transition from a deep state to a sibling of an ancestor.

        This ensures the interpreter correctly exits all intermediate states.
        """
        logger.info("🧪 Testing transition out of a deeply nested state...")
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "deep",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {
                        "a1": {
                            "initial": "a11",
                            "states": {"a11": {"on": {"GOTO_B": "b"}}},
                        }
                    },
                },
                "b": {},
            },
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Trigger the transition from the deepest state.
        interpreter.send("GOTO_B")

        # ✨ Assert: The interpreter is now in the target state 'b'.
        self.assertEqual(interpreter.current_state_ids, {"deep.b"})

    def test_deeply_nested_parallel_state_on_done(self) -> None:
        """Tests that `onDone` correctly fires from a deeply nested parallel state."""
        logger.info("🧪 Testing `onDone` from a nested parallel state...")
        # 🤖 Arrange: A machine where a parallel state is inside another state.
        machine_config: Dict[str, Any] = {  # noqa: DuplicatedCode
            "id": "m",
            "initial": "s1",
            "states": {
                "s1": {
                    "initial": "p_wrapper",
                    "onDone": "s2",
                    "states": {
                        "p_wrapper": {
                            "initial": "p",
                            "states": {
                                "p": {
                                    "type": "parallel",
                                    "onDone": "p_final",
                                    "states": {
                                        "a": {
                                            "initial": "a1",
                                            "states": {
                                                "a1": {"type": "final"}
                                            },
                                        },
                                        "b": {
                                            "initial": "b1",
                                            "states": {
                                                "b1": {"type": "final"}
                                            },
                                        },
                                    },
                                },
                                "p_final": {"type": "final"},
                            },
                        }
                    },
                },
                "s2": {},
            },
        }
        machine = create_machine(machine_config)

        # ⚡ Act: The machine should auto-transition upon start.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The machine correctly cascaded through all `onDone` events.
        self.assertEqual(interpreter.current_state_ids, {"m.s2"})

    def test_final_state_in_parallel_machine_triggers_on_done(self) -> None:
        """Tests one final region in a parallel state does not trigger onDone."""
        logger.info(
            "🧪 Testing one final region does not trigger parent `onDone`..."
        )
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "p_final",
            "type": "parallel",
            "onDone": "finished",  # This should not be reached
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {
                        "a1": {"on": {"FINISH_A": "a2"}},
                        "a2": {"type": "final"},
                    },
                },
                "b": {"initial": "b1", "states": {"b1": {}}},
            },
            "finished": {},
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Finish only one of the two parallel regions.
        interpreter.send("FINISH_A")

        # ✨ Assert: The machine remains in the parallel state.
        self.assertEqual(
            interpreter.current_state_ids, {"p_final.a.a2", "p_final.b.b1"}
        )

    # -------------------------------------------------------------------------
    # 🚀 Service Invocation (Invoke) Tests
    # -------------------------------------------------------------------------

    def test_invoke_sync_service_on_entry(self) -> None:
        """Tests invoking a sync service on entry and transitioning on `onDone`."""
        logger.info("🧪 Testing synchronous service invocation (`onDone`)...")
        # 🤖 Arrange: Define a simple service that returns data.
        logic = MachineLogic(
            services={"getUser": lambda i, c, e: {"name": "John Doe"}}
        )
        machine_config: Dict[str, Any] = {
            "id": "fetcher",
            "initial": "loading",
            "states": {
                "loading": {"invoke": {"src": "getUser", "onDone": "success"}},
                "success": {},
            },
        }
        machine = create_machine(machine_config, logic=logic)

        # ⚡ Act: Starting the interpreter enters the 'loading' state.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The service was called, and `onDone` transition occurred.
        self.assertEqual(interpreter.current_state_ids, {"fetcher.success"})

    def test_invoke_sync_service_on_error_transition(self) -> None:
        """Tests an `onError` transition is taken when a sync service fails."""
        logger.info("🧪 Testing synchronous service invocation (`onError`)...")

        # 🤖 Arrange: Define a service that always raises an exception.
        def failing_service(i, c, e):  # noqa: F841
            """A service designed to fail."""
            raise ValueError("Service failed")

        logic = MachineLogic(services={"badService": failing_service})
        machine_config: Dict[str, Any] = {
            "id": "fetcher",
            "initial": "loading",
            "states": {
                "loading": {
                    "invoke": {"src": "badService", "onError": "failure"}
                },
                "failure": {},
            },
        }
        machine = create_machine(machine_config, logic=logic)

        # ⚡ Act: Starting the interpreter invokes the failing service.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The `onError` transition was taken.
        self.assertEqual(interpreter.current_state_ids, {"fetcher.failure"})

    def test_invoke_service_populates_context_from_event_data(self) -> None:
        """Tests the context is updated from `done.invoke` event data."""
        logger.info("🧪 Testing context update from service `onDone` data...")
        # 🤖 Arrange: Define a service and an action to update context.
        logic = MachineLogic(
            services={
                "getUser": lambda i, c, e: {"name": "Jane Doe", "id": 123}
            },
            actions={"setUser": lambda i, c, e, a: c.update({"user": e.data})},
        )
        machine_config: Dict[str, Any] = {
            "id": "fetcher",
            "initial": "loading",
            "context": {"user": None},
            "states": {
                "loading": {
                    "invoke": {
                        "src": "getUser",
                        "onDone": {
                            "target": "success",
                            "actions": "setUser",
                        },
                    }
                },
                "success": {},
            },
        }
        machine = create_machine(machine_config, logic=logic)

        # ⚡ Act: Start the interpreter to run the service.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The context was updated with the service's return value.
        self.assertEqual(
            interpreter.context["user"], {"name": "Jane Doe", "id": 123}
        )

    def test_invoke_sync_service_that_returns_none(self) -> None:
        """Tests that services that return `None` are handled gracefully."""
        logger.info("🧪 Testing service that returns `None`...")
        # 🤖 Arrange
        action = MagicMock()
        logic = MachineLogic(
            services={"fireAndForget": lambda i, c, e: None},
            actions={"logDone": action},
        )
        machine_config: Dict[str, Any] = {
            "id": "none_service",
            "initial": "working",
            "states": {
                "working": {
                    "invoke": {
                        "src": "fireAndForget",
                        "onDone": {
                            "target": "done",
                            "actions": "logDone",
                        },
                    }
                },
                "done": {},
            },
        }
        machine = create_machine(machine_config, logic=logic)

        # ⚡ Act: Start the interpreter.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The machine transitioned, and the event data was `None`.
        self.assertEqual(interpreter.current_state_ids, {"none_service.done"})
        self.assertIsNone(action.call_args[0][2].data)

    def test_invoke_service_with_no_on_done_handler(self) -> None:
        """Test service without an `onDone` handler completes without error."""
        logger.info(
            "🧪 Testing service invocation with no `onDone` handler..."
        )
        # 🤖 Arrange: A service is invoked but has no transition handlers.
        logic = MachineLogic(services={"doNothing": lambda i, c, e: "data"})
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "working",
            "states": {"working": {"invoke": {"src": "doNothing"}}},
        }
        machine = create_machine(machine_config, logic=logic)
        # ⚡ Act: The machine should start and simply remain in the state.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The machine is stable in the state where the service ran.
        self.assertEqual(interpreter.current_state_ids, {"m.working"})

    # -------------------------------------------------------------------------
    # ⏱️ Timed Transition (After) Tests
    # -------------------------------------------------------------------------

    def test_after_transition_is_scheduled_and_fires(self) -> None:
        """Tests `SyncInterpreter` correctly fires an `after` transition."""
        logger.info("🧪 Testing successful `after` transition...")
        # 🤖 Arrange: Create the machine configuration.
        machine_config: Dict[str, Any] = {
            "id": "timer",
            "initial": "waiting",
            "states": {
                "waiting": {"after": {50: "finished"}},  # 50ms delay
                "finished": {},
            },
        }
        machine = create_machine(machine_config)

        # Use a threading.Event for reliable synchronization instead of polling.
        transition_happened = threading.Event()

        # A simple plugin to signal when the desired transition occurs.
        class TransitionWatcher(PluginBase):
            def on_transition(
                self, interpreter, from_states, to_states, transition
            ) -> None:
                """Sets the event when the target state is entered."""
                if any(s.id == "timer.finished" for s in to_states):
                    transition_happened.set()

        interpreter = SyncInterpreter(machine)
        interpreter.use(TransitionWatcher())
        interpreter.start()
        self.assertEqual(interpreter.current_state_ids, {"timer.waiting"})

        # ⚡ Act: Wait for the plugin to signal that the transition has occurred.
        # A generous timeout of 1 second is used to avoid test flakes on slow systems.
        event_was_set = transition_happened.wait(timeout=1.0)

        # ✨ Assert: The event should have been set, and the state should be correct.
        self.assertTrue(
            event_was_set,
            "The transition to 'finished' did not occur within the timeout.",
        )
        self.assertEqual(interpreter.current_state_ids, {"timer.finished"})
        interpreter.stop()

    def test_after_transition_is_cancelled_on_state_exit(self) -> None:
        """Tests an `after` transition is cancelled if the state is exited."""
        logger.info("🧪 Testing cancellation of `after` transition...")
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "timer_cancel",
            "initial": "waiting",
            "states": {
                "waiting": {
                    "after": {1000: "timeout"},  # 1s delay
                    "on": {"CANCEL": "cancelled"},
                },
                "timeout": {},
                "cancelled": {},
            },
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(
            interpreter.current_state_ids, {"timer_cancel.waiting"}
        )

        # ⚡ Act: Immediately send an event to exit the state.
        interpreter.send("CANCEL")

        # ✨ Assert: The machine should be in the 'cancelled' state.
        self.assertEqual(
            interpreter.current_state_ids, {"timer_cancel.cancelled"}
        )

        # ⏳ Wait for a duration less than the timer to confirm it's cancelled.
        time.sleep(0.1)

        # ✨ Assert: The state should remain 'cancelled', not 'timeout'.
        self.assertEqual(
            interpreter.current_state_ids, {"timer_cancel.cancelled"}
        )
        interpreter.stop()

    # -------------------------------------------------------------------------
    # 🎭 Actor Model (Spawn) Tests
    # -------------------------------------------------------------------------

    def test_spawn_blocking_waits_for_child(self) -> None:
        """Tests a blocking actor runs inline and stays registered."""
        logger.info("🧪 Testing blocking actor spawn waits for completion...")
        # 🤖 Arrange
        child_cfg = {
            "id": "childB",
            "initial": "step",
            "states": {"step": {"type": "final"}},
        }
        parent_cfg = {
            "id": "parentB",
            "initial": "a",
            "states": {
                "a": {"entry": ["spawn_blocking_childSvc"], "on": {"GO": "b"}},
                "b": {},
            },
        }
        machine = create_machine(
            parent_cfg,
            logic=MachineLogic(
                services={
                    "childSvc": lambda i, c, e: create_machine(child_cfg)
                }
            ),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()

        # ✨ Assert: Child finished, but remains in registry (blocking mode).
        self.assertEqual(len(interp._actors), 1)
        interp.stop()

    def test_spawn_non_blocking_creates_child_actor(self) -> None:
        """Tests that spawning a service starts at least one actor thread."""
        logger.info("🧪 Testing non-blocking spawn creates actor thread...")
        # 🤖 Arrange
        machine = create_machine(
            {
                "id": "parent",
                "initial": "a",
                "states": {"a": {"entry": ["spawn_child"]}},
            },
            logic=MachineLogic(
                services={
                    "child": lambda i, c, e: create_machine(
                        self._infinite_child_machine()
                    )
                }
            ),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.05)  # Allow thread to start

        # ✨ Assert
        self.assertTrue(
            any(t.name.startswith("actor-") for t in threading.enumerate())
        )
        interp.stop()

    def test_multiple_non_blocking_actors_spawned(self) -> None:
        """Tests two actor threads appear when two services are spawned."""
        logger.info("🧪 Testing multiple non-blocking actor spawns...")
        # 🤖 Arrange
        factory = lambda i, c, e: create_machine(  # noqa: E731
            self._infinite_child_machine()
        )
        machine = create_machine(
            {
                "id": "P",
                "initial": "s",
                "states": {"s": {"entry": ["spawn_a", "spawn_b"]}},
            },
            logic=MachineLogic(services={"a": factory, "b": factory}),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.05)

        # ✨ Assert
        actor_threads = [
            t for t in threading.enumerate() if t.name.startswith("actor-")
        ]
        self.assertGreaterEqual(len(actor_threads), 2)
        interp.stop()

    def test_actor_ids_are_unique_and_contain_uuid(self) -> None:
        """Tests two spawned services create two distinct actor threads/IDs."""
        logger.info("🧪 Testing actor ID uniqueness...")
        # 🤖 Arrange
        factory = lambda i, c, e: create_machine(  # noqa: E731
            self._infinite_child_machine()
        )
        machine = create_machine(
            {
                "id": "parentID",
                "initial": "start",
                "states": {"start": {"entry": ["spawn_one", "spawn_two"]}},
            },
            logic=MachineLogic(services={"one": factory, "two": factory}),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.05)

        # ✨ Assert
        actor_threads = [
            t for t in threading.enumerate() if t.name.startswith("actor-")
        ]
        ids = {t.name.removeprefix("actor-") for t in actor_threads}
        self.assertGreaterEqual(len(ids), 2)
        self.assertEqual(len(ids), len(set(ids)))  # All IDs are unique
        interp.stop()

    def test_spawn_actor_non_blocking_does_not_duplicate_actor_ids(
        self,
    ) -> None:
        """Tests spawning the same service twice yields unique actor IDs."""
        logger.info("🧪 Testing actor ID uniqueness for duplicate spawns...")
        # 🤖 Arrange: Use a long-lived child machine to ensure actors
        # persist long enough for the assertion to run.
        factory = lambda i, c, e: create_machine(  # noqa: E731
            self._infinite_child_machine()
        )
        parent_cfg = {
            "id": "dupParent",
            "initial": "s",
            "states": {"s": {"entry": ["spawn_child", "spawn_child"]}},
        }
        machine = create_machine(
            parent_cfg, logic=MachineLogic(services={"child": factory})
        )

        # ⚡ Act
        interpreter = SyncInterpreter(machine).start()
        time.sleep(0.05)  # Allow actors to spawn and register

        # ✨ Assert: There should be two unique actor IDs in the registry.
        actor_ids = list(interpreter._actors.keys())
        self.assertEqual(len(actor_ids), 2)
        self.assertEqual(len(set(actor_ids)), 2, "Actor IDs are not unique")
        interpreter.stop()

    def test_actor_factory_receives_parent_context(self) -> None:
        """Tests that a service factory receives the parent's context."""
        logger.info("🧪 Testing factory receives context...")
        # 🤖 Arrange
        saw_value = {}

        def factory(parent_interp, ctx, e):  # noqa: F841
            """A factory that inspects the received context."""
            saw_value["x"] = ctx["x"]
            return create_machine(
                {"id": "c", "initial": "f", "states": {"f": {"type": "final"}}}
            )

        parent_cfg = {
            "id": "ctxParent",
            "initial": "a",
            "context": {"x": 42},
            "states": {"a": {"entry": ["spawn_child"]}},
        }
        machine = create_machine(
            parent_cfg,
            logic=MachineLogic(services={"child": factory}),
        )

        # ⚡ Act
        SyncInterpreter(machine).start()

        # ✨ Assert
        self.assertEqual(saw_value["x"], 42)

    def test_spawn_blocking_action_preserves_parent_context(self) -> None:
        """Tests a blocking child actor can mutate the parent's context."""
        logger.info("🧪 Testing context mutation by blocking actor...")

        # 🤖 Arrange: Define a child factory that increments a counter
        # on the parent's context.
        def factory(
            interp: SyncInterpreter,
            ctx: Dict[str, Any],
            evt: Event,  # noqa: F841
        ) -> "MachineNode":  # noqa: F821
            """A factory that increments a counter on the received context."""
            ctx["count"] += 1
            return create_machine(
                {"id": "noop", "initial": "s", "states": {"s": {}}}
            )

        parent_cfg = {
            "id": "shareCtx",
            "initial": "a",
            "context": {"count": 0},
            "states": {"a": {"entry": ["spawn_blocking_childSvc"]}},
        }
        machine = create_machine(
            parent_cfg, logic=MachineLogic(services={"childSvc": factory})
        )

        # ⚡ Act: Start the interpreter, which will run the blocking actor.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The parent's context should reflect the change made by the child.
        self.assertEqual(interpreter.context["count"], 1)

    def test_spawn_actor_child_modifies_shared_list_in_context(self) -> None:
        """Tests a child actor can mutate a list in the parent's context."""
        logger.info("🧪 Testing mutation of shared list in context...")

        # 🤖 Arrange: Define a child factory that appends an item to a list
        # on the parent's context.
        def factory(
            interp: SyncInterpreter,
            ctx: Dict[str, Any],
            evt: Event,  # noqa: F841
        ) -> "MachineNode":  # noqa: F821
            """A factory that appends to a list on the received context."""
            ctx.setdefault("items", []).append("child_was_here")
            return create_machine(
                {"id": "noop", "initial": "s", "states": {"s": {}}}
            )

        parent_cfg = {
            "id": "listParent",
            "initial": "a",
            "context": {"items": []},
            "states": {"a": {"entry": ["spawn_blocking_childSvc"]}},
        }
        machine = create_machine(
            parent_cfg, logic=MachineLogic(services={"childSvc": factory})
        )

        # ⚡ Act: Start the interpreter.
        interpreter = SyncInterpreter(machine).start()

        # ✨ Assert: The list in the parent's context should be modified.
        self.assertEqual(interpreter.context["items"], ["child_was_here"])

    def test_non_blocking_actor_cleanup_after_child_stop(self) -> None:
        """Tests the _actors dictionary removes an entry when child finishes."""
        logger.info("🧪 Testing non-blocking actor cleanup...")
        # 🤖 Arrange
        child_cfg = {
            "id": "quick",
            "initial": "final",
            "states": {"final": {"type": "final"}},
        }
        machine = create_machine(
            {
                "id": "cleanup",
                "initial": "s",
                "states": {"s": {"entry": ["spawn_quick"]}},
            },
            logic=MachineLogic(
                services={"quick": lambda i, c, e: create_machine(child_cfg)}
            ),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.02)  # Allow time for child to finish and cleanup

        # ✨ Assert
        self.assertEqual(len(interp._actors), 0)
        interp.stop()

    def test_spawn_actor_child_machine_reaches_final_state(self) -> None:
        """Tests that a spawned child actor's machine is executed correctly."""
        logger.info("🧪 Testing child actor machine execution...")
        # 🤖 Arrange: Use a flag to verify that the child's logic runs.
        execution_flags = {}

        child_cfg = {
            "id": "runner",
            "initial": "start",
            "states": {"start": {"type": "final"}},
        }

        def factory(
            interp: SyncInterpreter,
            ctx: Dict[str, Any],
            evt: Event,  # noqa: F841
        ) -> "MachineNode":  # noqa: F821
            """A factory that sets a flag and returns the child machine."""
            execution_flags["factory_called"] = True
            return create_machine(child_cfg)

        machine = create_machine(
            {
                "id": "parentRunner",
                "initial": "a",
                "states": {"a": {"entry": ["spawn_child"]}},
            },
            logic=MachineLogic(services={"child": factory}),
        )

        # ⚡ Act: Start the parent, which spawns the child.
        SyncInterpreter(machine).start()
        time.sleep(0.02)  # Allow time for the non-blocking actor to run

        # ✨ Assert: The factory should have been called.
        self.assertTrue(execution_flags.get("factory_called", False))

    def test_parent_handles_event_queue_while_actor_runs(self) -> None:
        """Tests parent still processes events during actor execution."""
        logger.info("🧪 Testing parent event queue during actor execution...")
        # 🤖 Arrange
        child_cfg = {
            "id": "slowChild",
            "initial": "working",
            "states": {
                "working": {"after": {30: "done"}},  # 30ms delay
                "done": {"type": "final"},
            },
        }
        factory = lambda i, c, e: create_machine(child_cfg)  # noqa: E731
        parent_cfg = {
            "id": "queueParent",
            "initial": "idle",
            "states": {
                "idle": {
                    "entry": ["spawn_childSvc"],
                    "on": {"GO": "finished"},
                },
                "finished": {},
            },
        }
        machine = create_machine(
            parent_cfg,
            logic=MachineLogic(services={"childSvc": factory}),
        )
        interp = SyncInterpreter(machine).start()

        # ⚡ Act: Send event immediately; should not be blocked by actor.
        interp.send("GO")

        # ✨ Assert
        self.assertEqual(interp.current_state_ids, {"queueParent.finished"})
        interp.stop()

    def test_nested_actor_spawn(self) -> None:
        """Tests that a child actor can itself spawn another actor."""
        logger.info("🧪 Testing nested actor spawn...")
        # 🤖 Arrange
        grand_cfg = {
            "id": "grand",
            "initial": "final",
            "states": {"final": {"type": "final"}},
        }
        grand_factory = lambda i, c, e: create_machine(grand_cfg)  # noqa: E731
        child_cfg = {
            "id": "childNest",
            "initial": "init",
            "states": {"init": {"entry": ["spawn_grand"], "type": "final"}},
        }
        child_factory = lambda i, c, e: create_machine(  # noqa: E731
            child_cfg,
            logic=MachineLogic(services={"grand": grand_factory}),
        )
        parent_cfg = {
            "id": "nestParent",
            "initial": "start",
            "states": {"start": {"entry": ["spawn_child"]}},
        }
        machine = create_machine(
            parent_cfg,
            logic=MachineLogic(services={"child": child_factory}),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.05)  # Allow cascade to finish

        # ✨ Assert: Should have no lingering actors after cascade finish.
        self.assertEqual(len(interp._actors), 0)
        interp.stop()

    def test_actor_thread_is_daemon(self) -> None:
        """Tests a non-blocking actor runs in a daemon thread."""
        logger.info("🧪 Testing actor thread is a daemon...")
        # 🤖 Arrange
        machine = create_machine(
            {
                "id": "daemonParent",
                "initial": "s",
                "states": {"s": {"entry": ["spawn_job"]}},
            },
            logic=MachineLogic(
                services={
                    "job": lambda i, c, e: create_machine(
                        self._infinite_child_machine()
                    )
                }
            ),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.05)

        # ✨ Assert
        actor_threads = [
            t for t in threading.enumerate() if t.name.startswith("actor-")
        ]
        self.assertTrue(actor_threads, "No actor thread found")
        self.assertTrue(all(t.daemon for t in actor_threads))
        interp.stop()

    def test_spawn_non_blocking_actor_thread_name_contains_actor_id(
        self,
    ) -> None:
        """Tests an actor's thread name contains its unique ID with a UUID."""
        logger.info("🧪 Testing actor thread naming convention...")
        # 🤖 Arrange
        machine = create_machine(
            {
                "id": "threadName",
                "initial": "x",
                "states": {"x": {"entry": ["spawn_job"]}},
            },
            logic=MachineLogic(
                services={
                    "job": lambda i, c, e: create_machine(
                        self._infinite_child_machine()
                    )
                }
            ),
        )

        # ⚡ Act
        interpreter = SyncInterpreter(machine).start()
        time.sleep(0.05)  # Allow thread to start

        # ✨ Assert
        actor_threads = [
            t for t in threading.enumerate() if t.name.startswith("actor-")
        ]
        self.assertTrue(actor_threads, "No actor threads detected")
        # Check that the thread name follows the format 'actor-parent:child:uuid'
        for t in actor_threads:
            actor_id = t.name.removeprefix("actor-")
            parts = actor_id.split(":")
            self.assertGreaterEqual(
                len(parts), 3, "Actor ID format is incorrect"
            )
            # A simple regex to check for UUID v4 format
            self.assertRegex(
                parts[-1],
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            )
        interpreter.stop()

    def test_non_blocking_actor_finishes_before_parent_stop(self) -> None:
        """Tests stopping parent cleans up running actor threads."""
        logger.info("🧪 Testing parent stop cleans up actors...")
        # 🤖 Arrange
        machine = create_machine(
            {
                "id": "grace",
                "initial": "a",
                "states": {"a": {"entry": ["spawn_child"]}},
            },
            logic=MachineLogic(
                services={
                    "child": lambda i, c, e: create_machine(
                        self._infinite_child_machine()
                    )
                }
            ),
        )
        interp = SyncInterpreter(machine).start()
        time.sleep(0.05)
        before_count = len(
            [t for t in threading.enumerate() if t.name.startswith("actor-")]
        )
        self.assertGreaterEqual(before_count, 1)

        # ⚡ Act
        interp.stop()
        time.sleep(0.05)  # Allow time for threads to terminate

        # ✨ Assert
        after_count = len(
            [t for t in threading.enumerate() if t.name.startswith("actor-")]
        )
        self.assertEqual(after_count, 0)

    def test_spawn_actor_service_can_be_machine_node_direct(self) -> None:
        """Tests a service can be a direct MachineNode, not a factory."""
        logger.info("🧪 Testing direct MachineNode as a service...")
        # 🤖 Arrange
        child_node = create_machine(
            {"id": "node", "initial": "f", "states": {"f": {"type": "final"}}}
        )
        machine = create_machine(
            {
                "id": "direct",
                "initial": "a",
                "states": {"a": {"entry": ["spawn_childNode"]}},
            },
            logic=MachineLogic(services={"childNode": child_node}),
        )

        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.01)

        # ✨ Assert: Actor finished instantly and was cleaned up.
        self.assertEqual(len(interp._actors), 0)
        interp.stop()

    def test_spawn_actor_parent_can_snapshot_after_child_done(self) -> None:
        """Tests taking a snapshot after a child actor completes."""
        logger.info("🧪 Testing snapshot after child actor completion...")
        # 🤖 Arrange
        child_cfg = {
            "id": "snapC",
            "initial": "f",
            "states": {"f": {"type": "final"}},
        }
        machine = create_machine(
            {
                "id": "snapParent",
                "initial": "a",
                "states": {"a": {"entry": ["spawn_child"]}},
            },
            logic=MachineLogic(
                services={"child": lambda i, c, e: create_machine(child_cfg)}
            ),
        )
        interp = SyncInterpreter(machine).start()
        time.sleep(0.02)  # Wait for the child to complete

        # ⚡ Act: Get the snapshot string from the interpreter.
        snapshot_json_string = interp.get_snapshot()

        # ✨ Assert: Parse the JSON and check the data structure itself.
        # This is more robust than checking for an exact substring.
        snapshot_data = json.loads(snapshot_json_string)
        self.assertEqual(snapshot_data.get("state_ids"), ["snapParent.a"])

    def test_spawn_actor_with_after_timer_inside_child(self) -> None:
        """Tests child with an `after` timer runs correctly as an actor."""
        logger.info("🧪 Testing child actor with internal timer...")
        # 🤖 Arrange
        child_cfg = {
            "id": "timerChild",
            "initial": "wait",
            "states": {
                "wait": {"after": {20: "done"}},  # 20ms delay
                "done": {"type": "final"},
            },
        }
        machine = create_machine(
            {
                "id": "timerParent",
                "initial": "a",
                "states": {"a": {"entry": ["spawn_child"]}},
            },
            logic=MachineLogic(
                services={"child": lambda i, c, e: create_machine(child_cfg)}
            ),
        )
        # ⚡ Act
        interp = SyncInterpreter(machine).start()
        time.sleep(0.05)  # Wait for timer to fire and cleanup

        # ✨ Assert
        self.assertEqual(len(interp._actors), 0)
        interp.stop()

    # -------------------------------------------------------------------------
    # 📸 Snapshot & Restore Tests
    # -------------------------------------------------------------------------

    def test_snapshot_and_restore(self) -> None:
        """Tests an interpreter's state and context can be snapshotted and restored."""
        logger.info("🧪 Testing interpreter snapshot and restore...")
        # 🤖 Arrange: Create an interpreter and move it to a specific state.
        machine_config: Dict[str, Any] = {
            "id": "snap",
            "initial": "a",
            "context": {"count": 0},
            "states": {
                "a": {"on": {"NEXT": {"target": "b", "actions": "inc"}}},
                "b": {},
            },
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(
                actions={"inc": lambda i, c, e, a: c.update({"count": 1})}
            ),
        )
        original_interp = SyncInterpreter(machine).start()
        original_interp.send("NEXT")

        # ⚡ Act: Get a snapshot and create a new interpreter from it.
        snapshot = original_interp.get_snapshot()
        original_interp.stop()
        restored_interp = SyncInterpreter.from_snapshot(snapshot, machine)

        # ✨ Assert: The restored interpreter has the correct state and context.
        self.assertIsInstance(restored_interp, SyncInterpreter)
        self.assertEqual(restored_interp.status, "running")
        self.assertEqual(restored_interp.current_state_ids, {"snap.b"})
        self.assertEqual(restored_interp.context["count"], 1)

    def test_snapshot_of_parallel_state(self) -> None:
        """Tests a snapshot correctly captures all active parallel state regions."""
        logger.info("🧪 Testing snapshot of a machine in a parallel state...")
        # 🤖 Arrange: Start a machine in a parallel state.
        machine_config: Dict[str, Any] = {
            "id": "p",
            "type": "parallel",
            "states": {
                "a": {"initial": "a1", "states": {"a1": {}}},
                "b": {"initial": "b1", "states": {"b1": {}}},
            },
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Get the snapshot and parse it.
        snapshot_str = interpreter.get_snapshot()
        snapshot_data = json.loads(snapshot_str)

        # ✨ Assert: The snapshot contains both active state IDs.
        self.assertEqual(set(snapshot_data["state_ids"]), {"p.a.a1", "p.b.b1"})

    # -------------------------------------------------------------------------
    # 🔌 Plugin System Tests
    # -------------------------------------------------------------------------

    def test_plugins_are_called_during_lifecycle(self) -> None:
        """Test plugin hooks are called at correct points in the lifecycle."""
        logger.info("🧪 Testing plugin lifecycle hooks...")
        # 🤖 Arrange: Create a mock plugin and a simple machine.
        mock_plugin = MagicMock(spec=PluginBase)
        machine_config: Dict[str, Any] = {
            "id": "plug",
            "initial": "a",
            "context": {},
            "states": {
                "a": {"entry": "doit", "on": {"NEXT": "b"}},
                "b": {},
            },
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(actions={"doit": lambda i, c, e, a: None}),
        )
        interpreter = SyncInterpreter(machine)
        interpreter.use(mock_plugin)

        # ⚡ Act & ✨ Assert (Start)
        interpreter.start()
        mock_plugin.on_interpreter_start.assert_called_once_with(interpreter)
        mock_plugin.on_action_execute.assert_called_once()
        self.assertEqual(
            mock_plugin.on_transition.call_count, 1
        )  # Initial transition

        # ⚡ Act & ✨ Assert (Send)
        interpreter.send("NEXT")
        mock_plugin.on_event_received.assert_called_once()
        self.assertEqual(
            mock_plugin.on_transition.call_count, 2
        )  # Second transition

        # ⚡ Act & ✨ Assert (Stop)
        interpreter.stop()
        mock_plugin.on_interpreter_stop.assert_called_once_with(interpreter)

    def test_internal_transition_fires_on_transition_hook(self) -> None:
        """Tests the `on_transition` plugin hook fires for internal transitions."""
        logger.info(
            "🧪 Testing `on_transition` hook for internal transitions..."
        )
        # 🤖 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "s1",
            "states": {"s1": {"on": {"NOOP": {}}}},
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).use(mock_plugin).start()
        initial_call_count = mock_plugin.on_transition.call_count

        # ⚡ Act
        interpreter.send("NOOP")

        # ✨ Assert: The hook was called one more time.
        self.assertEqual(
            mock_plugin.on_transition.call_count, initial_call_count + 1
        )

    def test_unhandled_event_does_not_fire_on_transition_hook(self) -> None:
        """Tests `on_transition` hook does NOT fire for unhandled events."""
        logger.info("🧪 Testing `on_transition` hook for unhandled events...")
        # 🤖 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "s1",
            "states": {"s1": {"on": {"REAL_EVENT": {}}}},
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).use(mock_plugin).start()
        # ✨ Assert: Hook is called once for the initial transition.
        mock_plugin.on_transition.assert_called_once()

        # ⚡ Act: Send an event that has no defined transition.
        interpreter.send("UNHANDLED_EVENT")

        # ✨ Assert: The hook was not called again.
        mock_plugin.on_transition.assert_called_once()

    def test_plugin_on_guard_evaluated_hook(self) -> None:
        """Tests that the `on_guard_evaluated` plugin hook is called."""
        logger.info(
            "🧪 Testing `on_guard_evaluated` plugin hook with SyncInterpreter."
        )
        # 🤖 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        logic = MachineLogic(
            guards={
                "canProceed": lambda c, e: True,
                "cannotProceed": lambda c, e: False,
            }
        )
        machine_config: Dict[str, Any] = {
            "id": "guarded_sync",
            "initial": "start",
            "states": {
                "start": {
                    "on": {
                        "GO": [
                            {"target": "failure", "guard": "cannotProceed"},
                            {"target": "success", "guard": "canProceed"},
                        ]
                    }
                },
                "success": {},
                "failure": {},
            },
        }
        machine = create_machine(machine_config, logic=logic)
        interpreter = SyncInterpreter(machine).use(mock_plugin).start()
        test_event = Event("GO", payload={"value": 10})

        # ⚡ Act
        interpreter.send(test_event)

        # ✨ Assert
        self.assertEqual(mock_plugin.on_guard_evaluated.call_count, 2)

        # Check call for "cannotProceed" (was False)
        first_call_args = mock_plugin.on_guard_evaluated.call_args_list[0].args
        self.assertEqual(first_call_args[1], "cannotProceed")
        self.assertFalse(first_call_args[3])  # result

        # Check call for "canProceed" (was True)
        second_call_args = mock_plugin.on_guard_evaluated.call_args_list[
            1
        ].args
        self.assertEqual(second_call_args[1], "canProceed")
        self.assertTrue(second_call_args[3])  # result

    def test_plugin_on_service_start_hook(self) -> None:
        """Tests that the `on_service_start` plugin hook is called."""
        logger.info(
            "🧪 Testing `on_service_start` plugin hook with SyncInterpreter."
        )
        # 🤖 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        mock_service = MagicMock(return_value="sync_data")
        logic = MachineLogic(services={"mySyncService": mock_service})
        machine_config: Dict[str, Any] = {
            "id": "sync_service",
            "initial": "invoke_state",
            "states": {
                "invoke_state": {
                    "invoke": {"src": "mySyncService", "onDone": "done"}
                },
                "done": {},
            },
        }
        machine = create_machine(
            machine_config, logic=logic
        )  # noqa: DuplicateCode
        interpreter = SyncInterpreter(machine).use(mock_plugin)

        # ⚡ Act: Service invocation is on entry, so it runs during .start()
        interpreter.start()

        # ✨ Assert
        mock_plugin.on_service_start.assert_called_once()
        args, kwargs = mock_plugin.on_service_start.call_args
        self.assertEqual(args[0], interpreter)
        self.assertEqual(args[1].src, "mySyncService")
        self.assertTrue(mock_service.called)

    def test_plugin_on_service_done_hook(self) -> None:
        """Tests the `on_service_done` hook on successful sync service."""
        logger.info(
            "🧪 Testing `on_service_done` plugin hook with SyncInterpreter."
        )
        # 🤖 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        service_result = {"status": "sync_success"}
        mock_service = MagicMock(return_value=service_result)
        logic = MachineLogic(services={"mySyncService": mock_service})
        machine_config: Dict[str, Any] = {
            "id": "sync_service_done",
            "initial": "invoke_state",
            "states": {
                "invoke_state": {
                    "invoke": {"src": "mySyncService", "onDone": "done"}
                },
                "done": {},
            },
        }
        machine = create_machine(
            machine_config, logic=logic
        )  # noqa: DuplicateCode
        interpreter = SyncInterpreter(machine).use(mock_plugin)

        # ⚡ Act
        interpreter.start()

        # ✨ Assert
        mock_plugin.on_service_done.assert_called_once()
        args, kwargs = mock_plugin.on_service_done.call_args
        self.assertEqual(args[0], interpreter)
        self.assertEqual(args[1].src, "mySyncService")
        self.assertEqual(args[2], service_result)

    def test_plugin_on_service_error_hook(self) -> None:
        """Tests the `on_service_error` hook on sync service failure."""
        logger.info(
            "🧪 Testing `on_service_error` plugin hook with SyncInterpreter."
        )
        # 🤖 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        service_error = RuntimeError("Sync service failed!")
        mock_service = MagicMock(side_effect=service_error)
        logic = MachineLogic(services={"failingSyncService": mock_service})
        machine_config: Dict[str, Any] = {
            "id": "sync_service_error",
            "initial": "invoke_state",
            "states": {
                "invoke_state": {
                    "invoke": {
                        "src": "failingSyncService",
                        "onError": "failed",
                    }
                },
                "failed": {},
            },
        }
        machine = create_machine(
            machine_config, logic=logic
        )  # noqa: DuplicateCode
        interpreter = SyncInterpreter(machine).use(mock_plugin)

        # ⚡ Act
        interpreter.start()

        # ✨ Assert
        mock_plugin.on_service_error.assert_called_once()
        args, kwargs = mock_plugin.on_service_error.call_args
        self.assertEqual(args[0], interpreter)
        self.assertEqual(args[1].src, "failingSyncService")
        self.assertEqual(args[2], service_error)

    # -------------------------------------------------------------------------
    # ⚠️ Error Handling & Edge Case Tests
    # -------------------------------------------------------------------------

    def test_error_on_unsupported_async_action(self) -> None:
        """Tests `SyncInterpreter` raises `NotSupportedError` for async actions."""
        logger.info("❌ Testing error for unsupported `async` actions...")

        # 🤖 Arrange: Define an async function to be used as an action.
        async def my_async_action(i, c, e, a):  # noqa: F841
            """An async action not supported by SyncInterpreter."""
            pass

        machine_config: Dict[str, Any] = {
            "id": "async_test",
            "initial": "idle",
            "states": {"idle": {"entry": ["badAction"]}},
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(actions={"badAction": my_async_action}),
        )

        # ⚡ Act & ✨ Assert
        with self.assertRaisesRegex(
            NotSupportedError, "not supported by SyncInterpreter"
        ):
            SyncInterpreter(machine).start()

    def test_error_on_unsupported_async_service(self) -> None:
        """Tests `SyncInterpreter` raises `NotSupportedError` for async services."""
        logger.info("❌ Testing error for unsupported `async` services...")

        # 🤖 Arrange: Define an async function to be used as a service.
        async def my_async_service(i, c, e):  # noqa: F841
            """An async service not supported by SyncInterpreter."""
            return {}

        machine_config: Dict[str, Any] = {
            "id": "async_test",
            "initial": "active",
            "states": {"active": {"invoke": {"src": "badService"}}},
        }
        machine = create_machine(
            machine_config,
            logic=MachineLogic(services={"badService": my_async_service}),
        )
        # ⚡ Act & ✨ Assert
        with self.assertRaisesRegex(NotSupportedError, "is async"):
            SyncInterpreter(machine).start()

    def test_error_on_missing_action_implementation(self) -> None:
        """Tests `ImplementationMissingError` is raised for undefined actions."""
        logger.info("❌ Testing error for missing action implementation...")
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "missing",
            "initial": "a",
            "states": {"a": {"entry": ["no_such_action"]}},
        }
        # ⚡ Act & ✨ Assert: Error should be raised at machine creation time.
        with self.assertRaises(ImplementationMissingError):
            create_machine(machine_config)

    def test_error_on_missing_guard_implementation(self) -> None:
        """Tests `ImplementationMissingError` is raised for undefined guards."""
        logger.info("❌ Testing error for missing guard implementation...")
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "missing",
            "initial": "a",
            "states": {
                "a": {
                    "on": {"EVENT": {"target": "a", "guard": "no_such_guard"}}
                }
            },
        }
        # ⚡ Act & ✨ Assert: Error should be raised at machine creation time.
        with self.assertRaises(ImplementationMissingError):
            create_machine(machine_config)

    def test_error_on_missing_service_implementation(self) -> None:
        """Tests `ImplementationMissingError` is raised for undefined services."""
        logger.info("❌ Testing error for missing service implementation...")
        # 🤖 Arrange
        bad_cfg = {
            "id": "badSpawn",
            "initial": "a",
            "states": {"a": {"entry": ["spawn_missingSvc"]}},
        }
        # ⚡ Act & ✨ Assert: Failure occurs during `create_machine`.
        with self.assertRaises(ImplementationMissingError):
            create_machine(bad_cfg)

    def test_error_on_unresolvable_target_state(self) -> None:
        """Tests `StateNotFoundError` is raised for an invalid transition target."""
        logger.info(
            "❌ Testing error for an unresolvable transition target..."
        )
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "badpath",
            "initial": "a",
            "states": {"a": {"on": {"EVENT": "nonexistent"}}},
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()
        # ⚡ Act & ✨ Assert
        with self.assertRaises(StateNotFoundError):
            interpreter.send("EVENT")

    def test_invalid_config_shorthand_transition_raises_error(self) -> None:
        """Tests `InvalidConfigError` for malformed transition shorthand."""
        logger.info(
            "❌ Testing error for invalid shorthand transition config..."
        )
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "s1",
            "states": {"s1": {"on": {"E": 123}}},  # Invalid value for event
        }
        # ⚡ Act & ✨ Assert
        with self.assertRaisesRegex(
            InvalidConfigError, "Invalid transition config"
        ):
            create_machine(machine_config)

    def test_restore_from_snapshot_with_missing_state_id_raises_error(
        self,
    ) -> None:
        """Tests `StateNotFoundError` when restoring snapshot with invalid ID."""
        logger.info(
            "❌ Testing error when restoring snapshot with invalid state ID..."
        )
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "s1",
            "states": {"s1": {}},
        }
        machine = create_machine(machine_config)
        snapshot = '{"status": "running", "context": {}, "state_ids": ["m.nonexistent"]}'

        # ⚡ Act & ✨ Assert
        with self.assertRaisesRegex(
            StateNotFoundError,
            "Could not find state with ID 'm.nonexistent'",
        ):
            SyncInterpreter.from_snapshot(snapshot, machine)

    def test_transition_with_unhandled_event(self) -> None:
        """Tests the machine remains in state if an event is unhandled."""
        logger.info(
            "🧪 Testing that unhandled events cause no state change..."
        )
        # 🤖 Arrange
        machine_config: Dict[str, Any] = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"REAL_EVENT": "b"}}, "b": {}},
        }
        machine = create_machine(machine_config)
        interpreter = SyncInterpreter(machine).start()

        # ⚡ Act: Send an event that is not handled in the current state.
        interpreter.send("FAKE_EVENT")

        # ✨ Assert: The state remains unchanged.
        self.assertEqual(interpreter.current_state_ids, {"m.a"})

    def test_start_on_already_started_interpreter(self) -> None:
        """Tests that calling start() on a running interpreter is a no-op."""
        logger.info("🧪 Testing that `start()` is idempotent...")
        # 🤖 Arrange
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        interpreter = SyncInterpreter(machine).start()
        mock_plugin = MagicMock(spec=PluginBase)
        interpreter.use(mock_plugin)

        # ⚡ Act: Call start() again on the running interpreter.
        interpreter.start()

        # ✨ Assert: The start hook of the plugin was not called again.
        mock_plugin.on_interpreter_start.assert_not_called()

    def test_stop_on_already_stopped_interpreter(self) -> None:
        """Tests that calling stop() on a stopped interpreter is a no-op."""
        logger.info("🧪 Testing that `stop()` is idempotent...")
        # 🤖 Arrange
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.stop()
        mock_plugin = MagicMock(spec=PluginBase)
        interpreter.use(mock_plugin)

        # ⚡ Act: Call stop() again on the stopped interpreter.
        interpreter.stop()

        # ✨ Assert: The stop hook of the plugin was not called.
        mock_plugin.on_interpreter_stop.assert_not_called()

    def test_spawn_blocking_prefix_is_case_sensitive(self) -> None:
        """Tests wrong casing for spawn prefix fails at machine creation."""
        logger.info("🧪 Testing case-sensitivity of spawn prefix...")
        # 🤖 Arrange
        cfg = {
            "id": "caseParent",
            "initial": "a",
            "states": {
                "a": {"entry": ["spawn_Blocking_childSvc"]}
            },  # Incorrect 'B'
        }

        # ⚡ Act & ✨ Assert
        with self.assertRaises(ImplementationMissingError):
            create_machine(cfg)

    def test_spawn_action_name_must_start_with_spawn(self) -> None:
        """Tests a name not starting with 'spawn_' is an ordinary action."""
        logger.info("🧪 Testing non-spawn action name is handled correctly...")
        # 🤖 Arrange
        dummy_action = MagicMock()
        cfg = {
            "id": "nospawn",
            "initial": "a",
            "states": {"a": {"entry": ["spawnWrong"], "type": "final"}},
        }
        machine = create_machine(
            cfg, logic=MachineLogic(actions={"spawnWrong": dummy_action})
        )

        # ⚡ Act
        SyncInterpreter(machine).start()

        # ✨ Assert
        dummy_action.assert_called_once()

    def test_spawn_blocking_actor_removed_even_if_child_errors(self) -> None:
        """Tests a blocking actor raising an error surfaces the exception."""
        logger.info("🧪 Testing error propagation from blocking actor...")
        # 🤖 Arrange
        child_node = create_machine(
            {
                "id": "bad",
                "initial": "a",
                "states": {"a": {"entry": "fail"}},
            },
            logic=MachineLogic(
                actions={
                    "fail": lambda i, c, e, a: (_ for _ in ()).throw(
                        RuntimeError("x")
                    )
                }
            ),
        )
        parent_cfg = {
            "id": "parentBad",
            "initial": "a",
            "states": {"a": {"entry": ["spawn_blocking_badSvc"]}},
        }
        machine = create_machine(
            parent_cfg,
            logic=MachineLogic(
                services={"badSvc": lambda i, c, e: child_node}
            ),
        )

        # ⚡ Act & ✨ Assert
        with self.assertRaises(RuntimeError):
            SyncInterpreter(machine).start()


if __name__ == "__main__":
    unittest.main(verbosity=2)
