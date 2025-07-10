# -------------------------------------------------------------------------------
# 💡 Light Switch Logic
# examples/async/easy/class_approach/with_logic_loader/light_switch/light_switch_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for the async light switch demonstration.

Encapsulates the action to flip a light switch and count flips.
"""

import logging
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class LightSwitchLogic:
    """Encapsulates actions for a light switch state machine."""

    def increment_flips(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """💡 Increment flip counter in context.

        Args:
            interpreter: The running state machine interpreter.
            context: Mutable context dictionary.
            event: The triggering Event.
            action_def: Metadata about this action.
        """
        context["flips"] = context.get("flips", 0) + 1
        logger.info(f"💡 Switch flipped. Total flips: {context['flips']}.")
