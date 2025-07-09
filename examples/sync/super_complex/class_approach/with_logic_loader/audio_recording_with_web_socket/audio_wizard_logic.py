"""
Implementation logic for the “Audio recording with websocket” machine
(class-based, ready for LogicLoader auto-discovery).

⚠️  NOTE on strange guard / action names
---------------------------------------
The JSON uses names that contain spaces or emojis.  Python identifiers
can’t, so we:
1. implement a *normal* snake-case function, e.g.  websocket_token_is_defined
2. add an **alias attribute** on `self` that matches the exact string in
   the JSON.  LogicLoader will then find it.

The same trick is used for emojis like “🟢 sessionSubmitSucces”.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.xstate_statemachine import Event, SyncInterpreter, ActionDefinition

_log = logging.getLogger(__name__)


class AudioWizardLogic:
    # ------------------------------------------------------------------#
    # Guards                                                             #
    # ------------------------------------------------------------------#
    def websocket_token_is_defined(self, ctx: Dict, _evt: Event) -> bool:
        return bool(ctx.get("token"))

    def session_expired(self, ctx: Dict, _evt: Event) -> bool:
        return ctx.get("token_expired", False)

    def message_is_stop_recording(self, _ctx: Dict, evt: Event) -> bool:
        return evt.payload.get("message") == "stop_recording"

    def websocket_is_connected(self, ctx: Dict, _evt: Event) -> bool:
        return ctx.get("ws_connected", False)

    # ------------------------------------------------------------------#
    # Actions                                                            #
    # ------------------------------------------------------------------#
    # ── websocket branch ──────────────────────────────────────────────
    def connect(
        self, i: SyncInterpreter, ctx: Dict, _evt: Event, _a: ActionDefinition
    ) -> None:
        """Pretend to connect; in demo we just flag context & emit a success."""
        _log.info("🔌 Connecting WebSocket …")
        ctx["ws_connected"] = True
        # Queue a synthetic success event for the state machine.
        i.send("🟢 wsConnectSuccess")

    def udpdateToken(
        self, _i: SyncInterpreter, ctx: Dict, evt: Event, _a: ActionDefinition
    ) -> None:
        """Typo kept as-is to match JSON."""
        ctx["token"] = evt.payload.get("token", "DEMO_TOKEN")
        ctx["token_expired"] = False
        _log.info("🔑 Token updated → %s", ctx["token"])

    def unqueueData(
        self, _i: SyncInterpreter, ctx: Dict, _evt: Event, _a: ActionDefinition
    ) -> None:
        if ctx.get("data_queue"):
            data = ctx["data_queue"].pop(0)
            _log.info("📤 Sent chunk → %s", data)

    def saveRealtimeMessage(
        self, _i: SyncInterpreter, ctx: Dict, evt: Event, _a: ActionDefinition
    ) -> None:
        ctx.setdefault("messages", []).append(evt.payload.get("message"))
        _log.info("📥 Realtime msg saved → %s", evt.payload.get("message"))

    # ── media-recorder branch ─────────────────────────────────────────
    def queueStartRecording(
        self, _i: SyncInterpreter, ctx: Dict, _evt: Event, _a: ActionDefinition
    ) -> None:
        _log.info("🎙️  Start recording queued")
        ctx["data_queue"] = []

    def queueStopRecording(
        self, _i: SyncInterpreter, ctx: Dict, _evt: Event, _a: ActionDefinition
    ) -> None:
        _log.info("🛑 Stop recording queued")
        ctx["data_queue"].append("stop_recording")

    def queueData(
        self, _i: SyncInterpreter, ctx: Dict, evt: Event, _a: ActionDefinition
    ) -> None:
        chunk = evt.payload.get("message")
        ctx["data_queue"].append(chunk)
        _log.info("➕ Audio chunk queued")

    # ------------------------------------------------------------------#
    # Aliases so LogicLoader can match exotic names verbatim            #
    # ------------------------------------------------------------------#
    def __init__(self) -> None:
        # Guards
        self.__dict__["websocket token is defined"] = (
            self.websocket_token_is_defined
        )
        self.__dict__["Session expired"] = self.session_expired
        self.__dict__["message is stop_recording"] = (
            self.message_is_stop_recording
        )
        self.__dict__["websocket is connected"] = self.websocket_is_connected
        # Actions – the ones above are already legal identifiers;
        # no spaces or emojis to alias here.
