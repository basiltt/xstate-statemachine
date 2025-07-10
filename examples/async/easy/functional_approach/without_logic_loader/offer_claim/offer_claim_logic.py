# -------------------------------------------------------------------------------
# 🎉 Offer Claim Logic
# examples/async/easy/functional_approach/without_logic_loader/offer_claim/offer_claim_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for the async one-time offer claim demonstration.

Includes an action to record the claimant in context.
"""

import asyncio
import logging
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


async def set_claimant(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🎉 Record the user who claimed the offer in context.

    Args:
        interpreter: The running state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event carrying `payload['user']`.
        action_def: Metadata about this action.
    """
    logger.info("💾 Writing claim to database...")
    await asyncio.sleep(1.0)
    context["claimed_by"] = event.payload.get("user")
    logger.info(f"🎉 Offer claimed by '{context['claimed_by']}'!")
