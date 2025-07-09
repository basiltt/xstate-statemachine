# examples/async/complex/functional_approach/without_logic_loader/online_quiz/online_quiz_logic.py
import asyncio
import logging
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


# --- Actions ---
def set_quiz_id(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["quiz_id"] = e.payload.get("quiz_id")
    logging.info(f"📚 Starting quiz with ID: {ctx['quiz_id']}")


def store_quiz_data(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["questions"] = e.data.get("questions")
    logging.info(
        f"✅ Questions loaded successfully. Total: {len(ctx['questions'])}"
    )


def log_quiz_start(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    logging.info("⏱️  Quiz in progress! You have 8 seconds to complete it.")


def store_answer(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    q_id = e.payload.get("question_id")
    answer = e.payload.get("answer")
    ctx["user_answers"][q_id] = answer
    logging.info(f"  -> ✍️  Answered question {q_id} with '{answer}'")


def log_timeout(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    logging.warning("⏰ Time's up! Submitting answers automatically.")


def store_final_score(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["final_score"] = e.data
    logging.info(f"🎉 Quiz graded! Your score: {e.data.get('score')}%")


def set_error(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    ctx["error"] = str(e.data)
    logging.error(f"❌ An error occurred: {ctx['error']}")


# --- Services ---
async def load_quiz_data_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    quiz_id = ctx.get("quiz_id")
    logging.info(
        f"  -> ☁️  Invoking service: Fetching data for quiz '{quiz_id}'..."
    )
    await asyncio.sleep(1.5)

    if quiz_id == "python_basics":
        return {
            "questions": [
                {"id": 1, "text": "What is 2+2?", "correct": "4"},
                {
                    "id": 2,
                    "text": "What is the capital of France?",
                    "correct": "Paris",
                },
            ]
        }
    else:
        raise FileNotFoundError(f"Quiz with ID '{quiz_id}' not found.")


async def grade_quiz_service(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    logging.info("  -> 📝 Invoking service: Grading answers...")
    await asyncio.sleep(2.0)

    correct_answers = 0
    questions = ctx.get("questions", [])
    user_answers = ctx.get("user_answers", {})

    for question in questions:
        if user_answers.get(question["id"]) == question["correct"]:
            correct_answers += 1

    score = (correct_answers / len(questions)) * 100 if questions else 0
    return {"score": round(score, 2), "correct": correct_answers}
