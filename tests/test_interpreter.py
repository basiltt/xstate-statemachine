# tests/test_interpreter.py

# -----------------------------------------------------------------------------
# 🧪 Test Suite: Interpreter Runtime Execution
# -----------------------------------------------------------------------------
# This suite provides comprehensive testing for the Interpreter's runtime
# execution logic. It covers basic transitions, context manipulation, actions,
# guards, service invocation, delays, actor spawning, snapshots, and various
# error scenarios. Each test method is asynchronous and leverages the
# `IsolatedAsyncioTestCase` for proper event loop management.
# -----------------------------------------------------------------------------

import asyncio
import logging
import unittest
from typing import Any, Dict, Set
from unittest.mock import AsyncMock, MagicMock

from src.xstate_statemachine import (
    Interpreter,
    create_machine,
    MachineLogic,
    ImplementationMissingError,
    ActorSpawningError,
)
from xstate_statemachine import ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Test Helpers
# -----------------------------------------------------------------------------


async def cancel_all_tasks() -> None:
    """
    Cancels all running asyncio tasks except the current one.

    This helper is crucial for ensuring a clean slate between asynchronous tests,
    preventing "leaked" tasks from affecting subsequent tests.
    """
    current = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not current]
    if tasks:
        logger.info("🔄 Cancelling %d leftover task(s)...", len(tasks))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("✅ All leftover tasks cancelled.")


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestInterpreter
# -----------------------------------------------------------------------------


class TestInterpreter(unittest.IsolatedAsyncioTestCase):
    """
    Test suite for the Interpreter's asynchronous runtime execution logic.
    """

    guard_machine_config: Dict[str, Any]

    def setUp(self) -> None:
        """
        Sets up common configurations for guard-related tests.
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
        Tears down by cancelling any remaining asyncio tasks after each test.
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

        Args:
            interpreter (Interpreter): The interpreter instance under test.
            state_ids (Set[str]): A set of target state IDs to wait for.
            timeout (float): The maximum time in seconds to wait before failing.

        Raises:
            AssertionError: If the interpreter does not reach a target state.
        """
        logger.info(
            "🔍 Waiting for state(s) %s with timeout %.2fs",
            state_ids,
            timeout,
        )
        loop = asyncio.get_event_loop()
        start = loop.time()
        while True:
            if not interpreter.current_state_ids.isdisjoint(state_ids):
                logger.info(
                    "✅ Interpreter entered state(s) %s",
                    interpreter.current_state_ids,
                )
                return
            if loop.time() - start > timeout:
                self.fail(
                    f"⏰ Timed out waiting for {state_ids}, "
                    f"current: {interpreter.current_state_ids}"
                )
            await asyncio.sleep(0.01)

    # -------------------------------------------------------------------------
    # Tests: Simple Transitions
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Tests: Context and Actions
    # -------------------------------------------------------------------------
    async def test_context_and_actions(self) -> None:
        """Should execute actions that modify the machine's context."""
        mock_action = MagicMock()

        def increment_context(i, context, e, ad):
            context["count"] += 1

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
            logic=MachineLogic(actions={"increment": mock_action}),
        )
        interpreter = await Interpreter(machine_def).start()
        self.assertEqual(interpreter.context["count"], 0)

        await interpreter.send("INC")
        await asyncio.sleep(0.05)

        mock_action.assert_called_once()
        self.assertEqual(interpreter.context["count"], 1)

        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Tests: Guards
    # -------------------------------------------------------------------------
    async def test_guards(self) -> None:
        """Should block or allow transitions based on guard conditions."""
        # --- Scenario 1: Guard Fails ---
        logic_fail = MachineLogic(guards={"canLogin": lambda ctx, evt: False})
        interp_fail = await Interpreter(
            create_machine(self.guard_machine_config, logic=logic_fail)
        ).start()
        await interp_fail.send("LOGIN")
        await asyncio.sleep(0.05)
        self.assertEqual(interp_fail.current_state_ids, {"auth.idle"})
        await interp_fail.stop()

        # --- Scenario 2: Guard Passes ---
        logic_success = MachineLogic(
            guards={"canLogin": lambda ctx, evt: True}
        )
        interp_succ = await Interpreter(
            create_machine(self.guard_machine_config, logic=logic_success)
        ).start()
        await interp_succ.send("LOGIN")
        await self.wait_for_state(interp_succ, {"auth.success"})
        self.assertEqual(interp_succ.current_state_ids, {"auth.success"})
        await interp_succ.stop()

    # -------------------------------------------------------------------------
    # Tests: Service Invocation (invoke)
    # -------------------------------------------------------------------------
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
            logic=MachineLogic(services={"fetchUser": mock_service}),
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
            logic=MachineLogic(services={"fetchUser": mock_service}),
        )
        interpreter = await Interpreter(machine_def).start()
        await self.wait_for_state(interpreter, {"fetch.failure"})
        mock_service.assert_awaited_once()
        self.assertEqual(interpreter.current_state_ids, {"fetch.failure"})
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Tests: Delayed Transitions (after)
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Tests: Actor Spawning & Communication
    # -------------------------------------------------------------------------
    async def test_spawn_actor_and_communication(self) -> None:
        """Should spawn a child actor and allow communication."""
        child_machine = create_machine(
            {
                "id": "child",
                "initial": "active",
                "states": {"active": {"on": {"PING": {"actions": ["pong"]}}}},
            },
            logic=MachineLogic(
                actions={
                    "pong": lambda interp, ctx, evt, ad: asyncio.create_task(
                        interp.parent.send("PONG_RECEIVED")
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
            logic=parent_logic,
        )

        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"parent.spawning"})

        # ✅ FIX: Look for the spawned actor in the interpreter's internal `_actors`
        # dictionary instead of the context.
        child_interp = next(iter(interpreter._actors.values()), None)
        self.assertIsNotNone(child_interp)

        await child_interp.send("PING")
        await self.wait_for_state(interpreter, {"parent.ponged"})
        self.assertEqual(interpreter.current_state_ids, {"parent.ponged"})
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Tests: Snapshot & Restore
    # -------------------------------------------------------------------------
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
            logic=MachineLogic(
                actions={
                    "setData": lambda i, c, e, a: c.update({"data": "updated"})
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

    # -------------------------------------------------------------------------
    # Tests: Internal Transitions & Multiple Actions
    # -------------------------------------------------------------------------
    async def test_internal_transition_without_target(self) -> None:
        """Should execute actions on a transition without changing state."""
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

        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)

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
            logic=MachineLogic(
                actions={"action1": action1, "action2": action2}
            ),
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)
        action1.assert_called_once()
        action2.assert_called_once()
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Tests: Entry and Exit Actions
    # -------------------------------------------------------------------------
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
            logic=MachineLogic(
                actions={"onEnterB": entry_action, "onExitA": exit_action}
            ),
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"entryExit.b"})
        exit_action.assert_called_once()
        entry_action.assert_called_once()
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Tests: Parallel States
    # -------------------------------------------------------------------------
    async def test_parallel_state_onDone(self) -> None:
        """`onDone` on a parallel state should fire only when all regions are done."""
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
        self.assertEqual(
            interpreter.current_state_ids,
            {"parallel.active.a.a1", "parallel.active.b.b1"},
        )
        await interpreter.send("A_DONE")
        await self.wait_for_state(interpreter, {"parallel.active.a.a2"})
        self.assertNotIn("parallel.finished", interpreter.current_state_ids)
        await interpreter.send("B_DONE")
        await self.wait_for_state(interpreter, {"parallel.finished"})
        self.assertEqual(interpreter.current_state_ids, {"parallel.finished"})
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Tests: Deeply Nested Transitions
    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Tests: Event Payload Passing
    # -------------------------------------------------------------------------
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
        await interpreter.send("EVENT", **test_payload)
        await asyncio.sleep(0.01)

        mock_guard.assert_called_once()
        guard_args = mock_guard.call_args[0]
        self.assertEqual(guard_args[1].payload, test_payload)

        mock_action.assert_called_once()
        action_args = mock_action.call_args[0]
        self.assertEqual(action_args[2].payload, test_payload)
        await interpreter.stop()

    # -------------------------------------------------------------------------
    # Tests: Error Handling for Missing Implementations
    # -------------------------------------------------------------------------
    async def test_raises_error_for_missing_guard_implementation(self) -> None:
        """Should raise ImplementationMissingError if a guard is not defined."""
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {"a": {"on": {"EVENT": {"guard": "nonexistent"}}}},
            },
            logic=MachineLogic(),
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send("EVENT")
        await asyncio.sleep(0.01)

        task = interpreter._event_loop_task
        self.assertTrue(task.done())
        with self.assertRaises(ImplementationMissingError) as cm:
            task.result()

        # ✅ FIX: Updated assertion to match the actual exception message.
        self.assertIn(
            "Guard 'nonexistent' not implemented.", str(cm.exception)
        )
        await interpreter.stop()

    async def test_raises_error_for_missing_service_implementation(
        self,
    ) -> None:
        """Should raise ImplementationMissingError if a service is not defined."""
        machine = create_machine(
            {
                "id": "missing",
                "initial": "a",
                "states": {"a": {"invoke": {"src": "nonexistent"}}},
            },
            logic=MachineLogic(),
        )
        with self.assertRaises(ImplementationMissingError) as cm:
            await Interpreter(machine).start()

        # FIX: Updated assertion to match the actual, more specific exception message.
        self.assertIn(
            "Service 'nonexistent' referenced by state 'missing.a' is not registered.",
            str(cm.exception),
        )

    async def test_spawn_actor_fails_for_non_machine_service(self) -> None:
        """Should raise ActorSpawningError if spawning a non-MachineNode."""

        def bad_actor_service(i, c, e):
            return "not a machine"

        machine = create_machine(
            {
                "id": "spawner",
                "initial": "active",
                "states": {"active": {"entry": "spawn_badActor"}},
            },
            logic=MachineLogic(services={"badActor": bad_actor_service}),
        )
        with self.assertRaises(ActorSpawningError) as cm:
            await Interpreter(machine).start()

        # ✅ FIX: Update the assertion to match the new, more descriptive error message.
        self.assertIn(
            "Cannot spawn 'badActor'. Source in `services` is not a valid MachineNode or a function that returns one.",
            str(cm.exception),
        )

    async def test_sending_invalid_event_type(self) -> None:
        """Should raise TypeError when sending an unsupported event type."""
        interpreter = await Interpreter(
            create_machine({"id": "a", "initial": "b", "states": {"b": {}}})
        ).start()
        with self.assertRaises(TypeError) as cm:
            await interpreter.send(123)
        self.assertIn(
            "Unsupported event type passed to send()", str(cm.exception)
        )
        await interpreter.stop()

    async def test_invoke_is_cancelled_on_state_exit(self) -> None:
        """An invoked service should be cancelled when its state is exited."""
        fut = asyncio.Future()

        # FIX: Define the mock's side_effect as a coroutine function that awaits
        # the future. This ensures the service task blocks as intended.
        async def long_service_coro(*args, **kwargs):
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
        # Allow the event loop to run and register the task
        await asyncio.sleep(0.01)

        tasks = list(
            interpreter.task_manager._tasks_by_owner.get(
                "canceller.working", []
            )
        )
        self.assertEqual(len(tasks), 1)
        invoke_task = tasks[0]

        await interpreter.send("CANCEL")
        await self.wait_for_state(interpreter, {"canceller.cancelled"})

        # Assert that the task object we captured has been cancelled.
        self.assertTrue(invoke_task.cancelled())
        await interpreter.stop()

    async def test_after_timer_is_cancelled_on_state_exit(self) -> None:
        """A delayed 'after' transition should be cancelled on state exit."""
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
                interpreter.task_manager._tasks_by_owner[
                    "timer_canceller.waiting"
                ]
            ),
            1,
        )

        await interpreter.send("EARLY_EXIT")
        await self.wait_for_state(interpreter, {"timer_canceller.exited"})

        # After exiting 'waiting', the tasks for that owner should be gone
        self.assertEqual(
            len(
                interpreter.task_manager._tasks_by_owner.get(
                    "timer_canceller.waiting", []
                )
            ),
            0,
        )
        await interpreter.stop()

    async def test_parent_stopping_stops_child_actor(self) -> None:
        """When a parent interpreter stops, it should stop its child actors."""
        child_machine = create_machine(
            {"id": "child", "initial": "active", "states": {"active": {}}}
        )
        parent_machine = create_machine(
            {
                "id": "parent",
                "initial": "running",
                "states": {"running": {"entry": "spawn_child"}},
            },
            logic=MachineLogic(services={"child": child_machine}),
        )
        parent_interp = await Interpreter(parent_machine).start()
        await self.wait_for_state(parent_interp, {"parent.running"})
        self.assertEqual(len(parent_interp._actors), 1)

        child_interp = list(parent_interp._actors.values())[0]
        self.assertEqual(child_interp.status, "running")

        await parent_interp.stop()
        self.assertEqual(parent_interp.status, "stopped")
        self.assertEqual(child_interp.status, "stopped")

    async def test_eventless_transition_is_processed_async(self) -> None:
        """The async interpreter should also handle event-less transitions."""
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
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"async_transient.c"})
        self.assertEqual(interpreter.current_state_ids, {"async_transient.c"})
        await interpreter.stop()

    async def test_guarded_onDone_transition(self) -> None:
        """Should respect guards on onDone transitions."""
        mock_service = AsyncMock(return_value="data")
        logic = MachineLogic(
            services={"serv": mock_service},
            guards={"check": lambda c, e: c["allow"]},
        )
        # ✅ FIX: Pass the logic object to the machine.
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
        )  # Pass the logic here
        interpreter = await Interpreter(machine).start()
        await asyncio.sleep(0.1)
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_done.working"}
        )
        await interpreter.stop()

    async def test_async_action_can_send_event(self) -> None:
        """An async action should be able to send an event back to the machine."""

        async def action_sends(interp, ctx, evt, ad):
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
        await interpreter.send("START")
        await self.wait_for_state(interpreter, {"action_sender.c"})
        self.assertEqual(interpreter.current_state_ids, {"action_sender.c"})
        await interpreter.stop()

    async def test_error_in_async_action_stops_event_loop(self) -> None:
        """An unhandled exception in an async action should stop the interpreter."""

        async def failing_action(i, c, e, a):
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
        with self.assertRaises(RuntimeError):
            await interpreter.start()
            # ✅ FIX: Await the task to allow the exception to propagate.
            if interpreter._event_loop_task:
                await interpreter._event_loop_task

        self.assertEqual(interpreter.status, "stopped")

    async def test_complex_on_done_bubbling_async(self):
        """A nested final state should correctly bubble up to trigger a parent's onDone."""
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
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"m.s2"})
        self.assertEqual(interpreter.current_state_ids, {"m.s2"})
        await interpreter.stop()

    async def test_snapshot_of_parallel_state_async(self) -> None:
        """Should correctly snapshot and restore a machine in a parallel state."""
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
        snapshot = interpreter.get_snapshot()
        await interpreter.stop()

        restored = Interpreter.from_snapshot(snapshot, machine)
        self.assertEqual(
            restored.current_state_ids, {"m.p1.a.a1", "m.p1.b.b1"}
        )

    async def test_invoke_with_input_from_context(self) -> None:
        """Invoked service should receive static input defined in the machine."""

        async def check_input_service(i, c, e):
            # The 'input' from the invoke config is passed in the invoke event payload
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

        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"invoke_input.success"})
        mock_service.assert_awaited_once()
        await interpreter.stop()

    async def test_invoke_onError_transition_is_guarded(self) -> None:
        """A guarded onError transition should be blocked if the guard fails."""
        mock_service = AsyncMock(side_effect=RuntimeError("Service Failed"))
        logic = MachineLogic(
            services={"failingService": mock_service},
            guards={"shouldHandleError": lambda c, e: False},
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
        await asyncio.sleep(0.1)  # Allow service to fail

        # FIX: The interpreter should remain in the 'working' state and its event loop
        # should still be running because the error was handled internally.
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_error.working"}
        )
        self.assertFalse(interpreter._event_loop_task.done())
        self.assertEqual(interpreter.status, "running")

        await interpreter.stop()

    async def test_invoke_chooses_correct_guarded_onDone(self) -> None:
        """Should choose the correct onDone transition based on service output and guards."""

        async def service_returns_value(i, c, e):
            return {"value": 25}

        logic = MachineLogic(
            services={"valueService": service_returns_value},
            guards={
                "isLow": lambda c, e: e.data["value"] < 20,
                "isMed": lambda c, e: e.data["value"] < 30,
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

        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"guarded_choice.medium"})
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_choice.medium"}
        )
        await interpreter.stop()

    async def test_multiple_after_timers_in_one_state(self) -> None:
        """Should fire the shortest timer when multiple 'after' timers exist."""
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
        interpreter = await Interpreter(machine).start()
        await self.wait_for_state(interpreter, {"multi_timer.fastest"})
        self.assertEqual(
            interpreter.current_state_ids, {"multi_timer.fastest"}
        )
        await interpreter.stop()

    async def test_after_transition_is_guarded(self) -> None:
        """A guarded 'after' transition should not fire if the guard fails."""
        logic = MachineLogic(guards={"shouldFire": lambda c, e: False})
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
        await asyncio.sleep(0.1)
        # Stays in 'waiting' because the guard blocked the transition
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_after.waiting"}
        )
        await interpreter.stop()

    async def test_guarded_eventless_transition_async(self) -> None:
        """A guarded event-less transition should only be taken if the guard passes."""
        logic = MachineLogic(guards={"shouldGo": lambda c, e: c["go"]})
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
        await interpreter.send("NEXT")
        await self.wait_for_state(interpreter, {"guarded_transient.c"})
        self.assertEqual(
            interpreter.current_state_ids, {"guarded_transient.c"}
        )
        await interpreter.stop()

    async def test_self_transition_executes_entry_exit_actions(self) -> None:
        """An external self-transition should re-execute its entry/exit actions."""
        exit_action = MagicMock()
        entry_action = MagicMock()
        logic = MachineLogic(
            actions={"onExit": exit_action, "onEnter": entry_action}
        )
        machine = create_machine(
            {
                "id": "self_trans",
                "initial": "active",
                "states": {
                    "active": {
                        # FIX: Use a relative target ('.active') to define an external transition
                        # that exits and re-enters the state.
                        "on": {"LOOP": {"target": ".active"}},
                        "entry": "onEnter",
                        "exit": "onExit",
                    }
                },
            },
            logic=logic,
        )

        interpreter = await Interpreter(machine).start()
        # The initial entry action is called once on start.
        entry_action.assert_called_once()

        # Send the event to trigger the self-transition.
        await interpreter.send("LOOP")
        await asyncio.sleep(0.01)

        # The exit action should now have been called once, and the entry action a total of twice.
        self.assertEqual(exit_action.call_count, 1)
        self.assertEqual(entry_action.call_count, 2)
        await interpreter.stop()

    async def test_event_handled_by_ancestor_state(self) -> None:
        """An event should be handled by an ancestor if not handled by the current state."""
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

        await interpreter.send("GOTO_B")
        await self.wait_for_state(interpreter, {"ancestor_handler.b"})
        self.assertEqual(interpreter.current_state_ids, {"ancestor_handler.b"})
        await interpreter.stop()

    async def test_actor_onDone_is_triggered_on_child_final_state(
        self,
    ) -> None:
        """Parent should transition when a spawned actor with its own logic reaches a final state."""
        # FIX: The child's logic (including the action to notify the parent) must be
        # defined with the child machine itself.
        child_logic = MachineLogic(
            actions={
                "notifyParentDone": lambda i, c, e, a: asyncio.create_task(
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
                    # The action must be defined on the state where it's executed.
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
            logic=MachineLogic(services={"childActor": child_machine}),
        )

        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"parent.spawning"})

        self.assertEqual(len(interpreter._actors), 1)
        child_interp = next(iter(interpreter._actors.values()))
        await child_interp.send("FINISH")

        await self.wait_for_state(interpreter, {"parent.child_finished"})
        self.assertEqual(
            interpreter.current_state_ids, {"parent.child_finished"}
        )
        await interpreter.stop()

    async def test_parent_stop_cancels_multiple_child_actors(self) -> None:
        """Stopping a parent should stop all of its spawned child actors."""
        child_machine_1 = create_machine(
            {"id": "child1", "initial": "a", "states": {"a": {}}}
        )
        child_machine_2 = create_machine(
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
                services={"child1": child_machine_1, "child2": child_machine_2}
            ),
        )

        interpreter = await Interpreter(parent_machine).start()
        await self.wait_for_state(interpreter, {"multi_parent.running"})
        self.assertEqual(len(interpreter._actors), 2)

        actors = list(interpreter._actors.values())
        self.assertEqual(actors[0].status, "running")
        self.assertEqual(actors[1].status, "running")

        await interpreter.stop()
        self.assertEqual(actors[0].status, "stopped")
        self.assertEqual(actors[1].status, "stopped")

    async def test_send_on_unstarted_interpreter(self) -> None:
        """Events sent to an unstarted interpreter should be queued and processed on start."""
        machine = create_machine(
            {
                "id": "q",
                "initial": "a",
                "states": {"a": {"on": {"NEXT": "b"}}, "b": {}},
            }
        )
        interpreter = Interpreter(machine)

        # Send event before starting
        await interpreter.send("NEXT")

        self.assertEqual(interpreter.status, "uninitialized")
        self.assertEqual(interpreter.current_state_ids, set())

        # Start the interpreter
        await interpreter.start()

        # The queued event should be processed
        await self.wait_for_state(interpreter, {"q.b"})
        self.assertEqual(interpreter.current_state_ids, {"q.b"})
        await interpreter.stop()

    async def test_start_on_running_interpreter_is_noop(self) -> None:
        """Calling start() on an already running interpreter should do nothing."""
        machine = create_machine(
            {"id": "test", "initial": "a", "states": {"a": {}}}
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.status, "running")

        # Spy on the _enter_states method to ensure it's not called again
        interpreter._enter_states = AsyncMock()  # type: ignore

        await interpreter.start()
        interpreter._enter_states.assert_not_called()
        await interpreter.stop()

    async def test_stop_on_stopped_interpreter_is_noop(self) -> None:
        """Calling stop() on an already stopped interpreter should do nothing."""
        machine = create_machine(
            {"id": "test", "initial": "a", "states": {"a": {}}}
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.stop()
        self.assertEqual(interpreter.status, "stopped")

        # Spy on the task_manager to ensure it's not cancelled again
        interpreter.task_manager.cancel_all = AsyncMock()  # type: ignore
        await interpreter.stop()
        interpreter.task_manager.cancel_all.assert_not_called()

    async def test_snapshot_does_not_restore_transient_tasks(self) -> None:
        """Snapshot and restore should not persist 'after' timers."""
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

        restored = Interpreter.from_snapshot(snapshot, machine)
        # Manually start the restored interpreter's event loop for the test
        restored._event_loop_task = asyncio.create_task(
            restored._run_event_loop()
        )

        await asyncio.sleep(0.2)  # Wait longer than the original timer
        # State should not have changed, as the timer was not restored
        self.assertEqual(restored.current_state_ids, {"snap_after.waiting"})
        await restored.stop()

    async def test_unhandled_event_is_ignored(self) -> None:
        """Sending an event with no matching transition should result in no state change."""
        machine = create_machine(
            {
                "id": "unhandled",
                "initial": "a",
                "states": {"a": {"on": {"REAL_EVENT": "b"}}, "b": {}},
            }
        )
        interpreter = await Interpreter(machine).start()
        self.assertEqual(interpreter.current_state_ids, {"unhandled.a"})

        # Send an event that is not handled in state 'a'
        await interpreter.send("FAKE_EVENT")
        await asyncio.sleep(0.01)

        # The state should remain 'a'
        self.assertEqual(interpreter.current_state_ids, {"unhandled.a"})
        await interpreter.stop()

    async def test_final_state_in_parallel_machine_triggers_onDone(
        self,
    ) -> None:
        """A final state in one region of a parallel state should not trigger onDone alone."""
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
        await interpreter.send("FINISH_A")
        await self.wait_for_state(interpreter, {"p_final.a.a2"})
        # The machine is NOT done because region 'b' is not in a final state
        self.assertNotEqual(
            interpreter.current_state_ids, {"p_final.finished"}
        )
        self.assertTrue(interpreter.status, "running")
        await interpreter.stop()

    async def test_send_dict_event_object(self) -> None:
        """Should correctly process an event sent as a dictionary."""
        machine = create_machine(
            {
                "id": "dict_event",
                "initial": "a",
                "states": {"a": {"on": {"NEXT": "b"}}, "b": {}},
            }
        )
        interpreter = await Interpreter(machine).start()
        await interpreter.send({"type": "NEXT", "value": 123})
        await self.wait_for_state(interpreter, {"dict_event.b"})
        self.assertEqual(interpreter.current_state_ids, {"dict_event.b"})
        await interpreter.stop()

    async def test_interpreter_id_matches_machine_id(self) -> None:
        """The interpreter's ID should be initialized from the machine's ID."""
        machine = create_machine(
            {"id": "my-special-id", "initial": "a", "states": {"a": {}}}
        )
        interpreter = Interpreter(machine)
        self.assertEqual(interpreter.id, "my-special-id")

    async def test_transition_action_error_stops_event_loop(self) -> None:
        """An error in a transition action should stop the event loop."""

        async def failing_action(i, c, e, a):
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
        await interpreter.send("NEXT")
        await asyncio.sleep(0.01)  # Allow event loop to process

        self.assertTrue(interpreter._event_loop_task.done())
        with self.assertRaises(ValueError):
            await interpreter._event_loop_task

        self.assertEqual(interpreter.status, "stopped")


if __name__ == "__main__":
    unittest.main()
