# examples/async/super_complex/class_approach/with_logic_loader/smart_home/smart_home_logic.py
import asyncio
import json
import logging
import os
from typing import Dict, Any

from src.xstate_statemachine import (
    Interpreter,
    Event,
    ActionDefinition,
    create_machine,
    MachineLogic,
)
from src.xstate_statemachine.models import MachineNode


class SmartHomeLogic:
    """Class-based logic for the Smart Home Automation System."""

    def __init__(self):
        # Load the actor's machine definition once to be used by the service method
        with open("light_bulb_actor.json", "r") as f:
            self.light_bulb_config = json.load(f)

        # Define the logic for the actor machine
        self.light_bulb_actions = {
            "set_color": self.light_bulb_set_color_action
        }
        self.light_bulb_logic = MachineLogic(actions=self.light_bulb_actions)

    # --- Main Machine Actions & Guards ---
    def set_target_temp(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["target_temp"] = e.payload.get("temp")
        logging.info(f"🌡️  Climate target set to {ctx['target_temp']}°F.")

    def set_climate_error(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        logging.error(f"🔥 Climate control error: {ctx['error']}")

    def log_arming_delay(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info(
            "🛡️  Security system arming... You have 3 seconds to exit."
        )

    async def trigger_alarm(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.error("🚨🚨🚨 ALARM TRIGGERED! Motion detected! 🚨🚨🚨")
        for actor_id, actor in i._actors.items():
            if "light" in actor_id:
                await actor.send("SET_COLOR", color="red")

    def is_code_correct(self, ctx: Dict, e: Event) -> bool:
        is_correct = e.payload.get("code") == ctx["security_code"]
        if is_correct:
            logging.info("✅ Correct security code entered. System disarmed.")
        else:
            logging.warning("❌ Incorrect security code.")
        return is_correct

    def spawn_light_bulb(
        self, i: Interpreter, ctx: Dict, e: Event, ad: ActionDefinition
    ):
        pass

    # --- Services ---
    async def adjust_temperature_service(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        target = ctx["target_temp"]
        current = ctx["temperature"]
        logging.info(
            f"  -> 🌡️  Invoking service: Adjusting temperature from {current}°F to {target}°F..."
        )

        while ctx["temperature"] != target:
            await asyncio.sleep(1.0)
            if ctx["temperature"] < target:
                ctx["temperature"] += 1
            else:
                ctx["temperature"] -= 1
            logging.info(
                f"  ...current temperature is now {ctx['temperature']}°F"
            )

        logging.info("  -> 🌡️  Target temperature reached.")
        return {"final_temp": ctx["temperature"]}

    def light_bulb(self, i: Interpreter, ctx: Dict, e: Event) -> "MachineNode":
        """This service is discovered by LogicLoader. It returns a fully configured
        MachineNode instance for the interpreter to spawn as an actor."""
        return create_machine(
            self.light_bulb_config, logic=self.light_bulb_logic
        )

    # --- Light Bulb Actor Logic ---
    def light_bulb_set_color_action(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["color"] = e.payload.get("color")
        logging.info(f"💡 Light '{i.id}' changed color to {ctx['color']}.")
