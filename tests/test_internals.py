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

from src.xstate_machine import (
    PluginBase,
    LoggingInspector,
    Event,
    ImplementationMissingError,
    XStateMachineError,
)
from src.xstate_machine.events import DoneEvent
from src.xstate_machine.task_manager import TaskManager

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
