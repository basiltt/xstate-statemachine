# -----------------------------------------------------------------------------
# 📂 File Uploader Logic
# examples/sync/complex/class_approach/with_logic_loader/file_uploader/file_uploader_logic.py
# -----------------------------------------------------------------------------
"""
Encapsulates all synchronous logic for the File Uploader state machine:
  • Actions to select, clear, and log state.
  • Guard to ensure a file is selected before upload.
  • Services to upload and process files synchronously.
"""

import logging
import time
from typing import Any, Dict

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class FileUploaderLogic:
    """Implements actions, guards, and services for file uploading."""

    def set_selected_file(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📄 Select a file and reset any previous error.

        Args:
            interpreter: The SyncInterpreter instance.
            context: Mutable machine context.
            event: Event carrying 'file' in payload.
            action_def: Metadata for this action.
        """
        context["selectedFile"] = event.payload.get("file")
        context["error"] = None
        logger.info(f"📄 File selected: {context['selectedFile']}")

    def clear_context(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔄 Clear all context to prepare for a new upload."""
        context["selectedFile"] = None
        context["uploadResult"] = None
        context["error"] = None
        logger.info("🔄 Context cleared for new upload.")

    def set_upload_result(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """✅ Store upload result returned by the service.

        Args:
            interpreter: The SyncInterpreter instance.
            context: Mutable machine context.
            event: DoneEvent carrying 'data' from upload service.
            action_def: Metadata for this action.
        """
        context["uploadResult"] = event.data
        logger.info(f"✅ Upload successful. Result: {event.data}")

    def set_error(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """❌ Record error message from service failure.

        Args:
            interpreter: The SyncInterpreter instance.
            context: Mutable machine context.
            event: DoneEvent carrying error in 'data'.
            action_def: Metadata for this action.
        """
        context["error"] = str(event.data)
        logger.error(f"❌ Operation failed: {context['error']}")

    def log_complete(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🎉 Log that both upload and processing have completed."""
        logger.info("🎉 File upload and processing complete!")

    def is_file_selected(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """🛡️ Guard: Ensure a file is selected before invoking services.

        Args:
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            True if a file is selected; False otherwise.
        """
        selected = context.get("selectedFile") is not None
        if not selected:
            logger.warning("🛡️ Guard failed: No file selected. Action blocked.")
        return selected

    def upload_file_sync(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """📤 Service: Simulate blocking file upload.

        Args:
            interpreter: The SyncInterpreter instance.
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            A dict with upload status and file size.

        Raises:
            ConnectionError: On simulated network failure.
        """
        file_name = context.get("selectedFile")
        logger.info(f"📤 Uploading '{file_name}'...")
        time.sleep(1)
        if "fail" in file_name:
            raise ConnectionError("Network connection lost during upload")
        return {"status": "uploaded", "size": 1024}

    def process_file_sync(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
    ) -> Dict[str, Any]:
        """⚙️ Service: Simulate blocking server-side file processing.

        Args:
            interpreter: The SyncInterpreter instance.
            context: Mutable machine context.
            event: The triggering Event.

        Returns:
            A dict with processing status.

        Raises:
            ValueError: On simulated invalid file format.
        """
        file_name = context.get("selectedFile")
        logger.info(f"⚙️ Processing '{file_name}' on the server...")
        time.sleep(1)
        if "invalid" in file_name:
            raise ValueError("Invalid file format")
        return {"status": "processed"}
