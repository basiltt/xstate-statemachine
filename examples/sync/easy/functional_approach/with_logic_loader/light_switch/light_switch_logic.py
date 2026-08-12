# examples/sync/easy/functional_approach/with_logic_loader/light_switch/light_switch_logic.py
# -----------------------------------------------------------------------------
# 💡 Light Switch Logic (Functional with LogicLoader)
# -----------------------------------------------------------------------------
"""
Provides standalone actions for a light switch machine.

Key Concepts:
  • Functional Approach: Top-level functions auto-discovered.
  • LogicLoader: binds functions by name conventions.
"""

import logging
from typing import Any, Dict

from xstate_statemachine import SyncInterpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def set_brightness_to_default(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """💡 Action: Turn light ON (brightness 100%)."""
    context["brightness"] = 100
    logger.info(f"💡 Light ON. Brightness set to {context['brightness']}%.")


def set_brightness_to_zero(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🌑 Action: Turn light OFF (brightness 0%)."""
    context["brightness"] = 0
    logger.info(f"🌑 Light OFF. Brightness set to {context['brightness']}%.")
