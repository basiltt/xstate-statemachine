# -------------------------------------------------------------------------------
# 🤖 Warehouse Robot Logic
# examples/async/super_complex/class_approach/without_logic_loader/warehouse_robot/warehouse_robot_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for Warehouse Robot and its Pathfinder actor.

Illustrates:
  • Parallel states and actor spawning.
  • Communication between parent machine and actor.
  • Async actions and services for movement and picking.
"""
import asyncio
import json
import logging
import random
from typing import Any, Dict

from src.xstate_statemachine import (
    Interpreter,
    Event,
    ActionDefinition,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class WarehouseRobotLogic:
    """Implements actions, guards, and services for the warehouse robot."""

    def __init__(self) -> None:
        """Load the pathfinder actor definition and logic once."""
        with open("pathfinder_actor.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        self.pathfinder_config: Dict[str, Any] = config
        self.pathfinder_logic: MachineLogic = MachineLogic(
            actions={
                "send_path_to_parent": self.pathfinder_send_path,
                "send_failure_to_parent": self.pathfinder_send_failure,
                "send_timeout_failure_to_parent": self.pathfinder_send_timeout_failure,
            },
            services={
                "calculate_path_service": self.pathfinder_calculate_path
            },
        )

    def assign_order(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📦 Assign a new order and record target location."""
        items = event.payload.get("items", [])
        context["order_items"] = items
        context["picked_items"] = []
        context["target_location"] = items[0]["location"] if items else None
        logger.info(f"🤖 Order assigned with items: {items}")

    def store_path(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🗺️ Store a calculated path in context."""
        path = event.data.get("path", [])
        context["path"] = path
        logger.info(f"🗺️ Path received: {' -> '.join(path)}")

    async def store_picked_item(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """✅ Record picked item and notify on completion or next."""
        item = event.data.get("item_picked")
        context["picked_items"].append(item)
        total = len(context["picked_items"])
        needed = len(context["order_items"])
        logger.info(f"✅ Picked '{item}'. {total}/{needed} done.")
        if total == needed:
            await interpreter.send("ALL_ITEMS_PICKED")
            await interpreter.send("ALL_ITEMS_LOCATED")
        else:
            context["target_location"] = context["order_items"][total][
                "location"
            ]
            await interpreter.send("NEXT_ITEM")

    def set_movement_error(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚠️ Handle movement errors by notifying parent."""
        error = event.payload.get("error", "Unknown movement error")
        context["error"] = error
        logger.error(f"⚠️ Movement error: {error}")
        asyncio.create_task(interpreter.send("FATAL_ERROR"))

    def set_manipulation_error(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⚠️ Handle manipulation errors by notifying parent."""
        error = str(event.data)
        context["error"] = error
        logger.error(f"⚠️ Manipulation error: {error}")
        asyncio.create_task(interpreter.send("FATAL_ERROR"))

    def pathfinder_actor(
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
    ) -> MachineNode:
        """🔧 Service to spawn a new pathfinder actor machine."""
        return create_machine(
            self.pathfinder_config, logic=self.pathfinder_logic
        )

    async def follow_path_service(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """🏃 Service that moves the robot along the stored path."""
        for step in context.get("path", []):
            await asyncio.sleep(0.5)
            context["current_location"] = step
            logger.info(f"🏃 Moved to {step}")
        await interpreter.send("ARRIVED")
        return {"arrived": True}

    async def pick_item_service(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """🦾 Service that picks the next item in the order."""
        index = len(context.get("picked_items", []))
        item = context["order_items"][index]
        await asyncio.sleep(1.5)
        if random.random() < 0.1:
            raise RuntimeError(f"Grip failed for '{item['name']}'")
        return {"item_picked": item["name"]}

    async def return_to_base_service(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
    ) -> None:
        """🔙 Service to return robot to its charging base."""
        logger.info("🔙 Returning to base...")
        await asyncio.sleep(2.0)

    async def pathfinder_send_path(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],  # noqa
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📤 Actor action: send a calculated path back to parent."""
        path = event.data.get("path", [])
        await interpreter.parent.send("PATH_CALCULATED", path=path)

    async def pathfinder_send_failure(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],  # noqa
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """❌ Actor action: notify parent of failure."""
        await interpreter.parent.send("PATH_FAILED", error=str(event.data))

    async def pathfinder_send_timeout_failure(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⌛ Actor action: notify parent of timeout failure."""
        await interpreter.parent.send(
            "PATH_FAILED", error="Pathfinder timed out"
        )

    async def pathfinder_calculate_path(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """🛣️ Service: calculate a random path between two points."""
        start = interpreter.parent.context.get("current_location")
        end = interpreter.parent.context.get("target_location")
        logger.info(f"🛣️ Calculating path from {start} to {end}...")
        await asyncio.sleep(2.0)
        path = [
            start,
            f"R{random.randint(1, 5)}",
            f"C{random.randint(1, 5)}",
            end,
        ]
        return {"path": path}
