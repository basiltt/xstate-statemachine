# -------------------------------------------------------------------------------
# 🚦 Traffic Light Logic
# examples/async/basic/functional_approach/with_logic_loader/traffic_light/traffic_light_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for asynchronous traffic light simulation.
"""

import asyncio
import logging
from typing import Any, Dict

from xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


async def log_light_change(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,
) -> None:
    """💡 Log and simulate physical light change based on 'color' param."""
    color = action_def.params.get("color", "UNKNOWN")
    logger.info(f"💡 Changing light to {color}...")
    await asyncio.sleep(0.1)
    emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(color, "⚫")
    logger.info(f"{emoji} Light is now {color}")


def is_safe_to_change(
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
) -> bool:
    """🛣️ Guard: Always allow light change (stub for real sensor logic)."""
    logger.info("🚦 Checking safety for pedestrian crossing: OK")
    return True
