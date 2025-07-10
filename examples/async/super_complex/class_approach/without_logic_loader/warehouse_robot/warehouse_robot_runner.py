# -------------------------------------------------------------------------------
# 🤖 Warehouse Robot Runner
# examples/async/super_complex/class_approach/without_logic_loader/warehouse_robot/warehouse_robot_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the Warehouse Robot simulation.

Illustrates:
  • Actor spawning for pathfinding subtasks.
  • Parallel regions and service invocations.
  • Explicit MachineLogic binding for a complex class.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from warehouse_robot_logic import WarehouseRobotLogic  # noqa: E402

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the Warehouse Robot simulation."""
    logger.info(
        "\n--- 🤖 Warehouse Robot Simulation (Class / Explicit Logic) ---"
    )

    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "warehouse_robot.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic_provider = WarehouseRobotLogic()
    machine_logic = MachineLogic(
        actions={
            "assign_order": logic_provider.assign_order,
            "store_path": logic_provider.store_path,
            "store_picked_item": logic_provider.store_picked_item,
            "set_movement_error": logic_provider.set_movement_error,
            "set_manipulation_error": logic_provider.set_manipulation_error,
        },
        services={
            "pathfinder_actor": logic_provider.pathfinder_actor,
            "follow_path_service": logic_provider.follow_path_service,
            "pick_item_service": logic_provider.pick_item_service,
            "return_to_base_service": logic_provider.return_to_base_service,
        },
    )
    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    await interpreter.send(
        "ASSIGN_ORDER",
        items=[
            {"name": "Power Drill", "location": "C7"},
            {"name": "Wrench Set", "location": "B3"},
        ],
    )
    await asyncio.sleep(13.0)

    logger.info(f"Final state: {interpreter.current_state_ids}")
    logger.info(f"Final context: {interpreter.context}")

    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
