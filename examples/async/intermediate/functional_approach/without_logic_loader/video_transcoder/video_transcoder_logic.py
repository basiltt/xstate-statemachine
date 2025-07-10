# -------------------------------------------------------------------------------
# 🎬 Video Transcoder Logic
# examples/async/intermediate/functional_approach/without_logic_loader/video_transcoder/video_transcoder_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for the async video transcoder demonstration.

Includes actions to upload, handle success/failure, and a service to simulate
transcoding into multiple formats.
"""

import asyncio
import logging
from typing import Any, Dict

from src.xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


async def upload_video_file(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """📤 Simulate uploading a video file and send next event.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event carrying `payload['file_name']`.
        action_def: Metadata about this action.
    """
    file_name = event.payload.get("file_name")
    context["source_file"] = file_name
    logger.info(f"📤 Uploading '{file_name}'...")
    await asyncio.sleep(2.0)
    if "fail" in file_name:
        logger.error("❌ Upload failed.")
        await interpreter.send("UPLOAD_FAILED")
    else:
        path = f"/uploads/{file_name}"
        context["upload_path"] = path
        logger.info(f"✅ Upload complete. Path: {path}")
        await interpreter.send("UPLOAD_COMPLETE")


def set_transcoding_status(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """🎉 Store transcoding result into context.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The DoneEvent carrying `data`.
        action_def: Metadata about this action.
    """
    context["transcoding_status"] = event.data
    logger.info(f"🎉 Transcoding successful! Details: {event.data}")


def set_error(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """🔥 Store error from failed transcoding.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The DoneEvent carrying error `data`.
        action_def: Metadata about this action.
    """
    context["error"] = str(event.data)
    logger.error(f"🔥 An error occurred: {context['error']}")


async def transcode_video_service(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
) -> Dict[str, Any]:
    """⚙️ Async service to simulate video transcoding.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event.

    Returns:
        A dict with `status` and available `formats`.

    Raises:
        TypeError: If the codec is unsupported.
    """
    path = context.get("upload_path")
    logger.info(f"⚙️ Transcoding '{path}'...")
    await asyncio.sleep(3.0)
    if "unsupported" in path:
        raise TypeError("Unsupported video codec.")
    return {"status": "success", "formats": ["1080p", "720p", "480p"]}
