# -------------------------------------------------------------------------------
# 🏡 Smart Home Logic
# examples/async/super_complex/class_approach/with_logic_loader/smart_home/smart_home_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for the Smart Home Automation System.

Illustrates:
  • Top-level parallel states (lighting, climate, security).
  • Actor model: spawning light bulb actors.
  • Inter-actor communication (security triggering lights).
  • Invocation of services and timed transitions.
"""

import asyncio
import json
import logging
from typing import Any, Dict, TYPE_CHECKING

from src.xstate_statemachine import (
    Interpreter,
    Event,
    ActionDefinition,
    create_machine,
    MachineLogic,
)
from src.xstate_statemachine.models import MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class SmartHomeLogic:
    """Implements actions, guards, and services for the Smart Home system."""

    def __init__(self) -> None:
        """Loads the light bulb actor machine definition for spawning."""
        with open("light_bulb_actor.json", "r", encoding="utf-8") as f:
            self.light_bulb_config: Dict[str, Any] = json.load(f)

        self.light_bulb_logic: MachineLogic = MachineLogic(
            actions={"set_color": self.light_bulb_set_color_action}
        )

    def set_target_temp(  # noqa:
        self,
        interpreter: Interpreter,  # noqa:
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa:
    ) -> None:
        """🌡️ Set the desired climate temperature in context.

        Args:
            interpreter: The active state machine interpreter.
            context: Mutable machine context.
            event: Event carrying payload {'temp': int}.
            action_def: Metadata for this action.
        """
        context["target_temp"] = event.payload.get("temp")
        logger.info(f"🌡️ Climate target set to {context['target_temp']}°F.")

    def set_climate_error(  # noqa:
        self,
        interpreter: Interpreter,  # noqa:
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa:
    ) -> None:
        """🔥 Record climate service error in context.

        Args:
            interpreter: The active state machine interpreter.
            context: Mutable machine context.
            event: DoneEvent with 'data' error information.
            action_def: Metadata for this action.
        """
        context["error"] = str(event.data)
        logger.error(f"🔥 Climate control error: {context['error']}")

    def log_arming_delay(  # noqa:
        self,
        interpreter: Interpreter,  # noqa:
        context: Dict[str, Any],  # noqa:
        event: Event,  # noqa:
        action_def: ActionDefinition,  # noqa:
    ) -> None:
        """🛡️ Log delay before a security system arming."""
        logger.info("🛡️ Security system arming... You have 3 seconds to exit.")

    async def trigger_alarm(  # noqa:
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],  # noqa:
        event: Event,  # noqa:
        action_def: ActionDefinition,  # noqa:
    ) -> None:
        """🚨 Trigger alarm and notify all light actors to flash red.

        Args:
            interpreter: The active state machine interpreter.
            context: Mutable machine context.
            event: Triggering Event for motion detection.
            action_def: Metadata for this action.
        """
        logger.error("🚨🚨🚨 ALARM TRIGGERED! Motion detected! 🚨🚨🚨")
        for actor_id, actor in interpreter._actors.items():  # noqa
            if "light" in actor_id:
                await actor.send("SET_COLOR", color="red")

    def is_code_correct(  # noqa:
        self,
        context: Dict[str, Any],
        event: Event,
    ) -> bool:
        """✔️ Guard: validate disarm code against security_code in context.

        Args:
            context: Mutable machine context.
            event: Event carrying payload {'code': str}.

        Returns:
            True if codes match; False otherwise.
        """
        entered = event.payload.get("code")
        expected = context.get("security_code")
        valid = entered == expected
        if valid:
            logger.info("✅ Correct security code entered. System disarmed.")
        else:
            logger.warning("❌ Incorrect security code.")
        return valid

    def spawn_light_bulb(
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,
    ) -> None:
        """🚦 Placeholder spawn action; actual actor service is 'light_bulb'."""
        pass  # the interpreter’s spawn logic will invoke self.light_bulb()

    async def adjust_temperature_service(  # noqa:
        self,
        interpreter: Interpreter,  # noqa:
        context: Dict[str, Any],
        event: Event,  # noqa:
    ) -> Dict[str, Any]:
        """🔧 Service to adjust home temperature over time.

        Args:
            interpreter: The active state machine interpreter.
            context: Mutable machine context.
            event: Triggering Event for SET_TEMP.

        Returns:
            Mapping {'final_temp': int} when target is reached.
        """
        target = context["target_temp"]
        logger.info(
            f"-> 🌡️ Adjusting from {context['temperature']}°F to {target}°F..."
        )
        while context["temperature"] != target:
            await asyncio.sleep(1.0)
            context["temperature"] += (
                1 if context["temperature"] < target else -1
            )
            logger.info(
                f"...current temperature is {context['temperature']}°F"
            )
        logger.info("-> 🌡️ Target temperature reached.")
        return {"final_temp": context["temperature"]}

    def light_bulb(
        self,
        interpreter: Interpreter,  # noqa:
        context: Dict[str, Any],  # noqa:
        event: Event,  # noqa:
    ) -> MachineNode:
        """💡 Service returning the actor machine for a new light bulb."""
        return create_machine(
            self.light_bulb_config, logic=self.light_bulb_logic
        )

    def light_bulb_set_color_action(  # noqa:
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa:
    ) -> None:
        """💡 Action to set a light bulb actor's color in its context.

        Args:
            interpreter: The actor's interpreter instance.
            context: Mutable actor context.
            event: Event carrying payload {'color': str}.
            action_def: Metadata for this action.
        """
        context["color"] = event.payload.get("color")
        logger.info(
            f"💡 Light '{interpreter.id}' changed color to {context['color']}."
        )
