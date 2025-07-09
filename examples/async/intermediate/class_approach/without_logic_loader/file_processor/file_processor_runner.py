# examples/async/intermediate/class_approach/without_logic_loader/file_processor_runner.py
# -----------------------------------------------------------------------------
# ⚙️ Intermediate Example: Async File Processor (Class-Based / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Asynchronous Services (`invoke`) to simulate a long-running task.
#   - `onDone`/`onError` for branching based on the service outcome.
#   - Explicit Logic Binding of an `async` service method.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from file_processor_logic import FileProcessorLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def run_simulation(config, logic):
    interpreter = await Interpreter(
        create_machine(config, logic=logic)
    ).start()
    return interpreter


async def main():
    print(
        "\n--- ⚙️ Async File Processor Simulation (Class / Explicit Logic) ---"
    )

    with open("file_processor.json", "r") as f:
        config = json.load(f)

    logic_provider = FileProcessorLogic()
    machine_logic = MachineLogic(
        actions={
            "set_file_info": logic_provider.set_file_info,
            "log_success": logic_provider.log_success,
            "log_failure": logic_provider.log_failure,
        },
        services={"process_file": logic_provider.process_file},
    )

    # --- Scenario 1: Process a supported file type ---
    print("\n--- Scenario 1: Successful Image Processing ---")
    interpreter1 = await run_simulation(config, machine_logic)
    await interpreter1.send("UPLOAD", name="vacation.jpg", type="image")
    await asyncio.sleep(2.5)  # Wait for invoke
    await interpreter1.stop()

    # --- Scenario 2: Process an unsupported file type ---
    print("\n--- Scenario 2: Failed PDF Processing ---")
    interpreter2 = await run_simulation(config, machine_logic)
    await interpreter2.send("UPLOAD", name="report.pdf", type="pdf")
    await asyncio.sleep(2.5)  # Wait for invoke
    await interpreter2.stop()

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
