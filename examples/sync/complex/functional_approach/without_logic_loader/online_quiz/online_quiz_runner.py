# -----------------------------------------------------------------------------
# 📚 Online Quiz Runner
# examples/async/complex/functional_approach/without_logic_loader/online_quiz/online_quiz_runner.py
# -----------------------------------------------------------------------------
"""
Runs the async online quiz simulation:

  • START_QUIZ → load_quiz_data_service → store_quiz_data
  • on entry → log_quiz_start
  • ANSWER_QUESTION → store_answer
  • after timeout → log_timeout
  • SUBMIT_QUIZ → grade_quiz_service → store_final_score
  • onError → set_error
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

from src.xstate_statemachine import create_machine, Interpreter, MachineLogic

# Ensure project root on path
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../..")),
)
from online_quiz_logic import (
    set_quiz_id,
    store_quiz_data,
    log_quiz_start,
    store_answer,
    log_timeout,
    store_final_score,
    set_error,
    load_quiz_data_service,
    grade_quiz_service,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def wait_for_state(
    interpreter: Interpreter, state_id: str, timeout: float = 5.0
) -> bool:
    """⏳ Poll until the interpreter enters state_id or timeout."""  # noqa
    start = asyncio.get_event_loop().time()  # noqa
    while True:
        if state_id in interpreter.current_state_ids:
            logger.info(f"--> Reached '{state_id}'")
            return True
        if asyncio.get_event_loop().time() - start > timeout:
            logger.error(f"--> Timeout waiting for '{state_id}'")
            return False
        await asyncio.sleep(0.1)


async def main() -> None:
    """🚀 Execute Quiz scenarios."""
    print("\n--- 📚 Async Online Quiz Simulation ---")
    config_path = "online_quiz.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config: Dict[str, Any] = json.load(f)

    machine_logic = MachineLogic(
        actions={
            "set_quiz_id": set_quiz_id,
            "store_quiz_data": store_quiz_data,
            "log_quiz_start": log_quiz_start,
            "store_answer": store_answer,
            "log_timeout": log_timeout,
            "store_final_score": store_final_score,
            "set_error": set_error,
        },
        services={
            "load_quiz_data_service": load_quiz_data_service,
            "grade_quiz_service": grade_quiz_service,
        },
    )
    machine = create_machine(config, logic=machine_logic)

    # Scenario 1: Complete in time
    print("\n--- Scenario 1: Complete in time ---")
    interp1 = await Interpreter(machine).start()
    await interp1.send("START_QUIZ", quiz_id="python_basics")
    if await wait_for_state(interp1, "onlineQuiz.in_progress"):
        await interp1.send("ANSWER_QUESTION", question_id=1, answer="4")
        await interp1.send("ANSWER_QUESTION", question_id=2, answer="Paris")
        await asyncio.sleep(1)
        await interp1.send("SUBMIT_QUIZ")
        await wait_for_state(interp1, "onlineQuiz.finished", timeout=3.0)
        logger.info(f"Context: {interp1.context}")
    await interp1.stop()

    # Scenario 2: Time out
    print("\n--- Scenario 2: Time out ---")
    interp2 = await Interpreter(machine).start()
    await interp2.send("START_QUIZ", quiz_id="python_basics")
    if await wait_for_state(interp2, "onlineQuiz.in_progress"):
        await interp2.send("ANSWER_QUESTION", question_id=1, answer="4")
        logger.info("...waiting for timeout...")
        await asyncio.sleep(10)
        logger.info(f"Context: {interp2.context}")
    await interp2.stop()

    print("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    asyncio.run(main())
