# examples/sync/basic/class_approach/without_logic_loader/user_auth_logic.py
# -----------------------------------------------------------------------------
# 🔐 User Authentication Logic (Explicit MachineLogic)
# -----------------------------------------------------------------------------
"""
Contains all action, guard, and service implementations for user authentication.
"""

import logging
from typing import Any, Dict

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class UserAuthLogic:
    """Encapsulates actions, guards, and a service for user login/logout."""

    def cache_credentials(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📝 Store incoming login payload into context."""
        context["credentials"] = event.payload
        logger.info("📝 Caching credentials.")

    def increment_attempts(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📈 Increment login attempt counter on each try."""
        context["loginAttempts"] = context.get("loginAttempts", 0) + 1
        logger.info(f"📈 Login attempts: {context['loginAttempts']}")

    def is_not_locked_out(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """🛡️ Guard: Prevent login if too many failed attempts."""
        if context.get("loginAttempts", 0) >= 3:
            logger.error("❌ Account locked out.")
            return False
        return True

    def attempt_login(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, str]:
        """🔐 Service: Synchronous credential check.

        Args:
            interpreter: The running SyncInterpreter.
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            A dict with username on success.

        Raises:
            ValueError: If username/password are incorrect.
        """
        creds = context.get("credentials", {})
        username = creds.get("username")
        password = creds.get("password")
        logger.info(f"🔐 Attempting login for '{username}'...")
        if username == "admin" and password == "password123":
            return {"username": username}
        raise ValueError("Invalid username or password")

    def set_user(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """✅ On success, store username and reset state."""
        context["username"] = event.data.get("username")
        context["error"] = None
        context["credentials"] = None
        context["loginAttempts"] = 0
        logger.info(f"✅ User '{context['username']}' logged in.")

    def set_error(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚠️ Record login error and continue."""
        context["error"] = str(event.data)
        logger.warning(f"⚠️ Login failed: {context['error']}")

    def clear_context(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔄 Clear all user-related context on logout."""
        if context.get("username"):
            logger.info(f"👤 User '{context['username']}' logged out.")
        context["username"] = None
        context["error"] = None
        context["credentials"] = None
        context["loginAttempts"] = 0
