# examples/async/basic/class_approach/with_logic_loader/data_fetcher/data_fetcher_logic.py
import asyncio
import logging
import random
from typing import Dict

from xstate_statemachine import ActionDefinition, Interpreter, Event


class DataFetcherLogic:
    """Class-based logic for a data fetcher with retries."""

    MAX_RETRIES = 2

    async def fetch_data_action(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info(
            f"📡 Attempting to fetch data (Attempt #{ctx['retries'] + 1})..."
        )
        await asyncio.sleep(0.5)

        # Simulate a failing API call
        if random.random() > 0.4:
            logging.info("✅ Data fetched successfully!")
            ctx["data"] = {"id": 123, "content": "Hello, world!"}
            await i.send("FETCH_SUCCESS")
        else:
            logging.warning("❌ Fetch failed.")
            ctx["retries"] += 1
            await i.send("FETCH_FAILURE")

    def log_wait(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("⏳ Waiting 1 second before retrying...")

    def has_retries_left(self, ctx: Dict, e: Event) -> bool:
        has_retries = ctx["retries"] < self.MAX_RETRIES
        if not has_retries:
            logging.error("🚫 No retries left. Moving to final failed state.")
        return has_retries
