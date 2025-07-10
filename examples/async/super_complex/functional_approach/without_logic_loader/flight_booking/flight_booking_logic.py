# -------------------------------------------------------------------------------
# ✈️ Flight Booking Logic
# examples/async/super_complex/functional_approach/without_logic_loader/flight_booking/flight_booking_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for the Flight Booking example.

Illustrates:
  • Parallel states for booking and check-in.
  • Ancillary service actor spawning.
  • Delayed 'after' transitions (simulating 24h).
"""
import asyncio
import json
import logging
import random
import uuid
from typing import Any, Dict, Optional

from src.xstate_statemachine import (
    Interpreter,
    Event,
    ActionDefinition,
    create_machine,
    MachineLogic,
)
from src.xstate_statemachine.models import MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

_actor_config: Optional[Dict[str, Any]] = None
_actor_logic: Optional[MachineLogic] = None


def set_search_criteria(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔎 Store flight search criteria in context."""
    context["search_criteria"] = event.payload
    logger.info(
        f"✈️ Searching from {event.payload.get('from')} to {event.payload.get('to')}"
    )


def store_flight_options(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✅ Record available flight options."""
    context["options"] = event.data
    logger.info(f"✅ Found {len(event.data)} options")


def set_search_error(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """❌ Handle flight search failure."""
    context["error"] = str(event.data)
    logger.error(f"❌ Search failed: {context['error']}")


def set_selected_flight(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🛫 Store selected flight details."""
    context["selected_flight"] = event.payload
    logger.info(f"👍 Selected flight {event.payload.get('flight_no')}")


def store_payment_id(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """💳 Store payment transaction ID."""
    context["payment_id"] = event.data.get("transaction_id")
    logger.info(f"💳 Payment complete: {context['payment_id']}")


def set_payment_error(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """❌ Handle payment failure."""
    context["error"] = str(event.data)
    logger.error(f"❌ Payment failed: {context['error']}")


def generate_booking_reference(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🎉 Generate a booking reference code."""
    ref = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))
    context["booking_reference"] = ref
    logger.info(f"🎉 Booking confirmed: {ref}")


def log_checkin_wait(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🕒 Notify about check-in window delay."""
    logger.info("🕒 Check-in opens in 5 seconds (simulated).")


async def search_flights_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
) -> Any:
    """📡 Simulate flight search service."""
    logger.info("📡 Searching flights...")
    await asyncio.sleep(2.0)
    return [{"flight_no": "BA2490"}, {"flight_no": "VS103"}]


async def process_payment_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
) -> Dict[str, str]:
    """💳 Simulate payment processing service."""
    logger.info("💳 Processing payment...")
    await asyncio.sleep(1.5)
    return {"transaction_id": str(uuid.uuid4())}


def ancillary_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,
) -> MachineNode:
    """🔧 Return actor machine for ancillary services (seat, baggage)."""
    global _actor_config, _actor_logic
    if _actor_config is None:
        path = "ancillary_service_actor.json"
        with open(path, "r", encoding="utf-8") as f:
            _actor_config = json.load(f)
        _actor_logic = MachineLogic(
            actions={
                "update_details": actor_update_details,
                "notify_parent_confirmed": actor_notify_parent,
            }
        )
    cfg = _actor_config.copy()
    cfg.setdefault("context", {})["service_type"] = event.type
    return create_machine(cfg, logic=_actor_logic)


def spawn_ancillary_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🚼 Placeholder spawn action for ancillary_service."""
    pass


def actor_update_details(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔧 Actor action to update service details."""
    context["details"] = event.payload
    logger.info(f"🧳 Actor {interpreter.id} details: {context['details']}")


async def actor_notify_parent(
    interpreter: Interpreter,
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔔 Actor action to notify parent of confirmation."""
    logger.info(
        f"🔔 Actor {interpreter.id} confirmed {context['service_type']}"
    )
