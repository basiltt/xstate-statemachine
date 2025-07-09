# examples/async/complex/class_approach/without_logic_loader/iot_firmware_update_runner.py
# -----------------------------------------------------------------------------
# ⚡ Complex Example: IoT Firmware Update (Class-Based / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - A sequential, multi-stage async process with multiple `invoke` calls.
#   - `cond` (guard) to conditionally proceed with the update.
#   - `after` to simulate a timed internal process (applying the update).
#   - Explicit Logic Binding of all methods from a class instance.
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
from iot_firmware_update_logic import FirmwareUpdaterLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- ⚡ Async IoT Firmware Update Simulation (Class / Explicit Logic) ---"
    )

    with open("iot_firmware_update.json", "r") as f:
        config = json.load(f)

    logic_provider = FirmwareUpdaterLogic()

    # Manually create the MachineLogic object
    machine_logic = MachineLogic(
        actions={
            "store_update_info": logic_provider.store_update_info,
            "store_package_path": logic_provider.store_package_path,
            "log_applying_update": logic_provider.log_applying_update,
            "update_current_version": logic_provider.update_current_version,
            "set_error": logic_provider.set_error,
        },
        guards={
            "is_update_available": logic_provider.is_update_available,
        },
        services={
            "check_for_update_service": logic_provider.check_for_update_service,
            "download_firmware_service": logic_provider.download_firmware_service,
        },
    )

    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    # --- Simulation ---
    logging.info(
        f"Device started with firmware version {interpreter.context['current_version']}."
    )
    await interpreter.send("CHECK_FOR_UPDATE")

    # Wait long enough for all stages to potentially complete
    # Check (1.5s) + Download (2.5s) + Apply (5s) = 9s + buffer
    await asyncio.sleep(10)

    logging.info("\n--- Update Process Summary ---")
    logging.info(f"Final state: {interpreter.current_state_ids}")
    logging.info(f"Final context: {interpreter.context}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
