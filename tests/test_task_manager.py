# tests/test_task_manager.py

import asyncio
import logging
import unittest

from src.xstate_statemachine.task_manager import TaskManager

# Configure logging for test visibility
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestTaskManager(unittest.IsolatedAsyncioTestCase):
    """
    Asynchronous test suite for the TaskManager utility class.
    """

    async def test_add_and_cancel_all(self) -> None:
        """Should add tasks and successfully cancel all of them."""
        tm = TaskManager()
        task1 = asyncio.create_task(asyncio.sleep(0.1))
        task2 = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("owner1", task1)
        tm.add("owner2", task2)

        self.assertFalse(task1.done())
        self.assertFalse(task2.done())

        await tm.cancel_all()

        # After awaiting cancel_all, the tasks should be marked as cancelled.
        self.assertTrue(task1.cancelled())
        self.assertTrue(task2.cancelled())

    async def test_cancel_by_owner(self) -> None:
        """Should cancel tasks specifically associated with a given owner."""
        tm = TaskManager()
        t1 = asyncio.create_task(asyncio.sleep(0.1))
        t2 = asyncio.create_task(asyncio.sleep(0.1))
        t3 = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("owner1", t1)
        tm.add("owner1", t2)
        tm.add("owner2", t3)

        # ✅ FIX: The `cancel_by_owner` method is a coroutine and must be awaited.
        await tm.cancel_by_owner("owner1")

        # Assertions can be made immediately after awaiting.
        self.assertTrue(t1.cancelled())
        self.assertTrue(t2.cancelled())
        # The task from the other owner should be unaffected.
        self.assertFalse(t3.done())

        # Clean up the remaining task.
        await tm.cancel_all()

    async def test_task_removes_itself_on_completion(self) -> None:
        """Tasks should be automatically removed from tracking upon completion."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("owner", task)
        # Use the public `get_tasks_by_owner` method for checking.
        self.assertEqual(len(tm.get_tasks_by_owner("owner")), 1)

        # Wait for the task to complete naturally.
        await task

        # The done_callback should have removed the task from tracking.
        self.assertEqual(len(tm.get_tasks_by_owner("owner")), 0)

    # ---------- New/Corrected Tests ----------

    async def test_cancel_by_owner_on_nonexistent_owner(self) -> None:
        """Should not raise an error when cancelling a non-existent owner."""
        tm = TaskManager()
        try:
            # ✅ FIX: Await the coroutine.
            await tm.cancel_by_owner("nonexistent_owner")
        except Exception as e:
            self.fail(f"Cancelling a non-existent owner raised: {e}")

    async def test_cancel_all_on_empty_manager(self) -> None:
        """Should not raise an error when calling cancel_all on an empty manager."""
        tm = TaskManager()
        try:
            await tm.cancel_all()
        except Exception as e:
            self.fail(f"cancel_all on an empty manager raised: {e}")

    async def test_add_already_completed_task(self) -> None:
        """Should handle adding a task that is already complete."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0))
        await task  # Ensure it's complete before adding.

        tm.add("owner", task)
        await asyncio.sleep(
            0
        )  # Allow the event loop to run the done_callback.

        self.assertEqual(len(tm.get_tasks_by_owner("owner")), 0)

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
        # A completed task is still 'done' but not 'cancelled'.
        self.assertTrue(
            completed_task.done() and not completed_task.cancelled()
        )

    async def test_reuse_owner_id_after_completion(self) -> None:
        """Should allow reusing an owner ID after its previous tasks have completed."""
        tm = TaskManager()
        task1 = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("reusable_owner", task1)
        await task1  # Wait for completion, which triggers removal.

        self.assertEqual(len(tm.get_tasks_by_owner("reusable_owner")), 0)

        task2 = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("reusable_owner", task2)
        self.assertEqual(len(tm.get_tasks_by_owner("reusable_owner")), 1)

        await tm.cancel_all()

    async def test_cancel_by_owner_on_empty_task_set(self) -> None:
        """Should not fail if cancel_by_owner is called for an owner with no active tasks."""
        tm = TaskManager()
        # Add a task and let it complete, leaving the owner key with an empty set.
        tm.add("owner_with_no_tasks", asyncio.create_task(asyncio.sleep(0)))
        await asyncio.sleep(0.01)
        try:
            # ✅ FIX: Await the coroutine.
            await tm.cancel_by_owner("owner_with_no_tasks")
        except Exception as e:
            self.fail(f"cancel_by_owner on empty set failed: {e}")

    async def test_removal_of_cancelled_tasks_by_owner(self) -> None:
        """The owner's key should be removed after its tasks are cancelled."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("owner_to_cancel", task)

        self.assertIn("owner_to_cancel", tm._tasks_by_owner)
        # ✅ FIX: Await the coroutine to ensure the logic runs.
        await tm.cancel_by_owner("owner_to_cancel")
        self.assertNotIn("owner_to_cancel", tm._tasks_by_owner)

        # Confirm the task itself was cancelled.
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_cancel_all_leaves_no_owners(self) -> None:
        """The internal _tasks_by_owner dict should be empty after cancel_all."""
        tm = TaskManager()
        tm.add("owner1", asyncio.create_task(asyncio.sleep(0.1)))
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
        # ✅ FIX: Await the coroutine.
        await tm.cancel_by_owner("owner_3")

        self.assertEqual(len(tm._tasks_by_owner), 9)
        self.assertTrue(tasks[3].cancelled())

        await tm.cancel_all()
        # It's good practice to gather all tasks to prevent warnings.
        await asyncio.gather(*tasks, return_exceptions=True)

    async def test_done_callback_robustness(self) -> None:
        """The done callback should not fail if the owner key is already gone."""
        tm = TaskManager()
        task = asyncio.create_task(asyncio.sleep(0.01))

        # Add the task, which schedules its done_callback.
        tm.add("transient_owner", task)

        # Manually remove the owner key to simulate a race condition where
        # a cancel operation might run before the done_callback.
        del tm._tasks_by_owner["transient_owner"]

        # Wait for the task to complete. Its callback will now run.
        # If the callback is not robust, it might raise a KeyError.
        try:
            await task
        except Exception as ex:
            self.fail(f"Done callback was not robust to a missing key: {ex}")
