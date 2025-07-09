# examples/async/complex/functional_approach/without_logic_loader/online_quiz_runner.py
# -----------------------------------------------------------------------------
# 📚 Complex Example: Online Quiz (Functional / Explicit Logic)
# -----------------------------------------------------------------------------
#
# Key Concepts Illustrated:
#   - A multi-stage async process with two distinct `invoke` calls.
#   - `after` for enforcing a time limit.
#   - Explicit Logic Binding for all standalone `async` and `sync` functions.
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

# --- Logger Configuration ---
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


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
        "\n--- 📚 Async Online Quiz Simulation (Functional / Explicit Logic) ---"
    )

    with open("online_quiz.json", "r") as f:
        config = json.load(f)

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

    # --- Scenario 1: Successful Completion ---
    print("\n--- Scenario 1: User completes quiz in time ---")
    interpreter1 = await Interpreter(machine).start()
    await interpreter1.send("START_QUIZ", quiz_id="python_basics")

    if await wait_for_state(interpreter1, "onlineQuiz.in_progress"):
        await interpreter1.send("ANSWER_QUESTION", question_id=1, answer="4")
        await interpreter1.send(
            "ANSWER_QUESTION", question_id=2, answer="Wrong Answer"
        )
        await asyncio.sleep(1)
        await interpreter1.send("SUBMIT_QUIZ")

        await wait_for_state(interpreter1, "onlineQuiz.finished", timeout=3.0)
        logging.info(f"Final context for Scenario 1: {interpreter1.context}")

    await interpreter1.stop()

    # --- Scenario 2: User times out ---
    print("\n--- Scenario 2: User runs out of time ---")
    interpreter2 = await Interpreter(machine).start()
    await interpreter2.send("START_QUIZ", quiz_id="python_basics")

    if await wait_for_state(interpreter2, "onlineQuiz.in_progress"):
        await interpreter2.send("ANSWER_QUESTION", question_id=1, answer="4")
        logging.info("...user is thinking and time runs out...")
        # Wait for the 8-second 'after' timer to fire + grading service
        await asyncio.sleep(10.5)
        logging.info(f"Final context for Scenario 2: {interpreter2.context}")

    await interpreter2.stop()

    print("\n--- ✅ All Simulations Complete ---")


if __name__ == "__main__":
    # ✅ FIX: Use asyncio.run() to execute the async main function
    asyncio.run(main())
