# examples/sync/basic/class_approach/without_logic_loader/user_auth_logic.py

import logging
from typing import Dict

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition


class UserAuthLogic:
    """Encapsulates all implementation logic for the user auth state machine."""

    def cache_credentials(
        self, i: SyncInterpreter, c: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Action to store the login payload in the context."""
        c["credentials"] = e.payload
        logging.info("📝 Caching credentials for login attempt.")

    def set_user(
        self, i: SyncInterpreter, c: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Action to set the username in context upon successful login."""
        c["username"] = e.data.get("username")
        c["error"] = None
        c["credentials"] = None
        c["loginAttempts"] = 0
        logging.info(f"✅ User '{c['username']}' successfully logged in.")

    def set_error(
        self, i: SyncInterpreter, c: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Action to record the login error message in context."""
        c["error"] = str(e.data)
        logging.warning(f"🚨 Login failed: {c['error']}")

    def clear_context(
        self, i: SyncInterpreter, c: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Action to clear user data on logout."""
        if c.get("username"):
            logging.info(f"👤 User '{c['username']}' logged out.")
        c["username"] = None
        c["error"] = None
        c["credentials"] = None

    def increment_attempts(
        self, i: SyncInterpreter, c: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Action to increment the login attempt counter."""
        c["loginAttempts"] += 1
        logging.info(f"📈 Login attempts: {c['loginAttempts']}")

    def is_not_locked_out(self, c: Dict, e: Event) -> bool:
        """Guard to prevent login if attempts exceed a threshold."""
        max_attempts = 3
        if c["loginAttempts"] >= max_attempts:
            logging.error("❌ Account locked. Too many failed attempts.")
            return False
        return True

    def attempt_login(
        self, i: SyncInterpreter, c: Dict, e: Event
    ) -> Dict[str, str]:
        """Synchronous service to simulate a login attempt."""
        credentials = c.get("credentials", {})
        username = credentials.get("username")
        password = credentials.get("password")
        logging.info(f"🔐 Attempting login for user '{username}'...")
        if username == "admin" and password == "password123":
            return {"username": username}
        else:
            raise ValueError("Invalid username or password")
