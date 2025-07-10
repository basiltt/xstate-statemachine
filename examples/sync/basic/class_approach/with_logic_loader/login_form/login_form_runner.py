# examples/sync/basic/class_approach/with_logic_loader/login_form_runner.py
# -----------------------------------------------------------------------------
# 🔒 Basic Example: Synchronous Login Form (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
"""
Runner script for a synchronous login form state machine.

Key Concepts:
  • Uses `SyncInterpreter` for sync execution.
  • Class-based logic auto-discovered via `logic_providers`.
  • Guards & services demonstrate form validation and credential check.
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict

# 🛠️ Ensure project root is on PYTHONPATH
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)

from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    Event,
    ActionDefinition,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class LoginForm:
    """Encapsulates the login form state machine and its logic."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the machine and its SyncInterpreter.

        Args:
            config: The JSON-loaded machine configuration.
        """
        machine = create_machine(config, logic_providers=[self])
        self.interpreter = SyncInterpreter(machine)

    def update_field(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📝 Update username or password field in context.

        Args:
            interpreter: The running SyncInterpreter.
            context: Mutable machine context.
            event: Event carrying 'field' and 'value' in payload.
            action_def: Metadata about this action.
        """
        field = event.payload.get("field")
        value = event.payload.get("value")
        if field in context:
            context[field] = value
            logger.info(f"📝 Field '{field}' updated to '{value}'.")

    def set_error(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🚨 Record an error message after a failed service.

        Args:
            interpreter: The running SyncInterpreter.
            context: Mutable machine context.
            event: DoneEvent carrying error in `data`.
            action_def: Metadata about this action.
        """
        context["error"] = str(event.data)
        logger.warning(f"🚨 Error set: {context['error']}")

    def clear_error(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🧹 Clear the error message on successful login."""
        context["error"] = None
        logger.info("🧹 Error cleared.")

    def are_fields_filled(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """🛡️ Guard: Ensure both username and password are provided.

        Args:
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            True if both fields are non-empty; False otherwise.
        """
        filled = bool(context.get("username") and context.get("password"))
        if not filled:
            logger.warning("🛡️ Guard failed: Both fields must be filled.")
        return filled

    def verify_credentials(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, str]:
        """⚙️ Service: Synchronous credential verification.

        Args:
            interpreter: The running SyncInterpreter.
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            A dict with status on success.

        Raises:
            ValueError: If credentials are invalid.
        """
        logger.info("⚙️ Verifying credentials...")
        if (
            context.get("username") == "user"
            and context.get("password") == "pass"
        ):
            logger.info("✅ Credentials verified.")
            return {"status": "ok"}
        raise ValueError("Invalid credentials")

    def run_simulation(self) -> None:
        """🚀 Execute a predefined simulation of login scenarios."""
        print("\n--- 🔐 Synchronous Login Form Simulation ---")
        self.interpreter.start()
        logger.info(f"Initial State: {self.interpreter.current_state_ids}")

        time.sleep(2)

        print("\n--- Scenario 1: Submit with empty fields ---")
        self.interpreter.send("SUBMIT")
        logger.info(f"State remains: {self.interpreter.current_state_ids}")

        time.sleep(2)

        print("\n--- Scenario 2: Wrong credentials ---")
        self.interpreter.send("UPDATE_FIELD", field="username", value="user")
        self.interpreter.send("UPDATE_FIELD", field="password", value="wrong")
        self.interpreter.send("SUBMIT")
        logger.info(
            f"State after failure: {self.interpreter.current_state_ids}"
        )
        logger.info(f"Context: {self.interpreter.context}")

        time.sleep(2)

        print("\n--- Scenario 3: Correct credentials ---")
        self.interpreter.send("UPDATE_FIELD", field="password", value="pass")
        self.interpreter.send("SUBMIT")
        logger.info(f"Final State: {self.interpreter.current_state_ids}")
        logger.info(f"Final Context: {self.interpreter.context}")

        time.sleep(1)

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main() -> None:
    """Load configuration and run the login form simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "login_form.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Config not found at '{json_path}'")
        return

    form = LoginForm(config)
    form.run_simulation()


if __name__ == "__main__":
    main()
