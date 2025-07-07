# examples/with_logic_loader/coffee_machine/coffee_machine_hybrid_runner.py

# -----------------------------------------------------------------------------
# 🚀 Hybrid Logic Loader Runner
# -----------------------------------------------------------------------------
# This script demonstrates the "hybrid" capabilities of the `LogicLoader` by
# running two concurrent coffee machine simulations, each configured with a
# different logic-loading strategy.
#
# Key Concepts Illustrated:
#   - Logic Loading via Module Object: Machine A is configured by passing an
#     already-imported module object directly to the `create_machine` function.
#     This is useful, efficient, and provides strong typing.
#   - Logic Loading via String Path: Machine B is configured by passing the
#     full import path as a string, demonstrating the dynamic auto-discovery
#     feature of the `LogicLoader`.
#   - Concurrency: Both simulations run in parallel using `asyncio` to show
#     that both methods work seamlessly together.
# -----------------------------------------------------------------------------

import asyncio
import json
import logging
import os
import sys
from types import ModuleType
from typing import Any, Dict, List, Tuple, Union

# -----------------------------------------------------------------------------
# 🐍 Path Setup
# -----------------------------------------------------------------------------
# A simple way to handle paths for examples so the library can be found.
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)

from src.xstate_statemachine import Interpreter, create_machine

# -----------------------------------------------------------------------------
# ✨ Direct Logic Module Import
# -----------------------------------------------------------------------------
# To demonstrate the new feature, we import the logic module directly.
# This allows us to pass the `coffee_machine_logic` object itself.
from examples.with_logic_loader.coffee_machine.functional_approach import (
    coffee_machine_logic,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configure logging to include a custom 'name' field for differentiating
# between the concurrent machine instances (e.g., 'Machine-A (Module Object)').
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(name)s] - %(message)s",
)

# -----------------------------------------------------------------------------
# 🛠️ Simulation Helper Function
# -----------------------------------------------------------------------------


async def run_single_machine_simulation(
    machine_id: str,
    config: Dict[str, Any],
    scenarios: List[Tuple[str, float]],
    logic_modules: List[Union[str, ModuleType]],
) -> None:
    """Creates and runs one state machine, testing a logic loading method.

    This function encapsulates the lifecycle of a single interpreter and is
    parameterized to accept different logic loading strategies, making it a
    reusable component for this demonstration.

    Args:
        machine_id (str): A unique identifier for logging this instance's output.
        config (Dict[str, Any]): The machine configuration dictionary.
        scenarios (List[Tuple[str, float]]): The simulation steps as a list of
            (event_name, delay_after) tuples.
        logic_modules (List[Union[str, ModuleType]]): The list of logic modules
            to be passed to the `LogicLoader`. Can contain strings or module objects.
    """
    # 📝 Get a logger specific to this machine instance.
    logger = logging.getLogger(machine_id)
    loading_method = (
        "module object"
        if isinstance(logic_modules[0], ModuleType)
        else "string path"
    )
    logger.info("--- 🚀 Booting up using %s. ---", loading_method)

    # 🏭 Create the machine using the provided logic loading strategy.
    # The LogicLoader transparently handles both strings and module objects.
    machine_node = create_machine(config=config, logic_modules=logic_modules)

    # 🚀 Create and start the interpreter.
    interpreter = await Interpreter(machine_node).start()
    logger.info("✅ Initial state: %s", interpreter.current_state_ids)

    # 🏃‍♂️ Run through the defined scenarios for this machine instance.
    for event, delay in scenarios:
        logger.info("▶️ Sending event: '%s'", event)
        await interpreter.send(event)

        # ⏳ Wait for the specified delay.
        logger.info("...waiting for %.1fs...", delay)
        await asyncio.sleep(delay)

        # 📊 Log the state after the event and delay.
        logger.info("📊 Current state: %s", interpreter.current_state_ids)

    # 🛑 Gracefully stop the interpreter.
    await interpreter.stop()
    logger.info("--- 🏁 Shutting down. ---")


# -----------------------------------------------------------------------------
#  orchestrator
# -----------------------------------------------------------------------------


async def main() -> None:
    """Orchestrates concurrent simulations to demo hybrid logic loading.

    This function sets up and runs two coffee machines in parallel:
    - One using a direct module object for its logic.
    - One using a string path for dynamic logic discovery.
    """
    print("\n--- ☕ Running Hybrid Coffee Machine Simulations in Parallel ---")

    # 📂 Load the machine configuration once to be reused by all instances.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "../coffee_machine.json")
    with open(json_path, "r") as f:
        coffee_config = json.load(f)

    # 📝 Define simple, distinct scenarios for the two machines.
    scenarios_for_machine_a: List[Tuple[str, float]] = [
        ("SELECT_ESPRESSO", 0.1),
        ("BREW", 3.5),
    ]
    scenarios_for_machine_b: List[Tuple[str, float]] = [
        ("REFILL_WATER", 4.5),
        ("SELECT_LATTE", 0.1),
    ]

    # 🎭 Create concurrent tasks for each simulation, each with a different setup.

    # ✅ Task A demonstrates the NEW way: passing the imported module object.
    # This is efficient and provides better static analysis and IDE support.
    task_a = asyncio.create_task(
        run_single_machine_simulation(
            machine_id="Machine-A (Module Object)",
            config=coffee_config,
            scenarios=scenarios_for_machine_a,
            logic_modules=[coffee_machine_logic],  # Pass the imported module
        )
    )

    # ⏱️ Stagger the start of the second machine for clearer log interleaving.
    await asyncio.sleep(1)

    # ✅ Task B demonstrates the ORIGINAL way: passing the full import path as a string.
    # This is useful for highly dynamic applications where logic may not be known at startup.
    task_b = asyncio.create_task(
        run_single_machine_simulation(
            machine_id="Machine-B (String Path)",
            config=coffee_config,
            scenarios=scenarios_for_machine_b,
            logic_modules=[
                "examples.with_logic_loader.coffee_machine.functional_approach.coffee_machine_logic"
            ],
        )
    )

    # ✨ Gather and await the completion of all simulation tasks.
    await asyncio.gather(task_a, task_b)

    print("\n--- ✅ All hybrid simulations complete ---")


if __name__ == "__main__":
    # 👟 Run the main asynchronous event loop.
    asyncio.run(main())
