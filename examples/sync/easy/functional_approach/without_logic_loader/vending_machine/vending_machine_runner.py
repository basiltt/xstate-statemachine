# examples/sync/easy/functional_approach/without_logic_loader/vending_machine/vending_machine_runner.py

# -----------------------------------------------------------------------------
# 🥤 Easy Example: Synchronous Vending Machine
# -----------------------------------------------------------------------------
# This script demonstrates the most direct usage of the `SyncInterpreter`.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter` for a blocking workflow.
#   - External JSON Config: The machine logic is loaded from a separate file.
#   - Explicit Logic Binding: A `MachineLogic` object is created manually,
#     mapping function objects directly to the names in the config.
#   - Functional Approach: Actions and guards are standalone functions.
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
from typing import Any, Dict


from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    Event,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -----------------------------------------------------------------------------
# ⚙️ Machine Logic (Actions & Guards)
# -----------------------------------------------------------------------------


def add_coin_action(i: SyncInterpreter, ctx: Dict, e: Event, ad: Any) -> None:
    """Action to add a coin to the context."""
    ctx["coins"] += 1
    logging.info(f"🪙 Coin inserted. Total coins: {ctx['coins']}")


def dispense_drink_action(
    i: SyncInterpreter, ctx: Dict, e: Event, ad: Any
) -> None:
    """Action to dispense a drink and reset coins."""
    ctx["coins"] = 0
    logging.info("🥤 Drink dispensed! Enjoy.")


def enough_coins_guard(ctx: Dict, e: Event) -> bool:
    """Guard to check if enough coins have been inserted."""
    can_dispense = ctx["coins"] >= 2
    if not can_dispense:
        logging.warning(f"⚠️  Not enough coins. Need 2, have {ctx['coins']}.")
    return can_dispense


# -----------------------------------------------------------------------------
# 🚀 Main Simulation
# -----------------------------------------------------------------------------


def run_vending_machine_simulation():
    """Initializes and runs the vending machine simulation."""
    print("\n--- 🥤 Synchronous Vending Machine Simulation ---")

    # 1. Load the machine configuration from a JSON file.
    with open("vending_machine.json", "r") as f:
        vending_machine_config = json.load(f)

    # 2. Manually create the MachineLogic instance (no auto-discovery).
    vending_logic = MachineLogic(
        actions={
            "add_coin": add_coin_action,
            "dispense_drink": dispense_drink_action,
        },
        guards={"enough_coins": enough_coins_guard},
    )

    # 3. Create the machine and the synchronous interpreter.
    machine = create_machine(vending_machine_config, logic=vending_logic)
    interpreter = SyncInterpreter(machine)

    # 4. Start the machine and run the simulation.
    interpreter.start()
    logging.info(f"Initial state: {interpreter.current_state_ids}")

    logging.info("\n--- Inserting one coin and trying to select ---")
    interpreter.send("INSERT_COIN")
    interpreter.send("SELECT_DRINK")  # This will be blocked by the guard
    logging.info(f"State after first attempt: {interpreter.current_state_ids}")

    logging.info("\n--- Inserting another coin ---")
    interpreter.send("INSERT_COIN")
    logging.info(f"State: {interpreter.current_state_ids}")

    logging.info("\n--- Selecting drink again (should succeed) ---")
    interpreter.send("SELECT_DRINK")
    logging.info(f"Final state: {interpreter.current_state_ids}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    run_vending_machine_simulation()
