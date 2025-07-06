# tests/test_interpreter.py
import asyncio
import unittest
from typing import Any, Dict, Set
from unittest.mock import AsyncMock, MagicMock

from src.xstate_machine import (
    Interpreter,
    create_machine,
    MachineLogic,
    ImplementationMissingError,
    ActorSpawningError,
)


class TestInterpreter(unittest.IsolatedAsyncioTestCase):
    """Test suite for the Interpreter's runtime execution logic."""

    def setUp(self) -> None:
        """Set up common configs for tests that are used in multiple places."""
        self.guard_machine_config: Dict[str, Any] = {
            "id": "auth",
            "initial": "idle",
            "context": {"retries": 0},
            "states": {
                "idle": {
                    "on": {"LOGIN": {"target": "success", "guard": "canLogin"}}
                },
                "success": {},
            },
        }

    async def asyncTearDown(self) -> None:
        """Ensure all spawned tasks are cancelled after each test."""
        tasks = [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task()
        ]
        if tasks:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    async def wait_for_state(
        self,
        interpreter: Interpreter,
        state_ids: Set[str],
        timeout: float = 2.0,
    ) -> None:
        """Polls the interpreter until it enters one of the desired states."""
        start_time = asyncio.get_event_loop().time()
        while True:
            if not interpreter.current_state_ids.isdisjoint(state_ids):
                return
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.fail(
                    f"Timed out waiting for state(s) {state_ids}. "
                    f"Current states: {interpreter.current_state_ids}"
                )
            await asyncio.sleep(0.01)

    # ... [Keep existing tests: test_simple_transition, test_context_and_actions, test_guards] ...
    async def test_simple_transition(self) -> None:
        """Should transition from one state to another on an event."""
        machine_def = create_machine(
            {
                "id": "light",
                "initial": "green",
                "states": {
                    "green": {"on": {"TIMER": "yellow"}},
                    "yellow": {"on": {"TIMER": "red"}},
                    "red": {},
                },
            }
        )
        interpreter = await Interpreter(machine_def).start()
        self.assertEqual(interpreter.current_state_ids, {"light.green"})
        await interpreter.send("TIMER")
        await self.wait_for_state(interpreter, {"light.yellow"})
        self.assertEqual(interpreter.current_state_ids, {"light.yellow"})
        await interpreter.stop()

    async def test_context_and_actions(self) -> None:
        """Should execute actions that modify the machine's context."""
        mock_action = MagicMock()

        def increment_context(i, c, e, a):
            c["count"] += 1

        mock_action.side_effect = increment_context
        machine_def = create_machine(
            {
                "id": "counter",
                "initial": "active",
                "context": {"count": 0},
                "states": {
                    "active": {"on": {"INC": {"actions": ["increment"]}}}
                },
            },
            MachineLogic(actions={"increment": mock_action}),
        )
        interpreter = await Interpreter(machine_def).start()
        await interpreter.send("INC")
        await asyncio.sleep(0.05)
        mock_action.assert_called_once()
        self.assertEqual(interpreter.context["count"], 1)
        await interpreter.stop()

    async def test_guards(self) -> None:
        """Should block or allow transitions based on guard conditions."""
        logic_fail = MachineLogic(guards={"canLogin": lambda ctx, evt: False})
        interpreter_fail = await Interpreter(
            create_machine(self.guard_machine_config, logic_fail)
        ).start()
        await interpreter_fail.send("LOGIN")
        await asyncio.sleep(0.05)
        self.assertEqual(interpreter_fail.current_state_ids, {"auth.idle"})
        await interpreter_fail.stop()
        logic_success = MachineLogic(
            guards={"canLogin": lambda ctx, evt: True}
        )
        interpreter_success = await Interpreter(
            create_machine(self.guard_machine_config, logic_success)
        ).start()
        await interpreter_success.send("LOGIN")
        await self.wait_for_state(interpreter_success, {"auth.success"})
        self.assertEqual(
            interpreter_success.current_state_ids, {"auth.success"}
        )
        await interpreter_success.stop()

    async def test_invoke_on_done(self) -> None:
        """Should transition on successful completion of an invoked service."""
        mock_service = AsyncMock(return_value={"user": "Alice"})
        machine_def = create_machine(
            {
                "id": "fetch",
                "initial": "loading",
                "states": {
                    "loading": {
                        "invoke": {"src": "fetchUser", "onDone": "success"}
                    },
                    "success": {},
                },
            },
            MachineLogic(services={"fetchUser": mock_service}),
        )
        interpreter = await Interpreter(machine_def).start()
        await self.wait_for_state(interpreter, {"fetch.success"})
        mock_service.assert_awaited_once()
        self.assertEqual(interpreter.current_state_ids, {"fetch.success"})
        await interpreter.stop()

    async def test_invoke_on_error(self) -> None:
        """Should transition on failure of an invoked service."""
        mock_service = AsyncMock(side_effect=ValueError("API Error"))
        machine_def = create_machine(
            {
                "id": "fetch",
                "initial": "loading",
                "states": {
                    "loading": {
                        "invoke": {"src": "fetchUser", "onError": "failure"}
                    },
                    "failure": {},
                },
            },
            MachineLogic(services={"fetchUser": mock_service}),
        )
        interpreter = await Interpreter(machine_def).start()
        await self.wait_for_state(interpreter, {"fetch.failure"})
        mock_service.assert_awaited_once()
        self.assertEqual(interpreter.current_state_ids, {"fetch.failure"})
        await interpreter.stop()

    async def test_after_delayed_transition(self) -> None:
        """Should transition after the specified delay."""
        machine_def = create_machine(
            {
                "id": "timeout",
                "initial": "pending",
                "states": {
                    "pending": {"after": {"50": "finished"}},
                    "finished": {},
                },
            }
        )
        interpreter = await Interpreter(machine_def).start()
        await self.wait_for_state(interpreter, {"timeout.finished"})
        self.assertEqual(interpreter.current_state_ids, {"timeout.finished"})
        await interpreter.stop()

    async def test_spawn_actor_and_communication(self) -> None:
        """Should spawn a child actor and allow parent-child communication."""
        child_machine = create_machine(
            {
                "id": "child",
                "initial": "active",
                "states": {"active": {"on": {"PING": {"actions": ["pong"]}}}},
            },
            MachineLogic(
                actions={
                    "pong": lambda i, c, e, a: asyncio.create_task(
                        i.parent.send("PONG_RECEIVED")
                    )
                }
            ),
        )
        parent_logic = MachineLogic(services={"childLogic": child_machine})
        parent_machine = create_machine(
            {
                "id": "parent",
                "initial": "spawning",
                "context": {},
                "states": {
                    "spawning": {"entry": ["spawn_childLogic"]},
                    "ponged": {},
                },
                "on": {"PONG_RECEIVED": ".ponged"},
            },
            parent_logic,
        )
        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"parent.spawning"})
        child_interpreter = next(
            iter(interpreter.context.get("actors", {}).values()), None
        )
        self.assertIsNotNone(child_interpreter)
        await child_interpreter.send("PING")
        await self.wait_for_state(interpreter, {"parent.ponged"})
        self.assertEqual(interpreter.current_state_ids, {"parent.ponged"})
        await interpreter.stop()

    async def test_snapshot_and_restore(self) -> None:
        """Should correctly capture and restore the interpreter's state."""
        machine_def = create_machine(
            {
                "id": "snap",
                "initial": "first",
                "context": {"data": "initial"},
                "states": {
                    "first": {
                        "on": {
                            "NEXT": {
                                "target": "second",
                                "actions": ["setData"],
                            }
                        }
                    },
                    "second": {},
                },
            },
            MachineLogic(
                actions={
                    "setData": lambda i, c, e, ad: c.update(
                        {"data": "updated"}
                    )
                }
            ),
        )
        interpreter = await Interpreter(machine_def).start()
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"snap.second"})
        snapshot = interpreter.get_snapshot()
        await interpreter.stop()
        restored_interpreter = Interpreter.from_snapshot(snapshot, machine_def)
        self.assertEqual(
            restored_interpreter.current_state_ids, {"snap.second"}
        )
        self.assertEqual(restored_interpreter.context["data"], "updated")

    # --- NEW AND EXTENDED TESTS ---

    async def test_internal_transition_without_target(self) -> None:
        """Should execute actions on a transition without a target and not change state."""
        mock_action = MagicMock()
        machine = create_machine(
            {
                "id": "internal",
                "initial": "active",
                "states": {
                    "active": {"on": {"EVENT": {"actions": "doSomething"}}}
                },
            },
            MachineLogic(actions={"doSomething": mock_action}),
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})
        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)
        # State should not have changed
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})
        mock_action.assert_called_once()
        await interpreter.stop()

    async def test_multiple_actions_on_transition(self) -> None:
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
            MachineLogic(actions={"action1": action1, "action2": action2}),
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)
        action1.assert_called_once()
        action2.assert_called_once()
        await interpreter.stop()

    async def test_entry_and_exit_actions(self) -> None:
        """Should execute entry and exit actions when changing states."""
        entry_action = MagicMock()
        exit_action = MagicMock()
        machine = create_machine(
            {
                "id": "entryExit",
                "initial": "a",
                "states": {
                    "a": {"on": {"NEXT": "b"}, "exit": "onExitA"},
                    "b": {"entry": "onEnterB"},
                },
            },
            MachineLogic(
                actions={"onEnterB": entry_action, "onExitA": exit_action}
            ),
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"entryExit.b"})
        entry_action.assert_called_once()
        exit_action.assert_called_once()
        await interpreter.stop()

    async def test_parallel_state_onDone(self) -> None:
        """onDone transition on a parallel state should fire only when all regions are done."""
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
        interpreter = await Interpreter(machine).start()
        await interpreter.send("A_DONE")
        await self.wait_for_state(interpreter, {"parallel.active.a.a2"})
        # Should NOT be finished yet
        self.assertNotEqual(
            interpreter.current_state_ids, {"parallel.finished"}
        )
        self.assertIn("parallel.active.b.b1", interpreter.current_state_ids)

        # Now finish the second region
        await interpreter.send("B_DONE")
        await self.wait_for_state(interpreter, {"parallel.finished"})
        self.assertEqual(interpreter.current_state_ids, {"parallel.finished"})
        await interpreter.stop()

    async def test_deeply_nested_transition(self) -> None:
        """Should correctly transition out of and into deeply nested states."""
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
                                "states": {
                                    "a11": {"on": {"NEXT": "b.b1.b11"}}
                                },
                            }
                        },
                    },
                    "b": {
                        "initial": "b1",
                        "states": {
                            "b1": {"initial": "b11", "states": {"b11": {}}}
                        },
                    },
                },
            }
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"deep.a.a1.a11"})
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"deep.b.b1.b11"})
        self.assertEqual(interpreter.current_state_ids, {"deep.b.b1.b11"})
        await interpreter.stop()

    async def test_event_payload_is_passed_to_actions_and_guards(self) -> None:
        """Event payloads should be accessible in actions and guards."""
        mock_action = MagicMock()
        mock_guard = MagicMock(return_value=True)

        machine = create_machine(
            {
                "id": "payload",
                "initial": "idle",
                "states": {
                    "idle": {
                        "on": {
                            "EVENT": {
                                "actions": ["myAction"],
                                "guard": "myGuard",
                            }
                        }
                    },
                },
            },
            MachineLogic(
                actions={"myAction": mock_action},
                guards={"myGuard": mock_guard},
            ),
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("EVENT", value=42, user="test")
        await asyncio.sleep(0.01)

        mock_guard.assert_called_once()
        guard_args = mock_guard.call_args[0]
        self.assertEqual(guard_args[1].type, "EVENT")
        self.assertEqual(guard_args[1].payload, {"value": 42, "user": "test"})

        mock_action.assert_called_once()
        action_args = mock_action.call_args[0]
        self.assertEqual(action_args[2].type, "EVENT")
        self.assertEqual(action_args[2].payload, {"value": 42, "user": "test"})

        await interpreter.stop()

    async def test_raises_error_for_missing_guard_implementation(self) -> None:
        """Should raise ImplementationMissingError if a guard is not defined."""
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {"a": {"on": {"EVENT": {"guard": "nonexistent"}}}},
            },
            MachineLogic(),  # Empty logic
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("EVENT")

        # Give the event loop time to process the event and the task to fail
        await asyncio.sleep(0.01)

        # The exception is now stored in the background event loop task.
        # We access the task and check its result to trigger the exception.
        event_loop_task = interpreter._event_loop_task
        self.assertTrue(
            event_loop_task.done(),
            "Event loop task should have finished due to error.",
        )
        with self.assertRaises(ImplementationMissingError):
            event_loop_task.result()  # This re-raises the exception from the task

        # Stop is a no-op if already stopped/crashed, but good practice
        await interpreter.stop()

    async def test_raises_error_for_missing_service_implementation(
        self,
    ) -> None:
        """Should raise ImplementationMissingError if an invoked service is not defined."""
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {"a": {"invoke": {"src": "nonexistent"}}},
            },
            MachineLogic(),  # Empty logic
        )
        with self.assertRaises(ImplementationMissingError):
            await Interpreter(machine).start()
        # No stop needed as start() will fail.

    async def test_spawn_actor_fails_for_non_machine_service(self) -> None:
        """Should raise ActorSpawningError if the service is not a MachineNode."""
        machine = create_machine(
            {
                "id": "spawner",
                "initial": "active",
                "states": {"active": {"entry": "spawn_badActor"}},
            },
            MachineLogic(
                services={"badActor": lambda i, c, e: "I am not a machine"}
            ),
        )
        with self.assertRaises(ActorSpawningError):
            await Interpreter(machine).start()

    async def test_sending_invalid_event_type(self) -> None:
        """Should raise TypeError when sending an unsupported event type."""
        interpreter = await Interpreter(
            create_machine({"id": "a", "initial": "b", "states": {"b": {}}})
        ).start()
        with self.assertRaises(TypeError):
            await interpreter.send(123)
        await interpreter.stop()
