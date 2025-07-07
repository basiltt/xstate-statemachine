# examples/with_logic_loader/coffee_machine/functional_approach/coffee_machine_runner.py

# -----------------------------------------------------------------------------
# 🚀 Coffee Machine Runner (Functional Approach)
# -----------------------------------------------------------------------------
# This script serves as the entry point for running a simulation of the coffee
# machine that uses the "functional" logic approach.
#
# Key Concepts Illustrated:
#   - Orchestration: This script orchestrates a series of events to simulate
#     a user interacting with the coffee machine over time.
#   - Logic Auto-Discovery: It demonstrates how `create_machine` can be pointed
#     to a module path (`logic_modules`) to automatically find and bind the
#     necessary action, guard, and service implementations.
#   - Asynchronous Simulation: It uses `asyncio.sleep` to correctly wait for
#     long-running state machine processes (like services or timed transitions)
#     to complete.
# -----------------------------------------------------------------------------

import asyncio
import json
import logging
import os
import sys

# -----------------------------------------------------------------------------
# 🐍 Path Setup
# -----------------------------------------------------------------------------
# A simple way to handle paths for examples so the library can be found.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

# -----------------------------------------------------------------------------
# 📚 Library Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    Interpreter,
    LoggingInspector,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# ▶️ Main Simulation Runner
# -----------------------------------------------------------------------------


async def run_coffee_machine_example() -> None:
    """Initializes and runs the full coffee machine simulation.

    This function orchestrates the entire demonstration, running through a
    series of scenarios to showcase the state machine's behavior in response
    to various events and conditions.
    """
    print(
        "\n--- ☕ Initializing Coffee Machine Simulation (Functional Approach) ---"
    )

    # 📂 Load the machine configuration from the central JSON file.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "../coffee_machine.json")
    with open(json_path, "r") as f:
        coffee_config = json.load(f)

    # 🏭 Create the machine instance.
    # We pass the module path to `logic_modules` for auto-discovery. The
    # factory will import this module and bind functions automatically based on name.
    logger.info(
        "Creating machine with logic from 'coffee_machine_logic.py'..."
    )
    coffee_machine_node = create_machine(
        config=coffee_config,
        logic_modules=[
            "examples.with_logic_loader.coffee_machine.functional_approach.coffee_machine_logic"
        ],
    )

    # 🚀 Create the interpreter, attach a logger, and start the machine.
    interpreter = Interpreter(coffee_machine_node)
    interpreter.use(LoggingInspector())
    await interpreter.start()

    logger.info(
        "🚀 Machine started. Initial state: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # -------------------------------------------------------------------------
    # --- Scenario 1: Make an Espresso ---
    # -------------------------------------------------------------------------
    print("\n--- 🎬 Scenario 1: Making an Espresso ---")
    await interpreter.send("SELECT_ESPRESSO")
    await asyncio.sleep(0.1)  # Allow event loop to process.
    await interpreter.send("BREW")
    await asyncio.sleep(3.5)  # Wait for the 3-second brew time + buffer.
    await interpreter.send("TAKE_DRINK")
    await asyncio.sleep(0.1)
    logger.info(
        "✅ Scenario 1 Complete. State: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # -------------------------------------------------------------------------
    # --- Scenario 2: Make more coffees to use up resources ---
    # -------------------------------------------------------------------------
    print(
        "\n--- 🎬 Scenario 2: Making more coffees to trigger cleaning/refill ---"
    )
    # The first coffee is already made. We make 4 more to reach 5 total.
    for i in range(4):
        logger.info(
            "--- Making coffee #%d... ---",
            interpreter.context["coffeeCount"] + 1,
        )
        await interpreter.send("SELECT_LATTE")
        await interpreter.send("BREW")
        await asyncio.sleep(3.5)
        await interpreter.send("TAKE_DRINK")
        await asyncio.sleep(0.1)
        logger.info(
            "State after coffee #%d: %s", i + 2, interpreter.current_state_ids
        )
    logger.info(
        "✅ Scenario 2 Complete. State: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # -------------------------------------------------------------------------
    # --- Scenario 3: Try to brew with low water ---
    # -------------------------------------------------------------------------
    print(
        "\n--- 🎬 Scenario 3: Trying to brew with low water (should be blocked) ---"
    )
    await interpreter.send("SELECT_ESPRESSO")
    await asyncio.sleep(0.1)
    await interpreter.send(
        "BREW"
    )  # This should be blocked by the 'canBrew' guard.
    await asyncio.sleep(0.1)
    logger.info(
        "✅ Scenario 3 Complete. State: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # -------------------------------------------------------------------------
    # --- Scenario 4: Refill Water ---
    # -------------------------------------------------------------------------
    print("\n--- 🎬 Scenario 4: Refilling Water Tank ---")
    logger.info("Current water level: %d%%", interpreter.context["waterLevel"])
    await interpreter.send("REFILL_WATER")
    await asyncio.sleep(0.1)
    logger.info("Machine is now in state: %s", interpreter.current_state_ids)
    await asyncio.sleep(
        4.5
    )  # Wait a bit more than the 4-second refill service.
    logger.info(
        "✅ Scenario 4 Complete. State: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # -------------------------------------------------------------------------
    # --- Scenario 5: Try brewing again after refill ---
    # -------------------------------------------------------------------------
    print(
        "\n--- 🎬 Scenario 5: Trying to brew after refilling (should succeed) ---"
    )
    await interpreter.send("SELECT_LATTE")
    await interpreter.send("BREW")
    await asyncio.sleep(3.5)
    await interpreter.send("TAKE_DRINK")
    await asyncio.sleep(0.1)
    logger.info(
        "✅ Scenario 5 Complete. State: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # -------------------------------------------------------------------------
    # --- Scenario 6: Clean Machine ---
    # -------------------------------------------------------------------------
    print("\n--- 🎬 Scenario 6: Cleaning Machine ---")
    logger.info("Current coffee count: %d", interpreter.context["coffeeCount"])
    await interpreter.send("CLEAN_MACHINE")
    await asyncio.sleep(0.1)
    logger.info("Machine is now in state: %s", interpreter.current_state_ids)
    await asyncio.sleep(5.5)  # Wait a bit more than the 5-second clean time.
    logger.info(
        "✅ Scenario 6 Complete. State: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # 🛑 Gracefully stop the interpreter.
    await interpreter.stop()
    print("\n--- 🏁 Coffee Machine simulation ended ---")


# -----------------------------------------------------------------------------
# 👟 Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(run_coffee_machine_example())
