# examples/sync/basic/functional_approach/without_logic_loader/stopwatch_runner.py
# -----------------------------------------------------------------------------
# ⏱️ Stopwatch Runner (Functional without LogicLoader)
# -----------------------------------------------------------------------------
"""
Main script for synchronous stopwatch state machine with explicit logic binding.
"""

import json
import logging
import os
import sys
import time
from typing import Any, Dict

# 🛠️ Ensure project root on PYTHONPATH
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

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def record_time_action(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """⏱️ Record elapsed time in context."""
    context["elapsedTime"] = int(
        time.time() - context.get("startTime", time.time())
    )
    logger.info(f"⏱️ Time stopped at {context['elapsedTime']}s")


def reset_time_action(
    interpreter: SyncInterpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔄 Reset the stopwatch timer."""
    context["elapsedTime"] = 0
    logger.info("🔄 Timer reset to zero")


def main() -> None:
    """🚀 Execute the stopwatch simulation."""
    print("\n--- ⏱️ Synchronous Stopwatch Simulation ---")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "stopwatch.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    logic = MachineLogic(
        actions={
            "record_time": record_time_action,
            "reset_time": reset_time_action,
        }
    )
    machine = create_machine(config, logic=logic)
    interpreter = SyncInterpreter(machine)

    interpreter.start()
    logger.info(f"Initial State: {interpreter.current_state_ids}")

    print("\n--- START ---")
    interpreter.context["startTime"] = time.time()
    interpreter.send("START")
    logger.info(f"State: {interpreter.current_state_ids}")

    print("\n--- WAIT 3s ---")
    time.sleep(3)

    print("\n--- STOP ---")
    interpreter.send("STOP")
    logger.info(f"Context: {interpreter.context}")

    print("\n--- RESET ---")
    interpreter.send("RESET")
    logger.info(f"Context: {interpreter.context}")

    interpreter.stop()
    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
