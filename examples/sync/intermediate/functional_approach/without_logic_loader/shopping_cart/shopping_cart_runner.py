# examples/sync/intermediate/functional_approach/without_logic_loader/shopping_cart_runner.py
# -----------------------------------------------------------------------------
# 🛒 Intermediate Example: Shopping Cart (Explicit Logic)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous shopping cart state machine.

Key Concepts:
  • SyncInterpreter for blocking execution.
  • Explicit MachineLogic binding of actions, guards, and services.
  • Guard prevents checkout on empty cart.
  • Sync service simulates payment processing.
"""

import json
import logging
import sys
import os
import time
from typing import Any, Dict

from xstate_statemachine import (

# 🛡️ Windows consoles default to a legacy code page (cp1252), where the emoji
#    below raise UnicodeEncodeError and abort the example. Reconfiguring the
#    stream keeps the output readable everywhere; `errors="replace"` means a
#    terminal that still cannot render a glyph degrades instead of crashing.
if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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


def add_item_to_cart(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🛒 Action: Add payload['item'] to the cart."""
    item = event.payload.get("item")
    context.setdefault("items", []).append(item)
    logger.info(
        f"🛒 Added '{item}'. Cart now has {len(context['items'])} item(s)."
    )


def clear_cart(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🗑️ Action: Clear all items from the cart."""
    context["items"] = []
    logger.info("🗑️ Cart has been emptied.")


def cart_is_not_empty(context: Dict[str, Any], event: Event) -> bool:  # noqa
    """🛡️ Guard: Ensure the cart contains at least one item."""
    valid = len(context.get("items", [])) > 0
    if not valid:
        logger.warning("🛡️ Cannot checkout: Cart is empty.")
    return valid


def process_payment_sync(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
) -> Dict[str, Any]:
    """💳 Service: Simulate payment processing synchronously.

    Args:
        interpreter: The running SyncInterpreter.
        context: Mutable context dictionary.
        event: The triggering Event.

    Returns:
        A dict with confirmation code.
    """
    logger.info("💳 Processing payment...")
    time.sleep(1)
    logger.info("✅ Payment successful.")
    return {"confirmation": "XYZ-789"}


def main() -> None:
    """Load configuration and run the shopping cart simulation."""
    print("\n--- 🛒 Shopping Cart Simulation ---")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "shopping_cart.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = MachineLogic(
        actions={
            "add_item_to_cart": add_item_to_cart,
            "clear_cart": clear_cart,
        },
        guards={"cart_is_not_empty": cart_is_not_empty},
        services={"process_payment_sync": process_payment_sync},
    )
    machine = create_machine(config, logic=logic)
    interpreter = SyncInterpreter(machine)
    interpreter.start()
    logger.info(f"Initial State: {interpreter.current_state_ids}")

    time.sleep(1)  # Allow time for initial state logging

    print("\n--- Scenario 1: Checkout with empty cart ---")
    interpreter.send("CHECKOUT")
    logger.info(f"State: {interpreter.current_state_ids}\n")

    time.sleep(1)  # Allow time for state logging

    print("--- Scenario 2: Add items and checkout ---")
    interpreter.send("ADD_ITEM", item="Milk")
    interpreter.send("ADD_ITEM", item="Bread")
    interpreter.send("CHECKOUT")
    logger.info(f"Final State: {interpreter.current_state_ids}")
    logger.info(f"Final Context: {interpreter.context}")

    time.sleep(3)  # Allow time for final state logging

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
