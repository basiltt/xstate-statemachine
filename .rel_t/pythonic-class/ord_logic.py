"""Generated state machine logic — DO NOT EDIT BY HAND.

Source:    ord.json
Template:  pythonic-class
Generator: xstate-statemachine 0.7.0

Regenerate with::

    xsm generate-template ord.json --template pythonic-class

Implement your logic in the stubs below; the machine structure
above is derived from the source JSON and will be overwritten.
"""

import logging
from typing import Any, Dict, Union

from xstate_statemachine import (
    Interpreter,
    State,
    StateMachine,
    SyncInterpreter,
    action,
    guard,
    service,
)

logger = logging.getLogger(__name__)


# 🧩 Nested states are bound at module level and attached to their
#    parent via states=[...]. Declaring them as class attributes
#    would make the metaclass treat each as a top-level state.
work_pay_p = State('p', initial=True, after={5000: 'f', 'BACKOFF': {'target': 'p', 'guard': 'retry'}}, invoke={'src': 'charge', 'onDone': 'd', 'onError': 'f'})
work_pay_d = State('d', final=True)
work_pay_f = State('f', tags=['err'])
work_pay = State('pay', states=[work_pay_p, work_pay_d, work_pay_f])
work_ship_s = State('s', initial=True, always=[{'target': 't', 'guard': 'auto'}])
work_ship_t = State('t', final=True)
work_ship = State('ship', states=[work_ship_s, work_ship_t])

class OrdMachine(StateMachine):
    """Ord state machine using the declarative class-based API."""

    machine_id = 'ord'
    initial_context = {'n': 0}
    machine_root = State('', on={'CANCEL': 'cancelled'})

    cart = State('cart', initial=True, entry=['logCart'], on={'GO': {'target': 'work', 'guard': {'type': 'and', 'params': {'guards': ['ok', {'type': 'not', 'params': {'guards': ['banned']}}]}}}})
    work = State('work', parallel=True, on_done='done', states=[work_pay, work_ship])
    hist = State('hist', history='deep')
    done = State('done', final=True, meta={'ok': True})
    cancelled = State('cancelled', final=True)
    # Actions
    @action
    def log_cart(
            self,
            interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
            context: Dict[str, Any],
            event: Any,
            action_def: Any,
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
            logger.info("Executing action: logCart")
            # TODO: implement action logic
            pass
        except Exception:
            logger.exception("Action 'logCart' failed")
            raise

    # Guards
    @guard
    def auto(
            self,
            context: Dict[str, Any],
            event: Any,
    ) -> bool:
        """
        Evaluate the ``auto`` guard.

        Args:
            context: Current machine context dictionary.
            event: The event being evaluated.
        """
        logger.info("Evaluating guard: auto")
        # TODO: implement guard logic
        return True

    @guard
    def banned(
            self,
            context: Dict[str, Any],
            event: Any,
    ) -> bool:
        """
        Evaluate the ``banned`` guard.

        Args:
            context: Current machine context dictionary.
            event: The event being evaluated.
        """
        logger.info("Evaluating guard: banned")
        # TODO: implement guard logic
        return True

    @guard
    def ok(
            self,
            context: Dict[str, Any],
            event: Any,
    ) -> bool:
        """
        Evaluate the ``ok`` guard.

        Args:
            context: Current machine context dictionary.
            event: The event being evaluated.
        """
        logger.info("Evaluating guard: ok")
        # TODO: implement guard logic
        return True

    @guard
    def retry(
            self,
            context: Dict[str, Any],
            event: Any,
    ) -> bool:
        """
        Evaluate the ``retry`` guard.

        Args:
            context: Current machine context dictionary.
            event: The event being evaluated.
        """
        logger.info("Evaluating guard: retry")
        # TODO: implement guard logic
        return True

    # Services
    @service
    def charge(
            self,
            interpreter: Union[Interpreter[Any, Any], SyncInterpreter[Any, Any]],
            context: Dict[str, Any],
            event: Any,
    ) -> Dict[str, Any]:
        """
        Run the ``charge`` service.

        Args:
            interpreter: The running interpreter instance.
            context: Mutable machine context dictionary.
            event: The event that triggered this service.
        """
        try:
            logger.info("Running service: charge")
            # TODO: implement service logic
            return {"result": "done"}
        except Exception:
            logger.exception("Service 'charge' failed")
            raise
