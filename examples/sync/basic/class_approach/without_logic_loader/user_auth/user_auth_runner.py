# examples/sync/basic/class_approach/without_logic_loader/user_auth_runner.py
import json
import logging
import os
import sys
from typing import Any, Dict

from examples.sync.basic.class_approach.without_logic_loader.user_auth.user_auth_logic import (
    UserAuthLogic,
)

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
)


# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


class UserAuthSimulation:
    """Orchestrates the setup and execution of the authentication simulation."""

    def __init__(self, config_path: str):
        """Initializes the simulation by setting up the machine and interpreter."""
        # 1. Instantiate the logic provider class.
        auth_logic_instance = UserAuthLogic()

        # 2. Manually bind its methods to a MachineLogic object.
        machine_logic = MachineLogic(
            actions={
                "set_user": auth_logic_instance.set_user,
                "set_error": auth_logic_instance.set_error,
                "clear_context": auth_logic_instance.clear_context,
                "increment_attempts": auth_logic_instance.increment_attempts,
                "cache_credentials": auth_logic_instance.cache_credentials,
            },
            guards={
                "is_not_locked_out": auth_logic_instance.is_not_locked_out
            },
            services={"attempt_login": auth_logic_instance.attempt_login},
        )

        # 3. Load config and create the machine with the explicit logic.
        with open(config_path, "r") as f:
            machine_config = json.load(f)
        auth_machine = create_machine(machine_config, logic=machine_logic)
        self.interpreter = SyncInterpreter(auth_machine)

    def run(self):
        """Executes a sequence of events to simulate user authentication."""
        print("\n--- 🔐 Synchronous User Authentication Simulation ---")
        self.interpreter.start()
        logging.info(f"Initial State: {self.interpreter.current_state_ids}")

        # --- Scenarios ---
        print("\n--- Scenario 1: User enters wrong password ---")
        self.interpreter.send("LOGIN", username="admin", password="wrong")
        logging.info(f"Current State: {self.interpreter.current_state_ids}\n")

        print("--- Scenario 2: User enters correct password ---")
        self.interpreter.send(
            "LOGIN", username="admin", password="password123"
        )
        logging.info(f"Current State: {self.interpreter.current_state_ids}\n")

        print("--- Scenario 3: User logs out ---")
        self.interpreter.send("LOGOUT")
        logging.info(f"Current State: {self.interpreter.current_state_ids}\n")

        print(
            "--- Scenario 4: User fails login 3 times and gets locked out ---"
        )
        self.interpreter.send(
            "LOGIN", username="admin", password="1"
        )  # Attempt 1
        self.interpreter.send(
            "LOGIN", username="admin", password="2"
        )  # Attempt 2
        self.interpreter.send(
            "LOGIN", username="admin", password="3"
        )  # Attempt 3, should now be locked
        logging.info(f"Final State: {self.interpreter.current_state_ids}")

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main():
    """Entry point for the simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_dir, "user_auth.json")
    simulation = UserAuthSimulation(config_path=config_file)
    simulation.run()


if __name__ == "__main__":
    main()
