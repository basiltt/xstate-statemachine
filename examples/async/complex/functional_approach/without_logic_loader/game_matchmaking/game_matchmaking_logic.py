# examples/async/complex/functional_approach/without_logic_loader/game_matchmaking/game_matchmaking_logic.py
import asyncio
import logging
import random
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


# --- Actions ---


def set_player_info(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["player_id"] = e.payload.get("player_id")
    logging.info(
        f"🤺 Player '{ctx['player_id']}' is searching for a '{ctx['game_mode']}' match."
    )


def store_match_info(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["match_id"] = e.data.get("match_id")
    opponent = e.data.get("opponent")
    logging.info(
        f"🤝 Match Found! ID: {ctx['match_id']}. Opponent: {opponent}. Awaiting player acceptance."
    )


def set_search_error(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["error"] = str(e.data)
    logging.warning(f"😞 Could not find a match: {ctx['error']}")


def log_game_start(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    logging.info(
        f"⚔️ Game has started! Match ID: {ctx['match_id']}. Good luck!"
    )


def log_game_result(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    # This action is reused by multiple states
    state_id = list(i.current_state_ids)[0]
    if "victory" in state_id:
        result = "VICTORY"
        emoji = "🏆"
    elif "defeat" in state_id:
        result = "DEFEAT"
        emoji = "💔"
    else:
        result = "DRAW"
        emoji = "⏳"
    logging.info(f"{emoji} Game over! Result: {result}")


# --- Services ---


async def find_match_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    game_mode = ctx.get("game_mode")
    logging.info(
        f"  -> 📡 Invoking service: Searching for '{game_mode}' match..."
    )

    search_time = random.uniform(2.0, 4.0)
    await asyncio.sleep(search_time)

    if random.random() < 0.25:  # 25% chance of failure
        raise TimeoutError("No suitable opponents found in time.")

    return {
        "match_id": f"match_{random.randint(1000, 9999)}",
        "opponent": f"Player_{random.randint(100, 999)}",
    }
