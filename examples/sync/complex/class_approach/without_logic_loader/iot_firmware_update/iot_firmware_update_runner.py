# -----------------------------------------------------------------------------
# ⚡ IoT Firmware Update Runner
# examples/async/complex/class_approach/without_logic_loader/iot_firmware_update/iot_firmware_update_runner.py
# -----------------------------------------------------------------------------
"""
Runs the asynchronous IoT firmware update state machine:

  • CHECK_FOR_UPDATE → store_update_info
  • onDone cond → download_firmware_service → store_package_path
  • after 5s → log_applying_update → update_current_version
  • onError → set_error
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter, MachineLogic

# Ensure project root on path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from iot_firmware_update_logic import FirmwareUpdaterLogic

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the IoT Firmware Update simulation."""
    print("\n--- ⚡ Async IoT Firmware Update Simulation ---")
    config_path = "iot_firmware_update.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = FirmwareUpdaterLogic()
    machine_logic = MachineLogic(
        actions={
            "store_update_info": logic.store_update_info,
            "store_package_path": logic.store_package_path,
            "log_applying_update": logic.log_applying_update,
            "update_current_version": logic.update_current_version,
            "set_error": logic.set_error,
        },
        guards={"is_update_available": logic.is_update_available},
        services={
            "check_for_update_service": logic.check_for_update_service,
            "download_firmware_service": logic.download_firmware_service,
        },
    )

    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    logger.info(
        f"Device on version {interpreter.context.get('current_version')}."
    )
    await interpreter.send("CHECK_FOR_UPDATE")
    await asyncio.sleep(10)  # allow full update cycle
    logger.info(f"Final state: {interpreter.current_state_ids}")
    logger.info(f"Final context: {interpreter.context}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
