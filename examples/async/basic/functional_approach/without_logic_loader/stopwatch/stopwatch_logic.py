# examples/async/basic/functional_approach/without_logic_loader/stopwatch/stopwatch_logic.py
import asyncio
import logging
from typing import Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


async def log_status(
    i: Interpreter, ctx: Dict, e: Event, ad: ActionDefinition
):
    status = ad.params.get("status", "Unknown")
    logging.info("(Action: Updating UI display...)")
    await asyncio.sleep(0.1)
    logging.info(f"⏱️  Stopwatch is now: {status}")


def record_lap(i: Interpreter, ctx: Dict, e: Event, ad: ActionDefinition):
    # In a real app, this would get the current time and store it.
    logging.info("🏁 Lap time recorded!")


async def reset_timer(
    i: Interpreter, ctx: Dict, e: Event, ad: ActionDefinition
):
    logging.info("  (Action: Resetting hardware timer...)")
    await asyncio.sleep(0.2)
    ctx["elapsed_time"] = 0
    logging.info("🔄 Timer reset to 0.")
