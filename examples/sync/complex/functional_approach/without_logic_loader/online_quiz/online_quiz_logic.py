# -----------------------------------------------------------------------------
# 📚 Online Quiz Logic
# examples/async/complex/functional_approach/without_logic_loader/online_quiz/online_quiz_logic.py
# -----------------------------------------------------------------------------
"""
Functional logic for an async online quiz:

  • set_quiz_id         – action on START_QUIZ
  • store_quiz_data     – onDone of load_quiz_data_service
  • log_quiz_start      – entry log for quiz
  • store_answer        – record each answer
  • store_final_score   – onDone of grade_quiz_service
  • log_timeout         – on after transition
  • set_error           – error handler
  • load_quiz_data_service – fetch questions
  • grade_quiz_service      – compute score
"""

import asyncio
import logging
from typing import Any, Dict

from xstate_statemachine import Interpreter, Event, ActionDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def set_quiz_id(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """📚 Store quiz ID in context to start loading data."""
    context["quiz_id"] = event.payload.get("quiz_id")
    context["user_answers"] = {}
    logger.info(f"📚 Starting quiz with ID: {context['quiz_id']}")


def store_quiz_data(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✅ Store loaded questions for the quiz."""
    context["questions"] = event.data.get("questions", [])
    logger.info(f"✅ Questions loaded. Total: {len(context['questions'])}")


def log_quiz_start(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """⏱️ Log that quiz has begun with a time limit."""
    logger.info("⏱️ Quiz in progress! You have 8 seconds to complete it.")


def store_answer(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✍️ Record an answer for a given question ID."""
    q_id = event.payload.get("question_id")
    answer = event.payload.get("answer")
    context["user_answers"][q_id] = answer
    logger.info(f"✍️ Answered question {q_id} with '{answer}'")


def log_timeout(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],  # noqa
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """⌛ Log when the quiz time limit has been reached."""
    logger.warning("⌛ Time's up! Submitting answers automatically.")


def store_final_score(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🏆 Store the final quiz score after grading."""
    context["final_score"] = event.data
    logger.info(f"🏆 Quiz graded! Your score: {event.data.get('score')}%")


def set_error(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """❌ Record any error encountered during quiz flow."""
    context["error"] = str(event.data)
    logger.error(f"❌ An error occurred: {context['error']}")


async def load_quiz_data_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """☁️ Async service: Fetch quiz questions based on quiz_id."""
    quiz_id = context.get("quiz_id")
    logger.info(f"☁️ Fetching questions for quiz '{quiz_id}'...")
    await asyncio.sleep(1.5)
    if quiz_id == "python_basics":
        return {
            "questions": [
                {"id": 1, "text": "What is 2+2?", "correct": "4"},
                {"id": 2, "text": "Capital of France?", "correct": "Paris"},
            ]
        }
    raise FileNotFoundError(f"Quiz '{quiz_id}' not found.")


async def grade_quiz_service(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """📝 Async service: Grade user answers and compute score."""
    questions = context.get("questions", [])
    user_answers = context.get("user_answers", {})
    correct = sum(
        1 for q in questions if user_answers.get(q["id"]) == q["correct"]
    )
    score = round((correct / len(questions)) * 100 if questions else 0.0, 2)
    await asyncio.sleep(2.0)
    return {"score": score, "correct": correct}
