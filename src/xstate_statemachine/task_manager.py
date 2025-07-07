# src/xstate_statemachine/task_manager.py
import asyncio
from typing import Dict, Set

# ✨ FIX: Add the missing import for the library's logger.
from .logger import logger


# -----------------------------------------------------------------------------
# 📋 Task Manager
# -----------------------------------------------------------------------------
# Manages the lifecycle of background asyncio tasks, specifically for `invoke`
# and `after` transitions. This is crucial for resource management.
# -----------------------------------------------------------------------------


class TaskManager:
    """Manages the lifecycle of asyncio tasks for an interpreter."""

    def __init__(self):
        """Initializes the TaskManager."""
        # Use a dictionary to map owner IDs (typically state IDs) to their tasks.
        self._tasks_by_owner: Dict[str, Set[asyncio.Task]] = {}

    def add(self, owner_id: str, task: asyncio.Task) -> None:
        """
        Adds a task to manage and associates it with an owner.

        Args:
            owner_id: The ID of the state that owns this task.
            task: The asyncio.Task to manage.
        """
        if owner_id not in self._tasks_by_owner:
            self._tasks_by_owner[owner_id] = set()

        self._tasks_by_owner[owner_id].add(task)
        # When the task is done, remove it from the set to prevent memory leaks.
        task.add_done_callback(
            lambda t: self._tasks_by_owner.get(owner_id, set()).discard(t)
        )
        logger.debug(
            f"📋 Task added for owner '{owner_id}'. "
            f"Total tasks for owner: {len(self._tasks_by_owner[owner_id])}"
        )

    def cancel_by_owner(self, owner_id: str) -> None:
        """
        Cancels all tasks associated with a specific owner ID.

        This is called when a state is exited to clean up its running tasks.

        Args:
            owner_id: The ID of the state whose tasks should be cancelled.
        """
        if (
            owner_id not in self._tasks_by_owner
            or not self._tasks_by_owner[owner_id]
        ):
            return

        tasks_to_cancel = self._tasks_by_owner.pop(owner_id)
        logger.debug(
            f"🗑️  Cancelling {len(tasks_to_cancel)} tasks for owner '{owner_id}'..."
        )
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

    async def cancel_all(self) -> None:
        """Cancels all managed tasks from all owners."""
        if not self._tasks_by_owner:
            return

        logger.info("🛑 Cancelling all background tasks...")
        all_tasks = [
            task for tasks in self._tasks_by_owner.values() for task in tasks
        ]

        for task in all_tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*all_tasks, return_exceptions=True)
        self._tasks_by_owner.clear()
        logger.info("✅ All tasks cancelled.")
