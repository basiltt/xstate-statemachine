# -------------------------------------------------------------------------------
# ⚙️ Async File Processor Runner
# examples/async/intermediate/class_approach/without_logic_loader/file_processor_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the async File Processor simulation with explicit logic binding.

Illustrates:
  • Async service invocation (`invoke`).
  • `onDone` / `onError` transitions.
  • Explicit MachineLogic for actions and service.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, MachineLogic, create_machine

# -----------------------------------------------------------------------------
# 🛠️ Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from file_processor_logic import FileProcessorLogic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def run_simulation(
    config: Dict[str, Any], logic: MachineLogic
) -> Interpreter:
    """🔧 Helper to start an interpreter with given config and logic."""
    interpreter = await Interpreter(
        create_machine(config, logic=logic)
    ).start()
    return interpreter


async def main() -> None:
    """🚀 Execute the File Processor state machine simulation."""
    logger.info("\n--- ⚙️ Async File Processor Simulation ---")

    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "file_processor.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic_provider = FileProcessorLogic()
    machine_logic = MachineLogic(
        actions={
            "set_file_info": logic_provider.set_file_info,
            "log_success": logic_provider.log_success,
            "log_failure": logic_provider.log_failure,
        },
        services={"process_file": logic_provider.process_file},
    )

    # Scenario 1: supported file
    logger.info("\n--- Scenario 1: Successful Image Processing ---")
    interp1 = await run_simulation(config, machine_logic)
    await interp1.send("UPLOAD", name="vacation.jpg", type="image")
    await asyncio.sleep(2.5)
    await interp1.stop()

    # Scenario 2: unsupported file
    logger.info("\n--- Scenario 2: Failed PDF Processing ---")
    interp2 = await run_simulation(config, machine_logic)
    await interp2.send("UPLOAD", name="report.pdf", type="pdf")
    await asyncio.sleep(2.5)
    await interp2.stop()

    logger.info("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
