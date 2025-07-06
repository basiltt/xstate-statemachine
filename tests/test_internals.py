# tests/test_internals.py
import asyncio
import unittest
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


class TestPlugins(unittest.TestCase):
    """Tests the plugin system and built-in plugins."""

    def test_plugin_base_methods_do_not_raise_errors(self) -> None:
        """The base PluginBase methods should be no-ops."""
        plugin = PluginBase()
        try:
            plugin.on_interpreter_start(None)
            plugin.on_interpreter_stop(None)
            plugin.on_event_received(None, Event("TEST"))
            plugin.on_transition(None, set(), set(), None)
            plugin.on_action_execute(None, None)
        except Exception:
            self.fail("PluginBase methods raised an unexpected exception.")

    def test_logging_inspector_handles_various_events(self) -> None:
        """LoggingInspector should not crash on different event types."""
        inspector = LoggingInspector()
        mock_interpreter = MagicMock()
        mock_interpreter.context = {"value": 1}

        try:
            # Test with a standard event with payload
            inspector.on_event_received(
                mock_interpreter, Event("TEST", payload={"data": "test"})
            )
            # Test with a DoneEvent which has a 'data' attribute
            inspector.on_event_received(
                mock_interpreter,
                DoneEvent("done.test", data={"result": "ok"}, src="test"),
            )
            # Test with an event with no payload/data
            inspector.on_event_received(mock_interpreter, Event("SIMPLE"))
        except Exception:
            self.fail(
                "LoggingInspector failed to handle different event types."
            )


class TestExceptions(unittest.TestCase):
    """Tests that custom exceptions behave as expected."""

    def test_custom_exception_hierarchy(self) -> None:
        """Ensures custom exceptions inherit from the base exception."""
        self.assertTrue(
            issubclass(ImplementationMissingError, XStateMachineError)
        )


class TestTaskManager(unittest.IsolatedAsyncioTestCase):
    """Tests the asyncio TaskManager."""

    async def test_add_and_cancel_all(self) -> None:
        """Should add tasks and cancel them all."""
        tm = TaskManager()
        task1 = asyncio.create_task(asyncio.sleep(0.1))
        task2 = asyncio.create_task(asyncio.sleep(0.1))

        tm.add("owner1", task1)
        tm.add("owner2", task2)

        self.assertFalse(task1.done())
        self.assertFalse(task2.done())

        await tm.cancel_all()

        self.assertTrue(task1.cancelled())
        self.assertTrue(task2.cancelled())

    async def test_cancel_by_owner(self) -> None:
        """Should cancel tasks for a specific owner."""
        tm = TaskManager()
        task1_owner1 = asyncio.create_task(asyncio.sleep(0.1))
        task2_owner1 = asyncio.create_task(asyncio.sleep(0.1))
        task1_owner2 = asyncio.create_task(asyncio.sleep(0.1))

        tm.add("owner1", task1_owner1)
        tm.add("owner1", task2_owner1)
        tm.add("owner2", task1_owner2)

        tm.cancel_by_owner("owner1")
        await asyncio.sleep(0.01)  # Allow cancellation to propagate

        self.assertTrue(task1_owner1.cancelled())
        self.assertTrue(task2_owner1.cancelled())
        self.assertFalse(task1_owner2.done())

        await tm.cancel_all()  # Clean up remaining task

    async def test_task_removes_itself_on_completion(self) -> None:
        """Tasks should be removed from tracking upon natural completion."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("owner", task)

        self.assertEqual(len(tm._tasks_by_owner["owner"]), 1)
        await task
        # The done_callback should have removed the task
        self.assertEqual(len(tm._tasks_by_owner["owner"]), 0)
