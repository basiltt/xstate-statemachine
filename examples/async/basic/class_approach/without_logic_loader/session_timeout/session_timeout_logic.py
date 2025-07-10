# -------------------------------------------------------------------------------
# ⌛ Session Timeout Logic
# examples/async/basic/class_approach/without_logic_loader/session_timeout/session_timeout_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for session timeout handling.
"""

import asyncio
import logging
from typing import Any, Dict

from src.xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class SessionTimeoutLogic:
    """Handles user login action and timeout logging."""

    async def set_user(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """👤 Store user in context after login."""
        logger.info("🛂 Storing user session...")
        await asyncio.sleep(0.2)
        context["user"] = event.payload.get("user")

    def log_login(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔐 Log successful login and upcoming timeout."""
        logger.info(f"👤 User '{context['user']}' logged in; timeout in 3s.")

    def log_timeout(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⌛ Log session timeout due to inactivity."""
        logger.warning(f"⌛ Session for '{context['user']}' timed out.")
