# src/xstate_statemachine/task_manager.py

# -----------------------------------------------------------------------------
# 🗂️ Task Manager
# -----------------------------------------------------------------------------
# This module provides the TaskManager class, a utility for organizing and
# managing asyncio tasks associated with specific owners (e.g., state nodes).
# This is crucial for cleanly cancelling background operations like timers
# and invoked services when a state is exited.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
from collections import defaultdict
from typing import Dict, Set

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
    -    orphaned tasks are left running when a state is exited.
    """

    def __init__(self) -> None:
        """Initializes the TaskManager."""
        # 🗂️ A dictionary mapping an owner ID to a set of its running tasks.
        # Using defaultdict simplifies adding new owners.
        self._tasks_by_owner: Dict[str, Set[asyncio.Task]] = defaultdict(set)
        logger.debug("✨ TaskManager initialized.")

    def add(self, owner_id: str, task: asyncio.Task) -> None:
        """Adds and tracks a task under a specific owner.

        Args:
            owner_id: The ID of the owner (typically a state ID).
            task: The `asyncio.Task` to manage.
        """
        logger.debug("➕ Adding task under owner '%s'.", owner_id)
        self._tasks_by_owner[owner_id].add(task)

        # 🔗 When the task completes (successfully or not), automatically
        # remove it from the tracking set to prevent memory leaks.
        task.add_done_callback(
            lambda t: self._tasks_by_owner.get(owner_id, set()).discard(t)
        )

    def get_tasks_by_owner(self, owner_id: str) -> Set[asyncio.Task]:
        """Retrieves all tasks for a given owner.

        This provides a way to inspect running tasks without modifying them,
        respecting the encapsulation of the manager.

        Args:
            owner_id: The ID of the owner.

        Returns:
            A copy of the set of tasks belonging to the owner, or an empty set.
        """
        return self._tasks_by_owner.get(owner_id, set()).copy()

    async def cancel_by_owner(self, owner_id: str) -> None:
        """Cancels all tasks associated with a specific owner.

        This is the primary method used by the interpreter when a state is
        exited. It ensures all related background activity is stopped.

        Args:
            owner_id: The ID of the owner whose tasks should be cancelled.
        """
        # 🛡️ Safely get tasks to avoid KeyError if owner_id is already gone.
        tasks_to_cancel = self._tasks_by_owner.get(owner_id, set())
        if not tasks_to_cancel:
            return

        logger.debug(
            "❌ Cancelling %d tasks for owner '%s'.",
            len(tasks_to_cancel),
            owner_id,
        )
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        # ⏳ Wait for all tasks to acknowledge the cancellation. This is vital
        # for ensuring a clean shutdown of the tasks.
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        # 🧹 Clean up the tracking dictionary for this owner.
        if owner_id in self._tasks_by_owner:
            del self._tasks_by_owner[owner_id]
            logger.debug("🗑️ Removed owner '%s' from task tracking.", owner_id)

    async def cancel_all(self) -> None:
        """Cancels all tasks currently managed by this instance.

        This is typically called when the main interpreter is stopped.
        """
        logger.info("🛑 Cancelling all managed tasks...")
        all_tasks = [
            task for tasks in self._tasks_by_owner.values() for task in tasks
        ]

        if not all_tasks:
            logger.info("🤷 No tasks to cancel.")
            return

        for task in all_tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*all_tasks, return_exceptions=True)

        self._tasks_by_owner.clear()
        logger.info("✅ All managed tasks have been cancelled.")
