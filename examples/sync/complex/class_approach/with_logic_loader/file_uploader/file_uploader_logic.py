# examples/sync/complex/class_approach/with_logic_loader/file_uploader/file_uploader_logic.py

import logging
import time
from typing import Dict, Any

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition


class FileUploaderLogic:
    """Encapsulates all logic for the File Uploader state machine."""

    # --- Actions ---
    def set_selected_file(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["selectedFile"] = e.payload.get("file")
        ctx["error"] = None
        logging.info(f"📄 File selected: {ctx['selectedFile']}")

    def set_upload_result(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["uploadResult"] = e.data
        logging.info(f"✅ Upload successful. Result: {e.data}")

    def set_error(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["error"] = str(e.data)
        logging.error(f"❌ Operation failed: {ctx['error']}")

    def clear_context(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        ctx["selectedFile"] = None
        ctx["uploadResult"] = None
        ctx["error"] = None
        logging.info("🔄 Context cleared for new upload.")

    def log_complete(
        self, i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
    ):
        logging.info("🎉 File upload and processing complete!")

    # --- Guards ---
    def is_file_selected(self, ctx: Dict, e: Event) -> bool:
        selected = ctx.get("selectedFile") is not None
        if not selected:
            logging.warning("Guard: No file selected. Action blocked.")
        return selected

    # --- Services ---
    def upload_file_sync(
        self, i: SyncInterpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        file_name = ctx.get("selectedFile")
        logging.info(f"📤 Uploading '{file_name}'...")
        time.sleep(1)  # Simulate blocking upload
        if "fail" in file_name:
            raise ConnectionError("Network connection lost during upload")
        return {"status": "uploaded", "size": 1024}

    def process_file_sync(
        self, i: SyncInterpreter, ctx: Dict, e: Event
    ) -> Dict[str, Any]:
        file_name = ctx.get("selectedFile")
        logging.info(f"⚙️  Processing '{file_name}' on the server...")
        time.sleep(1)  # Simulate blocking processing
        if "invalid" in file_name:
            raise ValueError("Invalid file format")
        return {"status": "processed"}
