# /tests/test_task_manager.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: TaskManager Utility
# -----------------------------------------------------------------------------
# This module contains asynchronous unit tests for the 🚀 `TaskManager` helper
# defined in `src.xstate_statemachine.task_manager`.  The `TaskManager`
# centralises the creation, tracking, and cancellation of `asyncio.Task`
# objects, grouping them by an **owner ID** so that callers can:
#
#   • 🔖 Add tasks under a specific owner.
#   • ✂️ Cancel tasks en-masse (`cancel_all`).
#   • 🗑️ Cancel only those tasks belonging to a particular owner
#     (`cancel_by_owner`).
#
# These tests verify:
#
#   1. Correct tracking and clean-up of tasks.
#   2. Robust behaviour when cancelling *all* tasks or tasks for a
#      non-existent owner.
#   3. Automatic removal of finished tasks via the internal
#      `done_callback`.
#   4. Edge-case handling (e.g., mixed task states, empty manager).
#
# The file adheres to strict 🧹 **PEP 8** guidelines, includes ✨ rich emoji
# logging, and employs fully-typed Google-style docstrings to boost IDE
# auto-completion and maintainability.
# -----------------------------------------------------------------------------
"""
Asynchronous test cases for the :pyclass:`~src.xstate_statemachine.task_manager.TaskManager`
utility class.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import unittest

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.task_manager import TaskManager

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger: logging.Logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🧪 Test Class Definition
# -----------------------------------------------------------------------------


class TestTaskManager(unittest.IsolatedAsyncioTestCase):
    """Asynchronous unit tests for the :class:`TaskManager`.

    Each test exercises a different aspect of the TaskManager’s public API
    while ensuring no side-effects leak between tests 🧹.
    """

    # --------------------------------------------------------------------- #
    # 🚦 Core Functionality Tests                                           #
    # --------------------------------------------------------------------- #

    async def test_add_and_cancel_all(self) -> None:
        """Add tasks and then cancel all of them in one call.

        Checks that:

        * Tasks are correctly registered under their owners.
        * :py:meth:`TaskManager.cancel_all` cancels every tracked task.

        Raises
        ------
        AssertionError
            If any expectation about task state fails.
        """
        logger.info("🧪 test_add_and_cancel_all – setting up tasks...")
        tm: TaskManager = TaskManager()

        # 🏗️ Create two simple sleep tasks
        task1: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))
        task2: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))

        tm.add("owner1", task1)
        tm.add("owner2", task2)

        # ➡️ Pre-conditions
        self.assertFalse(task1.done())
        self.assertFalse(task2.done())

        logger.info("🔔 Cancelling *all* tasks through TaskManager...")
        await tm.cancel_all()

        # ✅ Post-conditions
        self.assertTrue(task1.cancelled())
        self.assertTrue(task2.cancelled())
        # 🧹 Task registry should be empty for all owners
        self.assertEqual(tm.get_tasks_by_owner("owner1"), set())
        self.assertEqual(tm.get_tasks_by_owner("owner2"), set())
        # 🕵️ Unknown owners should also report no tasks
        self.assertEqual(tm.get_tasks_by_owner("unknown_owner"), set())

    async def test_cancel_by_owner(self) -> None:
        """Cancel only the tasks associated with a single owner.

        Ensures other owners’ tasks remain untouched 🛡️.
        """
        logger.info("🧪 test_cancel_by_owner – creating tasks...")
        tm: TaskManager = TaskManager()

        t1: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))
        t2: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))
        t3: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))

        tm.add("owner1", t1)
        tm.add("owner1", t2)
        tm.add("owner2", t3)

        logger.info("✂️ Cancelling tasks for 'owner1' only...")
        await tm.cancel_by_owner("owner1")

        # ✅ The first two tasks are cancelled
        self.assertTrue(t1.cancelled())
        self.assertTrue(t2.cancelled())
        # ✅ The other owner’s task is still running
        self.assertFalse(t3.done())

        # 🧹 Clean-up remaining task
        await tm.cancel_all()

    async def test_task_removes_itself_on_completion(self) -> None:
        """Verify tasks are auto-removed from internal tracking once finished."""
        logger.info(
            "🧪 test_task_removes_itself_on_completion – verifying done_callback..."
        )
        tm: TaskManager = TaskManager()

        task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("owner", task)
        self.assertEqual(len(tm.get_tasks_by_owner("owner")), 1)

        # ⏳ Wait for completion so done_callback fires
        await task

        self.assertEqual(len(tm.get_tasks_by_owner("owner")), 0)

    # --------------------------------------------------------------------- #
    # 🌐 Robustness & Edge-Case Tests                                       #
    # --------------------------------------------------------------------- #

    async def test_cancel_by_owner_on_nonexistent_owner(self) -> None:
        """`cancel_by_owner` should *not* raise when owner does not exist."""
        logger.info(
            "🧪 test_cancel_by_owner_on_nonexistent_owner – calling cancel..."
        )
        tm: TaskManager = TaskManager()

        try:
            await tm.cancel_by_owner("nonexistent_owner")
        except Exception as exc:  # pragma: no cover
            self.fail(f"❌ Unexpected exception: {exc}")

    async def test_cancel_all_on_empty_manager(self) -> None:
        """`cancel_all` should be a no-op when no tasks are tracked."""
        logger.info(
            "🧪 test_cancel_all_on_empty_manager – empty manager scenario..."
        )
        tm: TaskManager = TaskManager()

        try:
            await tm.cancel_all()
        except Exception as exc:  # pragma: no cover
            self.fail(f"❌ Unexpected exception: {exc}")

    async def test_add_already_completed_task(self) -> None:
        """Adding a *completed* task should result in zero tracked tasks."""
        logger.info(
            "🧪 test_add_already_completed_task – pre-completed task..."
        )
        tm: TaskManager = TaskManager()

        task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0))
        await task  # Ensure completion

        tm.add("owner", task)
        await asyncio.sleep(0)  # Allow done_callback to run

        self.assertEqual(len(tm.get_tasks_by_owner("owner")), 0)

    async def test_cancel_all_with_mixed_task_states(self) -> None:
        """`cancel_all` should cancel pending tasks but ignore already-done ones."""
        logger.info(
            "🧪 test_cancel_all_with_mixed_task_states – mixed states..."
        )
        tm: TaskManager = TaskManager()

        pending_task: asyncio.Task[None] = asyncio.create_task(
            asyncio.sleep(0.1)
        )
        completed_task: asyncio.Task[None] = asyncio.create_task(
            asyncio.sleep(0)
        )
        await completed_task

        tm.add("owner1", pending_task)
        tm.add("owner2", completed_task)

        await tm.cancel_all()

        self.assertTrue(pending_task.cancelled())
        self.assertTrue(
            completed_task.done() and not completed_task.cancelled()
        )

    async def test_reuse_owner_id_after_completion(self) -> None:
        """Owner IDs should be reusable after their previous tasks finish."""
        logger.info(
            "🧪 test_reuse_owner_id_after_completion – lifecycle test..."
        )
        tm: TaskManager = TaskManager()

        task1: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("reusable_owner", task1)
        await task1

        self.assertEqual(len(tm.get_tasks_by_owner("reusable_owner")), 0)

        task2: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("reusable_owner", task2)
        self.assertEqual(len(tm.get_tasks_by_owner("reusable_owner")), 1)

        await tm.cancel_all()

    async def test_cancel_by_owner_on_empty_task_set(self) -> None:
        """Cancelling an owner with *no* active tasks must not fail."""
        logger.info(
            "🧪 test_cancel_by_owner_on_empty_task_set – verify graceful no-op..."
        )
        tm: TaskManager = TaskManager()

        tm.add("owner_with_no_tasks", asyncio.create_task(asyncio.sleep(0)))
        await asyncio.sleep(0.01)  # Let task finish & auto-remove

        try:
            await tm.cancel_by_owner("owner_with_no_tasks")
        except Exception as exc:  # pragma: no cover
            self.fail(f"❌ Unexpected exception: {exc}")

    async def test_removal_of_cancelled_tasks_by_owner(self) -> None:
        """Owner key should disappear after its tasks are cancelled."""
        logger.info(
            "🧪 test_removal_of_cancelled_tasks_by_owner – validating dict cleanup..."
        )
        tm: TaskManager = TaskManager()

        task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("owner_to_cancel", task)
        self.assertIn("owner_to_cancel", tm._tasks_by_owner)

        await tm.cancel_by_owner("owner_to_cancel")
        self.assertNotIn("owner_to_cancel", tm._tasks_by_owner)

        # Confirm cancellation
        with self.assertRaises(asyncio.CancelledError):
            await task

    async def test_cancel_all_leaves_no_owners(self) -> None:
        """`cancel_all` should empty the internal owner registry."""
        logger.info(
            "🧪 test_cancel_all_leaves_no_owners – ensuring dict empty..."
        )
        tm: TaskManager = TaskManager()

        tm.add("owner1", asyncio.create_task(asyncio.sleep(0.1)))
        await tm.cancel_all()

        self.assertEqual(len(tm._tasks_by_owner), 0)

    async def test_task_manager_handles_multiple_owners(self) -> None:
        """Managing many owners and selective cancellation works as expected."""
        logger.info(
            "🧪 test_task_manager_handles_multiple_owners – stress test..."
        )
        tm: TaskManager = TaskManager()
        tasks: list[asyncio.Task[None]] = []

        # 🏗️ Create 10 owners with one task each
        for i in range(10):
            task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))
            tm.add(f"owner_{i}", task)
            tasks.append(task)

        self.assertEqual(len(tm._tasks_by_owner), 10)

        # Cancel just one owner
        await tm.cancel_by_owner("owner_3")

        self.assertEqual(len(tm._tasks_by_owner), 9)
        self.assertTrue(tasks[3].cancelled())

        # Final clean-up to avoid asyncio warnings
        await tm.cancel_all()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def test_done_callback_robustness(self) -> None:
        """`done_callback` must not raise when owner is already removed.

        Simulates a race-condition where the internal dict entry is deleted
        *before* the callback executes.
        """
        logger.info(
            "🧪 test_done_callback_robustness – race condition simulation..."
        )
        tm: TaskManager = TaskManager()

        task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.01))
        tm.add("transient_owner", task)

        # Manually remove owner entry to mimic aggressive cancellation
        del tm._tasks_by_owner["transient_owner"]

        try:
            await task  # done_callback runs here
        except Exception as exc:  # pragma: no cover
            self.fail(f"❌ done_callback raised unexpected exception: {exc}")

    async def test_get_tasks_copy_is_isolated(self) -> None:
        """Returned set from ``get_tasks_by_owner`` is an *independent copy* 🔒.

        The caller should be free to mutate the returned set without affecting
        the internal bookkeeping of :class:`TaskManager`.

        Raises
        ------
        AssertionError
            If mutating the returned set changes the manager’s internal state.
        """
        logger.info(
            "🧪 test_get_tasks_copy_is_isolated – validating defensive copy..."
        )
        tm: TaskManager = TaskManager()

        task: asyncio.Task[None] = asyncio.create_task(asyncio.sleep(0.1))
        tm.add("owner_copy_test", task)

        # Retrieve a *copy* of the owner's task set.
        tasks_snapshot = tm.get_tasks_by_owner("owner_copy_test")
        self.assertEqual(len(tasks_snapshot), 1)

        # 🧪 Mutate the snapshot – this should *not* propagate back.
        tasks_snapshot.clear()
        self.assertEqual(len(tasks_snapshot), 0, "Snapshot mutation failed.")

        # ✅ Internal state must remain unchanged.
        self.assertEqual(
            len(tm.get_tasks_by_owner("owner_copy_test")),
            1,
            "❌ Internal state was modified by external mutation!",
        )

        await tm.cancel_all()  # Clean-up
