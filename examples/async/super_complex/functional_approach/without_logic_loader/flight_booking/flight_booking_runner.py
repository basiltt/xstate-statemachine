# -------------------------------------------------------------------------------
# ✈️ Flight Booking Runner
# examples/async/super_complex/functional_approach/without_logic_loader/flight_booking/flight_booking_runner.py
# -------------------------------------------------------------------------------
"""
Runner for the Flight Booking simulation.

Illustrates:
  • Explicit MachineLogic binding for standalone functions.
  • Actor spawning for ancillary services.
  • Delayed transitions, events, and context updates.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict

from flight_booking_logic import (
    set_search_criteria,
    store_flight_options,
    set_search_error,
    set_selected_flight,
    store_payment_id,
    set_payment_error,
    generate_booking_reference,
    log_checkin_wait,
    spawn_ancillary_service,
    search_flights_service,
    process_payment_service,
    ancillary_service,
)  # noqa: E402
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main() -> None:
    """🚀 Execute the Flight Booking simulation."""
    logger.info("\n--- ✈️ Flight Booking Simulation ---")

    root = os.path.dirname(__file__)
    config_path = os.path.join(root, "flight_booking.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine_logic = MachineLogic(
        actions={
            "set_search_criteria": set_search_criteria,
            "store_flight_options": store_flight_options,
            "set_search_error": set_search_error,
            "set_selected_flight": set_selected_flight,
            "store_payment_id": store_payment_id,
            "set_payment_error": set_payment_error,
            "generate_booking_reference": generate_booking_reference,
            "log_checkin_wait": log_checkin_wait,
            "spawn_ancillary_service": spawn_ancillary_service,
        },
        services={
            "search_flights_service": search_flights_service,
            "process_payment_service": process_payment_service,
            "ancillary_service": ancillary_service,
        },
    )
    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    logger.info("--- Step 1: Search & Book ---")
    await interpreter.send("SEARCH_FLIGHTS", **{"from": "LHR", "to": "JFK"})
    await asyncio.sleep(2.5)

    await interpreter.send("SELECT_FLIGHT", flight_no="BA2490")
    await asyncio.sleep(2.0)

    logger.info("--- Step 2: Ancillary Services ---")
    await interpreter.send("ADD_SEAT")
    await interpreter.send("ADD_BAGGAGE")
    await asyncio.sleep(0.5)

    seat_actor = next(
        (
            a
            for a in interpreter._actors.values()
            if a.context.get("service_type") == "ADD_SEAT"
        ),  # noqa
        None,
    )
    if seat_actor:
        await seat_actor.send("UPDATE_DETAILS", seat="14A")

    logger.info("--- Step 3: Waiting for Check-in ---")
    await asyncio.sleep(5.5)

    logger.info(f"Final states: {interpreter.current_state_ids}")
    await interpreter.stop()
    logger.info("--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
