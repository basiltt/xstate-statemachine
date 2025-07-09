# examples/async/basic/class_approach/without_logic_loader/session_timeout/session_timeout_logic.py
import asyncio
import logging
from typing import Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class SessionTimeoutLogic:
    """Class-based logic for a user session with a timeout."""

    async def set_user(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("  (Action: Storing user session...)")
        await asyncio.sleep(0.2)
        ctx["user"] = e.payload.get("user")

    def log_login(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info(
            f"👤 User '{ctx['user']}' logged in. Session will time out in 3 seconds."
        )

    def log_timeout(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.warning(
            f"⌛ Session for '{ctx['user']}' timed out due to inactivity."
        )
