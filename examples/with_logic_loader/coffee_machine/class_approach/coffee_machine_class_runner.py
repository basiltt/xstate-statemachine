# examples/with_logic_loader/coffee_machine/class_approach/coffee_machine_class_runner.py

# -----------------------------------------------------------------------------
# 🚀 Coffee Machine Runner (Class-Based)
# -----------------------------------------------------------------------------
# This script serves as the entry point for running the class-based
# CoffeeMachine simulation.
#
# It is responsible for:
#   1. Importing the `CoffeeMachine` logic class.
#   2. Loading the state machine configuration from a JSON file.
#   3. Instantiating the `CoffeeMachine`.
#   4. Executing a series of predefined scenarios to demonstrate the
#      machine's behavior.
# -----------------------------------------------------------------------------

import asyncio
import json
import logging
import os
import sys


# -----------------------------------------------------------------------------
# 🐍 Path Setup
# -----------------------------------------------------------------------------
# A simple way to handle paths so the library and logic module can be found.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

# 🏛️ Import the core logic class from its module.
from examples.with_logic_loader.coffee_machine.class_approach.coffee_machine_class_logic import (
    CoffeeMachine,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configure a global logger for clear, timestamped output for the runner.
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# -----------------------------------------------------------------------------
# ▶️ Main Execution
# -----------------------------------------------------------------------------


async def main() -> None:
    """Initializes and runs the class-based CoffeeMachine simulation.

    This function orchestrates the entire demonstration, running through a
    series of scenarios to showcase the state machine's behavior in response
    to various events and conditions.
    """
    print(
        "\n--- ☕ Initializing Coffee Machine Simulation (Class-Based Approach) ---"
    )

    # 📂 Load the machine configuration from the JSON file.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "../coffee_machine.json")
    with open(json_path, "r") as f:
        config = json.load(f)

    # 🏛️ Instantiate the main class, which handles all setup internally.
    coffee_machine = CoffeeMachine(config)
    interpreter = (
        coffee_machine.interpreter
    )  # Get a reference for easier access.

    # 🏁 Start the interpreter to put it in its initial state.
    await interpreter.start()
    print(
        f"\n🚀 Initial state: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 1: Make an Espresso ---
    print("\n--- 🎬 Scenario 1: Making an Espresso ---")
    await interpreter.send("SELECT_ESPRESSO")
    await interpreter.send("BREW")
    await asyncio.sleep(3.5)  # Wait for brew to finish.
    await interpreter.send("TAKE_DRINK")
    await asyncio.sleep(0.1)  # Allow state to settle.
    print(
        f"✅ Final state for scenario 1: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 2: Make more coffees to use up resources ---
    print("\n--- 🎬 Scenario 2: Making more coffees ---")
    for i in range(4):
        print(f"\nMaking coffee #{interpreter.context['coffeeCount'] + 1}...")
        await interpreter.send("SELECT_LATTE")
        await interpreter.send("BREW")
        await asyncio.sleep(3.5)
        await interpreter.send("TAKE_DRINK")
        await asyncio.sleep(0.1)
        print(
            f"State after coffee #{i + 2}: {interpreter.current_state_ids} | Context: {interpreter.context}"
        )
    print(
        f"✅ Final state for scenario 2: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 3: Try to brew with low water ---
    print(
        "\n--- 🎬 Scenario 3: Trying to brew with low water (should be blocked by guard) ---"
    )
    await interpreter.send("SELECT_ESPRESSO")
    await interpreter.send(
        "BREW"
    )  # This should be blocked by the 'canBrew' guard.
    await asyncio.sleep(0.1)
    print(
        f"✅ Final state for scenario 3: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 4: Refill Water ---
    print("\n--- 🎬 Scenario 4: Refilling Water Tank (invokes a service) ---")
    await interpreter.send("REFILL_WATER")
    await asyncio.sleep(4.5)  # Wait for the refill service to complete.
    print(
        f"✅ Final state for scenario 4: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 5: Try brewing again after refill ---
    print(
        "\n--- 🎬 Scenario 5: Trying to brew after refilling (should succeed) ---"
    )
    await interpreter.send("SELECT_LATTE")
    await interpreter.send("BREW")
    await asyncio.sleep(3.5)
    await interpreter.send("TAKE_DRINK")
    await asyncio.sleep(0.1)
    print(
        f"✅ Final state for scenario 5: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # --- Scenario 6: Clean Machine ---
    print(
        "\n--- 🎬 Scenario 6: Cleaning Machine (should be allowed by guard) ---"
    )
    await interpreter.send("CLEAN_MACHINE")
    await asyncio.sleep(5.5)  # Wait for cleaning cycle.
    print(
        f"✅ Final state for scenario 6: {interpreter.current_state_ids} | Context: {interpreter.context}"
    )

    # 🛑 Stop the interpreter gracefully.
    await interpreter.stop()
    print("\n--- 🏁 Coffee Machine simulation ended ---")


if __name__ == "__main__":
    # Run the main asynchronous event loop.
    asyncio.run(main())
