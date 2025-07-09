# examples/async/intermediate/class_approach/without_logic_loader/file_processor/file_processor_logic.py
import asyncio
import logging
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


class FileProcessorLogic:
    """Class-based logic for processing a file asynchronously."""

    # --- Actions ---
    def set_file_info(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["file_name"] = e.payload.get("name")
        ctx["file_type"] = e.payload.get("type")
        logging.info(
            f"📤 File '{ctx['file_name']}' uploaded. Beginning processing."
        )

    def log_success(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["processed_data"] = e.data
        logging.info(
            f"🎉 File processing successful! Result: {ctx['processed_data']}"
        )

    def log_failure(
        self, i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.error(f"🔥 File processing failed: {e.data}")

    # --- Services ---
    async def process_file(
        self, i: Interpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        file_type = ctx.get("file_type")
        logging.info(
            f"⚙️  Invoking service: Processing file of type '{file_type}'..."
        )
        await asyncio.sleep(2.0)

        if file_type == "image":
            return {"dimensions": "1920x1080", "format": "jpeg"}
        elif file_type == "text":
            return {"word_count": 250, "encoding": "utf-8"}
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
