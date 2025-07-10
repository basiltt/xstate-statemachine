# -------------------------------------------------------------------------------
# 🔐 Auth Flow Logic
# examples/async/intermediate/functional_approach/with_logic_loader/auth_flow/auth_flow_logic.py
# -------------------------------------------------------------------------------
"""
Functional logic for the async authentication flow demonstration.

Includes actions to cache credentials, handle success/failure, and a service
to simulate credential validation.
"""

import asyncio
import logging
from typing import Any, Dict

from src.xstate_statemachine import ActionDefinition, Event, Interpreter

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def cache_credentials(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔒 Cache incoming credentials for authentication.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event carrying `payload`.
        action_def: Metadata about this action.
    """
    context["credentials_to_try"] = event.payload
    user = event.payload.get("username")
    logger.info(f"📋 Caching credentials for user '{user}'")


def assign_user_to_context(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """✅ Store authenticated user info into context.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The DoneEvent carrying user data.
        action_def: Metadata about this action.
    """
    context["username"] = event.data.get("username")
    context["error"] = None
    context["credentials_to_try"] = None
    logger.info(f"🔑 User '{context['username']}' authenticated successfully.")


def assign_error_to_context(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,  # noqa
) -> None:
    """⚠️ Store authentication error into context.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The DoneEvent carrying error data.
        action_def: Metadata about this action.
    """
    context["error"] = str(event.data)
    context["credentials_to_try"] = None
    logger.warning(f"🛡️ Authentication failed: {context['error']}")


def clear_context(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
    action_def: ActionDefinition,  # noqa
) -> None:
    """🔄 Clear all authentication-related context on logout.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event.
        action_def: Metadata about this action.
    """
    user = context.get("username")
    logger.info(f"User '{user}' logged out.")
    context["username"] = None
    context["error"] = None
    context["credentials_to_try"] = None


async def authenticate_user(
    interpreter: Interpreter,  # noqa
    context: Dict[str, Any],
    event: Event,  # noqa
) -> Dict[str, Any]:
    """🔐 Async service to validate cached credentials.

    Args:
        interpreter: The state machine interpreter.
        context: Mutable context dictionary.
        event: The triggering Event.

    Returns:
        A dict with authenticated user details.

    Raises:
        PermissionError: If credentials are invalid.
    """
    creds = context.get("credentials_to_try", {})
    username = creds.get("username")
    password = creds.get("password")
    logger.info(f"🔐 Authenticating '{username}'...")
    await asyncio.sleep(1.0)
    if username == "admin" and password == "password123":
        return {"username": "admin", "role": "administrator"}
    raise PermissionError("Invalid credentials provided.")
