# examples/async/complex/functional_approach/without_logic_loader/game_matchmaking_runner.py
# -----------------------------------------------------------------------------
# ⚔️ Complex Example: Game Matchmaking (Functional / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - `invoke` for a long-running, fallible search operation.
#   - `after` to create a game timer.
#   - A multi-path final state (victory, defeat, draw).
#   - Explicit Logic Binding for standalone async/sync functions.
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import os
import sys
import random

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import create_machine, Interpreter, MachineLogic
from game_matchmaking_logic import (
    set_player_info,
    store_match_info,
    set_search_error,
    log_game_start,
    log_game_result,
    find_match_service,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ✅ FIX: Add a robust helper function to wait for a specific state
async def wait_for_state(
    interpreter: Interpreter, state_id: str, timeout: float = 5.0
) -> bool:
    """Polls the interpreter until it enters the desired state or times out."""
    start_time = asyncio.get_event_loop().time()
    while True:
        if state_id in interpreter.current_state_ids:
            logging.info(f"--> Reached expected state '{state_id}'")
            return True
        if asyncio.get_event_loop().time() - start_time > timeout:
            logging.error(
                f"--> Timed out waiting for state '{state_id}'. Current state: {interpreter.current_state_ids}"
            )
            return False
        await asyncio.sleep(0.1)


async def main():
    print(
        "\n--- ⚔️  Async Game Matchmaking Simulation (Functional / Explicit Logic) ---"
    )

    with open("game_matchmaking.json", "r") as f:
        config = json.load(f)

    machine_logic = MachineLogic(
        actions={
            "set_player_info": set_player_info,
            "store_match_info": store_match_info,
            "set_search_error": set_search_error,
            "log_game_start": log_game_start,
            "log_game_result": log_game_result,
        },
        services={
            "find_match_service": find_match_service,
        },
    )

    machine = create_machine(config, logic=machine_logic)

    # --- Scenario 1: Successful Match and Victory ---
    print("\n--- Scenario 1: Successful Match and Player Victory ---")
    interpreter1 = await Interpreter(machine).start()
    await interpreter1.send("SEARCH_FOR_MATCH", player_id="DragonSlayer91")

    # ✅ FIX: Use the helper to wait for either success or failure
    match_found = await wait_for_state(
        interpreter1, "gameMatchmaking.match_found"
    )

    if not match_found:
        logging.error("Scenario 1 failed to find a match. Stopping.")
    else:
        await interpreter1.send("ACCEPT_MATCH")
        await wait_for_state(interpreter1, "gameMatchmaking.in_game")

        logging.info("...game in progress for 3 seconds...")
        await asyncio.sleep(3)
        await interpreter1.send("PLAYER_VICTORY")

        await wait_for_state(interpreter1, "gameMatchmaking.game_over_victory")
        logging.info(
            f"Final state for Scenario 1: {interpreter1.current_state_ids}"
        )

    await interpreter1.stop()

    # --- Scenario 2: Match Found, but Game Times Out (Draw) ---
    print("\n--- Scenario 2: Game Ends in a Draw due to Timeout ---")
    interpreter2 = await Interpreter(machine).start()
    await interpreter2.send("SEARCH_FOR_MATCH", player_id="ShadowBlade")

    match_found_2 = await wait_for_state(
        interpreter2, "gameMatchmaking.match_found"
    )

    if not match_found_2:
        logging.error("Scenario 2 failed to find a match. Stopping.")
    else:
        await interpreter2.send("ACCEPT_MATCH")
        await wait_for_state(interpreter2, "gameMatchmaking.in_game")

        logging.info("...game in progress, waiting for timeout (10s)...")
        # The timeout is handled by the machine itself, so we just wait for the result
        await wait_for_state(
            interpreter2, "gameMatchmaking.game_over_draw", timeout=10.5
        )
        logging.info(
            f"Final state for Scenario 2: {interpreter2.current_state_ids}"
        )

    await interpreter2.stop()

    print("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
