# examples/async/intermediate/class_approach/with_logic_loader/api_fetcher/api_fetcher_logic.py
import asyncio
import logging
import random
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class ApiFetcherLogic:
    """Class-based logic for fetching data from a simulated API."""

    # --- Actions ---
    def set_user_id_to_fetch(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        # Action on the FETCH transition: save the ID to context
        ctx["user_id_to_fetch"] = e.payload.get("id")
        logging.info(f"📋 Setting user ID to fetch: {ctx['user_id_to_fetch']}")

    def set_user_data(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["user_data"] = e.data
        ctx["user_id_to_fetch"] = None  # Clean up
        logging.info(
            f"✅ Success! Data received for user: {e.data.get('name')}"
        )

    def set_error_message(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error_message"] = str(e.data)
        ctx["user_id_to_fetch"] = None  # Clean up
        logging.error(f"❌ Failure! Error: {ctx['error_message']}")

    # --- Services ---
    async def fetch_user_from_api(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        # Service now reads the ID from the machine's context
        user_id = ctx.get("user_id_to_fetch")
        logging.info(
            f"📞 Invoking service: Calling API for user_id '{user_id}' from context..."
        )
        await asyncio.sleep(1.5)  # Simulate network latency

        if user_id == "user123":
            return {"id": "user123", "name": "Alice"}
        else:
            raise ConnectionError(f"User with id '{user_id}' not found (404).")
