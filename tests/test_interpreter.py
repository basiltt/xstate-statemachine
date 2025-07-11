# /tests/test_interpreter.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Interpreter Runtime Execution
# -----------------------------------------------------------------------------
# This module provides a comprehensive test suite for the Interpreter's
# asynchronous runtime execution logic. It leverages the `IsolatedAsyncioTestCase`
# to ensure each test runs in a clean event loop, preventing state leakage
# between tests.
#
# The suite covers a wide range of statechart functionality, including:
#   - Basic state transitions and event handling.
#   - Context manipulation via actions.
#   - Conditional transitions using guards.
#   - Asynchronous service invocation (`invoke`) with `onDone` and `onError`.
#   - Timed transitions (`after`) and their cancellation.
#   - The actor model, including spawning, communication, and lifecycle.
#   - State snapshotting and restoration.
#   - Complex scenarios like parallel states, internal transitions, and
#     eventless transitions.
#   - Robust error handling for missing implementations and runtime exceptions.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import unittest
from typing import Any, Coroutine, Dict, Set
from unittest.mock import AsyncMock, MagicMock

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    ActorSpawningError,
    ImplementationMissingError,
    Interpreter,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import ActionDefinition
from xstate_statemachine import PluginBase, Event

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configures a logger for providing informative output during test execution.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Test Helpers
# -----------------------------------------------------------------------------


async def cancel_all_tasks() -> None:
    """Cancels all running asyncio tasks except the current one.

    This helper is crucial for ensuring a clean slate between asynchronous
    tests. It prevents "leaked" tasks from one test from interfering with
    the state or timing of subsequent tests, which is a common source of
    flakiness in async test suites.

    Returns:
        None
    """
    # 🕵️‍♂️ Get the currently executing task to avoid cancelling itself.
    current = asyncio.current_task()
    # 📋 Find all other tasks that are still running.
    tasks = [t for t in asyncio.all_tasks() if t is not current]
    if tasks:
        logger.info("🔄 Cancelling %d leftover task(s)...", len(tasks))
        # 🏃‍♂️ Issue cancellation requests to all identified tasks.
        for task in tasks:
            task.cancel()
        # 🙏 Wait for all tasks to acknowledge cancellation.
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✅ All leftover tasks successfully cancelled.")


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestInterpreter
# -----------------------------------------------------------------------------


class TestInterpreter(unittest.IsolatedAsyncioTestCase):
    """A collection of unit tests for the Interpreter's async runtime.

    This class rigorously tests the behavior of an interpreted state machine,
    ensuring that all features of the statechart specification are correctly
    implemented in the asynchronous environment.
    """

    # -------------------------------------------------------------------------
    # ♻️ Test Lifecycle Methods
    # -------------------------------------------------------------------------

    def setUp(self) -> None:
        """Sets up common configurations before each test.

        This method initializes a standard machine configuration that is used
        in multiple tests related to guards, reducing code duplication.
        """
        logger.info("🚀 Setting up common test configurations...")
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
        """Cleans up by cancelling any remaining tasks after each test.

        This is a critical step in maintaining test isolation for async code.
        It ensures that timers, invoked services, or other background tasks
        from one test do not spill over and affect the outcome of another.
        """
        logger.info("🧹 Performing async teardown and cleanup...")
        await cancel_all_tasks()
        logger.info("✅ Async teardown complete.")

    async def wait_for_state(
        self,
        interpreter: Interpreter,
        state_ids: Set[str],
        timeout: float = 2.0,
    ) -> None:
        """Polls the interpreter until it enters one of the desired states.

        This is a utility method that provides a reliable way to wait for an
        asynchronous operation within the interpreter to complete, preventing
        the need for arbitrary `asyncio.sleep()` calls.

        Args:
            interpreter: The interpreter instance being tested.
            state_ids: A set of target state IDs to wait for. The method
                succeeds if the interpreter enters any of these states.
            timeout: The maximum time in seconds to wait before failing.

        Raises:
            AssertionError: If the interpreter does not reach one of the
                target states within the specified timeout period.
        """
        logger.info(
            "⏳ Waiting (up to %.2fs) for state(s): %s", timeout, state_ids
        )
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        # 🔄 Poll the interpreter's state until a match or timeout.
        while True:
            # ✅ Success condition: The current state set has a non-empty
            # intersection with the target state set.
            if not interpreter.current_state_ids.isdisjoint(state_ids):
                logger.info(
                    "👍 Reached target state. Current state(s): %s",
                    interpreter.current_state_ids,
                )
                return

            # ❌ Failure condition: The timeout has been exceeded.
            if loop.time() - start_time > timeout:
                self.fail(
                    f"⏰ Timed out waiting for state(s) {state_ids}. "
                    f"Interpreter is still in: {interpreter.current_state_ids}"
                )

            # 😴 Wait a very short period before polling again.
            await asyncio.sleep(0.01)

    # -------------------------------------------------------------------------
    # 🔩 Core Functionality: Transitions, Context, and Actions
    # -------------------------------------------------------------------------

    async def test_simple_transition(self) -> None:
        """Should transition from one state to another on an event."""
        logger.info("🧪 Testing basic state transition on event.")
        # 📋 Arrange: Create a simple state machine.
        machine = create_machine(
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
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"light.green"})

        # 🚀 Act: Send an event to trigger a transition.
        await interpreter.send("TIMER")
        await self.wait_for_state(interpreter, {"light.yellow"})

        # ✅ Assert: The interpreter should now be in the new state.
        self.assertEqual(interpreter.current_state_ids, {"light.yellow"})
        await interpreter.stop()

    async def test_context_and_actions(self) -> None:
        """Should execute actions that modify the machine's context."""
        logger.info("🧪 Testing action execution and context mutation.")
        # 📋 Arrange: Create a mock action and a machine that uses it.
        mock_action = MagicMock()

        # This side effect directly modifies the context dictionary.
        # ✅ FIX: Unused parameters are prefixed with an underscore.
        def increment_context(
            _interp: Interpreter,
            context: Dict[str, Any],
            _event: Any,
            _ad: ActionDefinition,
        ) -> None:
            context["count"] += 1

        mock_action.side_effect = increment_context  # noqa
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
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.context["count"], 0)

        # 🚀 Act: Send an event to trigger the action.
        await interpreter.send("INC")
        await asyncio.sleep(0.05)  # Allow time for the event to be processed.

        # ✅ Assert: The action was called and the context was updated.
        mock_action.assert_called_once()
        self.assertEqual(interpreter.context["count"], 1)
        await interpreter.stop()

    async def test_internal_transition_without_target(self) -> None:
        """Should execute actions on a transition without changing state."""
        logger.info("🧪 Testing internal transitions that only run actions.")
        # 📋 Arrange: Define an event with an action but no `target`.
        mock_action = MagicMock()
        machine = create_machine(
            {
                "id": "internal",
                "initial": "active",
                "states": {
                    "active": {"on": {"EVENT": {"actions": "doSomething"}}}
                },
            },
            logic=MachineLogic(actions={"doSomething": mock_action}),
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})

        # 🚀 Act: Send the event.
        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)

        # ✅ Assert: The state remains the same, but the action was executed.
        self.assertEqual(interpreter.current_state_ids, {"internal.active"})
        mock_action.assert_called_once()
        await interpreter.stop()

    async def test_multiple_actions_on_transition(self) -> None:
        """Should execute all actions in a list for a transition."""
        logger.info("🧪 Testing execution of multiple actions in sequence.")
        # 📋 Arrange: Define two mock actions for a single event.
        action1 = MagicMock()  # noqa
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
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Send the event to trigger both actions.
        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)

        # ✅ Assert: Both actions were called.
        action1.assert_called_once()
        action2.assert_called_once()
        await interpreter.stop()

    async def test_entry_and_exit_actions(self) -> None:
        """Should execute entry and exit actions when changing states."""
        logger.info("🧪 Testing entry and exit action execution.")
        # 📋 Arrange: Define a machine with `entry` and `exit` actions.
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
            logic=MachineLogic(
                actions={"onEnterB": entry_action, "onExitA": exit_action}
            ),
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Transition from state 'a' to 'b'.
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"entryExit.b"})

        # ✅ Assert: The exit action of 'a' and entry action of 'b' were called.
        exit_action.assert_called_once()
        entry_action.assert_called_once()
        await interpreter.stop()

    async def test_self_transition_executes_entry_exit_actions(self) -> None:
        """An external self-transition should re-execute its entry/exit actions."""
        logger.info("🧪 Testing re-execution of actions on self-transitions.")
        # 📋 Arrange: Define a state that transitions to itself.
        exit_action = MagicMock()
        entry_action = MagicMock()
        machine = create_machine(
            {
                "id": "self_trans",
                "initial": "active",
                "states": {
                    "active": {
                        # A relative target ('.active') defines an external transition
                        # that explicitly exits and re-enters the state.
                        "on": {"LOOP": {"target": ".active"}},
                        "entry": "onEnter",
                        "exit": "onExit",
                    }
                },
            },
            logic=MachineLogic(
                actions={"onExit": exit_action, "onEnter": entry_action}
            ),
        )

        interpreter = await Interpreter(machine).start()
        # Initial entry action is called once on start.
        entry_action.assert_called_once()

        # 🚀 Act: Send the event to trigger the self-transition.
        await interpreter.send("LOOP")
        await asyncio.sleep(0.01)

        # ✅ Assert: The exit action was called once, and the entry action was
        # called a second time.
        self.assertEqual(exit_action.call_count, 1)
        self.assertEqual(entry_action.call_count, 2)
        await interpreter.stop()

    async def test_eventless_transition_is_processed_async(self) -> None:
        """The async interpreter should correctly handle event-less transitions."""
        logger.info(
            "🧪 Testing automatic processing of event-less transitions."
        )
        # 📋 Arrange: A machine with an event-less ("always") transition from 'b' to 'c'.
        machine = create_machine(
            {
                "id": "async_transient",
                "initial": "a",
                "states": {
                    "a": {"on": {"NEXT": "b"}},
                    "b": {"on": {"": "c"}},  # Event-less transition
                    "c": {},
                },
            }
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Transition to state 'b'. The interpreter should not stay in 'b'
        # but immediately proceed to 'c'.
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"async_transient.c"})

        # ✅ Assert: The final state is 'c'.
        self.assertEqual(interpreter.current_state_ids, {"async_transient.c"})
        await interpreter.stop()

    async def test_deeply_nested_transition(self) -> None:
        """Should correctly transition out of and into deeply nested states."""
        logger.info("🧪 Testing transitions between deeply nested states.")
        # 📋 Arrange: A machine with a transition targeting a deeply nested state ID.
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

        # 🚀 Act: Trigger the transition.
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"deep.b.b1.b11"})

        # ✅ Assert: The interpreter is now in the deeply nested target state.
        self.assertEqual(interpreter.current_state_ids, {"deep.b.b1.b11"})
        await interpreter.stop()

    async def test_event_handled_by_ancestor_state(self) -> None:
        """An event should be handled by an ancestor if not handled locally."""
        logger.info("🧪 Testing event bubbling to an ancestor state.")
        # 📋 Arrange: An event 'GOTO_B' is defined on the parent state 'a'.
        machine = create_machine(
            {
                "id": "ancestor_handler",
                "initial": "a",
                "states": {
                    "a": {
                        "initial": "a1",
                        "on": {"GOTO_B": "b"},
                        "states": {"a1": {}},
                    },
                    "b": {},
                },
            }
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(
            interpreter.current_state_ids, {"ancestor_handler.a.a1"}
        )

        # 🚀 Act: Send the event while in the child state 'a1'.
        await interpreter.send("GOTO_B")
        await self.wait_for_state(interpreter, {"ancestor_handler.b"})

        # ✅ Assert: The transition on the ancestor was taken.
        self.assertEqual(interpreter.current_state_ids, {"ancestor_handler.b"})
        await interpreter.stop()

    async def test_unhandled_event_is_ignored(self) -> None:
        """An event with no matching transition should result in no state change."""
        logger.info("🧪 Testing that unhandled events are safely ignored.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "unhandled",
                "initial": "a",
                "states": {"a": {"on": {"REAL_EVENT": "b"}}, "b": {}},
            }
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"unhandled.a"})

        # 🚀 Act: Send an event that is not defined for the current state.
        await interpreter.send("FAKE_EVENT")
        await asyncio.sleep(0.01)

        # ✅ Assert: The state has not changed.
        self.assertEqual(interpreter.current_state_ids, {"unhandled.a"})
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # 🛂 Guards and Conditional Logic
    # -------------------------------------------------------------------------

    async def test_guards_block_or_allow_transitions(self) -> None:
        """Should block or allow transitions based on guard conditions."""
        logger.info(
            "🧪 Testing guard logic for blocking/allowing transitions."
        )
        # --- Scenario 1: Guard returns False ---
        logic_fail = MachineLogic(
            guards={"canLogin": lambda _ctx, _evt: False}
        )
        interp_fail = await Interpreter(
            create_machine(self.guard_machine_config, logic=logic_fail)
        ).start()

        # 🚀 Act: Send event that should be blocked.
        await interp_fail.send("LOGIN")
        await asyncio.sleep(0.05)

        # ✅ Assert: State remains 'idle' because the guard failed.
        self.assertEqual(interp_fail.current_state_ids, {"auth.idle"})
        await interp_fail.stop()

        # --- Scenario 2: Guard returns True ---
        logic_success = MachineLogic(
            guards={"canLogin": lambda _ctx, _evt: True}
        )
        interp_succ = await Interpreter(
            create_machine(self.guard_machine_config, logic=logic_success)
        ).start()

        # 🚀 Act: Send event that should be allowed.
        await interp_succ.send("LOGIN")
        await self.wait_for_state(interp_succ, {"auth.success"})

        # ✅ Assert: State transitions to 'success' because the guard passed.
        self.assertEqual(interp_succ.current_state_ids, {"auth.success"})
        await interp_succ.stop()

    async def test_guarded_eventless_transition_async(self) -> None:
        """A guarded event-less transition should only be taken if guard passes."""
        logger.info("🧪 Testing guards on event-less transitions.")
        # 📋 Arrange: Guard 'shouldGo' will determine if the transition from 'b' to 'c' occurs.
        logic = MachineLogic(guards={"shouldGo": lambda c, _e: c["go"]})
        machine = create_machine(
            {
                "id": "guarded_transient",
                "initial": "a",
                "context": {"go": True},
                "states": {
                    "a": {"on": {"NEXT": "b"}},
                    "b": {"on": {"": {"target": "c", "guard": "shouldGo"}}},
                    "c": {},
                },
            },
            logic=logic,
        )

        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Transition to state 'b'. Since context['go'] is True, it should
        # automatically proceed to 'c'.
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"guarded_transient.c"})

        # ✅ Assert: The final state is 'c'.
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_transient.c"}
        )
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # 📞 Service Invocation (invoke)
    # -------------------------------------------------------------------------

    async def test_invoke_on_done(self) -> None:
        """Should transition on successful completion of an invoked service."""
        logger.info("🧪 Testing `onDone` transition for invoked services.")
        # 📋 Arrange: A mock service that completes successfully.
        mock_service = AsyncMock(return_value={"user": "Alice"})
        machine = create_machine(
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
            logic=MachineLogic(services={"fetchUser": mock_service}),
        )

        # 🚀 Act: Start the interpreter, which will immediately invoke the service.
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"fetch.success"})

        # ✅ Assert: The service was called and the `onDone` transition was taken.
        mock_service.assert_awaited_once()
        self.assertEqual(interpreter.current_state_ids, {"fetch.success"})
        await interpreter.stop()

    async def test_invoke_on_error(self) -> None:
        """Should transition on failure of an invoked service."""
        logger.info("🧪 Testing `onError` transition for invoked services.")
        # 📋 Arrange: A mock service that raises an exception.
        mock_service = AsyncMock(side_effect=ValueError("API Error"))
        machine = create_machine(
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
            logic=MachineLogic(services={"fetchUser": mock_service}),
        )

        # 🚀 Act: Start the interpreter.
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"fetch.failure"})

        # ✅ Assert: The service was called and the `onError` transition was taken.
        mock_service.assert_awaited_once()
        self.assertEqual(interpreter.current_state_ids, {"fetch.failure"})
        await interpreter.stop()

    async def test_invoke_is_cancelled_on_state_exit(self) -> None:
        """An invoked service should be cancelled when its state is exited."""
        logger.info("🧪 Testing that invoked services are cancelled on exit.")
        # 📋 Arrange: A future that a long-running mock service will wait on.
        fut = asyncio.Future()

        async def long_service_coro(*_args: Any, **_kwargs: Any) -> None:
            await fut

        long_service = AsyncMock(side_effect=long_service_coro)
        machine = create_machine(
            {
                "id": "canceller",
                "initial": "working",
                "states": {
                    "working": {
                        "invoke": {"src": "longRunner"},
                        "on": {"CANCEL": "cancelled"},
                    },
                    "cancelled": {},
                },
            },
            logic=MachineLogic(services={"longRunner": long_service}),
        )

        interpreter = await Interpreter(machine).start()
        await asyncio.sleep(
            0.01
        )  # Allow event loop to start the service task.

        tasks = list(
            interpreter.task_manager._tasks_by_owner.get(
                "canceller.working", []
            )
        )
        self.assertEqual(len(tasks), 1)
        invoke_task = tasks[0]

        # 🚀 Act: Send an event to exit the state where the service is running.
        await interpreter.send("CANCEL")
        await self.wait_for_state(interpreter, {"canceller.cancelled"})

        # ✅ Assert: The captured task object for the service is now cancelled.
        self.assertTrue(invoke_task.cancelled())
        await interpreter.stop()

    async def test_invoke_with_input_from_context(self) -> None:
        """Invoked service should receive static input from the config."""
        logger.info("🧪 Testing static `input` mapping for invoked services.")

        # 📋 Arrange: A mock service that asserts it received the correct input.
        async def check_input_service(
            _i: Interpreter, _c: Dict[str, Any], e: Any
        ) -> bool:
            # The 'input' from the invoke config is passed in the invoke event payload.
            self.assertEqual(e.payload.get("input"), {"userId": 123})
            return True

        mock_service = AsyncMock(side_effect=check_input_service)
        machine = create_machine(
            {
                "id": "invoke_input",
                "initial": "active",
                "states": {
                    "active": {
                        "invoke": {
                            "src": "serviceWithInput",
                            "input": {"userId": 123},
                            "onDone": "success",
                        }
                    },
                    "success": {},
                },
            },
            logic=MachineLogic(services={"serviceWithInput": mock_service}),
        )

        # 🚀 Act & Assert
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"invoke_input.success"})
        mock_service.assert_awaited_once()
        await interpreter.stop()

    async def test_guarded_onDone_transition(self) -> None:
        """Should respect guards on `onDone` transitions."""
        logger.info("🧪 Testing guards on `onDone` transitions.")
        # 📋 Arrange: A service and a guard that will fail.
        mock_service = AsyncMock(return_value="data")
        logic = MachineLogic(
            services={"serv": mock_service},
            guards={"check": lambda c, _e: c["allow"]},
        )
        machine = create_machine(
            {
                "id": "guarded_done",
                "initial": "working",
                "context": {"allow": False},
                "states": {
                    "working": {
                        "invoke": {
                            "src": "serv",
                            "onDone": {"target": "success", "guard": "check"},
                        }
                    },
                    "success": {},
                },
            },
            logic=logic,
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Wait for the service to finish.
        await asyncio.sleep(0.1)

        # ✅ Assert: The interpreter stays in 'working' because the guard failed.
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_done.working"}
        )
        await interpreter.stop()

    async def test_invoke_onError_transition_is_guarded(self) -> None:
        """A guarded `onError` transition should be blocked if the guard fails."""
        logger.info("🧪 Testing guards on `onError` transitions.")
        # 📋 Arrange: A failing service and a failing guard.
        mock_service = AsyncMock(side_effect=RuntimeError("Service Failed"))
        logic = MachineLogic(
            services={"failingService": mock_service},
            guards={"shouldHandleError": lambda _c, _e: False},
        )
        machine = create_machine(
            {
                "id": "guarded_error",
                "initial": "working",
                "states": {
                    "working": {
                        "invoke": {
                            "src": "failingService",
                            "onError": {
                                "target": "failed",
                                "guard": "shouldHandleError",
                            },
                        }
                    },
                    "failed": {},
                },
            },
            logic=logic,
        )

        interpreter = await Interpreter(machine).start()
        await asyncio.sleep(0.1)  # Allow service to fail.

        # ✅ Assert: The interpreter remains in the 'working' state and is still
        # running because the guarded transition was not taken.
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_error.working"}
        )
        self.assertFalse(interpreter._event_loop_task.done())
        self.assertEqual(interpreter.status, "running")
        await interpreter.stop()

    async def test_invoke_chooses_correct_guarded_onDone(self) -> None:
        """Should choose the correct `onDone` transition from a list."""
        logger.info("🧪 Testing `onDone` transition selection from a list.")

        # 📋 Arrange: A service and multiple guarded `onDone` transitions.
        async def service_returns_value(
            _i: Interpreter, _c: Dict[str, Any], _e: Any
        ) -> Dict[str, int]:
            return {"value": 25}

        logic = MachineLogic(
            services={"valueService": service_returns_value},
            guards={
                "isLow": lambda c, e: e.data["value"] < 20,  # Will fail
                "isMed": lambda c, e: e.data["value"] < 30,  # Will pass
            },
        )
        machine = create_machine(
            {
                "id": "guarded_choice",
                "initial": "working",
                "states": {
                    "working": {
                        "invoke": {
                            "src": "valueService",
                            "onDone": [
                                {"target": "low", "guard": "isLow"},
                                {"target": "medium", "guard": "isMed"},
                            ],
                        }
                    },
                    "low": {},
                    "medium": {},
                },
            },
            logic=logic,
        )

        # 🚀 Act & Assert
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"guarded_choice.medium"})
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_choice.medium"}
        )
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # ⏱️ Delayed Transitions (after)
    # -------------------------------------------------------------------------

    async def test_after_delayed_transition(self) -> None:
        """Should transition after the specified millisecond delay."""
        logger.info("🧪 Testing delayed `after` transitions.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "timeout",
                "initial": "pending",
                "states": {
                    "pending": {"after": {"50": "finished"}},
                    "finished": {},
                },
            }
        )
        # 🚀 Act & Assert
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"timeout.finished"})
        self.assertEqual(interpreter.current_state_ids, {"timeout.finished"})
        await interpreter.stop()

    async def test_after_timer_is_cancelled_on_state_exit(self) -> None:
        """A delayed 'after' transition should be cancelled on state exit."""
        logger.info("🧪 Testing cancellation of `after` timers on exit.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "timer_canceller",
                "initial": "waiting",
                "states": {
                    "waiting": {
                        "after": {"5000": "finished"},
                        "on": {"EARLY_EXIT": "exited"},
                    },
                    "finished": {},
                    "exited": {},
                },
            }
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(
            len(
                interpreter.task_manager._tasks_by_owner.get(
                    "timer_canceller.waiting", []
                )
            ),
            1,
        )

        # 🚀 Act: Exit the state before the timer fires.
        await interpreter.send("EARLY_EXIT")
        await self.wait_for_state(interpreter, {"timer_canceller.exited"})

        # ✅ Assert: The task associated with the timer has been cancelled and removed.
        self.assertEqual(
            len(
                interpreter.task_manager._tasks_by_owner.get(
                    "timer_canceller.waiting", []
                )
            ),
            0,
        )
        await interpreter.stop()

    async def test_multiple_after_timers_in_one_state(self) -> None:
        """Should fire the shortest timer when multiple 'after' timers exist."""
        logger.info("🧪 Testing selection of shortest `after` timer.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "multi_timer",
                "initial": "waiting",
                "states": {
                    "waiting": {"after": {"100": "fastest", "200": "slowest"}},
                    "fastest": {},
                    "slowest": {},
                },
            }
        )
        # 🚀 Act & Assert
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"multi_timer.fastest"})
        self.assertEqual(
            interpreter.current_state_ids, {"multi_timer.fastest"}
        )
        await interpreter.stop()

    async def test_after_transition_is_guarded(self) -> None:
        """A guarded 'after' transition should not fire if the guard fails."""
        logger.info("🧪 Testing guards on `after` transitions.")
        # 📋 Arrange
        logic = MachineLogic(guards={"shouldFire": lambda _c, _e: False})
        machine = create_machine(
            {
                "id": "guarded_after",
                "initial": "waiting",
                "states": {
                    "waiting": {
                        "after": {
                            "50": {"target": "finished", "guard": "shouldFire"}
                        }
                    }
                },
                "finished": {},
            },
            logic=logic,
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Wait longer than the timer duration.
        await asyncio.sleep(0.1)

        # ✅ Assert: The transition was blocked by the guard.
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_after.waiting"}
        )
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # 🎭 Actor Model
    # -------------------------------------------------------------------------

    async def test_spawn_actor_and_communication(self) -> None:
        """Should spawn a child actor and allow parent-child communication."""
        logger.info("🧪 Testing actor spawning and bi-directional events.")
        # 📋 Arrange: A child machine that sends an event to its parent.
        child_machine = create_machine(
            {
                "id": "child",
                "initial": "active",
                "states": {"active": {"on": {"PING": {"actions": ["pong"]}}}},
            },
            logic=MachineLogic(
                actions={
                    # ✅ FIX: Unused parameters are prefixed with an underscore.
                    "pong": lambda i, _c, _e, _ad: asyncio.create_task(
                        i.parent.send("PONG_RECEIVED")
                    )
                }
            ),
        )
        # 📋 Arrange: A parent machine that spawns the child.
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
            # ✅ FIX: Ignore type checker warning. It's valid to use a MachineNode
            # as a service for spawning actors.
            logic=MachineLogic(
                services={"childLogic": child_machine}  # type: ignore
            ),
        )

        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"parent.spawning"})

        child_interp = next(iter(interpreter._actors.values()), None)
        self.assertIsNotNone(child_interp, "Child actor was not spawned.")

        # 🚀 Act: Send an event to the child, which should trigger it to send an
        # event back to the parent.
        await child_interp.send("PING")
        await self.wait_for_state(interpreter, {"parent.ponged"})

        # ✅ Assert: The parent transitioned after receiving the child's event.
        self.assertEqual(interpreter.current_state_ids, {"parent.ponged"})
        await interpreter.stop()

    async def test_parent_stopping_stops_child_actor(self) -> None:
        """When a parent interpreter stops, it should stop its child actors."""
        logger.info("🧪 Testing that parent `stop` cascades to children.")
        # 📋 Arrange
        child_machine = create_machine(
            {"id": "child", "initial": "active", "states": {"active": {}}}
        )
        parent_machine = create_machine(
            {
                "id": "parent",
                "initial": "running",
                "states": {"running": {"entry": "spawn_child"}},
            },
            logic=MachineLogic(
                services={"child": child_machine}  # type: ignore
            ),
        )
        parent_interp = await Interpreter(parent_machine).start()
        await self.wait_for_state(parent_interp, {"parent.running"})

        # Add a small wait to ensure the actor is spawned.
        start_time = asyncio.get_event_loop().time()
        while len(parent_interp._actors) < 1:
            if asyncio.get_event_loop().time() - start_time > 2.0:
                self.fail("Timed out waiting for child actor to spawn.")
            await asyncio.sleep(0.01)

        self.assertEqual(len(parent_interp._actors), 1)

        child_interp = list(parent_interp._actors.values())[0]
        self.assertEqual(child_interp.status, "running")

        # 🚀 Act: Stop the parent interpreter.
        await parent_interp.stop()

        # ✅ Assert: Both parent and child interpreters are now stopped.
        self.assertEqual(parent_interp.status, "stopped")
        self.assertEqual(child_interp.status, "stopped")
        await parent_interp.stop()

    async def test_parent_stop_cancels_multiple_child_actors(self) -> None:
        """Stopping a parent should stop all of its spawned child actors."""
        logger.info("🧪 Testing stop cascade to multiple child actors.")
        # 📋 Arrange
        child1 = create_machine(
            {"id": "child1", "initial": "a", "states": {"a": {}}}
        )
        child2 = create_machine(
            {"id": "child2", "initial": "b", "states": {"b": {}}}
        )
        parent_machine = create_machine(
            {
                "id": "multi_parent",
                "initial": "running",
                "states": {
                    "running": {"entry": ["spawn_child1", "spawn_child2"]}
                },
            },
            logic=MachineLogic(
                services={"child1": child1, "child2": child2}  # type: ignore
            ),
        )

        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"multi_parent.running"})

        # Wait for the actors to be spawned, preventing a race condition.
        start_time = asyncio.get_event_loop().time()
        while len(interpreter._actors) < 2:
            if asyncio.get_event_loop().time() - start_time > 2.0:
                self.fail("Timed out waiting for child actors to spawn.")
            await asyncio.sleep(0.01)

        actors = list(interpreter._actors.values())
        self.assertEqual(len(actors), 2)
        self.assertEqual(actors[0].status, "running")
        self.assertEqual(actors[1].status, "running")

        # 🚀 Act: Stop the parent.
        await interpreter.stop()

        # ✅ Assert: All child actors are also stopped.
        self.assertEqual(actors[0].status, "stopped")
        self.assertEqual(actors[1].status, "stopped")

    async def test_actor_onDone_is_triggered_on_child_final_state(
        self,
    ) -> None:
        """Parent should transition when a spawned actor reaches a final state."""
        logger.info(
            "🧪 Testing parent reacts to child reaching a final state."
        )
        # 📋 Arrange: Define the child's logic separately from its configuration.
        child_logic = MachineLogic(
            actions={
                "notifyParentDone": lambda i, _c, _e, _a: asyncio.create_task(
                    i.parent.send("CHILD_DONE")
                )
            }
        )
        child_machine = create_machine(
            {
                "id": "child",
                "initial": "working",
                "states": {
                    "working": {"on": {"FINISH": "done"}},
                    "done": {"type": "final", "entry": ["notifyParentDone"]},
                },
            },
            logic=child_logic,
        )

        parent_machine = create_machine(
            {
                "id": "parent",
                "initial": "spawning",
                "states": {
                    "spawning": {
                        "entry": ["spawn_childActor"],
                        "on": {"CHILD_DONE": "child_finished"},
                    },
                    "child_finished": {},
                },
            },
            logic=MachineLogic(
                services={"childActor": child_machine}  # type: ignore
            ),
        )

        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"parent.spawning"})

        # 🚀 Act: Find the child actor and send it an event to make it finish.
        self.assertGreater(
            len(interpreter._actors), 0, "Child actor was not spawned."
        )
        child_interp = next(iter(interpreter._actors.values()))
        await child_interp.send("FINISH")

        # ✅ Assert: The parent should transition after receiving the notification.
        await self.wait_for_state(interpreter, {"parent.child_finished"})
        self.assertEqual(
            interpreter.current_state_ids, {"parent.child_finished"}
        )
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # 📸 Snapshot and State Management
    # -------------------------------------------------------------------------

    async def test_snapshot_and_restore(self) -> None:
        """Should correctly capture and restore the interpreter's state."""
        logger.info("🧪 Testing basic snapshot and restore functionality.")
        # 📋 Arrange
        machine = create_machine(
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
            logic=MachineLogic(
                actions={
                    "setData": lambda _i, c, _e, _a: c.update(
                        {"data": "updated"}
                    )
                }
            ),
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"snap.second"})

        # 🚀 Act: Get a snapshot of the interpreter's state.
        snapshot = interpreter.get_snapshot()
        await interpreter.stop()

        # Restore from the snapshot.
        restored_interpreter = Interpreter.from_snapshot(snapshot, machine)

        # ✅ Assert: The restored interpreter has the correct state and context.
        self.assertEqual(
            restored_interpreter.current_state_ids, {"snap.second"}
        )
        self.assertEqual(restored_interpreter.context["data"], "updated")

    async def test_snapshot_of_parallel_state_async(self) -> None:
        """Should correctly snapshot and restore a parallel state."""
        logger.info("🧪 Testing snapshot and restore of a parallel state.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "m",
                "initial": "p1",
                "states": {
                    "p1": {
                        "type": "parallel",
                        "states": {
                            "a": {"initial": "a1", "states": {"a1": {}}},
                            "b": {"initial": "b1", "states": {"b1": {}}},
                        },
                    }
                },
            }
        )
        interpreter = await Interpreter(machine).start()
        # 🚀 Act
        snapshot = interpreter.get_snapshot()
        await interpreter.stop()
        restored = Interpreter.from_snapshot(snapshot, machine)
        # ✅ Assert
        self.assertEqual(
            restored.current_state_ids, {"m.p1.a.a1", "m.p1.b.b1"}
        )

    async def test_snapshot_does_not_restore_transient_tasks(self) -> None:
        """Snapshot and restore should not persist 'after' timers."""
        logger.info("🧪 Testing that `after` timers are not restored.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "snap_after",
                "initial": "waiting",
                "states": {"waiting": {"after": {"100": "done"}}, "done": {}},
            }
        )
        interpreter = await Interpreter(machine).start()
        snapshot = interpreter.get_snapshot()
        await interpreter.stop()
        # 🚀 Act
        restored = Interpreter.from_snapshot(snapshot, machine)
        # Manually start the event loop for the restored interpreter.
        # ✅ FIX: Ignore unresolved attribute warning, as this is a specific
        # testing scenario that requires accessing a private method.
        restored._event_loop_task = asyncio.create_task(
            restored._run_event_loop()  # type: ignore
        )
        await asyncio.sleep(0.2)  # Wait longer than the original timer.
        # ✅ Assert: The state did not change because the timer was not restored.
        self.assertEqual(restored.current_state_ids, {"snap_after.waiting"})
        await restored.stop()

        # -------------------------------------------------------------------------
        # 🔌 Plugin System: New Hooks Tests
        # -------------------------------------------------------------------------

    async def test_plugin_on_guard_evaluated_hook(self) -> None:
        """The `on_guard_evaluated` plugin hook should be called with correct args."""
        logger.info("🧪 Testing `on_guard_evaluated` plugin hook.")
        # 📋 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        logic = MachineLogic(guards={"canProceed": lambda _c, _e: True})

        # FIXED MACHINE CONFIGURATION
        machine = create_machine(
            {
                "id": "guarded_machine",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {"CHECK": {"target": "b", "guard": "canProceed"}}
                    },
                    "b": {},  # Properly nested under 'states'
                },
            },
            logic=logic,
        )

        interpreter = await Interpreter(machine).use(mock_plugin).start()
        test_event = Event("CHECK", payload={"key": "value"})

        # 🚀 Act
        await interpreter.send(test_event)
        await self.wait_for_state(interpreter, {"guarded_machine.b"})

        # ✅ Assert
        mock_plugin.on_guard_evaluated.assert_called_once()
        args, kwargs = mock_plugin.on_guard_evaluated.call_args
        self.assertEqual(args[0], interpreter)
        self.assertEqual(args[1], "canProceed")
        self.assertEqual(args[2].type, test_event.type)
        self.assertEqual(args[2].payload, test_event.payload)
        self.assertTrue(args[3])  # result should be True

    async def test_plugin_on_service_start_hook(self) -> None:
        """The `on_service_start` plugin hook should be called before service execution."""
        logger.info("🧪 Testing `on_service_start` plugin hook.")
        # 📋 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        mock_service = AsyncMock(return_value="data")

        # Create a mock to ensure service is awaited after plugin hook.
        # This callable will represent the actual service implementation.
        async def real_service(*args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(0.01)  # Simulate some work
            return mock_service(*args, **kwargs)

        logic = MachineLogic(services={"myService": real_service})
        machine = create_machine(
            {
                "id": "service_machine",
                "initial": "invoke_state",
                "states": {
                    "invoke_state": {
                        "invoke": {"src": "myService", "onDone": "done"}
                    },
                    "done": {},
                },
            },
            logic=logic,
        )
        interpreter = await Interpreter(machine).use(mock_plugin).start()

        # 🚀 Act - Start the interpreter, service invocation is on entry.
        await self.wait_for_state(interpreter, {"service_machine.done"})

        # ✅ Assert - Check that on_service_start was called before the service itself.
        mock_plugin.on_service_start.assert_called_once()
        args, kwargs = mock_plugin.on_service_start.call_args
        self.assertEqual(args[0], interpreter)
        self.assertEqual(args[1].src, "myService")
        self.assertTrue(
            mock_service.called
        )  # Ensure the service itself was called

    async def test_plugin_on_service_done_hook(self) -> None:
        """The `on_service_done` plugin hook should be called on successful service completion."""
        logger.info("🧪 Testing `on_service_done` plugin hook.")
        # 📋 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        service_result = {"status": "success"}
        mock_service = AsyncMock(return_value=service_result)
        logic = MachineLogic(services={"myService": mock_service})
        machine = create_machine(
            {
                "id": "service_done_machine",
                "initial": "invoke_state",
                "states": {
                    "invoke_state": {
                        "invoke": {"src": "myService", "onDone": "done"}
                    },
                    "done": {},
                },
            },
            logic=logic,
        )
        interpreter = await Interpreter(machine).use(mock_plugin).start()

        # 🚀 Act
        await self.wait_for_state(interpreter, {"service_done_machine.done"})

        # ✅ Assert
        mock_plugin.on_service_done.assert_called_once()
        args, kwargs = mock_plugin.on_service_done.call_args
        self.assertEqual(args[0], interpreter)
        self.assertEqual(args[1].src, "myService")
        self.assertEqual(args[2], service_result)

    async def test_plugin_on_service_error_hook(self) -> None:
        """The `on_service_error` plugin hook should be called on service failure."""
        logger.info("🧪 Testing `on_service_error` plugin hook.")
        # 📋 Arrange
        mock_plugin = MagicMock(spec=PluginBase)
        service_error = ValueError("Service failed intentionally")
        mock_service = AsyncMock(side_effect=service_error)
        logic = MachineLogic(services={"myService": mock_service})
        machine = create_machine(
            {
                "id": "service_error_machine",
                "initial": "invoke_state",
                "states": {
                    "invoke_state": {
                        "invoke": {"src": "myService", "onError": "failed"}
                    },
                    "failed": {},
                },
            },
            logic=logic,
        )
        interpreter = await Interpreter(machine).use(mock_plugin).start()

        # 🚀 Act
        await self.wait_for_state(
            interpreter, {"service_error_machine.failed"}
        )

        # ✅ Assert
        mock_plugin.on_service_error.assert_called_once()
        args, kwargs = mock_plugin.on_service_error.call_args
        self.assertEqual(args[0], interpreter)
        self.assertEqual(args[1].src, "myService")
        self.assertEqual(args[2], service_error)

    # -------------------------------------------------------------------------
    # 🚦 Parallel States
    # -------------------------------------------------------------------------

    async def test_parallel_state_onDone(self) -> None:
        """`onDone` on a parallel state should fire only when all regions are done."""
        logger.info("🧪 Testing `onDone` condition for parallel states.")
        # 📋 Arrange
        machine = create_machine(  # noqa
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
        self.assertEqual(
            interpreter.current_state_ids,
            {"parallel.active.a.a1", "parallel.active.b.b1"},
        )
        # 🚀 Act: Finish the first region.
        await interpreter.send("A_DONE")
        await self.wait_for_state(interpreter, {"parallel.active.a.a2"})
        # ✅ Assert: The machine is not yet done.
        self.assertNotIn("parallel.finished", interpreter.current_state_ids)

        # 🚀 Act: Finish the second region.
        await interpreter.send("B_DONE")
        await self.wait_for_state(interpreter, {"parallel.finished"})
        # ✅ Assert: Now that both regions are done, the `onDone` transition fires.
        self.assertEqual(interpreter.current_state_ids, {"parallel.finished"})
        await interpreter.stop()

    async def test_final_state_in_parallel_machine_triggers_onDone(
        self,
    ) -> None:
        """A final state in one region should not trigger parent `onDone` alone."""
        logger.info("🧪 Testing `onDone` with only one region finished.")
        # 📋 Arrange
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
            }
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Finish only one of the two regions.
        await interpreter.send("FINISH_A")
        await self.wait_for_state(interpreter, {"p_final.a.a2"})

        # ✅ Assert: The machine is not 'finished' because region 'b' is not done.
        self.assertNotEqual(
            interpreter.current_state_ids, {"p_final.finished"}
        )
        self.assertEqual(interpreter.status, "running")
        await interpreter.stop()

    async def test_complex_on_done_bubbling_async(self) -> None:
        """A nested final state should correctly bubble up to trigger a parent's onDone."""
        logger.info("🧪 Testing `onDone` bubbling from deeply nested states.")
        # 📋 Arrange
        machine = create_machine(  # noqa
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
        # 🚀 Act & Assert
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"m.s2"})
        self.assertEqual(interpreter.current_state_ids, {"m.s2"})
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # ✉️ Event Handling and Payloads
    # -------------------------------------------------------------------------

    async def test_event_payload_is_passed_to_actions_and_guards(self) -> None:
        """Event payloads should be accessible in actions and guards."""
        logger.info("🧪 Testing event payload passing to actions/guards.")
        # 📋 Arrange
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
                    }
                },
            },
            logic=MachineLogic(
                actions={"myAction": mock_action},
                guards={"myGuard": mock_guard},
            ),
        )
        interpreter = await Interpreter(machine).start()
        test_payload = {"value": 42, "user": "test"}

        # 🚀 Act: Send an event with a payload.
        await interpreter.send("EVENT", **test_payload)
        await asyncio.sleep(0.01)

        # ✅ Assert: Both the guard and the action received the correct payload.
        mock_guard.assert_called_once()
        self.assertEqual(mock_guard.call_args[0][1].payload, test_payload)

        mock_action.assert_called_once()
        self.assertEqual(mock_action.call_args[0][2].payload, test_payload)
        await interpreter.stop()

    async def test_send_dict_event_object(self) -> None:
        """Should correctly process an event sent as a dictionary."""
        logger.info("🧪 Testing sending events as dictionary objects.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "dict_event",
                "initial": "a",
                "states": {"a": {"on": {"NEXT": "b"}}, "b": {}},
            }
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Send an event as a dict with a 'type' key.
        await interpreter.send({"type": "NEXT", "value": 123})
        await self.wait_for_state(interpreter, {"dict_event.b"})

        # ✅ Assert: The transition was processed correctly.
        self.assertEqual(interpreter.current_state_ids, {"dict_event.b"})
        await interpreter.stop()

    async def test_send_on_unstarted_interpreter(self) -> None:
        """Events sent to an unstarted interpreter should be queued."""
        logger.info("🧪 Testing that events are queued before `start`.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "q",
                "initial": "a",
                "states": {"a": {"on": {"NEXT": "b"}}, "b": {}},
            }
        )
        interpreter = Interpreter(machine)

        # 🚀 Act: Send an event before starting the interpreter.
        await interpreter.send("NEXT")
        self.assertEqual(interpreter.status, "uninitialized")
        self.assertEqual(interpreter.current_state_ids, set())

        # Start the interpreter.
        await interpreter.start()

        # ✅ Assert: The queued event was processed upon starting.
        await self.wait_for_state(interpreter, {"q.b"})
        self.assertEqual(interpreter.current_state_ids, {"q.b"})
        await interpreter.stop()

    async def test_async_action_can_send_event(self) -> None:
        """An async action should be able to send an event back to itself."""
        logger.info("🧪 Testing an action that sends a follow-up event.")

        # 📋 Arrange: An action that sends another event after a short delay.
        async def action_sends(
            interp: Interpreter, _c: Dict[str, Any], _e: Any, _ad: Any
        ) -> None:
            await asyncio.sleep(0.01)
            await interp.send("INTERNAL")

        machine = create_machine(
            {
                "id": "action_sender",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {"START": {"actions": "sendIt", "target": "b"}}
                    },
                    "b": {"on": {"INTERNAL": "c"}},
                    "c": {},
                },
            },
            logic=MachineLogic(actions={"sendIt": action_sends}),
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Send the initial event.
        await interpreter.send("START")
        await self.wait_for_state(interpreter, {"action_sender.c"})

        # ✅ Assert: The follow-up event was processed, leading to the final state.
        self.assertEqual(interpreter.current_state_ids, {"action_sender.c"})
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # 💯 Interpreter Lifecycle and State
    # -------------------------------------------------------------------------

    async def test_interpreter_id_matches_machine_id(self) -> None:
        """The interpreter's ID should be initialized from the machine's ID."""
        logger.info("🧪 Testing that the interpreter inherits the machine ID.")
        # 📋 Arrange
        machine = create_machine(
            {"id": "my-special-id", "initial": "a", "states": {"a": {}}}
        )
        # 🚀 Act
        interpreter = Interpreter(machine)
        # ✅ Assert
        self.assertEqual(interpreter.id, "my-special-id")

    async def test_start_on_running_interpreter_is_noop(self) -> None:
        """Calling `start()` on a running interpreter should be a no-op."""
        logger.info("🧪 Testing that `start()` is idempotent.")
        # 📋 Arrange
        machine = create_machine(
            {"id": "test", "initial": "a", "states": {"a": {}}}
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.status, "running")

        # Spy on an internal method to ensure it's not called again.
        interpreter._enter_states = AsyncMock()  # type: ignore

        # 🚀 Act
        await interpreter.start()

        # ✅ Assert
        interpreter._enter_states.assert_not_called()
        await interpreter.stop()

    async def test_stop_on_stopped_interpreter_is_noop(self) -> None:
        """Calling `stop()` on a stopped interpreter should be a no-op."""
        logger.info("🧪 Testing that `stop()` is idempotent.")
        # 📋 Arrange
        machine = create_machine(
            {"id": "test", "initial": "a", "states": {"a": {}}}
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.stop()
        self.assertEqual(interpreter.status, "stopped")

        # Spy on an internal method.
        interpreter.task_manager.cancel_all = AsyncMock()  # type: ignore

        # 🚀 Act
        await interpreter.stop()

        # ✅ Assert
        interpreter.task_manager.cancel_all.assert_not_called()

    # -------------------------------------------------------------------------
    # 💥 Error Handling and Edge Cases
    # -------------------------------------------------------------------------

    async def test_raises_error_for_missing_guard_implementation(self) -> None:
        """Should raise ImplementationMissingError for an undefined guard."""
        logger.info("🧪 Testing error for missing guard implementation.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {"a": {"on": {"EVENT": {"guard": "nonexistent"}}}},
            },
            logic=MachineLogic(),
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Send an event that uses the missing guard.
        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)

        # ✅ Assert: The event loop task should complete with an exception.
        task = interpreter._event_loop_task
        self.assertTrue(task.done())
        with self.assertRaises(ImplementationMissingError) as cm:
            task.result()
        self.assertIn(
            "Guard 'nonexistent' not implemented.", str(cm.exception)
        )
        await interpreter.stop()

    async def test_raises_error_for_missing_service_implementation(
        self,
    ) -> None:
        """Should raise ImplementationMissingError for an undefined service."""
        logger.info("🧪 Testing error for missing service implementation.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {"a": {"invoke": {"src": "nonexistent"}}},
            },
            logic=MachineLogic(),
        )
        # 🚀 Act & Assert
        with self.assertRaises(ImplementationMissingError) as cm:
            await Interpreter(machine).start()
        self.assertIn(
            "Service 'nonexistent' referenced by state 'missing.a' is not registered.",
            str(cm.exception),
        )

    async def test_spawn_actor_fails_for_non_machine_service(self) -> None:
        """Should raise ActorSpawningError for a non-MachineNode service."""
        logger.info("🧪 Testing error for spawning a non-machine actor.")

        # 📋 Arrange: A service that returns a string instead of a machine.
        def bad_actor_service(
            _i: Interpreter, _c: Dict[str, Any], _e: Any
        ) -> str:
            return "not a machine"

        machine = create_machine(
            {
                "id": "spawner",
                "initial": "active",
                "states": {"active": {"entry": "spawn_badActor"}},
            },
            logic=MachineLogic(services={"badActor": bad_actor_service}),
        )
        # 🚀 Act & Assert
        with self.assertRaises(ActorSpawningError) as cm:
            await Interpreter(machine).start()
        self.assertIn(
            "Cannot spawn 'badActor'. Source in `services` is not a valid MachineNode",
            str(cm.exception),
        )

    async def test_sending_invalid_event_type(self) -> None:
        """Should raise TypeError when sending an unsupported event type."""
        logger.info("🧪 Testing error for sending an invalid event type.")
        # 📋 Arrange
        interpreter = await Interpreter(
            create_machine({"id": "a", "initial": "b", "states": {"b": {}}})
        ).start()
        # 🚀 Act & Assert
        with self.assertRaises(TypeError) as cm:
            await interpreter.send(123)  # type: ignore
        self.assertIn(
            "Unsupported event type passed to send()", str(cm.exception)
        )
        await interpreter.stop()

    async def test_error_in_async_action_stops_event_loop(self) -> None:
        """An unhandled exception in an async action should stop the interpreter."""
        logger.info("🧪 Testing interpreter stops on unhandled action error.")

        # 📋 Arrange: An action that will raise a runtime error.
        async def failing_action(
            _i: Interpreter, _c: Dict[str, Any], _e: Any, _a: Any
        ) -> None:
            raise RuntimeError("Action failed!")

        machine = create_machine(
            {
                "id": "fail",
                "initial": "a",
                "states": {"a": {"entry": "failing"}},
            },
            logic=MachineLogic(actions={"failing": failing_action}),
        )
        interpreter = Interpreter(machine)

        # 🚀 Act & Assert: Starting the interpreter should propagate the error.
        with self.assertRaises(RuntimeError):
            await interpreter.start()
            if interpreter._event_loop_task:
                await interpreter._event_loop_task
        self.assertEqual(interpreter.status, "stopped")

    async def test_transition_action_error_stops_event_loop(self) -> None:
        """An error in a transition action should stop the event loop."""
        logger.info("🧪 Testing interpreter stops on transition action error.")

        # 📋 Arrange
        async def failing_action(
            _i: Interpreter, _c: Dict[str, Any], _e: Any, _a: Any
        ) -> Coroutine[Any, Any, None]:
            raise ValueError("Transition Action Failed")

        machine = create_machine(
            {
                "id": "fail_trans",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {"NEXT": {"target": "b", "actions": "failing"}}
                    },
                    "b": {},
                },
            },
            logic=MachineLogic(actions={"failing": failing_action}),
        )
        interpreter = await Interpreter(machine).start()

        # 🚀 Act: Trigger the failing action.
        await interpreter.send("NEXT")
        await asyncio.sleep(0.01)

        # ✅ Assert: The main event loop task should be done and contain the exception.
        self.assertTrue(interpreter._event_loop_task.done())
        with self.assertRaises(ValueError):
            await interpreter._event_loop_task

        self.assertEqual(interpreter.status, "stopped")


if __name__ == "__main__":
    unittest.main()
