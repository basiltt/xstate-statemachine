# examples/async/intermediate/functional_approach/without_logic_loader/video_transcoder/video_transcoder_logic.py
import asyncio
import logging
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


# --- Actions ---


async def upload_video_file(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    """Simulates uploading a file by setting context and waiting."""
    ctx["source_file"] = e.payload.get("file_name")
    logging.info(f"📤 Action: Starting upload for '{ctx['source_file']}'...")

    await asyncio.sleep(2.0)  # Simulate a 2-second upload time

    if "fail" in ctx["source_file"]:
        logging.error("❌ Upload failed due to a simulated network error.")
        await i.send("UPLOAD_FAILED")
    else:
        ctx["upload_path"] = f"/uploads/{ctx['source_file']}"
        logging.info(f"✅ Upload complete. Path: {ctx['upload_path']}")
        await i.send("UPLOAD_COMPLETE")


def set_transcoding_status(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    """Sets the final transcoding status from the service result."""
    ctx["transcoding_status"] = e.data
    logging.info(f"🎉 Transcoding successful! Details: {e.data}")


def set_error(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    """Stores the error from a failed service."""
    ctx["error"] = str(e.data)
    logging.error(f"🔥 An error occurred: {ctx['error']}")


# --- Services ---


async def transcode_video_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    """Simulates a long-running video transcoding process."""
    file_path = ctx.get("upload_path")
    logging.info(f"⚙️  Invoke: Starting to transcode '{file_path}'...")

    # Simulate processing time
    await asyncio.sleep(3.0)

    if "unsupported" in file_path:
        raise TypeError("Unsupported video codec in source file.")

    return {"status": "success", "formats": ["1080p", "720p", "480p"]}
