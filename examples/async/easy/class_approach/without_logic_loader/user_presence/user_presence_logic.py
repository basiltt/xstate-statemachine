# examples/async/easy/class_approach/without_logic_loader/user_presence/user_presence_logic.py
import asyncio
import logging
import time
from typing import Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class UserPresenceLogic:
    """Class-based logic for the user presence tracker with async actions."""

    async def update_last_seen(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("  (Action: Simulating network call to update status...)")
        await asyncio.sleep(0.5)  # Simulate I/O delay

        ctx["last_seen"] = time.time()
        if e.type == "CONNECT":
            ctx["user_id"] = e.payload.get("user_id")
            logging.info(f"🟢 User '{ctx['user_id']}' is now online.")
        else:
            logging.info(f"🔴 User '{ctx['user_id']}' went offline.")
