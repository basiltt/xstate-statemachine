# -------------------------------------------------------------------------------
# ⚔️ Game Matchmaking Logic
# examples/async/complex/functional_approach/without_logic_loader/game_matchmaking/game_matchmaking_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for asynchronous game matchmaking and match lifecycle.
"""

import asyncio
import logging
import random
from typing import Any, Dict

from src.xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def set_player_info(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🤺 Record player info and desired game mode."""
    context["player_id"] = event.payload.get("player_id")
    context["game_mode"] = event.payload.get("game_mode", "casual")
    logger.info(
        f"🤺 Player {context['player_id']} searching for {context['game_mode']} match."
    )


def store_match_info(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🤝 Save match ID and opponent details."""
    context["match_id"] = event.data.get("match_id")
    opponent = event.data.get("opponent")
    logger.info(f"🤝 Match {context['match_id']} vs {opponent} found.")


def set_search_error(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """😞 Log match search failure."""
    context["error"] = str(event.data)
    logger.warning(f"😞 Matchmaking failed: {context['error']}")


def log_game_start(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """⚔️ Announce game start."""
    logger.info(f"⚔️ Game started (match {context['match_id']}). Good luck!")


def log_game_result(
    interpreter: Interpreter,
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🏆 Log final game outcome."""
    state = next(iter(interpreter.current_state_ids), "")
    if "victory" in state:
        emoji, result = "🏆", "VICTORY"
    elif "defeat" in state:
        emoji, result = "💔", "DEFEAT"
    else:
        emoji, result = "⏳", "DRAW"
    logger.info(f"{emoji} Game over: {result}")


async def find_match_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """📡 Async matchmaking service returns match details."""
    mode = context.get("game_mode", "casual")
    logger.info(f"📡 Searching for {mode} match...")
    await asyncio.sleep(random.uniform(2.0, 4.0))
    if random.random() < 0.25:
        raise TimeoutError("No opponents found.")
    return {
        "match_id": f"match_{random.randint(1000, 9999)}",
        "opponent": f"Player_{random.randint(100, 999)}",
    }
