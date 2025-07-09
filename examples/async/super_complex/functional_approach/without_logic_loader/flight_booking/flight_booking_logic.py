# examples/async/super_complex/functional_approach/without_logic_loader/flight_booking/flight_booking_logic.py
import asyncio
import json
import logging
import os
import random
import uuid
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
def set_search_criteria(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["search_criteria"] = e.payload
    logging.info(
        f"✈️  New search: From {e.payload.get('from')} to {e.payload.get('to')}"
    )


def store_flight_options(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    logging.info(f"✅ Found {len(e.data)} flight options.")


def set_search_error(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["error"] = str(e.data)
    logging.error(f"❌ Could not find flights: {ctx['error']}")


def set_selected_flight(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["selected_flight"] = e.payload
    logging.info(f"👍 Flight {e.payload.get('flight_no')} selected.")


def store_payment_id(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["payment_id"] = e.data.get("transaction_id")
    logging.info(f"💳 Payment successful. Transaction ID: {ctx['payment_id']}")


def set_payment_error(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["error"] = str(e.data)
    logging.error(f"❌ Payment failed: {ctx['error']}")


def generate_booking_reference(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["booking_reference"] = "".join(
        random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6)
    )
    logging.info(
        f"🎉 Booking confirmed! Your reference is: {ctx['booking_reference']}"
    )


def log_checkin_wait(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    logging.info(
        "🕒 Check-in window is not open yet. Will open in 5 seconds (simulated 24 hours)."
    )


# --- Main Machine Services ---
async def search_flights_service(i: Interpreter, ctx: Dict, e: Event) -> list:
    logging.info("  -> 📡 Invoking service: Searching flight database...")
    await asyncio.sleep(2.0)
    return [{"flight_no": "BA2490"}, {"flight_no": "VS103"}]


async def process_payment_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, str]:
    logging.info("  -> 💳 Invoking service: Processing payment...")
    await asyncio.sleep(1.5)
    return {"transaction_id": str(uuid.uuid4())}


# --- Actor Logic ---
_actor_config = None
_actor_logic = None


def load_actor_defs():
    global _actor_config, _actor_logic
    if _actor_config is None:
        with open("ancillary_service_actor.json", "r") as f:
            _actor_config = json.load(f)
        _actor_logic = MachineLogic(
            actions={
                "update_details": actor_update_details,
                "notify_parent_confirmed": actor_notify_parent,
            }
        )


def ancillary_service(i: Interpreter, ctx: Dict, e: Event) -> "MachineNode":
    """Service that returns the machine definition for an ancillary service actor."""
    load_actor_defs()
    config = _actor_config.copy()
    config["context"] = config.get("context", {})
    # Use the action's type (e.g., "ADD_SEAT") as the service type
    config["context"]["service_type"] = e.type
    return create_machine(config, logic=_actor_logic)


def spawn_ancillary_service(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    # This is handled by the interpreter's built-in spawn logic.
    # The LogicLoader will fail to find it, which is why we must bind it manually
    # to the `ancillary_service` function in the runner.
    pass


def actor_update_details(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["details"] = e.payload
    logging.info(f"  -> 💺 Actor '{i.id}' updated details: {ctx['details']}")


async def actor_notify_parent(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    logging.info(f"  -> ✅ Actor '{i.id}' confirmed {ctx['service_type']}.")
    # In a real app, you might send an event back to the parent.
    await asyncio.sleep(0)  # Yield control
