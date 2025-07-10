# -------------------------------------------------------------------------------
# 📞 API Fetcher Logic
# examples/async/intermediate/class_approach/with_logic_loader/api_fetcher/api_fetcher_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for the async API Fetcher demonstration.

Includes actions to store request data, handle success/error, and a service
to simulate fetching user data from an external API.
"""

import asyncio
import logging
from typing import Any, Dict

from src.xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class ApiFetcherLogic:
    """Encapsulates actions and service for API data fetching."""

    def set_user_id_to_fetch(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔖 Store the user ID from the FETCH event into context.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The triggering Event carrying `payload['id']`.
            action_def: Metadata about this action.
        """
        user_id = event.payload.get("id")
        context["user_id_to_fetch"] = user_id
        logger.info(f"📋 Setting user ID to fetch: {user_id}")

    def set_user_data(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """✅ Store fetched user data and clear request ID.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The DoneEvent carrying `data` from the service.
            action_def: Metadata about this action.
        """
        context["user_data"] = event.data
        context["user_id_to_fetch"] = None
        name = event.data.get("name")
        logger.info(f"✅ Success! Data received for user: {name}")

    def set_error_message(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """❌ Record error message and clear request ID.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The DoneEvent carrying error `data`.
            action_def: Metadata about this action.
        """
        error = str(event.data)
        context["error_message"] = error
        context["user_id_to_fetch"] = None
        logger.error(f"❌ Failure! Error: {error}")

    async def fetch_user_from_api(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """📞 Async service to fetch user data based on context.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The triggering Event.

        Returns:
            A dict containing the user’s `id` and `name`.

        Raises:
            ConnectionError: If the user ID is not found.
        """
        user_id = context.get("user_id_to_fetch")
        logger.info(
            f"📞 Invoking service: Calling API for user_id '{user_id}'..."
        )
        await asyncio.sleep(1.5)
        if user_id == "user123":
            return {"id": "user123", "name": "Alice"}
        raise ConnectionError(f"User with id '{user_id}' not found (404).")
