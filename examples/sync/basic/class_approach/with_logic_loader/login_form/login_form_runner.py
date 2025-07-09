# examples/sync/basic/class_approach/with_logic_loader/login_form_runner.py

# -----------------------------------------------------------------------------
# 🔒 Basic Example: Synchronous Login Form (Class-Based with LogicLoader)
# -----------------------------------------------------------------------------
# This script simulates a basic login form.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Class-Based Logic: The `LoginForm` class encapsulates all logic.
#   - Automatic Logic Discovery: An instance of the `LoginForm` class is
#     passed to `create_machine` via `logic_providers`, allowing the
#     LogicLoader to auto-discover and bind its methods.
#   - Guards & Services: Demonstrates a guard (`are_fields_filled`) and a
#     synchronous service (`verify_credentials`).
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
from typing import Dict, Any

# --- Path Setup ---
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

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -----------------------------------------------------------------------------
# 🏛️ LoginForm Class
# -----------------------------------------------------------------------------
class LoginForm:
    """Encapsulates the logic and interpreter for a login form."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the LoginForm."""
        # Create the machine, passing `self` to `logic_providers`.
        # The LogicLoader will inspect this instance and bind its methods.
        machine = create_machine(config, logic_providers=[self])
        self.interpreter = SyncInterpreter(machine)

    # --- Actions ---
    def update_field(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Updates the username or password in the context."""
        field = e.payload.get("field")
        value = e.payload.get("value")
        if field in ctx:
            ctx[field] = value
            logging.info(f"📝 Field '{field}' updated.")

    def set_error(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Sets the error message from a failed service."""
        ctx["error"] = str(e.data)
        logging.warning(f"🚨 Error set: {ctx['error']}")

    def clear_error(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ) -> None:
        """Clears the error message on success."""
        ctx["error"] = None

    # --- Guards ---
    def are_fields_filled(self, ctx: Dict, e: Event) -> bool:
        """Checks if both username and password fields have values."""
        is_filled = bool(ctx["username"] and ctx["password"])
        if not is_filled:
            logging.warning("🛡️ Guard failed: Both fields are required.")
        return is_filled

    # --- Services ---
    def verify_credentials(
        self, i: SyncInterpreter, c: Dict, e: Event
    ) -> Dict[str, str]:
        """A synchronous service to simulate credential verification."""
        logging.info("⚙️ Service: Verifying credentials...")
        if c["username"] == "user" and c["password"] == "pass":
            logging.info("✅ Credentials verified.")
            return {"status": "ok"}
        else:
            raise ValueError("Invalid credentials")

    def run_simulation(self):
        """Runs a predefined simulation of the login form."""
        print("\n--- 🔐 Synchronous Login Form Simulation ---")
        self.interpreter.start()
        logging.info(f"Initial State: {self.interpreter.current_state_ids}")

        print("\n--- Scenario 1: Submit with empty fields ---")
        self.interpreter.send("SUBMIT")  # Should be blocked by guard
        logging.info(f"State is still: {self.interpreter.current_state_ids}\n")

        print("--- Scenario 2: Enter wrong credentials ---")
        self.interpreter.send("UPDATE_FIELD", field="username", value="user")
        self.interpreter.send("UPDATE_FIELD", field="password", value="wrong")
        self.interpreter.send("SUBMIT")
        logging.info(
            f"State after failed login: {self.interpreter.current_state_ids}"
        )
        logging.info(f"Context: {self.interpreter.context}\n")

        print("--- Scenario 3: Enter correct credentials ---")
        self.interpreter.send("UPDATE_FIELD", field="password", value="pass")
        self.interpreter.send("SUBMIT")
        logging.info(f"Final State: {self.interpreter.current_state_ids}")
        logging.info(f"Final Context: {self.interpreter.context}")

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


# -----------------------------------------------------------------------------
# 🚀 Main Execution
# -----------------------------------------------------------------------------
def main():
    """Loads config and runs the login form simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "login_form.json")
    try:
        with open(json_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"❌ Configuration file not found at '{json_path}'")
        return

    login_form = LoginForm(config)
    login_form.run_simulation()


if __name__ == "__main__":
    main()
