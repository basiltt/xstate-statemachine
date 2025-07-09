# examples/sync/super_complex/class_approach/with_logic_loader/install_wizard_runner.py
# -----------------------------------------------------------------------------
# 🛠️ Super-Complex Example: Installation Wizard (Class-Based / LogicLoader)
# -----------------------------------------------------------------------------
# This script simulates a multi-step software installation wizard.
#
# Key Concepts Illustrated:
#   - Deeply Nested States: `configuring` and `installing` are compound states.
#   - `onDone` Transitions: Automatically progresses from `configuring` to
#     `installing`, and then to `finished`.
#   - Synchronous Service: A single `invoke` orchestrates multiple conceptual
#     steps within the `installing` state.
#   - Automatic Logic Discovery: A `logic_providers` instance is used.
# -----------------------------------------------------------------------------
import json
import logging
import os
import sys

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../../../..")
    ),
)
from src.xstate_statemachine import create_machine, SyncInterpreter
from examples.sync.super_complex.class_approach.with_logic_loader.install_wizard.install_wizard_logic import (
    InstallWizardLogic,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


def main():
    print("\n--- 🛠️  Synchronous Installation Wizard Simulation ---")

    # Corrected path to load the JSON from its sub-directory
    with open("install_wizard.json", "r") as f:
        config = json.load(f)

    # Instantiate the logic provider
    wizard_logic = InstallWizardLogic()

    # Create the machine using auto-discovery
    machine = create_machine(config, logic_providers=[wizard_logic])

    # --- Scenario 1: Successful Installation ---
    print("\n--- Scenario 1: Successful Installation ---")
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logging.info(f"State: {interpreter.current_state_ids}")

    interpreter.send("BEGIN_SETUP")
    logging.info(f"State: {interpreter.current_state_ids}")

    interpreter.send("SUBMIT_NETWORK", host="192.168.1.1")
    logging.info(f"State: {interpreter.current_state_ids}")

    interpreter.send("SUBMIT_DATABASE", type="postgres", user="admin")
    logging.info(f"State: {interpreter.current_state_ids}")

    # This next send will complete the 'configuring' state, triggering its onDone
    # transition to 'installing', which then invokes the installation service.
    interpreter.send("SUBMIT_ADMIN", user="app_admin")
    logging.info(f"Final State: {interpreter.current_state_ids}")
    logging.info(f"Final Context: {interpreter.context}")
    interpreter.stop()

    # --- Scenario 2: Failed Installation ---
    print("\n--- Scenario 2: Failed Installation due to DB error ---")
    # Re-create the interpreter for a clean run
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    interpreter.send("BEGIN_SETUP")
    interpreter.send("SUBMIT_NETWORK", host="10.0.0.5")
    interpreter.send(
        "SUBMIT_DATABASE", type="unsupported_db"
    )  # This will cause the service to fail
    interpreter.send("SUBMIT_ADMIN", user="root")
    logging.info(f"Final State: {interpreter.current_state_ids}")
    logging.info(f"Final Context: {interpreter.context}")
    interpreter.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
