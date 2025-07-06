# tests/test_interpreter.py
import asyncio
import unittest
from typing import Any, Dict, Set
from unittest.mock import AsyncMock, MagicMock

from src.xstate_machine import Event, Interpreter, MachineLogic, create_machine


# -----------------------------------------------------------------------------
# 🧪 Test Suite for the Interpreter
# -----------------------------------------------------------------------------
# This suite tests the dynamic, runtime behavior of the state machine. It uses
# `unittest.IsolatedAsyncioTestCase` to provide a clean event loop for each
# async test, ensuring that tests do not interfere with one another.
# -----------------------------------------------------------------------------


class TestInterpreter(unittest.IsolatedAsyncioTestCase):
    """Test suite for the Interpreter's runtime execution logic."""

    def setUp(self) -> None:
        """Set up common configs for tests that are used in multiple places.

        This follows the DRY principle by preparing reusable test fixtures.
        """
        # 📝 Define a reusable config for guard-related tests.
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
        """Ensure all spawned tasks are cancelled after each test.

        This is a crucial cleanup step for robust async testing, preventing
        "Task exception was never retrieved" warnings from leaking between tests.
        """
        # 🗑️ Clean up any lingering tasks to prevent test interference.
        tasks = [
            t for t in asyncio.all_tasks() if t is not asyncio.current_task()
        ]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    # -------------------------------------------------------------------------
    # Test Helpers
    # -------------------------------------------------------------------------

    async def wait_for_state(
        self,
        interpreter: Interpreter,
        state_ids: Set[str],
        timeout: float = 2.0,
    ) -> None:
        """Polls the interpreter until it enters one of the desired states.

        This is a robust replacement for `asyncio.sleep()` that prevents race
        conditions in async tests by waiting for a specific condition.

        Args:
            interpreter: The interpreter instance to check.
            state_ids: A set of target state IDs to wait for.
            timeout: The maximum time to wait in seconds.

        Raises:
            AssertionError: If the state is not reached before the timeout.
        """
        start_time = asyncio.get_event_loop().time()
        while True:
            # ✅ Success condition: one of the current states is a target state.
            if not interpreter.current_state_ids.isdisjoint(state_ids):
                return

            # ❌ Timeout condition.
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.fail(
                    f"Timed out waiting for state(s) {state_ids}. "
                    f"Current states: {interpreter.current_state_ids}"
                )

            # ♻️ Yield control to the event loop.
            await asyncio.sleep(0.01)

    # -------------------------------------------------------------------------
    # Basic Transitions, Context, and Guards
    # -------------------------------------------------------------------------

    async def test_simple_transition(self) -> None:
        """Should transition from one state to another on an event."""
        # Ⓐ Arrange: Create a simple state machine.
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

        # 🚀 Act: Send an event to trigger a transition.
        await interpreter.send("TIMER")
        await self.wait_for_state(interpreter, {"light.yellow"})

        # ✅ Assert: The interpreter has moved to the correct new state.
        self.assertEqual(interpreter.current_state_ids, {"light.yellow"})
        await interpreter.stop()

    async def test_context_and_actions(self) -> None:
        """Should execute actions that modify the machine's context."""
        # Ⓐ Arrange: Create a machine with an action and a mock implementation.
        mock_action = MagicMock()
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

        # Define the side effect for the mock action to modify the context.
        def increment_context(interpreter, ctx, evt):
            ctx["count"] += 1

        mock_action.side_effect = increment_context

        # 🚀 Act: Send an event that triggers the action.
        await interpreter.send("INC")
        await asyncio.sleep(
            0.05
        )  # Sleep is fine here as the action is synchronous.

        # ✅ Assert: The action was called and the context was updated.
        mock_action.assert_called_once()
        self.assertEqual(interpreter.context["count"], 1)
        await interpreter.stop()

    async def test_guards(self) -> None:
        """Should block or allow transitions based on guard conditions."""
        # 🧪 Test 1: Guard returns False, transition should be blocked.
        logic_fail = MachineLogic(guards={"canLogin": lambda ctx, evt: False})
        interpreter_fail = await Interpreter(
            create_machine(self.guard_machine_config, logic_fail)
        ).start()

        await interpreter_fail.send("LOGIN")
        await asyncio.sleep(0.05)

        self.assertEqual(interpreter_fail.current_state_ids, {"auth.idle"})
        await interpreter_fail.stop()

        # 🧪 Test 2: Guard returns True, transition should be allowed.
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

    # -------------------------------------------------------------------------
    # Asynchronous Operations
    # -------------------------------------------------------------------------

    async def test_invoke_on_done(self) -> None:
        """Should transition on successful completion of an invoked service."""
        # Ⓐ Arrange: Mock an async service that returns successfully.
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

        # 🚀 Act: Start the interpreter, which will automatically invoke the service.
        interpreter = await Interpreter(machine_def).start()
        await self.wait_for_state(interpreter, {"fetch.success"})

        # ✅ Assert: The service was called and the machine transitioned.
        mock_service.assert_awaited_once()
        self.assertEqual(interpreter.current_state_ids, {"fetch.success"})
        await interpreter.stop()

    async def test_invoke_on_error(self) -> None:
        """Should transition on failure of an invoked service."""
        # Ⓐ Arrange: Mock an async service that raises an exception.
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

        # 🚀 Act: Start the interpreter.
        interpreter = await Interpreter(machine_def).start()
        await self.wait_for_state(interpreter, {"fetch.failure"})

        # ✅ Assert: The service was called and the machine transitioned to the failure state.
        mock_service.assert_awaited_once()
        self.assertEqual(interpreter.current_state_ids, {"fetch.failure"})
        await interpreter.stop()

    async def test_after_delayed_transition(self) -> None:
        """Should transition after the specified delay."""
        # Ⓐ Arrange
        machine_def = create_machine(
            {
                "id": "timeout",
                "initial": "pending",
                "states": {
                    "pending": {"after": {"50": "finished"}},  # 50ms delay
                    "finished": {},
                },
            }
        )
        interpreter = await Interpreter(machine_def).start()

        # 🚀 Act & ✅ Assert: Wait for the machine to reach the 'finished' state.
        await self.wait_for_state(interpreter, {"timeout.finished"})
        self.assertEqual(interpreter.current_state_ids, {"timeout.finished"})
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Actor Model and Snapshotting
    # -------------------------------------------------------------------------

    async def test_spawn_actor_and_communication(self) -> None:
        """Should spawn a child actor and allow parent-child communication."""
        # Ⓐ Arrange: Define a child machine that sends an event back to its parent.
        child_machine = create_machine(
            {
                "id": "child",
                "initial": "active",
                "states": {"active": {"on": {"PING": {"actions": ["pong"]}}}},
            },
            MachineLogic(
                actions={
                    "pong": lambda interpreter, ctx, evt: asyncio.create_task(
                        interpreter.parent.send("PONG_RECEIVED")
                    )
                }
            ),
        )

        # Ⓐ Arrange: Define a parent machine that spawns the child.
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

        # 🚀 Act: Start the parent interpreter.
        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"parent.spawning"})

        # ✅ Assert: Actor was created and is available in the context.
        child_interpreter = next(
            iter(interpreter.context.get("actors", {}).values()), None
        )
        self.assertIsNotNone(
            child_interpreter, "Child actor was not spawned correctly."
        )

        # 🚀 Act: Send an event to the child, which should trigger an event back to the parent.
        await child_interpreter.send("PING")
        await self.wait_for_state(interpreter, {"parent.ponged"})

        # ✅ Assert: The parent machine transitioned after hearing from the child.
        self.assertEqual(interpreter.current_state_ids, {"parent.ponged"})
        await interpreter.stop()

    async def test_snapshot_and_restore(self) -> None:
        """Should correctly capture and restore the interpreter's state."""
        # Ⓐ Arrange: Run a machine to a specific state and context.
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
                    "setData": lambda i, c, e: c.update({"data": "updated"})
                }
            ),
        )

        interpreter = await Interpreter(machine_def).start()
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"snap.second"})

        # 🚀 Act: Get snapshot and restore to a new interpreter.
        snapshot = interpreter.get_snapshot()
        await interpreter.stop()
        restored_interpreter = Interpreter.from_snapshot(snapshot, machine_def)

        # ✅ Assert: Restored state and context are correct.
        self.assertEqual(
            restored_interpreter.current_state_ids, {"snap.second"}
        )
        self.assertEqual(restored_interpreter.context["data"], "updated")
