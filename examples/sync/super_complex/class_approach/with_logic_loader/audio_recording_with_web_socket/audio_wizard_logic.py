# examples/sync/super_complex/class_approach/with_logic_loader/audio_wizard_logic.py
# -------------------------------------------------------------------------------
# 🎙️ Audio Wizard Logic
# -------------------------------------------------------------------------------
"""
Class-based logic for the “Audio recording with websocket” state machine,
with snake_case action and guard names to match the JSON contract.
"""

import logging
from typing import Any, Dict

from src.xstate_statemachine import Event, SyncInterpreter, ActionDefinition

logger = logging.getLogger(__name__)


class AudioWizardLogic:
    """Provides all guards and actions needed for the audio‐over‐WebSocket scenario."""

    def __init__(self) -> None:
        """🔗 Register alias names for LogicLoader auto‐discovery (to support exotic JSON keys)."""
        self.__dict__["websocket_token_is_defined"] = (
            self.websocket_token_is_defined
        )
        self.__dict__["session_expired"] = self.session_expired
        self.__dict__["message_is_stop_recording"] = (
            self.message_is_stop_recording
        )
        self.__dict__["websocket_is_connected"] = self.websocket_is_connected

    # -------------------------------------------------------------------------
    # 🛡️ Guards
    # -------------------------------------------------------------------------

    def websocket_token_is_defined(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """✔️ Guard: Ensure a WebSocket token exists in context."""
        return bool(context.get("token"))

    def session_expired(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """⏱️ Guard: Check if the stored token is expired."""
        return bool(context.get("token_expired", False))

    def message_is_stop_recording(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """🛑 Guard: Detect `stop_recording` marker in the message payload."""
        return event.payload.get("message") == "stop_recording"

    def websocket_is_connected(
        self, context: Dict[str, Any], event: Event
    ) -> bool:  # noqa
        """✔️ Guard: Check if WebSocket connection flag is set."""
        return bool(context.get("ws_connected", False))

    # -------------------------------------------------------------------------
    # ⚙️ Actions
    # -------------------------------------------------------------------------

    def connect(  # noqa
        self,
        interpreter: SyncInterpreter,
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔌 Action: Simulate WebSocket connect and enqueue success event."""
        logger.info("🔌 Connecting WebSocket…")
        context["ws_connected"] = True
        interpreter.send("🟢 wsConnectSuccess")

    def update_token(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🔑 Action: Update or set authentication token in context."""
        context["token"] = event.payload.get("token", "DEMO_TOKEN")
        context["token_expired"] = False
        logger.info(f"🔑 Token updated → {context['token']}")

    def unqueue_data(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📤 Action: Pop and send the next audio chunk, if any."""
        queue = context.get("data_queue", [])
        if queue:
            chunk = queue.pop(0)
            logger.info(f"📤 Sent chunk → {chunk}")

    def save_realtime_message(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """📥 Action: Append an incoming realtime message into log."""
        msg = event.payload.get("message")
        context.setdefault("messages", []).append(msg)
        logger.info(f"📥 Realtime msg saved → {msg}")

    def queue_start_recording(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🎙️ Action: Initialize the recording queue."""
        logger.info("🎙️ Start recording queued")
        context["data_queue"] = []

    def queue_stop_recording(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🛑 Action: Enqueue the stop‐recording marker."""
        logger.info("🛑 Stop recording queued")
        context.setdefault("data_queue", []).append("stop_recording")

    def queue_data(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """➕ Action: Enqueue an audio chunk from the payload."""
        chunk = event.payload.get("message")
        context.setdefault("data_queue", []).append(chunk)
        logger.info("➕ Audio chunk queued")
