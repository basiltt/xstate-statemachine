# examples/async/basic/functional_approach/with_logic_loader/traffic_light/traffic_light_logic.py
import asyncio
import logging
from typing import Dict

from src.xstate_statemachine import Interpreter, ActionDefinition, Event


async def log_light_change(
    i: Interpreter, ctx: Dict, e: Event, ad: ActionDefinition
):
    color = ad.params.get("color", "UNKNOWN")
    logging.info("  (Action: Updating physical light display...)")
    await asyncio.sleep(0.1)

    emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(color, "⚫")
    logging.info(f"{emoji} Light is now {color}")


def is_safe_to_change(ctx: Dict, e: Event) -> bool:
    # In a real system, we might check sensor data. Here, it's always true.
    logging.info(
        "🚦 Guard: Checking if it's safe to change for pedestrian... (Yes)"
    )
    return True
