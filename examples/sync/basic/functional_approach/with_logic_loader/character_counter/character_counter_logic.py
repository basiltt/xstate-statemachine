# examples/sync/basic/functional_approach/with_logic_loader/character_counter_logic.py
# -----------------------------------------------------------------------------
# 🔠 Character Counter Logic (Functional with LogicLoader)
# -----------------------------------------------------------------------------
"""
Provides standalone action and guard functions for a character counter-machine.
"""

import logging
from typing import Any, Dict

from src.xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def update_text_and_count(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✍️ Update text and compute character count.

    Args:
        interpreter: The running SyncInterpreter.
        context: Mutable machine context.
        event: Event carrying 'value' in payload.
        action_def: Metadata about this action.
    """
    text = event.payload.get("value", "")
    context["text"] = text
    context["charCount"] = len(text)
    logger.info(f"✍️ Text updated. Count: {context['charCount']}")


def log_limit_reached(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """⚠️ Log when character limit is exceeded.

    Args:
        interpreter: The running SyncInterpreter.
        context: Mutable machine context.
        event: Event that triggered the guard.
        action_def: Metadata about this action.
    """
    logger.warning(f"⚠️ Character limit of {context.get('limit')} reached!")


def is_under_limit(context: Dict[str, Any], event: Event) -> bool:
    """✔️ Guard: Allow update if text length ≤ limit.

    Args:
        context: Mutable machine context.
        event: Event carrying 'value' in payload.

    Returns:
        True if within limit; False otherwise.
    """
    return len(event.payload.get("value", "")) <= context.get("limit", 0)


def is_over_limit(context: Dict[str, Any], event: Event) -> bool:  # noqa
    """❌ Guard: Detect when text length > limit.

    Args:
        context: Mutable machine context.
        event: The triggering Event.

    Returns:
        True if over limit; False otherwise.
    """
    return len(context.get("text", "")) > context.get("limit", 0)
