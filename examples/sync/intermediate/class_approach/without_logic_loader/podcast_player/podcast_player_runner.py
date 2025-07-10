# examples/sync/intermediate/class_approach/without_logic_loader/podcast_player_runner.py
# -----------------------------------------------------------------------------
# 🎧 Intermediate Example: Podcast Player (Explicit Logic)
# -----------------------------------------------------------------------------
"""
Runner for a synchronous podcast player state machine.

Key Concepts:
  • SyncInterpreter for blocking execution.
  • Explicit MachineLogic binding of actions and services.
  • Error handling in sync service.
"""

import json
import logging
import os
import time
from typing import Any, Dict

from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    Event,
    ActionDefinition,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class PodcastPlayer:
    """Encapsulates logic and interpreter for a podcast player state machine."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize PodcastPlayer with explicit MachineLogic binding.

        Args:
            config: The JSON-loaded state machine configuration.
        """
        logic = MachineLogic(
            actions={
                "set_episode_details": self.set_episode_details,
                "set_error": self.set_error,
                "clear_error": self.clear_error,
                "reset_playback": self.reset_playback,
            },
            services={"load_episode_data": self.load_episode_data},
        )
        machine = create_machine(config, logic=logic)
        self.interpreter = SyncInterpreter(machine)

    def set_episode_details(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🎧 Action: Store loaded episode details in context."""
        context["currentEpisode"] = event.data
        title = event.data.get("title")
        logger.info(f"🎧 Loaded episode: '{title}'")

    def set_error(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🚨 Action: Record error from failed service."""
        context["error"] = str(event.data)
        logger.warning(f"🚨 Error: {context['error']}")

    def clear_error(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """🧹 Action: Clear existing error in context."""
        context["error"] = None

    def reset_playback(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],
        event: Event,  # noqa
        action_def: ActionDefinition,  # noqa
    ) -> None:
        """⏹️ Action: Reset playback position and clear episode."""
        context["currentEpisode"] = None
        context["playbackPosition"] = 0
        logger.info("⏹️ Playback stopped and reset.")

    def load_episode_data(  # noqa
        self,
        interpreter: SyncInterpreter,  # noqa
        context: Dict[str, Any],  # noqa
        event: Event,
    ) -> Dict[str, Any]:
        """⚙️ Service: Simulate synchronous loading of episode metadata.

        Args:
            interpreter: The running SyncInterpreter.
            context: Mutable context dictionary.
            event: Event carrying payload {'episodeId': str}.

        Returns:
            A dict with episode details.

        Raises:
            ValueError: If the episode is not found.
        """
        episode_id = event.payload.get("episodeId")
        logger.info(f"⚙️ Loading episode '{episode_id}'...")
        time.sleep(1)

        if episode_id == "ep123":
            return {"id": "ep123", "title": "The Art of State Machines"}
        raise ValueError("Episode not found")

    def run_simulation(self) -> None:
        """🚀 Execute a predefined podcast player simulation."""
        print("\n--- 🎧 Podcast Player Simulation ---")
        self.interpreter.start()
        logger.info(f"Initial State: {self.interpreter.current_state_ids}")

        time.sleep(1)  # Simulate initial delay

        print("\n--- Scenario 1: Load missing episode ---")
        self.interpreter.send("LOAD_EPISODE", episodeId="ep999")
        logger.info(f"State: {self.interpreter.current_state_ids}")
        logger.info(f"Context: {self.interpreter.context}\n")

        time.sleep(1)  # Simulate delay for error handling

        print("--- Scenario 2: Load and play episode ---")
        self.interpreter.send("LOAD_EPISODE", episodeId="ep123")
        logger.info(f"State: {self.interpreter.current_state_ids}")
        self.interpreter.send("PLAY")
        logger.info(f"State after PLAY: {self.interpreter.current_state_ids}")

        time.sleep(2)  # Simulate playback time

        print("\n--- Scenario 3: Pause and stop ---")
        self.interpreter.send("PAUSE")
        logger.info(f"State after PAUSE: {self.interpreter.current_state_ids}")
        self.interpreter.send("STOP")
        logger.info(f"Final State: {self.interpreter.current_state_ids}")
        logger.info(f"Final Context: {self.interpreter.context}")

        time.sleep(1)  # Simulate final delay

        self.interpreter.stop()


def main() -> None:
    """Load configuration and run the podcast player simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "podcast_player.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config: Dict[str, Any] = json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Config not found: '{config_path}'")
        return

    player = PodcastPlayer(config)
    player.run_simulation()


if __name__ == "__main__":
    main()
