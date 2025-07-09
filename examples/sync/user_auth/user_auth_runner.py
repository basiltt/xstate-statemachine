# examples/user_auth_runner.py

# -----------------------------------------------------------------------------
# 🚀 Class-Based Simulation Runner
# -----------------------------------------------------------------------------
# This script orchestrates the setup and execution of the user authentication
# simulation. It imports the logic from `user_auth_logic.py` and uses a
# class-based approach to run the simulation.
# -----------------------------------------------------------------------------

import json
import logging
import os
from typing import Any, Dict

# Make the library and logic files accessible
import sys


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
)

# 🧠 Import the separated logic class
from examples.sync.user_auth.user_auth_logic import UserAuthLogic

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class UserAuthSimulation:
    """Orchestrates the setup and execution of the authentication simulation."""

    def __init__(self, config_path: str):
        """
        Initializes the simulation by setting up the machine and interpreter.

        Args:
            config_path (str): The file path to the machine's JSON configuration.
        """
        # 1. Instantiate the logic provider
        auth_logic_instance = UserAuthLogic()

        # 2. Manually bind its methods to a MachineLogic object
        machine_logic = MachineLogic(
            actions={
                "set_user": auth_logic_instance.set_user,
                "set_error": auth_logic_instance.set_error,
                "clear_context": auth_logic_instance.clear_context,
                "increment_attempts": auth_logic_instance.increment_attempts,
                # ✅ FIX: Add the missing binding for the new action.
                "cache_credentials": auth_logic_instance.cache_credentials,
            },
            guards={
                "is_not_locked_out": auth_logic_instance.is_not_locked_out
            },
            services={"attempt_login": auth_logic_instance.attempt_login},
        )

        # 3. Load config, create the machine, and create the interpreter
        with open(config_path, "r") as f:
            machine_config = json.load(f)

        auth_machine = create_machine(machine_config, logic=machine_logic)
        self.interpreter = SyncInterpreter(auth_machine)

    def run(self):
        """Executes a sequence of events to simulate user authentication."""
        print("\n--- 🔐 Synchronous User Authentication Simulation ---")
        self.interpreter.start()
        logging.info(f"Initial State: {self.interpreter.current_state_ids}")

        # --- Scenario 1: Failed Login ---
        print("\n--- Scenario 1: User enters wrong password ---")
        self.interpreter.send("LOGIN", username="admin", password="wrong")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}\n")

        # --- Scenario 2: Successful Login ---
        print("--- Scenario 2: User enters correct password ---")
        self.interpreter.send(
            "LOGIN", username="admin", password="password123"
        )
        logging.info(f"Current State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}\n")

        # --- Scenario 3: Logout ---
        print("--- Scenario 3: User logs out ---")
        self.interpreter.send("LOGOUT")
        logging.info(f"Current State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}\n")

        # --- Scenario 4: Lockout ---
        print(
            "--- Scenario 4: User fails login 3 times and gets locked out ---"
        )
        self.interpreter.send(
            "LOGIN", username="admin", password="1"
        )  # Attempt 2
        self.interpreter.send(
            "LOGIN", username="admin", password="2"
        )  # Attempt 3
        # This fourth attempt should be blocked by the guard
        self.interpreter.send("LOGIN", username="admin", password="3")
        logging.info(f"Final State: {self.interpreter.current_state_ids}")
        logging.info(f"Context: {self.interpreter.context}")

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main():
    """Entry point for the simulation."""
    # Note: Assumes the script is run from the root project directory.
    config_file = "user_auth.json"
    if not os.path.exists(config_file):
        logging.error(f"❌ Configuration file not found at '{config_file}'")
        return

    simulation = UserAuthSimulation(config_path=config_file)
    simulation.run()


if __name__ == "__main__":
    main()
