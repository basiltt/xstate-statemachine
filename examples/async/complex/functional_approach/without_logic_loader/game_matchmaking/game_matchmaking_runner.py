# -------------------------------------------------------------------------------
# ⚔️ Async Game Matchmaking Runner
# examples/async/complex/functional_approach/without_logic_loader/game_matchmaking_runner.py
# -------------------------------------------------------------------------------
"""
Runner for asynchronous game matchmaking simulation
with explicit functional logic binding.
"""

import asyncio
import json
import logging
import os
import sys

from src.xstate_statemachine import Interpreter, MachineLogic, create_machine

# -----------------------------------------------------------------------------
# 📂 Project Path Setup
# -----------------------------------------------------------------------------
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from game_matchmaking_logic import (  # noqa: E402
    set_player_info,
    store_match_info,
    set_search_error,
    log_game_start,
    log_game_result,
    find_match_service,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def wait_for_state(
    interpreter: Interpreter, state_id: str, timeout: float = 5.0
) -> bool:
    """⏳ Poll until interpreter enters `state_id` or `timeout` is reached."""
    start = asyncio.get_event_loop().time()
    while True:
        if state_id in interpreter.current_state_ids:
            logger.info(f"--> Reached {state_id}")
            return True
        if asyncio.get_event_loop().time() - start > timeout:
            logger.error(f"--> Timeout waiting for {state_id}")
            return False
        await asyncio.sleep(0.1)


async def main() -> None:
    """🚀 Execute game matchmaking scenarios."""
    logger.info("\n--- ⚔️ Async Game Matchmaking Simulation ---")

    path = os.path.join(os.path.dirname(__file__), "game_matchmaking.json")
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    logic_map = {
        "set_player_info": set_player_info,
        "store_match_info": store_match_info,
        "set_search_error": set_search_error,
        "log_game_start": log_game_start,
        "log_game_result": log_game_result,
    }
    service_map = {"find_match_service": find_match_service}
    machine = create_machine(
        config, logic=MachineLogic(actions=logic_map, services=service_map)
    )

    # Scenario 1: Victory Path
    logger.info("\n--- Scenario 1: Victory Path ---")
    interpreter1 = await Interpreter(machine).start()
    await interpreter1.send("SEARCH_FOR_MATCH", player_id="DragonSlayer")
    if await wait_for_state(interpreter1, "gameMatchmaking.match_found"):
        await interpreter1.send("ACCEPT_MATCH")
        await wait_for_state(interpreter1, "gameMatchmaking.in_game")
        await asyncio.sleep(3)
        await interpreter1.send("PLAYER_VICTORY")
        await wait_for_state(interpreter1, "gameMatchmaking.game_over_victory")
        logger.info(f"Final state: {interpreter1.current_state_ids}")
    await interpreter1.stop()

    # Scenario 2: Draw by Timeout
    logger.info("\n--- Scenario 2: Draw by Timeout ---")
    interpreter2 = await Interpreter(machine).start()
    await interpreter2.send("SEARCH_FOR_MATCH", player_id="ShadowBlade")
    if await wait_for_state(interpreter2, "gameMatchmaking.match_found"):
        await interpreter2.send("ACCEPT_MATCH")
        await wait_for_state(interpreter2, "gameMatchmaking.in_game")
        await wait_for_state(
            interpreter2, "gameMatchmaking.game_over_draw", timeout=10.5
        )
        logger.info(f"Final state: {interpreter2.current_state_ids}")
    await interpreter2.stop()

    logger.info("\n--- ✅ All Scenarios Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
