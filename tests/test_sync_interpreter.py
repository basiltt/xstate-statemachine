# tests/test_sync_interpreter.py
import json

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
from typing import Any, Dict
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
    InvalidConfigError,
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

    def test_event_payload_is_passed_to_actions(self) -> None:
        """Should pass the event payload correctly to actions."""
        mock_action = MagicMock()
        machine = create_machine(
            {
                "id": "payload_test",
                "initial": "idle",
                "states": {"idle": {"on": {"DATA": {"actions": "process"}}}},
            },
            logic=MachineLogic(actions={"process": mock_action}),
        )
        interpreter = SyncInterpreter(machine).start()
        payload = {"user": "test", "id": 123}
        interpreter.send("DATA", **payload)
        self.assertEqual(mock_action.call_args[0][2].payload, payload)

    def test_reentrant_send_from_action_is_queued(self) -> None:
        """Should queue events sent from within an action, not process immediately."""
        call_order = []

        def action_sends_event(interpreter, ctx, evt, ad):
            call_order.append("action_A")
            interpreter.send("EVENT_B")
            call_order.append("action_A_finished")

        def action_for_b(interpreter, ctx, evt, ad):
            call_order.append("action_B")

        machine = create_machine(
            {
                "id": "reentrant",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "EVENT_A": {"target": "b", "actions": "actionA"}
                        }
                    },
                    "b": {"on": {"EVENT_B": {"target": "c"}}},
                    "c": {"entry": "actionB"},
                },
            },
            logic=MachineLogic(
                actions={
                    "actionA": action_sends_event,
                    "actionB": action_for_b,
                }
            ),
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("EVENT_A")
        self.assertEqual(
            call_order, ["action_A", "action_A_finished", "action_B"]
        )
        self.assertEqual(interpreter.current_state_ids, {"reentrant.c"})

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
            logic=logic,
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
            logic=logic,
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

    def test_eventless_transition_is_taken_immediately(self) -> None:
        """Should take an event-less ("always") transition upon state entry."""
        machine = create_machine(
            {
                "id": "transient",
                "initial": "a",
                "states": {
                    "a": {"on": {"NEXT": "b"}},
                    "b": {"on": {"": {"target": "c"}}},
                    "c": {},
                },
            }
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("NEXT")
        self.assertEqual(interpreter.current_state_ids, {"transient.c"})

    def test_guarded_eventless_transitions(self) -> None:
        """Should choose the correct guarded event-less transition."""
        machine = create_machine(
            {
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
            },
            logic=MachineLogic(
                guards={"isOk": lambda c, e: c["status"] == "ok"}
            ),
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("CHECK")
        self.assertEqual(
            interpreter.current_state_ids, {"transient_guarded.success"}
        )
        interpreter.stop()
        interpreter = SyncInterpreter(machine).start()
        interpreter.context["status"] = "error"
        interpreter.send("CHECK")
        self.assertEqual(
            interpreter.current_state_ids, {"transient_guarded.failure"}
        )

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
            logic=logic,
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
        machine = create_machine(self.nested_machine_config, logic=logic)
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(call_order, ["enterA", "enterA1"])
        call_order.clear()
        interpreter.send("T1")
        self.assertEqual(call_order, ["exitA1", "exitA", "enterB"])

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
        interpreter.send("A_DONE")
        self.assertNotIn("parallel.finished", interpreter.current_state_ids)
        interpreter.send("B_DONE")
        self.assertEqual(interpreter.current_state_ids, {"parallel.finished"})

    def test_transition_from_nested_state_to_ancestor_sibling(self) -> None:
        """Should correctly exit nested states to transition to a sibling of an ancestor."""
        machine = create_machine(
            {
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
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("GOTO_B")
        self.assertEqual(interpreter.current_state_ids, {"deep.b"})

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
            logic=logic,
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
            logic=logic,
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
            logic=logic,
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(
            interpreter.context["user"], {"name": "Jane Doe", "id": 123}
        )

    def test_invoke_sync_service_that_returns_none(self) -> None:
        """Should handle services that return None without error."""
        action = MagicMock()
        logic = MachineLogic(
            services={"fireAndForget": lambda i, c, e: None},
            actions={"logDone": action},
        )
        machine = create_machine(
            {
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
            },
            logic=logic,
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"none_service.done"})
        self.assertIsNone(action.call_args[0][2].data)

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
        original_interp = SyncInterpreter(machine).start()
        original_interp.send("NEXT")

        snapshot = original_interp.get_snapshot()
        original_interp.stop()

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

        async def my_async_action(i, c, e, a):
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

        async def my_async_service(i, c, e):
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
        """Should raise NotSupportedError when SyncInterpreter tries to spawn."""
        machine = create_machine(
            {
                "id": "spawner",
                "initial": "active",
                "states": {"active": {"entry": "spawn_something"}},
            },
            logic=MachineLogic(
                services={
                    "something": create_machine(
                        {"id": "child", "initial": "a", "states": {"a": {}}}
                    )
                }
            ),
        )
        interpreter = SyncInterpreter(machine)
        with self.assertRaisesRegex(
            NotSupportedError, "Actor spawning is not supported"
        ):
            interpreter.start()

    def test_error_on_missing_action_implementation(self) -> None:
        """Should raise ImplementationMissingError for undefined actions."""
        with self.assertRaises(ImplementationMissingError):
            create_machine(
                {
                    "id": "missing",
                    "initial": "a",
                    "states": {"a": {"entry": ["no_such_action"]}},
                }
            )

    def test_error_on_missing_guard_implementation(self) -> None:
        """Should raise ImplementationMissingError for undefined guards."""
        with self.assertRaises(ImplementationMissingError):
            create_machine(
                {
                    "id": "missing",
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "EVENT": {
                                    "target": "a",
                                    "guard": "no_such_guard",
                                }
                            }
                        }
                    },
                }
            )

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
        interpreter.start()

        mock_plugin.on_interpreter_start.assert_called_once_with(interpreter)
        mock_plugin.on_action_execute.assert_called_once()

        interpreter.send("NEXT")
        mock_plugin.on_event_received.assert_called_once()
        self.assertEqual(mock_plugin.on_transition.call_count, 2)

        interpreter.stop()
        mock_plugin.on_interpreter_stop.assert_called_once_with(interpreter)

    # -------------------------------------------------------------------------
    # Corrected and New Tests from Previous Iteration
    # -------------------------------------------------------------------------

    def test_context_is_copied_not_referenced(self) -> None:
        """Should perform a deep copy of the initial context."""
        config = {
            "id": "m",
            "initial": "s1",
            "context": {"data": {"nested": "value"}},
            "states": {"s1": {}},
        }
        machine = create_machine(config)
        interpreter = SyncInterpreter(machine).start()
        interpreter.context["data"]["nested"] = "changed"
        self.assertEqual(config["context"]["data"]["nested"], "value")

    def test_deeply_nested_parallel_state_on_done(self) -> None:
        """Should correctly fire onDone from a deeply nested parallel state."""
        machine = create_machine(
            {
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
        )
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"m.s2"})

    def test_guard_receives_context_and_event_payload_correctly(self) -> None:
        """Should pass event payload correctly to guards."""
        guard = MagicMock(return_value=True)
        machine = create_machine(
            {
                "id": "m",
                "initial": "s1",
                "context": {"x": 1},
                "states": {"s1": {"on": {"E": {"guard": "myGuard"}}}},
            },
            logic=MachineLogic(guards={"myGuard": guard}),
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("E", y=2)
        guard.assert_called_once()
        self.assertEqual(guard.call_args[0][0]["x"], 1)
        self.assertEqual(guard.call_args[0][1].payload, {"y": 2})

    def test_invalid_config_shorthand_transition_raises_error(self) -> None:
        """Should raise InvalidConfigError for malformed transition shorthand."""
        with self.assertRaisesRegex(
            InvalidConfigError, "Invalid transition config"
        ):
            create_machine(
                {
                    "id": "m",
                    "initial": "s1",
                    "states": {"s1": {"on": {"E": 123}}},
                }
            )

    def test_internal_transition_fires_on_transition_hook(self) -> None:
        """Should fire the on_transition hook for internal transitions."""
        mock_plugin = MagicMock(spec=PluginBase)
        machine = create_machine(
            {
                "id": "m",
                "initial": "s1",
                "states": {"s1": {"on": {"NOOP": {}}}},
            }
        )
        interpreter = SyncInterpreter(machine).use(mock_plugin).start()
        interpreter.send("NOOP")
        self.assertEqual(mock_plugin.on_transition.call_count, 2)

    def test_unhandled_event_does_not_fire_on_transition_hook(self) -> None:
        """Should NOT fire the on_transition hook for an unhandled event."""
        mock_plugin = MagicMock(spec=PluginBase)
        machine = create_machine(
            {
                "id": "m",
                "initial": "s1",
                "states": {"s1": {"on": {"REAL_EVENT": {}}}},
            }
        )
        interpreter = SyncInterpreter(machine).use(mock_plugin).start()
        interpreter.send("UNHANDLED_EVENT")
        mock_plugin.on_transition.assert_called_once()

    def test_restore_from_snapshot_with_missing_state_id_raises_error(
        self,
    ) -> None:
        """Should raise StateNotFoundError when a snapshot state is not in the machine."""
        machine = create_machine(
            {"id": "m", "initial": "s1", "states": {"s1": {}}}
        )
        snapshot = '{"status": "running", "context": {}, "state_ids": ["m.nonexistent"]}'

        # ✅ FIX: Updated the regular expression to match the new, more
        # precise error message produced by the exception.
        with self.assertRaisesRegex(
            StateNotFoundError,
            "Could not find state with ID 'm.nonexistent'",
        ):
            SyncInterpreter.from_snapshot(snapshot, machine)

    def test_invoke_service_with_no_on_done_handler(self) -> None:
        """A service invocation without an onDone handler should complete without error."""
        logic = MachineLogic(services={"doNothing": lambda i, c, e: "data"})
        machine = create_machine(
            {
                "id": "m",
                "initial": "working",
                "states": {"working": {"invoke": {"src": "doNothing"}}},
            },
            logic=logic,
        )
        # The machine should start and simply remain in the 'working' state.
        interpreter = SyncInterpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"m.working"})

    def test_transition_with_multiple_actions_in_list(self) -> None:
        """Should execute a sequence of actions defined in a list."""
        call_order = []
        logic = MachineLogic(
            actions={
                "action1": lambda i, c, e, a: call_order.append(1),
                "action2": lambda i, c, e, a: call_order.append(2),
            }
        )
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "E": {
                                "target": "b",
                                "actions": ["action1", "action2"],
                            }
                        }
                    },
                    "b": {},
                },
            },
            logic=logic,
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("E")
        self.assertEqual(call_order, [1, 2])

    def test_complex_nested_entry_actions(self) -> None:
        """Should fire entry actions from the outermost to innermost state."""
        call_order = []
        logic = MachineLogic(
            actions={
                "enterA": lambda i, c, e, a: call_order.append("A"),
                "enterB": lambda i, c, e, a: call_order.append("B"),
                "enterC": lambda i, c, e, a: call_order.append("C"),
            }
        )
        machine = create_machine(
            {
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
            },
            logic=logic,
        )
        SyncInterpreter(machine).start()
        self.assertEqual(call_order, ["A", "B", "C"])

    def test_complex_nested_exit_actions(self) -> None:
        """Should fire exit actions from the innermost to outermost state."""
        call_order = []
        logic = MachineLogic(
            actions={
                "exitA": lambda i, c, e, a: call_order.append("A"),
                "exitB": lambda i, c, e, a: call_order.append("B"),
                "exitC": lambda i, c, e, a: call_order.append("C"),
            }
        )
        machine = create_machine(
            {
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
            },
            logic=logic,
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("FINISH")
        self.assertEqual(call_order, ["C", "B", "A"])

    def test_transition_with_unhandled_event(self) -> None:
        """Should remain in the same state if an event is unhandled."""
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"REAL_EVENT": "b"}}, "b": {}},
            }
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("FAKE_EVENT")
        self.assertEqual(interpreter.current_state_ids, {"m.a"})

    def test_self_transition_on_state(self) -> None:
        """An external self-transition should re-execute entry/exit actions."""
        exit_action = MagicMock()
        entry_action = MagicMock()
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {"LOOP": ".a"},
                        "entry": "onEnter",
                        "exit": "onExit",
                    }
                },
            },
            logic=MachineLogic(
                actions={"onEnter": entry_action, "onExit": exit_action}
            ),
        )

        interpreter = SyncInterpreter(machine).start()
        entry_action.assert_called_once()
        exit_action.assert_not_called()

        interpreter.send("LOOP")
        self.assertEqual(entry_action.call_count, 2)
        self.assertEqual(exit_action.call_count, 1)

    def test_start_on_already_started_interpreter(self) -> None:
        """Calling start() on a running SyncInterpreter should be a no-op."""
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        interpreter = SyncInterpreter(machine).start()
        # To verify it's a no-op, we can check that a plugin hook isn't called again.
        mock_plugin = MagicMock(spec=PluginBase)
        interpreter.use(mock_plugin)
        interpreter.start()  # Second call
        mock_plugin.on_interpreter_start.assert_not_called()

    def test_stop_on_already_stopped_interpreter(self) -> None:
        """Calling stop() on a stopped SyncInterpreter should be a no-op."""
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.stop()

        mock_plugin = MagicMock(spec=PluginBase)
        interpreter.use(mock_plugin)
        interpreter.stop()  # Second call
        mock_plugin.on_interpreter_stop.assert_not_called()

    def test_snapshot_of_parallel_state(self) -> None:
        """Should correctly snapshot a machine in a parallel state."""
        machine = create_machine(
            {
                "id": "p",
                "type": "parallel",
                "states": {
                    "a": {"initial": "a1", "states": {"a1": {}}},
                    "b": {"initial": "b1", "states": {"b1": {}}},
                },
            }
        )
        interpreter = SyncInterpreter(machine).start()
        snapshot_str = interpreter.get_snapshot()
        snapshot = json.loads(snapshot_str)
        self.assertEqual(set(snapshot["state_ids"]), {"p.a.a1", "p.b.b1"})

    def test_final_state_in_parallel_machine_triggers_onDone(self) -> None:
        """A final state in one parallel region should NOT trigger onDone alone."""
        machine = create_machine(
            {
                "id": "p_final",
                "type": "parallel",
                "onDone": "finished",
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
        )
        interpreter = SyncInterpreter(machine).start()
        interpreter.send("FINISH_A")
        # Still in the parallel state because region 'b' is not done
        self.assertEqual(
            interpreter.current_state_ids, {"p_final.a.a2", "p_final.b.b1"}
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
