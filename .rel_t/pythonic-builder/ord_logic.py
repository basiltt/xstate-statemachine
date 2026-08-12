"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    ord.json
Template:  pythonic-builder
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template ord.json --template pythonic-builder

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""

import logging
from typing import Any, Dict

from xstate_statemachine import MachineBuilder, SyncInterpreter, action, guard, service

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------

@action
def log_cart(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
    action_def: Any,
) -> None:
    """Execute the ``logCart`` action.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this action.
        action_def: Metadata about the action being executed.
    """
    logger.info("Executing action: logCart")
    try:
        # TODO: implement action logic
        pass
    except Exception:
        logger.exception("Action 'logCart' failed")
        raise

# -----------------------------------------------------------------------
# Guards
# -----------------------------------------------------------------------

@guard
def auto(
    context: Dict[str, Any],
    event: Any,
) -> bool:
    """Evaluate the ``auto`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard: auto")
    # TODO: implement guard logic
    return True

@guard
def banned(
    context: Dict[str, Any],
    event: Any,
) -> bool:
    """Evaluate the ``banned`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard: banned")
    # TODO: implement guard logic
    return True

@guard
def ok(
    context: Dict[str, Any],
    event: Any,
) -> bool:
    """Evaluate the ``ok`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard: ok")
    # TODO: implement guard logic
    return True

@guard
def retry(
    context: Dict[str, Any],
    event: Any,
) -> bool:
    """Evaluate the ``retry`` guard.

    Args:
        context: Current machine context dictionary.
        event: The event being evaluated.
    """
    logger.info("Evaluating guard: retry")
    # TODO: implement guard logic
    return True

# -----------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------

@service
def charge(
    interpreter: SyncInterpreter[Dict[str, Any], Any],
    context: Dict[str, Any],
    event: Any,
) -> Dict[str, Any]:
    """Run the ``charge`` service.

    Args:
        interpreter: The running interpreter instance.
        context: Mutable machine context dictionary.
        event: The event that triggered this service.
    """
    logger.info("Running service: charge")
    try:
        # TODO: implement service logic
        return {"result": "done"}
    except Exception:
        logger.exception("Service 'charge' failed")
        raise


def build() -> Any:
    """Build the ord machine (builder style)."""
    builder = MachineBuilder('ord')
    builder.context({'n': 0})
    builder.root(on={'CANCEL': 'cancelled'})
    builder.state('cart', initial=True, entry=['logCart'], on={'GO': {'target': 'work', 'guard': {'type': 'and', 'params': {'guards': ['ok', {'type': 'not', 'params': {'guards': ['banned']}}]}}}})
    builder.state('work', parallel=True, on_done='done')
    builder.child_states('work', states={'pay': {'initial': 'p', 'states': {'p': {'after': {5000: 'f', 'BACKOFF': {'target': 'p', 'guard': 'retry'}}, 'invoke': {'src': 'charge', 'onDone': 'd', 'onError': 'f'}}, 'd': {'type': 'final'}, 'f': {'tags': ['err']}}}, 'ship': {'initial': 's', 'states': {'s': {'always': [{'target': 't', 'guard': 'auto'}]}, 't': {'type': 'final'}}}}, parallel=True)
    builder.state('hist', history='deep')
    builder.state('done', final=True, meta={'ok': True})
    builder.state('cancelled', final=True)
    builder.action("logCart", log_cart)
    builder.guard("auto", auto)
    builder.guard("banned", banned)
    builder.guard("ok", ok)
    builder.guard("retry", retry)
    builder.service("charge", charge)
    return builder.build()
