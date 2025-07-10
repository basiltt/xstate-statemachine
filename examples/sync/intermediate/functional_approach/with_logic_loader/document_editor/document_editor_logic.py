# examples/sync/intermediate/functional_approach/with_logic_loader/document_editor_logic.py
# -----------------------------------------------------------------------------
# 📝 Document Editor Logic (Functional with LogicLoader)
# -----------------------------------------------------------------------------
"""
Standalone actions and services for a synchronous document editor state machine.

Key Concepts:
  • Functional approach with auto-discovery via logic_modules.
  • Nested states: 'typing' and 'formatting' under 'editing'.
  • Synchronous service with error handling.
"""

import logging
from typing import Any, Dict

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def set_content(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✍️ Action: Set the initial document content.

    Args:
        interpreter: The running SyncInterpreter.
        context: Mutable context dictionary.
        event: Event carrying payload {'content': str}.
        action_def: Metadata for this action.
    """
    content = event.payload.get("content", "")
    context["content"] = content
    logger.info(f"✍️ Document content set to: '{content}'")


def update_content(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✍️ Action: Append a character to document content.

    Args:
        interpreter: The running SyncInterpreter.
        context: Mutable context dictionary.
        event: Event carrying payload {'key': str}.
        action_def: Metadata for this action.
    """
    key = event.payload.get("key", "")
    context["content"] += key
    logger.info(f"✍️ Content updated: '{context['content']}'")


def enter_format_mode(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🎨 Action: Log entry into formatting mode."""
    logger.info("🎨 Entered formatting mode.")


def toggle_bold(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """** Action: Toggle bold formatting flag in context.

    Args:
        interpreter: The running SyncInterpreter.
        context: Mutable context dictionary.
        event: The triggering Event.
        action_def: Metadata for this action.
    """
    context["isBold"] = not context.get("isBold", False)
    state = "ON" if context["isBold"] else "OFF"
    logger.info(f"** Toggled Bold: {state} **")


def log_entry(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """➡️ Action: Log upon entering the 'editing' parent state."""
    logger.info("➡️ Entering 'editing' state.")


def log_exit(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """⬅️ Action: Log upon exiting the 'editing' parent state."""
    logger.info("⬅️ Exiting 'editing' state.")


def save_document(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """💾 Service: Simulate saving the document synchronously.

    Args:
        interpreter: The running SyncInterpreter.
        context: Mutable context dictionary.
        event: The triggering Event.

    Returns:
        A dict with save status and content length.

    Raises:
        ValueError: If content is too short to save.
    """
    content = context.get("content", "")
    logger.info(f"💾 Saving document: '{content}'")
    if len(content) < 5:
        raise ValueError("Content too short to save!")
    logger.info("✅ Document saved successfully.")
    return {"status": "saved", "length": len(content)}
