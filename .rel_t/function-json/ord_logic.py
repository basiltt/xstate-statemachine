"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    ord.json
Template:  function-json
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template ord.json --template function-json

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""

import asyncio
import logging
from typing import Any, Dict, Union

from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------

async def log_cart(
    interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
    context: Dict[str, Any],
    event: Event,
    action_def: ActionDefinition,
) -> None:
    """
    Execute the ``logCart`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    try:
        logger.info("Executing action logCart")
        # TODO: implement
    except Exception:
        logger.exception("Action 'logCart' failed")
        raise

# -----------------------------------------------------------------------
# Guards
# -----------------------------------------------------------------------

def auto(
    context: Dict[str, Any],
    event: Event,
) -> bool:
    """
    Evaluate the ``auto`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard auto")
    # TODO: implement guard logic
    return True

def banned(
    context: Dict[str, Any],
    event: Event,
) -> bool:
    """
    Evaluate the ``banned`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard banned")
    # TODO: implement guard logic
    return True

def ok(
    context: Dict[str, Any],
    event: Event,
) -> bool:
    """
    Evaluate the ``ok`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard ok")
    # TODO: implement guard logic
    return True

def retry(
    context: Dict[str, Any],
    event: Event,
) -> bool:
    """
    Evaluate the ``retry`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard retry")
    # TODO: implement guard logic
    return True

# -----------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------

async def charge(
    interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
    context: Dict[str, Any],
    event: Event,
) -> Dict[str, Any]:
    """
    Run the ``charge`` service.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this service.
    """
    try:
        logger.info("Running service charge")
        await asyncio.sleep(1)
        # TODO: implement service
        return {'result': 'done'}
    except Exception:
        logger.exception("Service 'charge' failed")
        raise
