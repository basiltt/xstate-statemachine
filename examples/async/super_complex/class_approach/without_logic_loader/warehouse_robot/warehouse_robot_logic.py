# examples/async/super_complex/class_approach/without_logic_loader/warehouse_robot/warehouse_robot_logic.py
import asyncio
import json
import logging
import os
import random
from typing import Dict, Any

from src.xstate_statemachine import (
    Interpreter,
    Event,
    ActionDefinition,
    create_machine,
    MachineLogic,
)
from src.xstate_statemachine.models import MachineNode


class WarehouseRobotLogic:
    """Class-based logic for the Warehouse Robot and its Pathfinder actor."""

    def __init__(self):
        with open("pathfinder_actor.json", "r") as f:
            self.pathfinder_config = json.load(f)
        self.pathfinder_logic = MachineLogic(
            actions={
                "send_path_to_parent": self.pathfinder_send_path,
                "send_failure_to_parent": self.pathfinder_send_failure,
                "send_timeout_failure_to_parent": self.pathfinder_send_timeout_failure,
            },
            services={
                "calculate_path_service": self.pathfinder_calculate_path
            },
        )

    # --- Main Robot Actions ---
    def assign_order(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["order_items"] = e.payload.get("items", [])
        logging.info(f"🤖 New order assigned with items: {ctx['order_items']}")
        ctx["target_location"] = ctx["order_items"][0]["location"]

    def store_path(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["path"] = e.payload.get("path")
        logging.info(f"🗺️  Path received: {' -> '.join(ctx['path'])}")

    def store_picked_item(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        item = e.data.get("item_picked")
        ctx["picked_items"].append(item)
        logging.info(
            f"✅ Item '{item}' picked. Total picked: {len(ctx['picked_items'])}/{len(ctx['order_items'])}"
        )

        if len(ctx["picked_items"]) == len(ctx["order_items"]):
            logging.info("🎉 All items picked!")
            asyncio.create_task(
                i.send({"type": "FINISH_MANIPULATION"})
            )  # A non-existent event to stop this region, effectively. A better model would have a transition. Forcing final state.
            i._active_state_nodes = {
                s
                for s in i._active_state_nodes
                if not s.id.startswith(f"{i.id}.fulfilling.manipulation")
            }
            i._active_state_nodes.add(
                i.machine.get_state_by_id(
                    f"{i.id}.fulfilling.manipulation.all_items_picked"
                )
            )

        else:
            ctx["target_location"] = ctx["order_items"][
                len(ctx["picked_items"])
            ]["location"]
            asyncio.create_task(i.send("NEXT_ITEM"))

    def set_movement_error(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        logging.error(f"MOVEMENT ERROR: {ctx['error']}")
        asyncio.create_task(i.send("FATAL_ERROR"))

    def set_manipulation_error(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        logging.error(f"MANIPULATION ERROR: {ctx['error']}")
        asyncio.create_task(i.send("FATAL_ERROR"))

    # --- Main Robot Services ---
    def pathfinder_actor(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> "MachineNode":
        return create_machine(
            self.pathfinder_config, logic=self.pathfinder_logic
        )

    async def follow_path_service(self, i: Interpreter, ctx: Dict, e: Event):
        logging.info(
            f"  -> 🏃 Invoking service: Following path to {ctx['path'][-1]}..."
        )
        for step in ctx["path"]:
            await asyncio.sleep(0.5)
            ctx["current_location"] = step
            logging.info(f"     ...moved to {step}")
        logging.info(f"  -> ✅ Arrived at {ctx['current_location']}")
        await i.send("ARRIVED")

    async def pick_item_service(self, i: Interpreter, ctx: Dict, e: Event):
        item_to_pick = ctx["order_items"][len(ctx["picked_items"])]
        logging.info(
            f"  -> 🦾 Invoking service: Picking item '{item_to_pick['name']}'..."
        )
        await asyncio.sleep(1.5)
        if random.random() < 0.1:
            raise RuntimeError(
                f"Arm failed to grip item '{item_to_pick['name']}'."
            )
        return {"item_picked": item_to_pick["name"]}

    async def return_to_base_service(
        self, i: Interpreter, ctx: Dict, e: Event
    ):
        logging.info("🤖 Returning to charging base...")
        await asyncio.sleep(2)

    # --- Pathfinder Actor Logic ---
    async def pathfinder_send_path(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        path = e.data.get("path")
        await i.parent.send(
            {"type": "PATH_CALCULATED", "payload": {"path": path}}
        )

    async def pathfinder_send_failure(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        await i.parent.send(
            {"type": "PATH_FAILED", "payload": {"error": str(e.data)}}
        )

    async def pathfinder_send_timeout_failure(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        await i.parent.send(
            {
                "type": "PATH_FAILED",
                "payload": {"error": "Pathfinder timed out"},
            }
        )

    async def pathfinder_calculate_path(
        self, i: Interpreter, ctx: Dict, e: Event
    ):
        start = i.parent.context["current_location"]
        end = i.parent.context["target_location"]
        logging.info(
            f"      -> 🤖 Pathfinder Actor: Calculating path from {start} to {end}..."
        )
        await asyncio.sleep(2)
        # Simulate a simple path
        path = [
            start,
            f"R{random.randint(1, 5)}",
            f"C{random.randint(1, 5)}",
            end,
        ]
        return {"path": path}
