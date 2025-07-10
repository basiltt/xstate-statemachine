# examples/sync/basic/class_approach/without_logic_loader/user_auth_runner.py
# -----------------------------------------------------------------------------
# 🔐 Synchronous User Authentication Runner (Explicit Logic)
# -----------------------------------------------------------------------------
"""
Orchestrates a synchronous user authentication simulation.

Key Concepts:
  • Explicit `MachineLogic` binding of actions, guards, services.
  • `SyncInterpreter` for deterministic, blocking execution.
"""

import json
import logging
import os
import sys
import time

# 🛠️ Ensure project root on PYTHONPATH
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
)
from user_auth_logic import UserAuthLogic

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class UserAuthSimulation:
    """Sets up and runs the user authentication state machine."""

    def __init__(self, config_path: str) -> None:
        """Load config, bind logic, and prepare the interpreter.

        Args:
            config_path: Path to the JSON machine definition.
        """
        logic = UserAuthLogic()
        machine_logic = MachineLogic(
            actions={
                "cache_credentials": logic.cache_credentials,
                "increment_attempts": logic.increment_attempts,
                "set_user": logic.set_user,
                "set_error": logic.set_error,
                "clear_context": logic.clear_context,
            },
            guards={"is_not_locked_out": logic.is_not_locked_out},
            services={"attempt_login": logic.attempt_login},
        )
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        machine = create_machine(config, logic=machine_logic)
        self.interpreter = SyncInterpreter(machine)

    def run(self) -> None:
        """Execute a sequence of events simulating login and logout flows."""
        print("\n--- 🔐 Synchronous User Authentication Simulation ---")
        self.interpreter.start()
        logger.info(f"Initial State: {self.interpreter.current_state_ids}")

        time.sleep(2)  # Simulate some initial delay

        print("\n--- Scenario 1: Wrong password ---")
        self.interpreter.send("LOGIN", username="admin", password="wrong")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(2)  # Simulate some delay before next action

        print("\n--- Scenario 2: Correct password ---")
        self.interpreter.send(
            "LOGIN", username="admin", password="password123"
        )
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(2)  # Simulate some delay before next action

        print("\n--- Scenario 3: Logout ---")
        self.interpreter.send("LOGOUT")
        logger.info(f"State: {self.interpreter.current_state_ids}")

        time.sleep(2)  # Simulate some delay before next action

        print("\n--- Scenario 4: Lockout after 3 fails ---")
        for pwd in ("1", "2", "3"):
            self.interpreter.send("LOGIN", username="admin", password=pwd)
        logger.info(f"Final State: {self.interpreter.current_state_ids}")

        time.sleep(2)  # Simulate some delay before stopping

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


def main() -> None:
    """Entry point to start the authentication simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(current_dir, "user_auth.json")
    sim = UserAuthSimulation(config_file)
    sim.run()


if __name__ == "__main__":
    main()
