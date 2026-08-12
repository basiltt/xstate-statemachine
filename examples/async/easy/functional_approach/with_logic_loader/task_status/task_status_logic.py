# -------------------------------------------------------------------------------
# ⚙️ Task Status Logic
# examples/async/easy/functional_approach/with_logic_loader/task_status/task_status_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for the async task status demonstration.

Includes actions to set and clear a current task ID.
"""

import asyncio
import logging
from typing import Any, Dict

from xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


async def set_task_id(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """⚙️ Register a new task ID in context.

    Args:
        interpreter: The running state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event carrying `payload['id']`.
        action_def: Metadata about this action.
    """
    logger.info("🔖 Registering task in queue...")
    await asyncio.sleep(0.7)
    context["current_task_id"] = event.payload.get("id")
    logger.info(f"⚙️ Task started. ID: {context['current_task_id']}")


async def clear_task_id(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🧹 Clear the current task ID after completion.

    Args:
        interpreter: The running state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event.
        action_def: Metadata about this action.
    """
    logger.info(f"✅ Completing task {context.get('current_task_id')}...")
    await asyncio.sleep(0.3)
    context["current_task_id"] = None
    logger.info("🧹 Task ID cleared.")
