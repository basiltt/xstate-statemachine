# examples/async/complex/functional_approach/with_logic_loader/streaming_service/streaming_service_logic.py
import asyncio
import logging
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


# --- Actions ---
def set_content_id(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["content_id"] = e.payload.get("content_id")
    logging.info(f"▶️  Content selected: {ctx['content_id']}")


def store_manifest(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["manifest_data"] = e.data
    logging.info(
        f"✅ Manifest loaded. Available resolutions: {e.data.get('resolutions')}"
    )


def set_quality_hd(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["quality_level"] = "1080p"
    logging.info("  -> High network speed detected. Selecting HD quality.")


def set_quality_sd(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["quality_level"] = "480p"
    logging.info("  -> Low network speed. Selecting SD quality as fallback.")


def log_playback_started(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    logging.info(
        f"🎉 Playing '{ctx['content_id']}' in {ctx['quality_level']}!"
    )


def set_error(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["error"] = str(e.data)
    logging.error(f"❌ A critical error occurred: {ctx['error']}")


# --- Guards ---
def can_play_hd(ctx: Dict, e: Event) -> bool:
    """Checks if the network speed from the event payload is sufficient for HD."""
    return e.payload.get("network_speed_mbps", 0) > 5


# --- Services ---
async def load_manifest_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    content_id = ctx.get("content_id")
    logging.info(
        f"  -> ☁️  Invoking service: Fetching manifest for '{content_id}'..."
    )
    await asyncio.sleep(1.5)

    if content_id == "movie_123":
        return {
            "title": "The State Machine",
            "duration": 3600,
            "resolutions": ["480p", "1080p"],
        }
    else:
        raise FileNotFoundError("Content not available in your region.")


async def buffer_video_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    quality = ctx.get("quality_level")
    logging.info(f"  -> ⏳ Invoking service: Buffering video at {quality}...")

    # HD takes longer to buffer
    buffer_time = 1.0 if quality == "480p" else 2.5
    await asyncio.sleep(buffer_time)

    logging.info("  -> ✅ Buffer complete.")
    return {"status": "ready_to_play"}
