# /src/xstate_statemachine/task_manager.py
# -----------------------------------------------------------------------------
# 🗂️ Asynchronous Task Manager
# -----------------------------------------------------------------------------
# This module provides the `TaskManager` class, a specialized utility for
# organizing and managing the lifecycle of `asyncio.Task` objects. These tasks
# are typically created for background operations like `after` timers and
# `invoke`d services.
#
# This class is crucial for preventing resource leaks. By associating each task
# with an "owner" (typically a state ID), it can cleanly cancel all related
# background operations when a state is exited, ensuring no orphaned tasks are
# left running. This encapsulation of task lifecycle management is a key aspect
# of the library's robustness in an asynchronous environment.
# -----------------------------------------------------------------------------
"""
Provides a manager for asyncio tasks associated with state machine states.

This utility is essential for the asynchronous `Interpreter` to safely manage
the lifecycle of background processes.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
from collections import defaultdict
from typing import Dict, Set, Any

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 📋 TaskManager Class Definition
# -----------------------------------------------------------------------------


class TaskManager:
    """A manager for organizing and cancelling asyncio tasks by owner.

    This class provides a clean API to add, retrieve, and cancel groups of
    `asyncio.Task` objects. It is essential for the interpreter to manage the
    lifecycle of background processes tied to specific states, ensuring no
    orphaned tasks are left running when a state is exited.

    It functions as a robust "Resource Manager" for `asyncio` tasks.
    """

    def __init__(self) -> None:
        """Initializes the TaskManager."""
        # 🗂️ A dictionary mapping an owner ID (e.g., a state ID) to a set
        #    of its running tasks. Using `defaultdict(set)` simplifies adding
        #    tasks to new owners without needing to check if the key exists.
        self._tasks_by_owner: Dict[str, Set[asyncio.Task[Any]]] = defaultdict(
            set
        )
        logger.debug("✨ TaskManager initialized.")

    def add(self, owner_id: str, task: asyncio.Task[Any]) -> None:
        """Adds and tracks a task under a specific owner.

        Args:
            owner_id: The ID of the owner, which is typically the unique ID
                      of the state that created the task (e.g., from an
                      `invoke` or `after` block).
            task: The `asyncio.Task` to manage.
        """
        logger.debug("➕ Adding task under owner '%s'.", owner_id)
        self._tasks_by_owner[owner_id].add(task)

        # 🔗 When the task completes (or is cancelled), automatically remove
        # it from the tracking set. This is a crucial cleanup step that
        # prevents the `_tasks_by_owner` dictionary from growing indefinitely
        # and leaking memory.
        task.add_done_callback(
            lambda t: self._tasks_by_owner.get(owner_id, set()).discard(t)
        )

    def get_tasks_by_owner(self, owner_id: str) -> Set[asyncio.Task[Any]]:
        """Retrieves all tasks for a given owner.

        This provides a way to inspect running tasks without modifying them,
        respecting the encapsulation of the manager. It returns a copy to
        prevent external modification of the internal task set.

        Args:
            owner_id: The ID of the owner whose tasks are to be retrieved.

        Returns:
            A copy of the set of tasks belonging to the owner, or an empty
            set if the owner has no tasks.
        """
        return self._tasks_by_owner.get(owner_id, set()).copy()

    async def cancel_by_owner(self, owner_id: str) -> None:
        """Cancels all tasks associated with a specific owner.

        This is the primary method used by the `Interpreter` when a state is
        exited. It ensures all related background activity (timers, services)
        is stopped cleanly and immediately.

        Args:
            owner_id: The ID of the owner whose tasks should be cancelled.
        """
        # 🛡️ Safely get tasks to avoid a KeyError if the owner_id has already
        # been cleaned up, which can happen in complex, fast-moving state
        # transitions.
        tasks_to_cancel = self._tasks_by_owner.get(owner_id)
        if not tasks_to_cancel:
            return  # ✅ No tasks for this owner, nothing to do.

        logger.debug(
            "❌ Cancelling %d task(s) for owner '%s'.",
            len(tasks_to_cancel),
            owner_id,
        )

        # 🛑 Issue the cancellation request to all tasks owned by the state.
        for task in list(tasks_to_cancel):  # Iterate over a copy
            if not task.done():
                task.cancel()

        # ⏳ Wait for all tasks to acknowledge the cancellation. This is vital
        # for ensuring a clean, graceful shutdown of the tasks before
        # proceeding. `return_exceptions=True` prevents one failed task from
        # halting the cancellation of others.
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        # 🧹 Clean up the tracking dictionary for this owner.
        if owner_id in self._tasks_by_owner:
            del self._tasks_by_owner[owner_id]
            logger.debug("🗑️ Removed owner '%s' from task tracking.", owner_id)

    async def cancel_all(self) -> None:
        """Cancels all tasks currently managed by this instance.

        This is typically called when the main interpreter is stopped to ensure
        a clean shutdown of all background activity across the entire state
        machine.
        """
        logger.info("🛑 Cancelling all managed tasks...")
        #  একত্রিত Flatten the dictionary of sets into a single list of all tasks.
        all_tasks = [
            task for tasks in self._tasks_by_owner.values() for task in tasks
        ]

        if not all_tasks:
            logger.info("🤷 No running tasks to cancel.")
            return

        # 🛑 Issue cancellation requests.
        for task in all_tasks:
            if not task.done():
                task.cancel()

        # ⏳ Wait for all cancellations to complete.
        await asyncio.gather(*all_tasks, return_exceptions=True)

        # 🧹 Clear the entire tracking dictionary.
        self._tasks_by_owner.clear()
        logger.info("✅ All managed tasks have been cancelled successfully.")
