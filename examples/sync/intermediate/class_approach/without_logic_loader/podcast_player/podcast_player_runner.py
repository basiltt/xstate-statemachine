# examples/sync/intermediate/class_approach/without_logic_loader/podcast_player_runner.py

# -----------------------------------------------------------------------------
# 🎧 Intermediate Example: Synchronous Podcast Player (Class-Based)
# -----------------------------------------------------------------------------
# This script simulates a simple podcast player.
#
# Key Concepts Illustrated:
#   - Synchronous Execution: Uses the `SyncInterpreter`.
#   - Class-Based Logic: The `PodcastPlayer` class encapsulates all logic.
#   - Explicit Logic Binding: A `MachineLogic` object is manually created
#     to map logic names from the JSON to the class's instance methods,
#     demonstrating the "without_logic_loader" approach.
#   - Sync Service with Error Handling: The `invoke` of `load_episode_data`
#     can succeed (`onDone`) or fail (`onError`).
# -----------------------------------------------------------------------------

import json
import logging
import os
import sys
import time
from typing import Any, Dict

# --- Path Setup ---
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from src.xstate_statemachine import (
    create_machine,
    SyncInterpreter,
    MachineLogic,
    Event,
    ActionDefinition,
)

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# -----------------------------------------------------------------------------
# 🏛️ PodcastPlayer Class
# -----------------------------------------------------------------------------
class PodcastPlayer:
    """Encapsulates the logic and interpreter for a podcast player."""

    def __init__(self, config: Dict[str, Any]):
        """Initializes the PodcastPlayer."""
        # 1. Manually create the MachineLogic object, binding names to methods.
        machine_logic = MachineLogic(
            actions={
                "set_episode_details": self.set_episode_details,
                "set_error": self.set_error,
                "clear_error": self.clear_error,
                "reset_playback": self.reset_playback,
            },
            services={"load_episode_data": self.load_episode_data},
        )

        # 2. Create the machine and interpreter with the explicit logic.
        machine = create_machine(config, logic=machine_logic)
        self.interpreter = SyncInterpreter(machine)

    # --- Actions ---
    def set_episode_details(self, i, ctx, e, ad):
        ctx["currentEpisode"] = e.data
        logging.info(f"🎧 Loaded: '{e.data.get('title')}'")

    def set_error(self, i, ctx, e, ad):
        ctx["error"] = str(e.data)
        logging.warning(f"🚨 Error: {ctx['error']}")

    def clear_error(self, i, ctx, e, ad):
        ctx["error"] = None

    def reset_playback(self, i, ctx, e, ad):
        ctx["currentEpisode"] = None
        ctx["playbackPosition"] = 0
        logging.info("⏹️ Playback stopped and reset.")

    # --- Services ---
    def load_episode_data(
        self, i: SyncInterpreter, ctx: Dict, e: Event
    ) -> Dict:
        """A synchronous service to simulate fetching episode metadata."""
        episode_id = e.payload.get("episodeId")
        logging.info(f"⚙️ Service: Loading data for episode '{episode_id}'...")
        time.sleep(1)  # Simulate blocking I/O

        if episode_id == "ep123":
            return {"id": "ep123", "title": "The Art of State Machines"}
        else:
            raise ValueError("Episode not found")

    def run_simulation(self):
        """Runs a predefined simulation of using the podcast player."""
        print("\n--- 🎧 Synchronous Podcast Player Simulation ---")
        self.interpreter.start()
        logging.info(f"Initial State: {self.interpreter.current_state_ids}")

        print("\n--- Scenario 1: Load a non-existent episode ---")
        self.interpreter.send("LOAD_EPISODE", episodeId="ep999")
        logging.info(
            f"State after failed load: {self.interpreter.current_state_ids}"
        )
        logging.info(f"Context: {self.interpreter.context}\n")

        print("--- Scenario 2: Load and play an existing episode ---")
        self.interpreter.send("LOAD_EPISODE", episodeId="ep123")
        logging.info(
            f"State after successful load: {self.interpreter.current_state_ids}"
        )

        self.interpreter.send("PLAY")
        logging.info(
            f"State after playing: {self.interpreter.current_state_ids}"
        )

        print("\n--- Scenario 3: Pause and Stop ---")
        self.interpreter.send("PAUSE")
        logging.info(
            f"State after pausing: {self.interpreter.current_state_ids}"
        )
        self.interpreter.send("STOP")
        logging.info(f"Final State: {self.interpreter.current_state_ids}")
        logging.info(f"Final Context: {self.interpreter.context}")

        self.interpreter.stop()
        print("\n--- ✅ Simulation Complete ---")


# -----------------------------------------------------------------------------
# 🚀 Main Execution
# -----------------------------------------------------------------------------
def main():
    """Loads config and runs the podcast player simulation."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "podcast_player.json")
    try:
        with open(json_path, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        logging.error(f"❌ Configuration file not found at '{json_path}'")
        return

    player = PodcastPlayer(config)
    player.run_simulation()


if __name__ == "__main__":
    main()
