# examples/async/easy/functional_approach/with_logic_loader/task_status/task_status_logic.py
import asyncio
import logging
from typing import Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


async def set_task_id(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    logging.info("  (Action: Registering task with queue...)")
    await asyncio.sleep(0.7)  # Simulate latency
    ctx["current_task_id"] = e.payload.get("id")
    logging.info(f"⚙️ Task started. ID: {ctx['current_task_id']}")


async def clear_task_id(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    logging.info(
        f"  (Action: Updating task '{ctx['current_task_id']}' as complete...)"
    )
    await asyncio.sleep(0.3)  # Simulate latency
    logging.info(f"✅ Task finished. ID: {ctx['current_task_id']}")
    ctx["current_task_id"] = None
