# -------------------------------------------------------------------------------
# 📝 Collaborative Editor Logic
# examples/async/super_complex/functional_approach/with_logic_loader/collaborative_editor/collaborative_editor_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for the Collaborative Editor example.

Illustrates:
  • Spawning collaborator cursor actors.
  • Debounced autosave using 'after' transitions.
  • Inter-actor communication and cleanup.
"""
import asyncio
import json
import logging
import os
import random
import time
from typing import Any, Dict, Optional

from src.xstate_statemachine import (
    Interpreter,
    Event,
    ActionDefinition,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

_actor_config: Optional[Dict[str, Any]] = None
_actor_logic: Optional[MachineLogic] = None


async def update_local_content(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✍️ Append typed character and trigger content-changed event."""
    context["local_content"] += event.payload.get("key", "")
    await interpreter.send("CONTENT_CHANGED")


def start_autosave_timer(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """⏲️ Log that an autosave timer has started."""
    logger.info("⏲️ Content changed; auto-saving in 3s...")


def update_server_content(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """☁️ Update context with saved content and timestamp."""
    context["server_content"] = event.data.get("content")
    context["last_saved"] = time.time()
    logger.info("✅ Document saved to server.")


def set_sync_error(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """❌ Store sync error and log it."""
    context["error"] = str(event.data)
    logger.error(f"❌ Sync failed: {context['error']}")


async def destroy_collaborator_cursor(
    interpreter: Interpreter,
    context: Dict[str, Any],  # noqa
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🗑️ Stop and remove a cursor actor for a leaving collaborator."""
    user_id = event.payload.get("user_id")
    actor_to_stop = next(
        (
            a
            for a in interpreter._actors.values()  # noqa
            if a.context.get("user_id") == user_id
        ),
        None,
    )
    if actor_to_stop:
        logger.info(f"🗑️ Removing cursor for {user_id}")
        await actor_to_stop.stop()
        interpreter._actors.pop(actor_to_stop.id, None)  # noqa


async def save_to_server_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """☁️ Async service to save content to server."""
    logger.info("☁️ Saving content...")
    await asyncio.sleep(1.5)
    if random.random() < 0.1:
        raise ConnectionError("Server unavailable.")
    return {"content": context["local_content"]}


def collaborator_cursor(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,
) -> MachineNode:
    """👤 Service to spawn a new collaborator cursor actor."""
    global _actor_config, _actor_logic
    if _actor_config is None:
        path = os.path.join("collaborator_cursor_actor.json")
        with open(path, "r", encoding="utf-8") as f:
            _actor_config = json.load(f)
        _actor_logic = MachineLogic(
            actions={"update_position": actor_update_position}
        )

    cfg = _actor_config.copy()
    cfg.setdefault("context", {})
    cfg["context"].update(
        {
            "user_id": event.payload.get("user_id"),
            "color": random.choice(["orange", "purple", "green"]),
        }
    )
    return create_machine(cfg, logic=_actor_logic)


def actor_update_position(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🖱️ Update cursor position for a collaborator actor."""
    context["position"] = event.payload.get("position")
    logger.info(
        f"🖱️ Cursor {context['user_id']} moved to {context['position']}"
    )
