# examples/async/super_complex/class_approach/without_logic_loader/warehouse_robot_runner.py
# -----------------------------------------------------------------------------
# 🤖 Super-Complex Example: Warehouse Robot (Class-Based / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Parallel states for concurrent robot actions (movement, manipulation).
#   - Spawning an actor (`pathfinder`) to handle a sub-task.
#   - Communication from actor back to parent machine.
#   - Multiple `invoke` calls for different async tasks.
#   - Explicit Logic Binding for a complex class with actor logic.
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
from warehouse_robot_logic import WarehouseRobotLogic

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- 🤖 Async Warehouse Robot Simulation (Class / Explicit Logic) ---"
    )

    with open("warehouse_robot.json", "r") as f:
        config = json.load(f)

    logic_provider = WarehouseRobotLogic()

    # Manually bind all actions, guards, and services
    machine_logic = MachineLogic(
        actions={
            "assign_order": logic_provider.assign_order,
            "store_path": logic_provider.store_path,
            "store_picked_item": logic_provider.store_picked_item,
            "set_movement_error": logic_provider.set_movement_error,
            "set_manipulation_error": logic_provider.set_manipulation_error,
        },
        services={
            # The key 'pathfinder_actor' must match the name in 'spawn_pathfinder_actor'
            "pathfinder_actor": logic_provider.pathfinder_actor,
            "follow_path_service": logic_provider.follow_path_service,
            "pick_item_service": logic_provider.pick_item_service,
            "return_to_base_service": logic_provider.return_to_base_service,
        },
    )

    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    # --- Simulation ---
    order = {
        "items": [
            {"name": "Power Drill", "location": "C7"},
            {"name": "Wrench Set", "location": "B3"},
        ]
    }

    await interpreter.send("ASSIGN_ORDER", **order)

    # Wait long enough for the entire fulfillment process
    await asyncio.sleep(13)

    logging.info("\n--- Fulfillment Summary ---")
    logging.info(f"Final state: {interpreter.current_state_ids}")
    # ✅ FIX: Print the context directly to avoid JSON serialization errors
    logging.info(f"Final context: {interpreter.context}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
