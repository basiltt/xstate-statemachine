# examples/sync/easy/functional_approach/with_logic_loader/light_switch/light_switch_logic.py

# -----------------------------------------------------------------------------
# 💡 Light Switch Logic (Functional)
# -----------------------------------------------------------------------------
# This module provides standalone functions for the light switch state machine.
# These functions are designed to be discovered automatically by the LogicLoader.
# -----------------------------------------------------------------------------
import logging
from typing import Dict, Any

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# --- Logger ---
logger = logging.getLogger(__name__)


# --- Actions ---


def set_brightness_to_default(
    i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
) -> None:
    """Action to set the brightness to 100 when the light is turned on."""
    ctx["brightness"] = 100
    logger.info(f"💡 Light turned ON. Brightness set to {ctx['brightness']}%.")


def set_brightness_to_zero(
    i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
) -> None:
    """Action to set the brightness to 0 when the light is turned off."""
    ctx["brightness"] = 0
    logger.info(
        f"🌑 Light turned OFF. Brightness set to {ctx['brightness']}%."
    )
