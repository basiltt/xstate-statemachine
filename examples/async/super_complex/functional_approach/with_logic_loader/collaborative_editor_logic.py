# examples/async/super_complex/functional_approach/with_logic_loader/collaborative_editor/collaborative_editor_logic.py
import asyncio
import json
import logging
import os
import random
import time
from typing import Dict, Any

from src.xstate_statemachine import (
    Interpreter,
    Event,
    ActionDefinition,
    create_machine,
    MachineLogic,
)
from src.xstate_statemachine.models import MachineNode


# --- Main Machine Actions ---
async def update_local_content(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["local_content"] += e.payload.get("key", "")
    await i.send("CONTENT_CHANGED")


def start_autosave_timer(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    logging.info(
        "✍️ Content changed. Unsaved changes present. Auto-saving in 3s."
    )


def update_server_content(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["server_content"] = e.data.get("content")
    ctx["last_saved"] = time.time()
    logging.info("✅ Document saved and synced successfully.")


def set_sync_error(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["error"] = str(e.data)
    logging.error(f"❌ Could not save document: {ctx['error']}")


async def destroy_collaborator_cursor(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    user_id_to_remove = e.payload.get("user_id")
    actor_to_stop = next(
        (
            actor
            for actor in i._actors.values()
            if actor.context.get("user_id") == user_id_to_remove
        ),
        None,
    )

    if actor_to_stop:
        logging.info(
            f"👤 Collaborator '{user_id_to_remove}' left. Destroying cursor actor."
        )
        await actor_to_stop.stop()
        if actor_to_stop.id in i._actors:
            del i._actors[actor_to_stop.id]


# --- Main Machine Services ---
async def save_to_server_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    logging.info("  -> ☁️ Invoking service: Saving content to server...")
    await asyncio.sleep(1.5)
    if random.random() < 0.1:
        raise ConnectionError("Failed to connect to server.")
    return {"content": ctx["local_content"]}


# --- Actor Logic ---
_actor_config = None
_actor_logic = None


def load_actor_defs():
    global _actor_config, _actor_logic
    if _actor_config is None:
        with open("collaborator_cursor_actor.json", "r") as f:
            _actor_config = json.load(f)
        _actor_logic = MachineLogic(
            actions={"update_position": actor_update_position}
        )


def collaborator_cursor(i: Interpreter, ctx: Dict, e: Event) -> "MachineNode":
    """
    This service is called by the interpreter's `spawn_` logic.
    It uses the event payload to set the initial context of the new actor.
    """
    load_actor_defs()
    # Create a fresh copy of the config to avoid state pollution
    machine_config = _actor_config.copy()

    # ✅ FIX: Set initial context for the spawned actor
    machine_config["context"] = machine_config.get("context", {})
    machine_config["context"]["user_id"] = e.payload.get("user_id")
    machine_config["context"]["color"] = random.choice(
        ["orange", "purple", "green"]
    )

    return create_machine(machine_config, logic=_actor_logic)


def actor_update_position(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["position"] = e.payload.get("position")
    logging.info(
        f"  -> 🖱️  Cursor for user '{ctx['user_id']}' (color: {ctx['color']}) moved to {ctx['position']}"
    )
