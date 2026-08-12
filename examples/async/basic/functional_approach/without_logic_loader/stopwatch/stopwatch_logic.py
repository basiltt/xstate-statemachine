# -------------------------------------------------------------------------------
# ⏱️ Stopwatch Logic
# examples/async/basic/functional_approach/without_logic_loader/stopwatch/stopwatch_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for async stopwatch simulation.
"""

import asyncio
import logging
from typing import Any, Dict

from xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


async def log_status(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,
) -> None:
    """⏱️ Log current stopwatch status based on 'status' param."""
    status = action_def.params.get("status", "Unknown")
    logger.info(f"⏱️ Updating display to: {status}")
    await asyncio.sleep(0.1)


def record_lap(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🏁 Record a lap time (stub for real implementation)."""
    logger.info("🏁 Lap recorded!")


async def reset_timer(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔄 Reset the stopwatch timer in context."""
    logger.info("🔄 Resetting timer to zero...")
    await asyncio.sleep(0.2)
    context["elapsed_time"] = 0
    logger.info("✅ Timer reset complete.")
