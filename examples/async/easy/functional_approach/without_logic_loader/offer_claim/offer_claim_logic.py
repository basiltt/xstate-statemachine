# examples/async/easy/functional_approach/without_logic_loader/offer_claim/offer_claim_logic.py
import asyncio
import logging
from typing import Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


async def set_claimant(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    logging.info("  (Action: Writing claim to database...)")
    await asyncio.sleep(1.0)  # Simulate database write delay
    ctx["claimed_by"] = e.payload.get("user")
    logging.info(f"🎉 Offer claimed by '{ctx['claimed_by']}'!")
