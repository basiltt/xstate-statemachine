# examples/async/intermediate/functional_approach/with_logic_loader/auth_flow/auth_flow_logic.py
import asyncio
import logging
from typing import Dict, Any

from src.xstate_statemachine import Interpreter, Event, ActionDefinition


# --- Actions ---
def cache_credentials(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    # This action runs on the LOGIN transition
    ctx["credentials_to_try"] = e.payload
    logging.info(
        f"📋 Caching credentials for user '{e.payload.get('username')}'"
    )


def assign_user_to_context(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["username"] = e.data.get("username")
    ctx["error"] = None
    ctx["credentials_to_try"] = None  # Clean up
    logging.info(f"🔑 User '{ctx['username']}' authenticated successfully.")


def assign_error_to_context(
    i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition
):
    ctx["error"] = str(e.data)
    ctx["credentials_to_try"] = None  # Clean up
    logging.warning(f"🛡️ Authentication failed: {ctx['error']}")


def clear_context(i: Interpreter, ctx: Dict, e: Event, a: ActionDefinition):
    logging.info(f"User '{ctx['username']}' logged out.")
    ctx["username"] = None
    ctx["error"] = None
    ctx["credentials_to_try"] = None


# --- Services ---
async def authenticate_user(
    i: Interpreter, ctx: Dict, e: Event
) -> Dict[str, Any]:
    # The service now reads from the context
    credentials = ctx.get("credentials_to_try", {})
    username = credentials.get("username")
    password = credentials.get("password")

    logging.info(
        f"🔐 Invoking service: Authenticating '{username}' from context..."
    )
    await asyncio.sleep(1.0)  # Simulate call to auth service

    if username == "admin" and password == "password123":
        return {"username": "admin", "role": "administrator"}
    else:
        raise PermissionError("Invalid credentials provided.")
