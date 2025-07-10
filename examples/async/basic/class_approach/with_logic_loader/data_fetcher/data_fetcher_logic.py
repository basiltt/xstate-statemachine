# -------------------------------------------------------------------------------
# 📡 Data Fetcher Logic
# examples/async/basic/class_approach/with_logic_loader/data_fetcher/data_fetcher_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for async data fetching with retry support.
"""

import asyncio
import logging
import random
from typing import Any, Dict

from src.xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class DataFetcherLogic:
    """Implements data fetch action, retry wait logging, and retry guard."""

    MAX_RETRIES: int = 2

    async def fetch_data_action(  # noqa
        self,
        interpreter: Interpreter,
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🐡 Attempt to fetch data, retrying up to MAX_RETRIES on failure.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable machine context dict.
            event: The triggering Event.
            action_def: Metadata for this action.
        """
        attempt = context.get("retries", 0) + 1
        logger.info(f"📡 Fetch attempt #{attempt}...")
        await asyncio.sleep(0.5)
        if random.random() > 0.4:
            context["data"] = {"id": 123, "content": "Hello, world!"}
            logger.info("✅ Data fetched successfully!")
            await interpreter.send("FETCH_SUCCESS")
        else:
            context["retries"] = attempt
            logger.warning("❌ Fetch failed, will retry.")
            await interpreter.send("FETCH_FAILURE")

    def log_wait(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⏳ Log waiting message before next retry."""
        logger.info("⏳ Waiting 1 second before retrying...")

    def has_retries_left(
        self,
        context: Dict[str, Any],
        event: Event,
    ) -> bool:
        """✔️ Guard: Allow retry if retries < MAX_RETRIES.

        Args:
            context: Mutable machine context dict.
            event: The triggering Event.

        Returns:
            True if retries remain; False otherwise.
        """
        remaining = context.get("retries", 0) < self.MAX_RETRIES
        if not remaining:
            logger.error("🚫 No retries left. Transitioning to failure.")
        return remaining
