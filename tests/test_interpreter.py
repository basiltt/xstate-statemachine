"""
tests/test_interpreter.py
-------------------------
Refactored test suite for the XState Interpreter's runtime execution logic.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import unittest
from typing import Any, Dict, Set

from unittest.mock import AsyncMock, MagicMock

from src.xstate_machine import (
    Interpreter,
    create_machine,
    MachineLogic,
    ImplementationMissingError,
    ActorSpawningError,
    Event,  # 📝 Import Event for type hinting
)

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# To enable console output, uncomment the following:
# handler = logging.StreamHandler()
# handler.setLevel(logging.INFO)
# handler.setFormatter(
#     logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
# )
# logger.addHandler(handler)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
async def cancel_all_tasks() -> None:
    """
    Cancel all running asyncio tasks except the current one.

    This helper is crucial for ensuring a clean slate between asynchronous tests,
    preventing "leaked" tasks from affecting subsequent tests or keeping the
    event loop alive unexpectedly.

    Args:
        None

    Returns:
        None
    """
    current = asyncio.current_task()
    # 📝 Get all tasks, excluding the current one
    tasks = [t for t in asyncio.all_tasks() if t is not current]
    if tasks:
        logger.info("🔄 Cancelling %d leftover task(s)...", len(tasks))
        # ⚠️ Cancel all tasks and gather their results (including exceptions from cancellation)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✅ All leftover tasks cancelled.")


# -----------------------------------------------------------------------------
# Test Class
# -----------------------------------------------------------------------------
class TestInterpreter(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the Interpreter's runtime execution logic.

    Covers basic transitions, context/actions, guards, service invocation,
    delays, actor spawning, snapshots, and error scenarios. Each test method
    is asynchronous and leverages the `IsolatedAsyncioTestCase` for proper
    async event loop management.
    """

    # Type hints for instance variables
    guard_machine_config: Dict[str, Any]

    def setUp(self) -> None:
        """
        Set up common configurations for guard-related tests.

        Initializes a machine definition with a guard condition that can be
        manipulated by `MachineLogic` for testing different guard behaviors.

        Args:
            None

        Returns:
            None
        """
        logger.info("🚀 Setting up guard machine configuration...")
        self.guard_machine_config = {
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
        """
        Tear down by cancelling any remaining asyncio tasks.

        This method is called after each asynchronous test, ensuring that
        any background tasks started by the interpreter are properly
        cleaned up to prevent interference with subsequent tests.

        Args:
            None

        Returns:
            None
        """
        logger.info("🧹 Performing async teardown...")
        await cancel_all_tasks()
        logger.info("✅ Async teardown complete.")

    async def wait_for_state(
        self,
        interpreter: Interpreter,
        state_ids: Set[str],
        timeout: float = 2.0,
    ) -> None:
        """
        Polls the interpreter until it enters one of the desired states.

        This utility function simplifies waiting for asynchronous state
        transitions in tests, preventing race conditions and providing
        a clear timeout mechanism.

        Args:
            interpreter (Interpreter): The interpreter instance under test.
            state_ids (Set[str]): A set of fully qualified target state IDs to wait for.
            timeout (float): The maximum time in seconds to wait before failing.

        Raises:
            AssertionError: If the interpreter does not reach any of the target states
                            within the specified timeout.

        Returns:
            None
        """
        logger.info(
            "🔍 Waiting for state(s) %s with timeout %.2fs", state_ids, timeout
        )
        loop = asyncio.get_event_loop()
        start = loop.time()
        while True:
            # ✅ Check if the current state IDs intersect with the desired state IDs
            if not interpreter.current_state_ids.isdisjoint(state_ids):
                logger.info(
                    "✅ Interpreter entered state(s) %s",
                    interpreter.current_state_ids,
                )
                return
            # ⏰ Check for timeout
            if loop.time() - start > timeout:
                logger.error(
                    "❌ Timed out waiting for %s. Current states: %s",
                    state_ids,
                    interpreter.current_state_ids,
                )
                self.fail(
                    f"⏰ Timed out waiting for {state_ids}, "
                    f"current: {interpreter.current_state_ids}"
                )
            await asyncio.sleep(0.01)  # ⏳ Yield control to event loop

    # -----------------------------------------------------------------------------
    # Tests: Simple Transitions
    # -----------------------------------------------------------------------------
    async def test_simple_transition(self) -> None:
        """
        Should transition from one state to another on an event.

        Verifies the fundamental behavior of state changes in response to events.
        """
        logger.info("🚀 Testing simple transition...")
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
        # 🏗️ Create and start the interpreter
        interpreter = await Interpreter(machine_def).start()
        # 🚧 Ensure we start in the initial state
        self.assertEqual(
            interpreter.current_state_ids,
            {"light.green"},
            "Interpreter should start in 'green' state",
        )
        logger.debug("Current state: %s", interpreter.current_state_ids)

        await interpreter.send("TIMER")  # 📝 Send the transition event
        await self.wait_for_state(interpreter, {"light.yellow"})
        # ✅ Verify new state
        self.assertEqual(
            interpreter.current_state_ids,
            {"light.yellow"},
            "Interpreter should transition to 'yellow' state",
        )
        logger.debug(
            "Transitioned to state: %s", interpreter.current_state_ids
        )
        await interpreter.stop()  # 🛑 Stop the interpreter

    # -----------------------------------------------------------------------------
    # Tests: Context and Actions
    # -----------------------------------------------------------------------------
    async def test_context_and_actions(self) -> None:
        """
        Should execute actions that modify the machine's context.

        Validates that side-effect actions are invoked and correctly update
        the interpreter's context data.
        """
        logger.info("🚀 Testing context mutation via actions...")
        mock_action = MagicMock()

        # Define an action function that modifies context
        def increment_context(
            interp: Interpreter,
            context: Dict[str, Any],
            event: Event,
            action_def: Any,
        ) -> None:
            """Increments the 'count' in the machine's context."""
            context["count"] += 1  # 🧪 Mutate context

        mock_action.side_effect = increment_context
        machine_def = create_machine(
            {
                "id": "counter",
                "initial": "active",
                "context": {"count": 0},  # Initial context
                "states": {
                    "active": {"on": {"INC": {"actions": ["increment"]}}}
                },
            },
            MachineLogic(
                actions={"increment": mock_action}
            ),  # Map action name to implementation
        )
        interpreter = await Interpreter(machine_def).start()
        self.assertEqual(
            interpreter.context["count"], 0, "Initial count should be 0"
        )

        await interpreter.send("INC")  # 📝 Send event to trigger action
        await asyncio.sleep(0.05)  # ⏳ Allow action to run asynchronously

        # ✅ Verify the action was called and context updated
        mock_action.assert_called_once()  # Assert action function was invoked
        self.assertEqual(
            interpreter.context["count"], 1, "Count should be incremented to 1"
        )
        logger.debug(
            "Context 'count' after action: %d", interpreter.context["count"]
        )
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Guards
    # -----------------------------------------------------------------------------
    async def test_guards(self) -> None:
        """
        Should block or allow transitions based on guard conditions.

        Verifies both scenarios: when a guard fails (transition blocked) and
        when a guard passes (transition allowed).
        """
        logger.info("🚀 Testing guard functionality...")

        # --- Scenario 1: Guard Fails (transition blocked) ---
        logger.info(
            "   Testing guard failing scenario: 'canLogin' returns False"
        )
        # Define MachineLogic where 'canLogin' guard always returns False
        logic_fail = MachineLogic(guards={"canLogin": lambda ctx, evt: False})
        interp_fail = await Interpreter(
            create_machine(self.guard_machine_config, logic_fail)
        ).start()
        self.assertEqual(
            interp_fail.current_state_ids,
            {"auth.idle"},
            "Interpreter should start in 'idle'",
        )

        await interp_fail.send("LOGIN")  # 📝 Send event
        await asyncio.sleep(0.05)  # ⏳ Allow guard evaluation
        self.assertEqual(
            interp_fail.current_state_ids,
            {"auth.idle"},
            "State should remain 'idle' because guard failed",
        )
        logger.debug("State remained 'idle' as expected when guard failed.")
        await interp_fail.stop()

        # --- Scenario 2: Guard Passes (transition allowed) ---
        logger.info(
            "   Testing guard passing scenario: 'canLogin' returns True"
        )
        # Define MachineLogic where 'canLogin' guard always returns True
        logic_success = MachineLogic(
            guards={"canLogin": lambda ctx, evt: True}
        )
        interp_succ = await Interpreter(
            create_machine(self.guard_machine_config, logic_success)
        ).start()
        self.assertEqual(
            interp_succ.current_state_ids,
            {"auth.idle"},
            "Interpreter should start in 'idle'",
        )

        await interp_succ.send("LOGIN")  # 📝 Send event
        await self.wait_for_state(
            interp_succ, {"auth.success"}
        )  # ⏳ Wait for transition
        self.assertEqual(
            interp_succ.current_state_ids,
            {"auth.success"},
            "State should transition to 'success' because guard passed",
        )
        logger.debug(
            "State transitioned to 'success' as expected when guard passed."
        )
        await interp_succ.stop()

    # -----------------------------------------------------------------------------
    # Tests: Service Invocation (invoke)
    # -----------------------------------------------------------------------------
    async def test_invoke_on_done(self) -> None:
        """
        Should transition on successful completion of an invoked service.

        Ensures that `onDone` transitions fire correctly after an asynchronous
        service completes its execution successfully.
        """
        logger.info("🚀 Testing invoke onDone transition...")
        mock_service = AsyncMock(
            return_value={"user": "Alice"}
        )  # 🧪 Mock service to return a value

        machine_def = create_machine(
            {
                "id": "fetch",
                "initial": "loading",
                "states": {
                    "loading": {
                        "invoke": {
                            "src": "fetchUser",
                            "onDone": "success",
                        }  # Invoke service and transition onDone
                    },
                    "success": {},
                },
            },
            MachineLogic(
                services={"fetchUser": mock_service}
            ),  # Map service name to mock implementation
        )
        interpreter = await Interpreter(machine_def).start()

        # ⏳ Wait for the interpreter to reach the 'success' state, indicating service completion
        await self.wait_for_state(interpreter, {"fetch.success"})

        # ✅ Verify the mock service was called and the state transitioned correctly
        mock_service.assert_awaited_once()  # Assert the service was awaited
        self.assertEqual(
            interpreter.current_state_ids,
            {"fetch.success"},
            "State should be 'success' after service done",
        )
        logger.debug(
            "Service 'fetchUser' invoked and state transitioned to 'success'."
        )
        await interpreter.stop()

    async def test_invoke_on_error(self) -> None:
        """
        Should transition on failure of an invoked service.

        Ensures that `onError` transitions fire correctly when an asynchronous
        service raises an exception.
        """
        logger.info("🚀 Testing invoke onError transition...")
        mock_service = AsyncMock(
            side_effect=ValueError("API Error")
        )  # 🧪 Mock service to raise an error

        machine_def = create_machine(
            {
                "id": "fetch",
                "initial": "loading",
                "states": {
                    "loading": {
                        "invoke": {
                            "src": "fetchUser",
                            "onError": "failure",
                        }  # Invoke service and transition onError
                    },
                    "failure": {},
                },
            },
            MachineLogic(
                services={"fetchUser": mock_service}
            ),  # Map service name to mock implementation
        )
        interpreter = await Interpreter(machine_def).start()

        # ⏳ Wait for the interpreter to reach the 'failure' state, indicating service error
        await self.wait_for_state(interpreter, {"fetch.failure"})

        # ✅ Verify the mock service was called and the state transitioned correctly
        mock_service.assert_awaited_once()  # Assert the service was awaited
        self.assertEqual(
            interpreter.current_state_ids,
            {"fetch.failure"},
            "State should be 'failure' after service error",
        )
        logger.debug(
            "Service 'fetchUser' invoked and state transitioned to 'failure' on error."
        )
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Delayed Transitions (after)
    # -----------------------------------------------------------------------------
    async def test_after_delayed_transition(self) -> None:
        """
        Should transition after the specified delay.

        Validates the 'after' property in state definitions, ensuring that
        the interpreter automatically transitions to a target state after
        a specified time delay.
        """
        logger.info("🚀 Testing delayed transition (after property)...")
        machine_def = create_machine(
            {
                "id": "timeout",
                "initial": "pending",
                "states": {
                    "pending": {"after": {"50": "finished"}},
                    "finished": {},
                },  # 50ms delay
            }
        )
        interpreter = await Interpreter(machine_def).start()
        # ⏳ Wait for the interpreter to reach the 'finished' state
        await self.wait_for_state(interpreter, {"timeout.finished"})
        # ✅ Verify the state transitioned as expected after the delay
        self.assertEqual(
            interpreter.current_state_ids,
            {"timeout.finished"},
            "State should transition to 'finished' after delay",
        )
        logger.debug("Delayed transition to 'finished' successful.")
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Actor Spawning & Communication
    # -----------------------------------------------------------------------------
    async def test_spawn_actor_and_communication(self) -> None:
        """
        Should spawn a child actor and allow parent-child communication.

        Verifies that child state machines can be spawned as actors and that
        events can be sent between the parent and child interpreters.
        """
        logger.info("🚀 Testing actor spawning and messaging...")

        # 1. Define the child machine: It responds to 'PING' by sending 'PONG_RECEIVED' to its parent.
        child_machine = create_machine(
            {
                "id": "child",
                "initial": "active",
                "states": {
                    "active": {
                        "on": {"PING": {"actions": ["pong"]}}
                    }  # On PING, execute 'pong' action
                },
            },
            MachineLogic(
                actions={
                    "pong": lambda interp, ctx, evt, ad: asyncio.create_task(
                        interp.parent.send("PONG_RECEIVED")
                    )
                }  # 'pong' action sends an event back to the parent
            ),
        )

        # 2. Define the parent machine: Spawns the child and transitions when it receives 'PONG_RECEIVED'.
        parent_logic = MachineLogic(
            services={"childLogic": child_machine}
        )  # Map service name to child machine
        parent_machine = create_machine(
            {
                "id": "parent",
                "initial": "spawning",
                "context": {},
                "states": {
                    "spawning": {
                        "entry": ["spawn_childLogic"]
                    },  # On entry, spawn the child actor
                    "ponged": {},
                },
                "on": {
                    "PONG_RECEIVED": ".ponged"
                },  # Transition to 'ponged' when PONG_RECEIVED
            },
            parent_logic,
        )

        # 3. Start the parent interpreter
        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(
            interpreter, {"parent.spawning"}
        )  # Ensure parent is in spawning state

        # 4. Get the spawned child interpreter
        # Actors are stored in the interpreter's context, usually under 'actors' or similar
        child_interp = next(
            iter(interpreter.context.get("actors", {}).values()), None
        )
        self.assertIsNotNone(
            child_interp, "Child interpreter should be spawned"
        )

        # 5. Send an event from parent to child
        await child_interp.send("PING")  # 📝 Send 'PING' event to the child

        # 6. Wait for the parent to transition based on the child's response
        await self.wait_for_state(
            interpreter, {"parent.ponged"}
        )  # ⏳ Wait for parent to receive PONG_RECEIVED

        # ✅ Verify the parent successfully transitioned
        self.assertEqual(
            interpreter.current_state_ids,
            {"parent.ponged"},
            "Parent should transition to 'ponged' state",
        )
        logger.debug(
            "Actor communication successful: Parent received PONG_RECEIVED from child."
        )
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Snapshot & Restore
    # -----------------------------------------------------------------------------
    async def test_snapshot_and_restore(self) -> None:
        """
        Should correctly capture and restore the interpreter's state.

        Validates that `get_snapshot()` and `from_snapshot()` preserve
        the active state IDs and the machine's context data, allowing
        for reliable state persistence and rehydration.
        """
        logger.info("🚀 Testing snapshot and restore functionality...")
        machine_def = create_machine(
            {
                "id": "snap",
                "initial": "first",
                "context": {"data": "initial"},  # Initial context data
                "states": {
                    "first": {
                        "on": {
                            "NEXT": {
                                "target": "second",
                                "actions": ["setData"],
                            }
                        }  # Transition and action
                    },
                    "second": {},
                },
            },
            MachineLogic(
                actions={
                    "setData": lambda i, c, e, a: c.update({"data": "updated"})
                }
            ),  # Action to modify context
        )

        # 1. Create and run an interpreter to a specific state
        interpreter = await Interpreter(machine_def).start()
        await interpreter.send("NEXT")  # Trigger transition and action
        await self.wait_for_state(
            interpreter, {"snap.second"}
        )  # Wait for the state to settle

        # 2. Capture a snapshot of the interpreter's current state
        snapshot = interpreter.get_snapshot()
        logger.debug("Captured snapshot: %s", snapshot)
        await interpreter.stop()  # Stop the original interpreter

        # 3. Restore a new interpreter from the captured snapshot
        restored_interpreter = Interpreter.from_snapshot(snapshot, machine_def)

        # ✅ Verify that the restored interpreter has the correct state and context
        self.assertEqual(
            restored_interpreter.current_state_ids,
            {"snap.second"},
            "Restored interpreter should be in 'second' state",
        )
        self.assertEqual(
            restored_interpreter.context["data"],
            "updated",
            "Restored interpreter context 'data' should be 'updated'",
        )
        logger.debug(
            "Snapshot restored successfully. State: %s, Context: %s",
            restored_interpreter.current_state_ids,
            restored_interpreter.context,
        )

    # -----------------------------------------------------------------------------
    # Tests: Internal Transitions & Multiple Actions
    # -----------------------------------------------------------------------------
    async def test_internal_transition_without_target(self) -> None:
        """
        Should execute actions on a transition without a target and not change state.

        Validates the behavior of internal transitions, where actions are executed
        without exiting and re-entering the current state, and thus no state change occurs.
        """
        logger.info("🚀 Testing internal transition (no target)...")
        mock_action = MagicMock()
        machine = create_machine(
            {
                "id": "internal",
                "initial": "active",
                "states": {
                    "active": {"on": {"EVENT": {"actions": "doSomething"}}}
                },  # No target specified
            },
            MachineLogic(actions={"doSomething": mock_action}),
        )
        interpreter = await Interpreter(machine).start()
        # 🚧 Ensure initial state is active
        self.assertEqual(
            interpreter.current_state_ids,
            {"internal.active"},
            "Initial state should be 'internal.active'",
        )

        await interpreter.send(
            "EVENT"
        )  # 📝 Send event to trigger internal transition
        await asyncio.sleep(0.01)  # ⏳ Allow action to run

        # ✅ Verify no state change occurred, but the action was executed
        self.assertEqual(
            interpreter.current_state_ids,
            {"internal.active"},
            "State should remain 'internal.active' after internal transition",
        )
        mock_action.assert_called_once()  # Assert the action was invoked
        logger.debug(
            "Internal transition executed action without changing state."
        )
        await interpreter.stop()

    async def test_multiple_actions_on_transition(self) -> None:
        """
        Should execute all actions in a list for a transition.

        Validates that when multiple actions are specified for a single
        transition, all of them are invoked in the correct sequence.
        """
        logger.info("🚀 Testing multiple actions on transition...")
        action1 = MagicMock()
        action2 = MagicMock()
        machine = create_machine(
            {
                "id": "multi",
                "initial": "a",
                "states": {
                    "a": {"on": {"EVENT": {"actions": ["action1", "action2"]}}}
                },  # List of actions
            },
            MachineLogic(
                actions={"action1": action1, "action2": action2}
            ),  # Map actions to mocks
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("EVENT")  # 📝 Send event
        await asyncio.sleep(0.01)  # ⏳ Allow actions to run

        # ✅ Verify both actions were called exactly once
        action1.assert_called_once()
        action2.assert_called_once()
        logger.debug("Both action1 and action2 were executed as expected.")
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Entry and Exit Actions
    # -----------------------------------------------------------------------------
    async def test_entry_and_exit_actions(self) -> None:
        """
        Should execute entry and exit actions when changing states.

        Validates that state lifecycle hooks (`entry` and `exit` actions)
        are correctly invoked when the interpreter enters or exits a state.
        """
        logger.info("🚀 Testing entry and exit actions...")
        entry_action = MagicMock()
        exit_action = MagicMock()
        machine = create_machine(
            {
                "id": "entryExit",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {"NEXT": "b"},
                        "exit": "onExitA",
                    },  # Define exit action for state 'a'
                    "b": {
                        "entry": "onEnterB"
                    },  # Define entry action for state 'b'
                },
            },
            MachineLogic(
                actions={"onEnterB": entry_action, "onExitA": exit_action}
            ),  # Map actions to mocks
        )
        interpreter = await Interpreter(machine).start()
        # Ensure interpreter is in initial state 'a'
        self.assertEqual(interpreter.current_state_ids, {"entryExit.a"})

        await interpreter.send(
            "NEXT"
        )  # 📝 Send event to transition from 'a' to 'b'
        await self.wait_for_state(
            interpreter, {"entryExit.b"}
        )  # ⏳ Wait for state 'b' to be active

        # ✅ Verify that exit action of 'a' and entry action of 'b' were called
        exit_action.assert_called_once()  # 'onExitA' should be called when exiting 'a'
        entry_action.assert_called_once()  # 'onEnterB' should be called when entering 'b'
        logger.debug("Entry and exit actions executed successfully.")
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Parallel States
    # -----------------------------------------------------------------------------
    async def test_parallel_state_onDone(self) -> None:
        """
        `onDone` transition on a parallel state should fire only when all regions are done.

        Validates the behavior of parallel states, ensuring that a parallel state's
        `onDone` transition is only triggered when all of its child regions have
        reached their final states.
        """
        logger.info("🚀 Testing parallel state onDone behavior...")
        machine = create_machine(
            {
                "id": "parallel",
                "initial": "active",
                "states": {
                    "active": {
                        "type": "parallel",  # Define 'active' as a parallel state
                        "onDone": "finished",  # Transition to 'finished' when 'active' is done
                        "states": {
                            "a": {  # First parallel region
                                "initial": "a1",
                                "states": {
                                    "a1": {"on": {"A_DONE": "a2"}},
                                    "a2": {
                                        "type": "final"
                                    },  # Final state for region 'a'
                                },
                            },
                            "b": {  # Second parallel region
                                "initial": "b1",
                                "states": {
                                    "b1": {"on": {"B_DONE": "b2"}},
                                    "b2": {
                                        "type": "final"
                                    },  # Final state for region 'b'
                                },
                            },
                        },
                    },
                    "finished": {},
                },
            }
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(
            interpreter.current_state_ids,
            {
                "parallel.active.a.a1",
                "parallel.active.b.b1",
            },  # Both initial parallel states active
            "Initial states for parallel regions should be active",
        )

        # 1. Complete the first parallel region ('a')
        await interpreter.send("A_DONE")  # 📝 Send event to finish region 'a'
        await self.wait_for_state(
            interpreter, {"parallel.active.a.a2"}
        )  # Wait for region 'a' to enter final state
        self.assertIn(
            "parallel.active.a.a2",
            interpreter.current_state_ids,
            "Region 'a' should be in its final state 'a2'",
        )
        self.assertNotIn(
            "parallel.finished",
            interpreter.current_state_ids,
            "Should NOT transition to 'finished' yet (region 'b' is not done)",
        )
        logger.debug(
            "Region 'a' completed, 'finished' state not yet reached as expected."
        )

        # 2. Complete the second parallel region ('b')
        await interpreter.send("B_DONE")  # 📝 Send event to finish region 'b'
        await self.wait_for_state(
            interpreter, {"parallel.finished"}
        )  # Wait for the entire parallel state to be done

        # ✅ Verify that the parent parallel state transitioned to 'finished'
        self.assertEqual(
            interpreter.current_state_ids,
            {"parallel.finished"},
            "Should transition to 'finished' when all parallel regions are done",
        )
        logger.debug(
            "All parallel regions completed, 'finished' state reached."
        )
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Deeply Nested Transitions
    # -----------------------------------------------------------------------------
    async def test_deeply_nested_transition(self) -> None:
        """
        Should correctly transition out of and into deeply nested states.

        Verifies the interpreter's ability to navigate complex, multi-level
        state hierarchies, correctly exiting nested states and entering
        deeply nested target states.
        """
        logger.info("🚀 Testing deeply nested transitions...")
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
                                },  # Transition to deep nested state
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
        # 🚧 Verify initial deeply nested state
        self.assertEqual(
            interpreter.current_state_ids,
            {"deep.a.a1.a11"},
            "Initial state should be 'deep.a.a1.a11'",
        )
        logger.debug("Initial deep state: %s", interpreter.current_state_ids)

        await interpreter.send("NEXT")  # 📝 Trigger the deep transition
        await self.wait_for_state(
            interpreter, {"deep.b.b1.b11"}
        )  # ⏳ Wait for transition to complete

        # ✅ Verify the interpreter is in the new deeply nested state
        self.assertEqual(
            interpreter.current_state_ids,
            {"deep.b.b1.b11"},
            "Should transition to deeply nested 'deep.b.b1.b11'",
        )
        logger.debug(
            "Successfully transitioned to deep nested state: %s",
            interpreter.current_state_ids,
        )
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Event Payload Passing
    # -----------------------------------------------------------------------------
    async def test_event_payload_is_passed_to_actions_and_guards(self) -> None:
        """
        Event payloads should be accessible in actions and guards.

        Ensures that any additional data provided with an event (the "payload")
        is correctly encapsulated within the `Event` object and made available
        to both guard conditions and actions triggered by that event.
        """
        logger.info(
            "🚀 Testing event payload propagation to actions and guards..."
        )
        mock_action = MagicMock()
        mock_guard = MagicMock(
            return_value=True
        )  # Guard must pass for action to run

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

        # 📝 Send event with a custom payload
        test_payload = {"value": 42, "user": "test"}
        await interpreter.send("EVENT", **test_payload)
        await asyncio.sleep(
            0.01
        )  # ⏳ Allow processing of event, guard, and action

        # ✅ Verify guards received the Event object with the correct payload
        mock_guard.assert_called_once()
        # The Event object is the second argument (index 1) to the guard function
        guard_args = mock_guard.call_args[0]
        self.assertIsInstance(
            guard_args[1], Event, "Guard should receive an Event object"
        )
        self.assertEqual(
            guard_args[1].payload,
            test_payload,
            "Guard should receive the correct event payload",
        )
        logger.debug("Guard received payload: %s", guard_args[1].payload)

        # ✅ Verify actions received the Event object with the correct payload
        mock_action.assert_called_once()
        # The Event object is the third argument (index 2) to the action function
        action_args = mock_action.call_args[0]
        self.assertIsInstance(
            action_args[2], Event, "Action should receive an Event object"
        )
        self.assertEqual(
            action_args[2].payload,
            test_payload,
            "Action should receive the correct event payload",
        )
        logger.debug("Action received payload: %s", action_args[2].payload)
        await interpreter.stop()

    # -----------------------------------------------------------------------------
    # Tests: Error Handling for Missing Implementations
    # -----------------------------------------------------------------------------
    async def test_raises_error_for_missing_guard_implementation(self) -> None:
        """
        Should raise ImplementationMissingError if a guard is not defined in MachineLogic.

        This test verifies that the interpreter correctly identifies and surfaces
        errors when a machine definition references a guard that has no corresponding
        implementation provided in the `MachineLogic`. The error is expected to
        be re-raised when awaiting the interpreter's internal event loop task.
        """
        logger.info("🚀 Testing missing guard implementation error...")
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {
                    "a": {"on": {"EVENT": {"guard": "nonexistent"}}}
                },  # Referencing a missing guard
            },
            MachineLogic(),  # No 'nonexistent' guard provided here
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send(
            "EVENT"
        )  # This event will try to evaluate the missing guard
        await asyncio.sleep(
            0.01
        )  # ⏳ Allow event processing to attempt guard evaluation

        # The error occurs in the interpreter's internal event loop task.
        # We check if the task is done and then attempt to get its result,
        # which will re-raise any exceptions that occurred within the task.
        task = interpreter._event_loop_task
        self.assertTrue(
            task.done(),
            "Interpreter's event loop task should be done (due to error)",
        )
        logger.debug(
            "Interpreter task state: done=%s, exception=%s",
            task.done(),
            task.exception(),
        )

        with self.assertRaises(ImplementationMissingError) as cm:
            task.result()  # ❌ This line re-raises the underlying ImplementationMissingError

        # Updated assertion to match the exact error message from the traceback
        self.assertIn(
            "Guard 'nonexistent' is not implemented.",
            str(cm.exception),
            "Error message should indicate missing guard",
        )
        logger.info(
            "✅ Correctly raised ImplementationMissingError for missing guard: %s",
            cm.exception,
        )
        await interpreter.stop()

    async def test_raises_error_for_missing_service_implementation(
        self,
    ) -> None:
        """
        Should raise ImplementationMissingError if an invoked service is not defined.

        This test ensures that the interpreter fails to start if an `invoke`
        declaration points to a service that has no corresponding implementation
        in the provided `MachineLogic`. This prevents runtime errors from
        unresolvable service calls.
        """
        logger.info("🚀 Testing missing service implementation error...")
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {
                    "a": {"invoke": {"src": "nonexistent"}}
                },  # Referencing a missing service
            },
            MachineLogic(),  # No 'nonexistent' service provided
        )
        with self.assertRaises(ImplementationMissingError) as cm:
            # ❌ Interpreter.start() should immediately fail due to the missing service
            await Interpreter(machine).start()

        # Updated assertion to match the exact error message from the traceback
        self.assertIn(
            "Service 'nonexistent' is not implemented.",
            str(cm.exception),
            "Error message should indicate missing service",
        )
        logger.info(
            "✅ Correctly raised ImplementationMissingError for missing service: %s",
            cm.exception,
        )

    async def test_spawn_actor_fails_for_non_machine_service(self) -> None:
        """
        Should raise ActorSpawningError if the service mapped for spawning is not a MachineNode.

        This test validates that when an `entry` action attempts to `spawn` an
        actor, it enforces that the source of the actor must be a valid
        `MachineNode` definition. Attempting to spawn a non-machine source
        should result in an `ActorSpawningError`.
        """
        logger.info("🚀 Testing actor spawn error for invalid service type...")

        # Define a service that returns a plain string, not a MachineNode
        def bad_actor_service(
            interp: Interpreter, context: Dict[str, Any], event: Event
        ) -> Any:
            return "not a machine"

        machine = create_machine(
            {
                "id": "spawner",
                "initial": "active",
                "states": {
                    "active": {"entry": "spawn_badActor"}
                },  # Attempt to spawn 'badActor'
            },
            MachineLogic(
                services={"badActor": bad_actor_service}
            ),  # Map to a non-machine function
        )
        with self.assertRaises(ActorSpawningError) as cm:
            # ❌ Interpreter.start() should fail because 'spawn_badActor' is invoked on entry
            await Interpreter(machine).start()

        # Updated assertion to match the exact error message from the traceback
        self.assertIn(
            "Cannot spawn 'badActor'. The corresponding item in `services` logic is not a valid MachineNode.",
            str(cm.exception),
            "Error message should indicate invalid actor source",
        )
        logger.info(
            "✅ Correctly raised ActorSpawningError for invalid actor source: %s",
            cm.exception,
        )

    async def test_sending_invalid_event_type(self) -> None:
        """
        Should raise TypeError when sending an unsupported event type.

        This test verifies that the `interpreter.send()` method enforces
        type validation for the event argument, ensuring that only strings
        (event names) or `Event` objects are accepted.
        """
        logger.info("🚀 Testing invalid event type error on send()...")
        # Create a minimal machine just to have an interpreter instance
        interpreter = await Interpreter(
            create_machine({"id": "a", "initial": "b", "states": {"b": {}}})
        ).start()

        with self.assertRaises(TypeError) as cm:
            # ❌ Attempt to send an integer, which is an invalid event type
            await interpreter.send(123)  # type: ignore # Ignoring type check for test purpose

        # Updated assertion to match the exact error message from the traceback
        self.assertIn(
            "Unsupported event type passed to send(): <class 'int'>",
            str(cm.exception),
            "Error message should indicate invalid event type",
        )
        logger.info(
            "✅ Correctly raised TypeError for invalid event type: %s",
            cm.exception,
        )
        await interpreter.stop()
