"""
tests/test_internals.py
------------------------
Refactored test suite for plugins, exceptions, and TaskManager internals.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import unittest
from typing import Any, Set

from unittest.mock import MagicMock

from src.xstate_statemachine import (
    PluginBase,
    LoggingInspector,
    Event,
    ImplementationMissingError,
    XStateMachineError,
)
from src.xstate_statemachine.events import DoneEvent
from src.xstate_statemachine.task_manager import TaskManager
from xstate_statemachine import StateNotFoundError

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# To enable console output, uncomment:
# handler = logging.StreamHandler()
# handler.setLevel(logging.INFO)
# handler.setFormatter(
#     logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
# )
# logger.addHandler(handler)


# -----------------------------------------------------------------------------
# Tests: Plugin System
# -----------------------------------------------------------------------------
class TestPlugins(unittest.TestCase):
    """
    Test suite for the plugin system and built-in plugins.

    This suite ensures that the `PluginBase` class provides no-op default
    implementations for its methods, preventing unintended side effects or
    errors if subclasses don't override them. It also verifies that the
    `LoggingInspector` correctly handles various event types without crashing,
    ensuring robust logging behavior.
    """

    def test_plugin_base_methods_do_not_raise_errors(self) -> None:
        """
        The base PluginBase methods should execute without error.

        Verifies that the default implementations of `PluginBase` methods
        are simple no-operations and do not raise any exceptions when called,
        confirming their role as abstract base class placeholders.
        """
        logger.info("🚀 Testing PluginBase no-op methods...")
        plugin = PluginBase()
        try:
            # 🧪 Call each method of PluginBase with dummy arguments
            plugin.on_interpreter_start(None)  # Start hook
            plugin.on_interpreter_stop(None)  # Stop hook
            plugin.on_event_received(
                None, Event("TEST")
            )  # Event received hook
            plugin.on_transition(
                None, set(), set(), None
            )  # Transition hook (from_states, to_states, event)
            plugin.on_action_execute(None, None)  # Action execution hook
        except Exception as ex:
            # ❌ Fail the test if any unexpected exception is caught
            logger.error(
                "❌ PluginBase method raised an unexpected exception: %s", ex
            )
            self.fail("PluginBase methods raised an unexpected exception.")
        logger.info("✅ PluginBase no-op methods passed without errors.")

    def test_logging_inspector_handles_various_events(self) -> None:
        """
        LoggingInspector should not crash on different event types.

        This test specifically checks the robustness of `LoggingInspector.on_event_received`
        by feeding it various `Event` and `DoneEvent` types, including those with
        and without payloads, to ensure it processes them gracefully without errors.
        """
        logger.info(
            "🚀 Testing LoggingInspector event handling for various types..."
        )
        inspector = LoggingInspector()
        # Create a mock interpreter as it's typically passed to plugin methods
        mock_interp = MagicMock()
        mock_interp.context = {"value": 1}  # Simulate some context

        try:
            # 🧪 Test with a standard Event with a payload
            logger.debug("   Sending standard Event with payload...")
            inspector.on_event_received(
                mock_interp, Event("TEST_EVENT", payload={"data": "test_data"})
            )

            # 🧪 Test with a DoneEvent (used for service completion)
            logger.debug("   Sending DoneEvent...")
            inspector.on_event_received(
                mock_interp,
                DoneEvent(
                    "done.invoke.test_service",
                    data={"result": "success"},
                    src="test_service",
                ),
            )

            # 🧪 Test with a simple Event (no payload)
            logger.debug("   Sending simple Event without payload...")
            inspector.on_event_received(mock_interp, Event("SIMPLE_EVENT"))

        except Exception as ex:
            # ❌ Fail the test if any unexpected exception is caught
            logger.error(
                "❌ LoggingInspector failed to handle event: %s",
                ex,
                exc_info=True,
            )
            self.fail(
                "LoggingInspector failed to handle different event types gracefully."
            )
        logger.info(
            "✅ LoggingInspector handled all tested event types without crashing."
        )

    def test_logging_inspector_on_transition(self) -> None:
        """Ensures LoggingInspector's on_transition method runs without error."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        mock_interp.context = {"value": 1}

        # Mock StateNode and TransitionDefinition for the call
        from_state = MagicMock()
        from_state.id = "state.a"
        from_state.is_atomic = True
        from_state.is_final = False

        to_state = MagicMock()
        to_state.id = "state.b"
        to_state.is_atomic = True
        to_state.is_final = False

        transition = MagicMock()
        transition.event = "TEST_EVENT"

        try:
            inspector.on_transition(
                mock_interp, {from_state}, {to_state}, transition
            )
        except Exception as ex:
            self.fail(
                f"LoggingInspector.on_transition raised an unexpected exception: {ex}"
            )

    def test_logging_inspector_on_action_execute(self) -> None:
        """Ensures LoggingInspector's on_action_execute method runs without error."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        action_def = MagicMock()
        action_def.type = "testAction"

        try:
            inspector.on_action_execute(mock_interp, action_def)
        except Exception as ex:
            self.fail(
                f"LoggingInspector.on_action_execute raised an unexpected exception: {ex}"
            )

    def test_logging_inspector_with_primitive_payload(self) -> None:
        """LoggingInspector should handle non-dict payloads gracefully."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        mock_interp.context = {}

        try:
            # Test with a string payload
            inspector.on_event_received(
                mock_interp,
                Event("EVENT_WITH_STRING", payload="a string value"),
            )
            # Test with an integer payload
            inspector.on_event_received(
                mock_interp, Event("EVENT_WITH_INT", payload=123)
            )
        except Exception as ex:
            self.fail(
                f"LoggingInspector failed to handle primitive payloads: {ex}"
            )

    def test_custom_plugin_hooks_are_callable(self) -> None:
        """A custom plugin's overridden methods should be callable."""
        call_order = []

        class CustomPlugin(PluginBase):
            def on_interpreter_start(self, interpreter: Any) -> None:
                call_order.append("start")

            def on_event_received(
                self, interpreter: Any, event: Event
            ) -> None:
                call_order.append("event")

            def on_action_execute(self, interpreter: Any, action: Any) -> None:
                call_order.append("action")

            def on_transition(
                self,
                interpreter: Any,
                from_states: Set[Any],
                to_states: Set[Any],
                transition: Any,
            ) -> None:
                call_order.append("transition")

            def on_interpreter_stop(self, interpreter: Any) -> None:
                call_order.append("stop")

        plugin = CustomPlugin()
        plugin.on_interpreter_start(None)
        plugin.on_event_received(None, Event("test"))
        plugin.on_action_execute(None, None)
        plugin.on_transition(None, set(), set(), None)
        plugin.on_interpreter_stop(None)

        self.assertEqual(
            call_order, ["start", "event", "action", "transition", "stop"]
        )

    def test_logging_inspector_handles_internal_transition(self) -> None:
        """LoggingInspector should log context changes on internal transitions."""
        inspector = LoggingInspector()
        mock_interp = MagicMock()
        mock_interp.context = {"count": 10}

        state_node = MagicMock()
        state_node.id = "state.a"
        state_node.is_atomic = True
        state_node.is_final = False

        transition = MagicMock()
        transition.event = "INTERNAL_EVENT"
        transition.actions = [
            "someAction"
        ]  # An internal transition must have actions

        # For an internal transition, from_states and to_states are the same
        try:
            inspector.on_transition(
                mock_interp, {state_node}, {state_node}, transition
            )
        except Exception as ex:
            self.fail(f"LoggingInspector failed on internal transition: {ex}")


# -----------------------------------------------------------------------------
# Tests: Exception Hierarchy
# -----------------------------------------------------------------------------
class TestExceptions(unittest.TestCase):
    """
    Test suite for the custom exception hierarchy within the XState machine library.

    This suite specifically validates that custom exceptions, like `ImplementationMissingError`,
    correctly inherit from the base `XStateMachineError`, ensuring a consistent and
    predictable error handling structure for users of the library.
    """

    def test_custom_exception_hierarchy(self) -> None:
        """
        Ensures ImplementationMissingError inherits from XStateMachineError.

        This assertion verifies the designed inheritance relationship, which is
        crucial for allowing users to catch all library-specific errors using
        a single base exception type.
        """
        logger.info("🚀 Testing custom exception hierarchy...")
        # 🧪 Check if ImplementationMissingError is a subclass of XStateMachineError
        is_sub = issubclass(ImplementationMissingError, XStateMachineError)
        self.assertTrue(
            is_sub,
            "ImplementationMissingError should subclass XStateMachineError to maintain hierarchy",
        )
        if is_sub:
            logger.info(
                "✅ Exception hierarchy is correct: ImplementationMissingError inherits from XStateMachineError."
            )
        else:
            logger.error(
                "❌ Exception hierarchy is incorrect: ImplementationMissingError does NOT inherit from XStateMachineError."
            )

    def test_all_custom_exceptions_inherit_from_base(self) -> None:
        """Ensures all defined custom exceptions inherit from XStateMachineError."""
        from src.xstate_statemachine import exceptions

        custom_exceptions = [
            exceptions.InvalidConfigError,
            exceptions.StateNotFoundError,
            exceptions.ImplementationMissingError,
            exceptions.ActorSpawningError,
            exceptions.NotSupportedError,
        ]

        for exc in custom_exceptions:
            with self.subTest(exception=exc.__name__):
                self.assertTrue(issubclass(exc, XStateMachineError))

    def test_state_not_found_error_message_with_reference(self) -> None:
        """StateNotFoundError should format its message correctly with a reference state."""
        err = StateNotFoundError(
            target=".unknown", reference_id="parent.state"
        )
        expected_msg = "Could not resolve target state '.unknown' from state 'parent.state'."
        self.assertEqual(str(err), expected_msg)
        self.assertEqual(err.target, ".unknown")
        self.assertEqual(err.reference_id, "parent.state")

    def test_state_not_found_error_message_without_reference(self) -> None:
        """StateNotFoundError should format its message correctly without a reference state."""
        err = StateNotFoundError(target="nonexistent")
        expected_msg = "Could not resolve target state 'nonexistent'."
        self.assertEqual(str(err), expected_msg)
        self.assertEqual(err.target, "nonexistent")
        self.assertIsNone(err.reference_id)


# -----------------------------------------------------------------------------
# Tests: TaskManager
# -----------------------------------------------------------------------------
class TestTaskManager(unittest.IsolatedAsyncioTestCase):
    """
    Asynchronous test suite for the `TaskManager` utility class.

    This suite covers the core functionalities of `TaskManager`, including
    adding and tracking asyncio tasks, canceling tasks by specific owners,
    canceling all tracked tasks, and verifying that tasks are automatically
    removed from tracking upon their natural completion.
    """

    async def test_add_and_cancel_all(self) -> None:
        """
        Should add tasks to the manager and successfully cancel all of them.

        Verifies the `TaskManager`'s global cancellation functionality,
        ensuring that all tracked tasks are cancelled when `cancel_all()` is invoked.
        """
        logger.info("🚀 Testing TaskManager.add() and .cancel_all()...")
        tm = TaskManager()
        # 🧪 Create dummy asyncio tasks that run for a short duration
        task1 = asyncio.create_task(asyncio.sleep(0.1))
        task2 = asyncio.create_task(asyncio.sleep(0.1))

        # 📝 Add tasks to the TaskManager under different owners
        tm.add("owner1", task1)
        tm.add("owner2", task2)

        # 🚧 Assert that tasks are not yet done or cancelled initially
        self.assertFalse(
            task1.done(), "Task1 should not be done yet before cancellation"
        )
        self.assertFalse(
            task2.done(), "Task2 should not be done yet before cancellation"
        )
        logger.debug(
            "Tasks added to TaskManager. Initial state: Task1 done=%s, Task2 done=%s",
            task1.done(),
            task2.done(),
        )

        await tm.cancel_all()  # 📝 Invoke global cancellation

        # ✅ Assert that both tasks are now cancelled
        self.assertTrue(
            task1.cancelled(), "Task1 should be cancelled after cancel_all"
        )
        self.assertTrue(
            task2.cancelled(), "Task2 should be cancelled after cancel_all"
        )
        logger.info("✅ All tasks successfully cancelled by .cancel_all().")

    async def test_cancel_by_owner(self) -> None:
        """
        Should cancel tasks specifically associated with a given owner.

        Ensures that `cancel_by_owner()` precisely targets and cancels only
        those tasks belonging to the specified owner, leaving others unaffected.
        """
        logger.info("🚀 Testing TaskManager.cancel_by_owner()...")
        tm = TaskManager()
        # 🧪 Create three dummy tasks, two for 'owner1' and one for 'owner2'
        t1 = asyncio.create_task(asyncio.sleep(0.1))
        t2 = asyncio.create_task(asyncio.sleep(0.1))
        t3 = asyncio.create_task(asyncio.sleep(0.1))

        # 📝 Add tasks, associating them with their respective owners
        tm.add("owner1", t1)
        tm.add("owner1", t2)
        tm.add("owner2", t3)
        logger.debug("Tasks added. t1, t2 for owner1; t3 for owner2.")

        tm.cancel_by_owner("owner1")  # 📝 Cancel only tasks for 'owner1'
        await asyncio.sleep(
            0.01
        )  # ⏳ Allow a moment for cancellation to process

        # ✅ Assert that tasks for 'owner1' are cancelled
        self.assertTrue(t1.cancelled(), "t1 (owner1) should be cancelled")
        self.assertTrue(t2.cancelled(), "t2 (owner1) should be cancelled")
        # 🚧 Assert that tasks for 'owner2' remain active (not done/cancelled)
        self.assertFalse(
            t3.done(), "t3 (owner2) should remain active and not done"
        )
        self.assertFalse(t3.cancelled(), "t3 (owner2) should not be cancelled")
        logger.info(
            "✅ .cancel_by_owner() successfully cancelled tasks for the specified owner, leaving others untouched."
        )

        await tm.cancel_all()  # 🔄 Clean up any remaining active tasks to ensure a clean test environment

    async def test_task_removes_itself_on_completion(self) -> None:
        """
        Tasks should be automatically removed from tracking upon their natural completion.

        Verifies that the `TaskManager` uses done callbacks to automatically
        clean up references to tasks once they finish executing, preventing memory
        leaks and ensuring the manager only tracks active tasks.
        """
        logger.info(
            "🚀 Testing automatic task removal from TaskManager on natural completion..."
        )
        tm = TaskManager()
        # 🧪 Create a short-lived task that will complete naturally
        task = asyncio.create_task(asyncio.sleep(0.01))

        tm.add("owner", task)  # 📝 Add the task to be tracked
        # 🚧 Assert that the task is initially being tracked
        self.assertEqual(
            len(tm._tasks_by_owner.get("owner", [])),
            1,
            "TaskManager should track one task initially",
        )
        logger.debug(
            "Task added to TaskManager. Currently tracking: %s",
            tm._tasks_by_owner,
        )

        await task  # ⏳ Wait for the task to complete naturally

        # ✅ After natural completion, assert that the TaskManager has removed its reference
        # The owner entry might disappear entirely if it was the last task for that owner.
        self.assertEqual(
            len(tm._tasks_by_owner.get("owner", [])),
            0,
            "Task should be automatically removed from TaskManager after natural completion",
        )
        logger.info(
            "✅ Automatic task removal on completion works as expected."
        )

    async def test_cancel_by_owner_on_nonexistent_owner(self) -> None:
        """Should not raise an error when cancelling tasks for an owner that does not exist."""
        tm = TaskManager()
        try:
            tm.cancel_by_owner("nonexistent_owner")
        except Exception as ex:
            self.fail(
                f"Cancelling a nonexistent owner raised an exception: {ex}"
            )

    async def test_cancel_all_on_empty_manager(self) -> None:
        """Should execute without error when cancel_all is called on an empty TaskManager."""
        tm = TaskManager()
        try:
            await tm.cancel_all()
        except Exception as ex:
            self.fail(
                f"cancel_all on an empty manager raised an exception: {ex}"
            )

    async def test_add_already_completed_task(self) -> None:
        """Should handle adding a task that is already complete."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0))
        await task  # Ensure task is complete

        tm.add("owner", task)
        # Yield to the event loop to allow the done_callback to fire
        await asyncio.sleep(0)

        # Now the task should be removed
        self.assertEqual(len(tm._tasks_by_owner.get("owner", [])), 0)

    async def test_cancel_all_with_mixed_task_states(self) -> None:
        """Should correctly cancel pending tasks while ignoring completed ones."""
        tm = TaskManager()

        pending_task = asyncio.create_task(asyncio.sleep(0.1))
        completed_task = asyncio.create_task(asyncio.sleep(0))
        await completed_task

        tm.add("owner1", pending_task)
        tm.add("owner2", completed_task)

        await tm.cancel_all()

        self.assertTrue(pending_task.cancelled())
        self.assertTrue(
            completed_task.done() and not completed_task.cancelled()
        )

    async def test_reuse_owner_id_after_completion(self) -> None:
        """Should allow reusing an owner ID after its previous tasks have completed."""
        tm = TaskManager()
        task1 = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("reusable_owner", task1)
        await task1

        self.assertEqual(len(tm._tasks_by_owner.get("reusable_owner", [])), 0)

        task2 = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("reusable_owner", task2)
        self.assertEqual(len(tm._tasks_by_owner.get("reusable_owner", [])), 1)

        await tm.cancel_all()

    async def test_cancel_by_owner_on_empty_task_set(self) -> None:
        """Should not fail if cancel_by_owner is called for an owner with no active tasks."""
        tm = TaskManager()
        tm.add("owner_with_no_tasks", asyncio.create_task(asyncio.sleep(0)))
        await asyncio.sleep(0.01)  # Let task complete and be removed

        try:
            tm.cancel_by_owner("owner_with_no_tasks")
        except Exception as ex:
            self.fail(
                f"cancel_by_owner on an owner with no tasks failed: {ex}"
            )

    async def test_removal_of_cancelled_tasks(self) -> None:
        """The owner's task set should be empty after its tasks are cancelled by owner."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("owner_to_cancel", task)

        self.assertIn("owner_to_cancel", tm._tasks_by_owner)
        tm.cancel_by_owner("owner_to_cancel")
        self.assertNotIn("owner_to_cancel", tm._tasks_by_owner)

        # Suppress exception from cancelled task
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_cancel_all_leaves_no_owners(self) -> None:
        """The internal _tasks_by_owner dict should be empty after cancel_all."""
        tm = TaskManager()
        tm.add("owner1", asyncio.create_task(asyncio.sleep(0.1)))
        tm.add("owner2", asyncio.create_task(asyncio.sleep(0.1)))

        await tm.cancel_all()
        self.assertEqual(len(tm._tasks_by_owner), 0)

    async def test_task_manager_handles_multiple_owners(self) -> None:
        """Should correctly manage tasks from many different owners."""
        tm = TaskManager()
        tasks = []
        for i in range(10):
            task = asyncio.create_task(asyncio.sleep(0.1))
            tm.add(f"owner_{i}", task)
            tasks.append(task)

        self.assertEqual(len(tm._tasks_by_owner), 10)
        tm.cancel_by_owner("owner_3")

        # Yield to the event loop to allow the cancellation to be processed
        await asyncio.sleep(0)

        self.assertEqual(len(tm._tasks_by_owner), 9)
        self.assertTrue(tasks[3].cancelled())

        await tm.cancel_all()
        # Suppress CancelledError for the remaining tasks
        await asyncio.gather(*tasks, return_exceptions=True)

    async def test_done_callback_robustness(self) -> None:
        """The done callback should not fail if the owner key is already gone."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("transient_owner", task)

        # Manually remove the owner before the task's done_callback fires
        # This simulates a potential race condition
        del tm._tasks_by_owner["transient_owner"]

        # Now, wait for the task to complete. Its callback will run.
        # If it's not robust, it might raise a KeyError.
        try:
            await task
        except Exception as ex:
            self.fail(f"Done callback was not robust to a missing key: {ex}")
