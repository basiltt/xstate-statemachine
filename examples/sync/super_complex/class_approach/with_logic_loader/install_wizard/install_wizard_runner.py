# examples/sync/super_complex/class_approach/with_logic_loader/install_wizard/install_wizard_runner.py
# -----------------------------------------------------------------------------
# 🛠️ Install Wizard Runner
# -----------------------------------------------------------------------------
"""
Runner for the installation wizard simulation:

  • Configures network, database, admin steps
  • onDone transitions automatically invoke installation service
  • Handles success and failure scenarios
"""

import json
import logging
import time
from typing import Any, Dict

from install_wizard_logic import InstallWizardLogic  # noqa: E402
from src.xstate_statemachine import create_machine, SyncInterpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """🚀 Execute installation wizard simulation."""
    print("\n--- 🛠️ Installation Wizard Simulation ---")
    config_path = "install_wizard.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = InstallWizardLogic()
    machine = create_machine(config, logic_providers=[logic])

    # Scenario 1: Successful install
    print("\n--- Scenario 1: Successful Installation ---")
    interp = SyncInterpreter(machine)
    interp.start()
    logger.info("State: %s", interp.current_state_ids)
    interp.send("BEGIN_SETUP")
    time.sleep(1)  # Simulate some delay for user input
    interp.send("SUBMIT_NETWORK", host="192.168.1.1")
    time.sleep(1)  # Simulate some delay for user input
    interp.send("SUBMIT_DATABASE", type="postgres", user="admin")
    time.sleep(1)  # Simulate some delay for user input
    interp.send("SUBMIT_ADMIN", user="app_admin")

    time.sleep(1)  # Simulate some delay for user input
    logger.info("Final State: %s", interp.current_state_ids)
    logger.info("Final Context: %s", interp.context)
    interp.stop()

    # Scenario 2: Failure due to unsupported DB
    print("\n--- Scenario 2: Failed Installation ---")
    interp = SyncInterpreter(machine)
    interp.start()
    interp.send("BEGIN_SETUP")
    time.sleep(1)  # Simulate some delay for user input
    interp.send("SUBMIT_NETWORK", host="10.0.0.5")
    time.sleep(1)  # Simulate some delay for user input
    interp.send("SUBMIT_DATABASE", type="unsupported_db", user="root")
    time.sleep(1)  # Simulate some delay for user input
    interp.send("SUBMIT_ADMIN", user="root")
    time.sleep(1)  # Simulate some delay for user input
    logger.info("Final State: %s", interp.current_state_ids)
    logger.info("Final Context: %s", interp.context)

    interp.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
