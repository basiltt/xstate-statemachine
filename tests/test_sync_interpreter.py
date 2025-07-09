# tests/test_sync_interpreter.py

# -----------------------------------------------------------------------------
# 🧪 Test Suite: SyncInterpreter
# -----------------------------------------------------------------------------
# This suite provides comprehensive testing for the `SyncInterpreter`, which
# is the synchronous execution engine for the state machine library. It verifies
# core synchronous functionality including transitions, actions, guards, and
# error handling for unsupported asynchronous features.
# -----------------------------------------------------------------------------

import unittest
import logging
from typing import Any, Dict, List
from unittest.mock import MagicMock

from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    NotSupportedError,
    Event,
    StateNotFoundError,
    ImplementationMissingError,
    PluginBase,
    ActionDefinition,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestSyncInterpreter
# -----------------------------------------------------------------------------


class TestSyncInterpreter(unittest.TestCase):
    """
    Test suite for the `SyncInterpreter` class.

    This class contains synchronous test methods to validate all features
    of the `SyncInterpreter`, ensuring it correctly executes state logic
    in a blocking manner across a wide variety of scenarios.
    """

    def setUp(self) -> None:
        """Set up common machine configurations for reuse in multiple tests."""
        self.nested_machine_config = {
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
    # Basic Transition and Action Tests
    # -------------------------------------------------------------------------

    def test_simple_transition(self) -> None:
        """Should transition from one state to another on an event."""
        machine = create_machine(
            {
                "id": "light",
                "initial": "green",
                "states": {"green": {"on": {"TIMER": "yellow"}}, "yellow": {}},
            }
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"light.green"})
        interpreter.send("TIMER")
        self.assertEqual(interpreter.current_state_ids, {"light.yellow"})
        interpreter.stop()

    def test_context_and_actions(self) -> None:
        """Should execute synchronous actions that modify context."""
        mock_action = MagicMock()

        def increment(i, ctx, evt, ad):
            ctx["count"] += evt.payload.get("amount", 1)

        mock_action.side_effect = increment
        machine = create_machine(
            {
                "id": "counter",
                "initial": "active",
                "context": {"count": 0},
                "states": {
                    "active": {"on": {"INC": {"actions": ["increment"]}}}
                },
            },
            logic=MachineLogic(actions={"increment": mock_action}),
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("INC", amount=5)
        mock_action.assert_called_once()
        self.assertEqual(interpreter.context["count"], 5)
        interpreter.stop()

    def test_multiple_actions_on_transition(self) -> None:
        """Should execute all actions in a list for a transition."""
        action1 = MagicMock()
        action2 = MagicMock()
        machine = create_machine(
            {
                "id": "multi",
                "initial": "a",
                "states": {
                    "a": {"on": {"EVENT": {"actions": ["action1", "action2"]}}}
                },
            },
            logic=MachineLogic(
                actions={"action1": action1, "action2": action2}
            ),
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("EVENT")
        action1.assert_called_once()
        action2.assert_called_once()

    def test_internal_transition_does_not_change_state(self) -> None:
        """Should execute actions on an internal transition without changing state."""
        action = MagicMock()
        machine = create_machine(
            {
                "id": "internal",
                "initial": "active",
                "states": {"active": {"on": {"EVENT": {"actions": "doIt"}}}},
            },
            logic=MachineLogic(actions={"doIt": action}),
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})
        interpreter.send("EVENT")
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})
        action.assert_called_once()

    # -------------------------------------------------------------------------
    # Guard and Transition Logic Tests
    # -------------------------------------------------------------------------

    def test_guards_allow_transition(self) -> None:
        """Should allow a transition when the guard condition returns true."""
        logic = MachineLogic(guards={"canLogin": lambda ctx, evt: True})
        machine = create_machine(
            {
                "id": "auth",
                "initial": "idle",
                "states": {
                    "idle": {
                        "on": {
                            "LOGIN": {"target": "success", "guard": "canLogin"}
                        }
                    },
                    "success": {},
                },
            },
            logic,
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("LOGIN")
        self.assertEqual(interpreter.current_state_ids, {"auth.success"})

    def test_guards_block_transition(self) -> None:
        """Should block a transition when the guard condition returns false."""
        logic = MachineLogic(guards={"canLogin": lambda ctx, evt: False})
        machine = create_machine(
            {
                "id": "auth",
                "initial": "idle",
                "states": {
                    "idle": {
                        "on": {
                            "LOGIN": {"target": "success", "guard": "canLogin"}
                        }
                    },
                    "success": {},
                },
            },
            logic,
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("LOGIN")
        self.assertEqual(interpreter.current_state_ids, {"auth.idle"})

    def test_chooses_first_passing_guarded_transition(self) -> None:
        """Should select the first transition whose guard passes from a list."""
        machine = create_machine(
            {
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
            },
            logic=MachineLogic(
                guards={
                    "isLow": lambda ctx, evt: ctx["value"] < 10,
                    "isMed": lambda ctx, evt: ctx["value"] < 20,
                }
            ),
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("CHECK")
        self.assertEqual(interpreter.current_state_ids, {"chooser.med"})

    def test_falls_through_to_unguarded_transition(self) -> None:
        """Should select an unguarded transition if all guarded ones fail."""
        machine = create_machine(
            {
                "id": "chooser",
                "initial": "start",
                "context": {"value": 50},
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
            },
            logic=MachineLogic(
                guards={
                    "isLow": lambda ctx, evt: ctx["value"] < 10,
                    "isMed": lambda ctx, evt: ctx["value"] < 20,
                }
            ),
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("CHECK")
        self.assertEqual(interpreter.current_state_ids, {"chooser.high"})

    # -------------------------------------------------------------------------
    # State Hierarchy and Entry/Exit Action Tests
    # -------------------------------------------------------------------------

    def test_entry_and_exit_actions_fire_in_order(self) -> None:
        """Should fire exit and entry actions in the correct order on transition."""
        call_order = []
        logic = MachineLogic(
            actions={
                "exitA": lambda i, c, e, a: call_order.append("exitA"),
                "enterB": lambda i, c, e, a: call_order.append("enterB"),
            }
        )
        machine = create_machine(
            {
                "id": "lifecyle",
                "initial": "a",
                "states": {
                    "a": {"exit": "exitA", "on": {"NEXT": "b"}},
                    "b": {"entry": "enterB"},
                },
            },
            logic,
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("NEXT")
        self.assertEqual(call_order, ["exitA", "enterB"])

    def test_nested_entry_exit_actions_fire_correctly(self) -> None:
        """Should fire hierarchical entry/exit actions from parent to child."""
        call_order = []
        logic = MachineLogic(
            actions={
                "enterA": lambda i, c, e, a: call_order.append("enterA"),
                "exitA": lambda i, c, e, a: call_order.append("exitA"),
                "enterA1": lambda i, c, e, a: call_order.append("enterA1"),
                "exitA1": lambda i, c, e, a: call_order.append("exitA1"),
                "enterB": lambda i, c, e, a: call_order.append("enterB"),
            }
        )
        machine = create_machine(self.nested_machine_config, logic)
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(call_order, ["enterA", "enterA1"])

        call_order.clear()
        interpreter.send("T1")
        self.assertEqual(
            call_order,
            ["exitA1", "exitA", "enterB"],
            "Exit deep-to-shallow, Enter shallow",
        )

    def test_compound_state_onDone_transition(self) -> None:
        """Should transition via onDone when a child state reaches a final state."""
        machine = create_machine(
            {
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
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertIn("completer.working.step1", interpreter.current_state_ids)
        interpreter.send("NEXT")
        self.assertEqual(interpreter.current_state_ids, {"completer.finished"})

    def test_parallel_state_onDone_transition(self) -> None:
        """Should transition via onDone only when all parallel regions are final."""
        machine = create_machine(
            {
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
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(
            interpreter.current_state_ids,
            {"parallel.active.a.a1", "parallel.active.b.b1"},
        )

        interpreter.send("A_DONE")  # Finish first region
        self.assertNotIn("parallel.finished", interpreter.current_state_ids)

        interpreter.send("B_DONE")  # Finish second region
        self.assertEqual(interpreter.current_state_ids, {"parallel.finished"})

    # -------------------------------------------------------------------------
    # Service Invocation (Invoke) Tests
    # -------------------------------------------------------------------------

    def test_invoke_sync_service_on_entry(self) -> None:
        """Should invoke a synchronous service upon state entry and transition."""
        logic = MachineLogic(
            services={"getUser": lambda i, c, e: {"name": "John Doe"}}
        )
        machine = create_machine(
            {
                "id": "fetcher",
                "initial": "loading",
                "states": {
                    "loading": {
                        "invoke": {"src": "getUser", "onDone": "success"}
                    },
                    "success": {},
                },
            },
            logic,
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"fetcher.success"})

    def test_invoke_sync_service_onError_transition(self) -> None:
        """Should transition via onError when a synchronous service raises an exception."""

        def failing_service(i, c, e):
            raise ValueError("Service failed")

        logic = MachineLogic(services={"badService": failing_service})
        machine = create_machine(
            {
                "id": "fetcher",
                "initial": "loading",
                "states": {
                    "loading": {
                        "invoke": {"src": "badService", "onError": "failure"}
                    },
                    "failure": {},
                },
            },
            logic,
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"fetcher.failure"})

    def test_invoke_service_populates_context_from_event_data(self) -> None:
        """Should update context from the data payload of the done.invoke event."""
        logic = MachineLogic(
            services={
                "getUser": lambda i, c, e: {"name": "Jane Doe", "id": 123}
            },
            actions={"setUser": lambda i, c, e, a: c.update({"user": e.data})},
        )
        machine = create_machine(
            {
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
            },
            logic,
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(
            interpreter.context["user"], {"name": "Jane Doe", "id": 123}
        )

    # -------------------------------------------------------------------------
    # Snapshot & Restore Tests
    # -------------------------------------------------------------------------

    def test_snapshot_and_restore(self) -> None:
        """Should correctly capture and restore the interpreter's state and context."""
        machine = create_machine(
            {
                "id": "snap",
                "initial": "a",
                "context": {"count": 0},
                "states": {
                    "a": {"on": {"NEXT": {"target": "b", "actions": "inc"}}},
                    "b": {},
                },
            },
            logic=MachineLogic(
                actions={"inc": lambda i, c, e, a: c.update({"count": 1})}
            ),
        )
        # Run original interpreter to a specific point
        original_interp = SyncInterpreter(machine).start()
        original_interp.send("NEXT")
        self.assertEqual(original_interp.current_state_ids, {"snap.b"})
        self.assertEqual(original_interp.context["count"], 1)

        # Take snapshot and stop
        snapshot = original_interp.get_snapshot()
        original_interp.stop()

        # Restore from snapshot
        restored_interp = SyncInterpreter.from_snapshot(snapshot, machine)
        self.assertIsInstance(restored_interp, SyncInterpreter)
        self.assertEqual(restored_interp.status, "running")
        self.assertEqual(restored_interp.current_state_ids, {"snap.b"})
        self.assertEqual(restored_interp.context["count"], 1)

    # -------------------------------------------------------------------------
    # Error Handling and Unsupported Feature Tests
    # -------------------------------------------------------------------------

    def test_error_on_unsupported_after_transition(self) -> None:
        """Should raise NotSupportedError if machine uses `after`."""
        machine = create_machine(
            {
                "id": "timer",
                "initial": "active",
                "states": {
                    "active": {"after": {"100": "finished"}},
                    "finished": {},
                },
            }
        )
        with self.assertRaisesRegex(NotSupportedError, "`after` transitions"):
            SyncInterpreter(machine).start()

    def test_error_on_unsupported_async_action(self) -> None:
        """Should raise NotSupportedError if an action is async."""

        async def my_async_action(i, ctx, evt, ad):
            pass

        machine = create_machine(
            {
                "id": "async_test",
                "initial": "idle",
                "states": {"idle": {"entry": ["badAction"]}},
            },
            logic=MachineLogic(actions={"badAction": my_async_action}),
        )
        with self.assertRaisesRegex(NotSupportedError, "is async"):
            SyncInterpreter(machine).start()

    def test_error_on_unsupported_async_service(self) -> None:
        """Should raise NotSupportedError if an invoked service is async."""

        async def my_async_service(i, ctx, evt):
            return {}

        machine = create_machine(
            {
                "id": "async_test",
                "initial": "active",
                "states": {"active": {"invoke": {"src": "badService"}}},
            },
            logic=MachineLogic(services={"badService": my_async_service}),
        )
        with self.assertRaisesRegex(NotSupportedError, "is async"):
            SyncInterpreter(machine).start()

    def test_error_on_unsupported_spawn_action(self) -> None:
        """Should raise NotSupportedError for spawn_ actions."""
        machine = create_machine(
            {
                "id": "spawner",
                "initial": "active",
                "states": {"active": {"entry": ["spawn_something"]}},
            }
        )
        with self.assertRaisesRegex(NotSupportedError, "Actor spawning"):
            SyncInterpreter(machine).start()

    def test_error_on_missing_action_implementation(self) -> None:
        """Should raise ImplementationMissingError for undefined actions."""
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {"a": {"entry": ["no_such_action"]}},
            }
        )
        with self.assertRaises(ImplementationMissingError):
            SyncInterpreter(machine).start()

    def test_error_on_missing_guard_implementation(self) -> None:
        """Should raise ImplementationMissingError for undefined guards."""
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "EVENT": {"target": "a", "guard": "no_such_guard"}
                        }
                    }
                },
            }
        )
        interpreter = SyncInterpreter(machine).start()
        with self.assertRaises(ImplementationMissingError):
            interpreter.send("EVENT")

    def test_error_on_unresolvable_target_state(self) -> None:
        """Should raise StateNotFoundError for an invalid transition target."""
        machine = create_machine(
            {
                "id": "badpath",
                "initial": "a",
                "states": {"a": {"on": {"EVENT": "nonexistent"}}},
            }
        )
        interpreter = SyncInterpreter(machine).start()
        with self.assertRaises(StateNotFoundError):
            interpreter.send("EVENT")

    # -------------------------------------------------------------------------
    # Plugin System Tests
    # -------------------------------------------------------------------------

    def test_plugins_are_called_during_lifecycle(self) -> None:
        """Should call plugin hooks at correct points in the sync lifecycle."""
        mock_plugin = MagicMock(spec=PluginBase)
        machine = create_machine(
            {
                "id": "plug",
                "initial": "a",
                "context": {},
                "states": {
                    "a": {"entry": "doit", "on": {"NEXT": "b"}},
                    "b": {},
                },
            },
            logic=MachineLogic(actions={"doit": lambda i, c, e, a: None}),
        )

        interpreter = SyncInterpreter(machine)
        interpreter.use(mock_plugin)

        # Test start
        interpreter.start()
        mock_plugin.on_interpreter_start.assert_called_once_with(interpreter)
        mock_plugin.on_action_execute.assert_called_once()  # For entry action

        # Test send and transition
        interpreter.send("NEXT")
        mock_plugin.on_event_received.assert_called_once()
        self.assertEqual(mock_plugin.on_transition.call_count, 1)

        # Test stop
        interpreter.stop()
        mock_plugin.on_interpreter_stop.assert_called_once_with(interpreter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
