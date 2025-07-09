# examples/sync/basic/functional_approach/with_logic_loader/character_counter_logic.py

# -----------------------------------------------------------------------------
# 🔠 Character Counter Logic (Functional)
# -----------------------------------------------------------------------------
# This module provides standalone functions for a character counter state machine.
# These functions are designed to be discovered automatically by the LogicLoader.
# -----------------------------------------------------------------------------
import logging
from typing import Dict, Any

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# --- Logger ---
logger = logging.getLogger(__name__)


# --- Actions ---


def update_text_and_count(
    i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
) -> None:
    """Updates the text and character count in the context."""
    new_text = e.payload.get("value", "")
    ctx["text"] = new_text
    ctx["charCount"] = len(new_text)
    logging.info(f"✍️  Text updated. Count: {ctx['charCount']}.")


def log_limit_reached(
    i: SyncInterpreter, ctx: Dict, e: Event, a: ActionDefinition
) -> None:
    """Logs a message when the character limit has been reached."""
    logging.warning(f"⚠️  Character limit of {ctx['limit']} reached!")


# --- Guards ---


def is_under_limit(ctx: Dict, e: Event) -> bool:
    """Checks if the new text length is within the defined limit."""
    new_text = e.payload.get("value", "")
    return len(new_text) <= ctx["limit"]


def is_over_limit(ctx: Dict, e: Event) -> bool:
    """Checks if the current text length is over the defined limit."""
    return len(ctx["text"]) > ctx["limit"]
