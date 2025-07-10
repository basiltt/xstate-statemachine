# -------------------------------------------------------------------------------
# 🟢 User Presence Logic
# examples/async/easy/class_approach/without_logic_loader/user_presence/user_presence_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for the async user presence tracker.

Simulates network I/O to update last-seen timestamps.
"""

import asyncio
import logging
import time
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class UserPresenceLogic:
    """Provides actions for tracking user online/offline presence."""

    async def update_last_seen(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🌐 Simulate I/O delay and update last-seen timestamp.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dictionary.
            event: The triggering Event (CONNECT or DISCONNECT).
            action_def: Metadata about this action.
        """
        logger.info("⏳ Simulating network call to update presence...")
        await asyncio.sleep(0.5)
        context["last_seen"] = time.time()
        if event.type == "CONNECT":
            context["user_id"] = event.payload.get("user_id")
            logger.info(f"🟢 User '{context['user_id']}' is now online.")
        else:
            logger.info(f"🔴 User '{context.get('user_id')}' went offline.")
