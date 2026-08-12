# -------------------------------------------------------------------------------
# 📁 File Processor Logic
# examples/async/intermediate/class_approach/without_logic_loader/file_processor/file_processor_logic.py
# -------------------------------------------------------------------------------
"""
Class-based logic for the async File Processor demonstration.

Includes actions to record upload info, handle success/failure, and a service
to simulate file processing based on type.
"""

import asyncio
import logging
from typing import Any, Dict

from xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class FileProcessorLogic:
    """Encapsulates actions and service for file processing."""

    def set_file_info(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📤 Store file metadata into context on UPLOAD event.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The triggering Event carrying `payload['name']` & `['type']`.
            action_def: Metadata about this action.
        """
        context["file_name"] = event.payload.get("name")
        context["file_type"] = event.payload.get("type")
        logger.info(
            f"📤 File '{context['file_name']}' uploaded. Beginning processing."
        )

    def log_success(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🎉 Log processing result on success.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The DoneEvent carrying `data`.
            action_def: Metadata about this action.
        """
        context["processed_data"] = event.data
        logger.info(f"🎉 File processing successful! Result: {event.data}")

    def log_failure(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔥 Log error on service failure.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The DoneEvent carrying error `data`.
            action_def: Metadata about this action.
        """
        logger.error(f"🔥 File processing failed: {event.data}")

    async def process_file(  # noqa
        self,
        interpreter: Interpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """⚙️ Async service to process a file based on its type.

        Args:
            interpreter: The state machine interpreter.
            context: Mutable context dictionary.
            event: The triggering Event.

        Returns:
            A dict with processing results (`dimensions` or `word_count`).

        Raises:
            ValueError: If the file type is unsupported.
        """
        file_type = context.get("file_type")
        logger.info(f"⚙️ Processing file of type '{file_type}'...")
        await asyncio.sleep(2.0)
        if file_type == "image":
            return {"dimensions": "1920x1080", "format": "jpeg"}
        if file_type == "text":
            return {"word_count": 250, "encoding": "utf-8"}
        raise ValueError(f"Unsupported file type: {file_type}")
