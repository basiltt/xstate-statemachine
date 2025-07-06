# src/xstate_python/task_manager.py
import asyncio
from typing import Dict, Set
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
        self._tasks: Set[asyncio.Task] = set()

    def add(self, task: asyncio.Task):
        """Adds a task to manage and ensures it's cleaned up upon completion."""
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        logger.debug(
            f"📋 Task added: {task.get_name()}. Total tasks: {len(self._tasks)}"
        )

    async def cancel_all(self):
        """Cancels all managed tasks."""
        if not self._tasks:
            return

        logger.info(f"🛑 Cancelling {len(self._tasks)} background tasks...")
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("✅ All tasks cancelled.")
