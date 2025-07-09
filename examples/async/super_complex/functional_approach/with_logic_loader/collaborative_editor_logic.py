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


async def spawn_collaborator_cursor(
    i: Interpreter, ctx: Dict, e: Event, ad: ActionDefinition
):
    # ✅ FIX: This action now needs to be explicitly implemented to pass context.
    # The interpreter's built-in `spawn_` only works for simple cases.
    # To pass initial context, we do it manually.
    user_id = e.payload.get("user_id")
    logging.info(f"👤 User '{user_id}' joined. Spawning cursor actor.")

    # Get the actor's machine definition from the service
    actor_machine_def_callable = i.machine.logic.services.get(
        "collaborator_cursor"
    )
    if not actor_machine_def_callable:
        logging.error("Could not find 'collaborator_cursor' service to spawn.")
        return

    actor_machine = actor_machine_def_callable(i, ctx, e)

    # Set the initial context for this specific actor
    actor_machine.initial_context["user_id"] = user_id
    actor_machine.initial_context["color"] = random.choice(
        ["orange", "purple", "green"]
    )

    # The rest is the same as the internal _spawn_actor logic
    actor_id = f"{i.id}:collaborator_cursor:{user_id}"  # Use a predictable ID
    actor_interpreter = Interpreter(actor_machine)
    actor_interpreter.parent = i
    actor_interpreter.id = actor_id
    await actor_interpreter.start()

    i._actors[actor_id] = actor_interpreter
    logging.info(f"✅ Actor '{actor_id}' spawned successfully.")


async def destroy_collaborator_cursor(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    user_id_to_remove = e.payload.get("user_id")

    # ✅ FIX: Find the actor by inspecting its internal context
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
        # It's safer to remove the actor after stopping it
        if actor_to_stop.id in i._actors:
            del i._actors[actor_to_stop.id]
    else:
        logging.warning(
            f"Could not find actor for user '{user_id_to_remove}' to destroy."
        )


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
    """Service that returns the machine definition for a collaborator cursor actor."""
    load_actor_defs()
    # Note: We return a *copy* of the config to avoid modifying the original
    return create_machine(_actor_config.copy(), logic=_actor_logic)


def actor_update_position(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["position"] = e.payload.get("position")
    logging.info(
        f"  -> 🖱️  Cursor for user '{ctx['user_id']}' (color: {ctx['color']}) moved to {ctx['position']}"
    )
