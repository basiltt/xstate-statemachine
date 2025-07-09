# examples/sync/intermediate/functional_approach/with_logic_loader/document_editor_logic.py

# -----------------------------------------------------------------------------
# 📝 Document Editor Logic (Functional)
# -----------------------------------------------------------------------------
# This module provides standalone functions for the document editor state machine.
# These functions are designed to be discovered automatically by the LogicLoader.
# -----------------------------------------------------------------------------

import logging
from typing import Any, Dict

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition

logger = logging.getLogger(__name__)

# --- Actions ---


def set_content(i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition):
    """Sets the initial content of the document."""
    ctx["content"] = e.payload.get("content", "")
    logging.info(f"✍️ Document content set to: '{ctx['content']}'")


def update_content(
    i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
):
    """Appends a character to the document's content."""
    ctx["content"] += e.payload.get("key", "")
    logging.info(f"✍️ Content updated: '{ctx['content']}'")


def enter_format_mode(
    i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition
):
    """Logs entry into the formatting sub-state."""
    logging.info("🎨 Entered formatting mode.")


def toggle_bold(i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition):
    """Toggles the 'isBold' flag in the context."""
    ctx["isBold"] = not ctx["isBold"]
    logging.info(f"** Toggled Bold: {'ON' if ctx['isBold'] else 'OFF'} **")


def log_entry(i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition):
    """Logs a message upon entering the parent 'editing' state."""
    logging.info("➡️  Entering 'editing' state.")


def log_exit(i: SyncInterpreter, ctx: Dict, e: Event, ad: ActionDefinition):
    """Logs a message upon exiting the parent 'editing' state."""
    logging.info("⬅️  Exiting 'editing' state.")


# --- Services ---


def save_document(i: SyncInterpreter, ctx: Dict, e: Event) -> Dict[str, Any]:
    """A synchronous service that 'saves' the document."""
    content_to_save = ctx.get("content", "")
    logging.info(f"💾 Saving document with content: '{content_to_save}'...")
    if len(content_to_save) < 5:
        raise ValueError("Content too short to save!")
    logging.info("✅ Document saved successfully.")
    return {"status": "saved", "length": len(content_to_save)}
