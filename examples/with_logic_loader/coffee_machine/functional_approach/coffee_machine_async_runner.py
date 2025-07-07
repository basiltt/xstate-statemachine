# examples/with_logic_loader/coffee_machine/functional_approach/coffee_machine_async_runner.py

# -----------------------------------------------------------------------------
# 🚀 Concurrent Machine Runner (Functional Approach)
# -----------------------------------------------------------------------------
# This script demonstrates how to create and run multiple, independent state
# machine interpreters concurrently using Python's `asyncio` library.
#
# Key Concepts Illustrated:
#   - Concurrency: Two coffee machine simulations are run in parallel,
#     showcasing how the library handles multiple independent state contexts.
#   - Logic Auto-Discovery: The `create_machine` function uses the
#     `logic_modules` argument to dynamically discover and load the required
#     actions, guards, and services from a specified module.
#   - DRY Principle: The `run_single_machine_simulation` function encapsulates
#     the logic for running one simulation, which is then reused for each
#     concurrent task.
# -----------------------------------------------------------------------------

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

# -----------------------------------------------------------------------------
# 🐍 Path Setup
# -----------------------------------------------------------------------------
# A simple way to handle paths for examples so the library can be found.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

from src.xstate_statemachine import Interpreter, create_machine

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configure logging to include a custom 'name' field, which we'll use to
# differentiate between concurrent machine instances (e.g., 'Machine-A').
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
)


# -----------------------------------------------------------------------------
# 🛠️ Simulation Helper Function
# -----------------------------------------------------------------------------


async def run_single_machine_simulation(
    machine_id: str, config: Dict[str, Any], scenarios: List[Tuple[str, float]]
) -> None:
    """Creates and runs one state machine instance through its scenarios.

    This function encapsulates the entire lifecycle of a single interpreter:
    creation, startup, event processing, and shutdown. It's designed to be
    run as an independent asynchronous task.

    Args:
        machine_id (str): A unique identifier for this machine instance, used
            for logging to distinguish its output from other concurrent runs.
        config (Dict[str, Any]): The machine configuration dictionary.
        scenarios (List[Tuple[str, float]]): A list of (event_name, delay_after)
            tuples that define the simulation steps for this instance.
    """
    # 📝 Get a logger specific to this machine instance.
    logger = logging.getLogger(machine_id)
    logger.info("--- 🚀 Booting up machine. ---")

    # 🏭 Create the machine instance. This uses the `LogicLoader`'s auto-discovery
    # feature by pointing to the module containing the implementations.
    machine_node = create_machine(
        config=config,
        logic_modules=[
            "examples.with_logic_loader.coffee_machine.functional_approach.coffee_machine_logic"
        ],
    )

    # 🚀 Create and start the interpreter. The `await` here ensures the
    # machine is fully initialized before we proceed.
    interpreter = await Interpreter(machine_node).start()
    logger.info(
        "✅ Initial state: %s | Context: %s",
        interpreter.current_state_ids,
        interpreter.context,
    )

    # 🏃‍♂️ Run through the defined scenarios for this machine instance.
    for event, delay in scenarios:
        logger.info("▶️ Sending event: '%s'", event)
        await interpreter.send(event)

        # ⏳ Wait for the specified delay to simulate processing time (e.g., brewing).
        logger.info("...waiting for %.1fs...", delay)
        await asyncio.sleep(delay)

        # 📊 Log the state after the event and delay.
        logger.info(
            "📊 Current state: %s | Context: %s",
            interpreter.current_state_ids,
            interpreter.context,
        )

    # 🛑 Gracefully stop the interpreter.
    await interpreter.stop()
    logger.info("--- 🏁 Shutting down. ---")


# -----------------------------------------------------------------------------
#  orchestrator
# -----------------------------------------------------------------------------


async def main() -> None:
    """Main function to orchestrate and run multiple simulations concurrently.

    This function sets up the environment, defines the different scenarios for
    each machine, and uses `asyncio` to create and manage the concurrent tasks.
    """
    print(
        "\n--- ☕ Running Multiple Coffee Machine Simulations in Parallel ---"
    )

    # 📂 Load the machine configuration once to be reused by all instances.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "../coffee_machine.json")
    with open(json_path, "r") as f:
        coffee_config = json.load(f)

    # 📝 Define different scenarios for two separate machine instances.
    # This demonstrates that each machine will have its own independent state and context.

    # Machine A will make an espresso, then a latte.
    scenarios_for_machine_a: List[Tuple[str, float]] = [
        ("SELECT_ESPRESSO", 0.1),
        ("BREW", 3.5),  # 3s brew time + 0.5s buffer
        ("TAKE_DRINK", 0.5),
        ("SELECT_LATTE", 0.1),
        ("BREW", 3.5),  # 3s brew time + 0.5s buffer
        ("TAKE_DRINK", 0.1),
    ]

    # Machine B will start slightly later, refill its water, then make a coffee.
    scenarios_for_machine_b: List[Tuple[str, float]] = [
        ("REFILL_WATER", 4.5),  # 4s refill time + 0.5s buffer
        ("SELECT_ESPRESSO", 0.1),
        ("BREW", 3.5),  # 3s brew time + 0.5s buffer
        ("TAKE_DRINK", 0.1),
    ]

    # 🎭 Create concurrent tasks for each machine simulation.
    task_a = asyncio.create_task(
        run_single_machine_simulation(
            "Machine-A", coffee_config, scenarios_for_machine_a
        )
    )

    # ⏱️ Add a small delay before starting the second machine.
    # This makes the interleaved execution in the logs easier to follow.
    await asyncio.sleep(1)

    task_b = asyncio.create_task(
        run_single_machine_simulation(
            "Machine-B", coffee_config, scenarios_for_machine_b
        )
    )

    # ✨ Gather and await the completion of all simulation tasks.
    # The program will not proceed past this line until both task_a and task_b are done.
    await asyncio.gather(task_a, task_b)

    print("\n--- ✅ All simulations complete ---")


if __name__ == "__main__":
    # 👟 Run the main asynchronous event loop.
    asyncio.run(main())
