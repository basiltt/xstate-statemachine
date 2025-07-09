# examples/async/super_complex/functional_approach/without_logic_loader/flight_booking_runner.py
# -----------------------------------------------------------------------------
# ✈️ Super-Complex Example: Flight Booking System (Functional / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - Parallel states for post-booking management and check-in status.
#   - Spawning actors for ancillary services (seats, baggage).
#   - A long-running `after` timer to simulate a 24-hour check-in window.
#   - Explicit Logic Binding of all standalone functions.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
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
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


async def main():
    print(
        "\n--- ✈️  Async Flight Booking Simulation (Functional / Explicit Logic) ---"
    )

    with open("flight_booking.json", "r") as f:
        config = json.load(f)

    # Manually bind all standalone functions
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
            # The spawn action name must match the service that provides the actor
            "spawn_ancillary_service": spawn_ancillary_service,
        },
        services={
            "search_flights_service": search_flights_service,
            "process_payment_service": process_payment_service,
            # This service provides the actor definition
            "ancillary_service": ancillary_service,
        },
    )

    machine = create_machine(config, logic=machine_logic)
    interpreter = await Interpreter(machine).start()

    # --- Simulation ---
    logging.info("--- Step 1: Searching and Booking ---")
    await interpreter.send("SEARCH_FLIGHTS", **{"from": "LHR", "to": "JFK"})
    await asyncio.sleep(2.5)  # Wait for search

    await interpreter.send("SELECT_FLIGHT", flight_no="BA2490")
    await asyncio.sleep(2.0)  # Wait for payment

    logging.info(f"Booking state: {interpreter.current_state_ids}")
    logging.info(f"Booking Ref: {interpreter.context['booking_reference']}")

    logging.info("\n--- Step 2: Adding Ancillary Services ---")
    await interpreter.send("ADD_SEAT")
    await interpreter.send("ADD_BAGGAGE")
    await asyncio.sleep(0.5)

    # Find the spawned actors and interact with them
    seat_actor = next(
        (
            actor
            for actor in interpreter._actors.values()
            if actor.context.get("service_type") == "ADD_SEAT"
        ),
        None,
    )
    if seat_actor:
        await seat_actor.send("UPDATE_DETAILS", seat="14A")

    logging.info(f"Number of active actors: {len(interpreter._actors)}")

    logging.info("\n--- Step 3: Waiting for Check-in Window ---")
    # Wait for the 5-second 'after' timer to fire
    await asyncio.sleep(5.5)

    logging.info("\n--- Booking Summary ---")
    logging.info(f"Final state: {interpreter.current_state_ids}")

    await interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
