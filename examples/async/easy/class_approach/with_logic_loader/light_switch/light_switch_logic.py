# examples/async/easy/class_approach/with_logic_loader/light_switch/light_switch_logic.py
import logging
from typing import Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class LightSwitchLogic:
    """Class-based logic for a simple light switch."""

    def increment_flips(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["flips"] += 1
        logging.info(f"💡 Switch flipped. Total flips: {ctx['flips']}.")
