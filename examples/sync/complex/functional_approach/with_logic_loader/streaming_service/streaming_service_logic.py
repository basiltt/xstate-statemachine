# -----------------------------------------------------------------------------
# 🎬 Streaming Service Logic
# examples/async/complex/functional_approach/with_logic_loader/streaming_service/streaming_service_logic.py
# -----------------------------------------------------------------------------
"""
Functional logic for an async streaming service:

  • set_content_id      – action on selecting content
  • store_manifest      – onDone of load_manifest_service
  • set_quality_hd/sd   – guards decide on play event
  • buffer_video_service– service to buffer before playing
  • log_playback_started– action when playing
  • set_error           – error handler
"""

import asyncio
import logging
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def set_content_id(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """▶️ Store selected content ID in context."""
    context["content_id"] = event.payload.get("content_id")
    logger.info(f"▶️ Content selected: {context['content_id']}")


def store_manifest(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✅ Store manifest data returned by the service."""
    context["manifest_data"] = event.data
    resolutions = event.data.get("resolutions")
    logger.info(f"✅ Manifest loaded. Available resolutions: {resolutions}")


def set_quality_hd(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔍 Select HD quality on high network speed."""
    context["quality_level"] = "1080p"
    logger.info("→ High speed detected. Selecting HD quality.")


def set_quality_sd(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔍 Select SD quality on low network speed."""
    context["quality_level"] = "480p"
    logger.info("→ Low speed detected. Selecting SD quality.")


def log_playback_started(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🎉 Log when playback starts."""
    logger.info(
        f"🎉 Playing '{context.get('content_id')}' at {context.get('quality_level')}!"
    )


def set_error(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """❌ Record any critical error."""
    context["error"] = str(event.data)
    logger.error(f"❌ Critical error: {context['error']}")


def can_play_hd(context: Dict[str, Any], event: Event) -> bool:  # noqa
    """✔️ Guard: Allow HD if network_speed_mbps > 5."""
    speed = event.payload.get("network_speed_mbps", 0)
    allowed = speed > 5
    if not allowed:
        logger.info("⚠️ HD not allowed due to low speed.")
    return allowed


async def load_manifest_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """☁️ Async service: Load streaming manifest."""
    content_id = context.get("content_id")
    logger.info(f"☁️ Fetching manifest for '{content_id}'...")
    await asyncio.sleep(1.5)
    if content_id == "movie_123":
        return {
            "title": "The State Machine",
            "duration": 3600,
            "resolutions": ["480p", "1080p"],
        }
    raise FileNotFoundError("Content not available in your region.")


async def buffer_video_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """⏳ Async service: Buffer video before playback."""
    quality = context.get("quality_level")
    logger.info(f"⏳ Buffering at {quality}...")
    await asyncio.sleep(1.0 if quality == "480p" else 2.5)
    logger.info("✅ Buffer complete.")
    return {"status": "ready_to_play"}
