# examples/sync/easy/functional_approach/without_logic_loader/vending_machine/vending_machine_runner.py
# -----------------------------------------------------------------------------
# 🥤 Easy Example: Synchronous Vending Machine (Explicit Logic)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous vending machine demonstration.

Key Concepts:
  • SyncInterpreter for blocking flow.
  • Explicit MachineLogic binding of actions and guards.
"""

import json
import logging
import time
from typing import Any, Dict

from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    Event,
    ActionDefinition,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def add_coin(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🪙 Action: Insert a coin and increment count."""
    context["coins"] = context.get("coins", 0) + 1
    logger.info(f"🪙 Coin inserted. Total coins: {context['coins']}.")


def dispense_drink(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🥤 Action: Dispense drink and reset coin count."""
    context["coins"] = 0
    logger.info("🥤 Drink dispensed! Enjoy.")


def enough_coins(
    context: Dict[str, Any],
    event: Event,  # noqa
) -> bool:
    """🛡️ Guard: Allow dispense only if ≥2 coins inserted."""
    count = context.get("coins", 0)
    allowed = count >= 2
    if not allowed:
        logger.warning(f"⚠️ Need 2 coins, have {count}. Action blocked.")
    return allowed


def run_vending_machine() -> None:
    """🚀 Load config, bind logic, and run vending machine simulation."""
    print("\n--- 🥤 Vending Machine Simulation ---")

    config_path = "vending_machine.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    logic = MachineLogic(
        actions={"add_coin": add_coin, "dispense_drink": dispense_drink},
        guards={"enough_coins": enough_coins},
    )
    machine = create_machine(config, logic=logic)
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f"Initial State: {interpreter.current_state_ids}")

    time.sleep(1)  # Simulate some initial delay

    print("\n--- Inserting one coin and selecting ---")
    interpreter.send("INSERT_COIN")
    interpreter.send("SELECT_DRINK")
    logger.info(f"State: {interpreter.current_state_ids}")

    time.sleep(2)  # Simulate some delay before next action

    print("\n--- Inserting second coin ---")
    interpreter.send("INSERT_COIN")
    logger.info(f"State: {interpreter.current_state_ids}")

    time.sleep(2)  # Simulate some delay before dispensing

    print("\n--- Selecting drink ---")
    interpreter.send("SELECT_DRINK")
    logger.info(f"Final State: {interpreter.current_state_ids}")

    time.sleep(3)  # Simulate some delay before stopping

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    run_vending_machine()
