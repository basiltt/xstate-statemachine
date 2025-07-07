"""
examples/drone_machine.py
-------
A simple simulation of a drone's flight using the XState machine library.

This script demonstrates fundamental state machine concepts:
initial states, event-driven transitions, timed transitions ('after'),
and the execution of actions.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------


import asyncio
import logging
from typing import Any, Dict

from src.xstate_machine import Interpreter, MachineLogic, create_machine, Event

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
# Configure logging for the entire application to display INFO level messages and above.
logging.basicConfig(
    level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s"
)
# Get a logger instance for this specific module
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Machine Configurations
# -----------------------------------------------------------------------------


def get_drone_config() -> Dict[str, Any]:
    """
    Returns the configuration dictionary for the drone state machine.

    This configuration defines the states, transitions, and initial context
    for managing a drone's flight lifecycle.

    Returns:
        Dict[str, Any]: The configuration for the drone machine.
    """
    return {
        "id": "drone",
        "initial": "idle",
        "context": {"battery": 100},  # 🔋 Initial battery level
        "states": {
            "idle": {
                "on": {"TAKEOFF": "flying"}
            },  # 🚀 Drone takes off from idle
            "flying": {
                # ⏱️ After 5 seconds in 'flying' state, transition to 'landing'
                "after": {
                    "5000": {
                        "target": "landing",
                        "actions": [
                            "logLowBattery"
                        ],  # 🗣️ Log low battery warning
                    }
                },
                "on": {"LAND": "landing"},  # ⬇️ Manual land command
            },
            "landing": {"type": "final"},  # 🎉 Final state after landing
        },
    }


# -----------------------------------------------------------------------------
# Machine Logic (Actions, Services, Guards)
# -----------------------------------------------------------------------------


class DroneLogic(MachineLogic):
    """
    Encapsulates all custom logic (actions, guards, services) for the drone state machine.

    This class centralizes the behavioral aspects of the state machine, adhering to
    the principle of separation of concerns.
    """

    def __init__(self):
        """Initializes the DroneLogic with necessary components."""
        super().__init__()
        self._setup_actions()
        # No guards or services for this simple example, but they would be set up here.

    def _setup_actions(self) -> None:
        """
        Defines and sets up all action functions used by the state machine.

        Actions are side effects performed during state transitions or on entry/exit of states.
        Each action receives the interpreter, context, event, and action definition.
        """
        self.actions = {
            "logLowBattery": self._log_low_battery,
        }

    # --- Actions ---

    def _log_low_battery(
        self,
        interpreter: Interpreter,
        ctx: Dict[str, Any],
        evt: Event,
        action_def: Any,
    ) -> None:
        """
        Action: Logs a low battery warning message.

        This action is triggered when the drone automatically transitions to 'landing'
        due to the 'after' (timeout) condition in the 'flying' state.

        Args:
            interpreter (Interpreter): The state machine interpreter.
            ctx (Dict[str, Any]): The current state machine context.
            evt (Event): The event that triggered this action (e.g., a timeout event).
            action_def (Any): The action definition (unused here, but required by signature).
        """
        battery_level = ctx.get("battery", "unknown")
        logger.warning(
            f"🔋 Low battery ({battery_level}%). Returning to land."
        )


# -----------------------------------------------------------------------------
# Main Simulation
# -----------------------------------------------------------------------------


async def main() -> None:
    """
    Runs a simulation of a drone's flight cycle using a state machine.

    This function demonstrates basic state transitions, timed transitions ('after'),
    and the execution of actions within the state machine context.
    """
    logger.info("🎬 --- Drone Flight Simulation --- 🎬\n")

    # 📦 Get machine configuration
    drone_config = get_drone_config()

    # 🧠 Create the logic instance for the drone machine
    drone_logic = DroneLogic()

    # 🏭 Create the drone state machine
    machine = create_machine(drone_config, drone_logic)

    # 🚀 Create and start the interpreter
    interpreter = Interpreter(machine)
    await interpreter.start()
    logger.info(f"Initial State: {interpreter.current_state_ids}")

    # Simulate drone takeoff
    logger.info("➡️ Sending TAKEOFF event...")
    await interpreter.send("TAKEOFF")

    # Wait for the machine to enter the 'flying' state before printing
    await asyncio.sleep(0.1)  # ⏱️ Short delay to allow state transition
    logger.info(f"Current State: {interpreter.current_state_ids}")

    # The 'after' transition in the 'flying' state will automatically trigger
    # the 'landing' state after 5 seconds. We wait a bit longer to ensure it happens.
    logger.info(
        "⏳ Waiting for automatic landing due to low battery (simulated after 5 seconds)..."
    )
    await asyncio.sleep(6)  # ⏱️ Wait 5s for 'after' + 1s buffer
    logger.info(f"Final State: {interpreter.current_state_ids}")

    # 🛑 Stop the interpreter
    await interpreter.stop()
    logger.info("Interpreter stopped.")


if __name__ == "__main__":
    asyncio.run(main())
