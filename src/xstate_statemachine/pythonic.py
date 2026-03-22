# src/xstate_statemachine/pythonic.py
"""
🐍 Pythonic API for xstate-statemachine.

This module provides three API styles for defining state machines
in pure Python, without writing JSON config dicts:

1. **Class-based** — ``StateMachine`` base class with metaclass
2. **Builder** — ``MachineBuilder`` fluent API
3. **Functional** — ``build_machine()`` with module-level helpers

All three styles compile to the same JSON config dict +
``MachineLogic`` pair and delegate to the existing
``create_machine()`` factory.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import functools
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .exceptions import InvalidConfigError, NotSupportedError
from .factory import create_machine as _original_create_machine
from .machine_logic import MachineLogic

# -------------------------------------------------------------------------
# 🛠️ Internal Helpers
# -------------------------------------------------------------------------


def _snake_to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase.

    Matches the behavior of ``LogicLoader._snake_to_camel`` in
    ``logic_loader.py`` so that function names auto-map
    consistently.

    Args:
        snake_str: A snake_case string
            (e.g., ``"my_action_name"``).

    Returns:
        The camelCase equivalent
            (e.g., ``"myActionName"``).
    """
    components = snake_str.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


# -------------------------------------------------------------------------
# 🏗️ State
# -------------------------------------------------------------------------


class State:
    """A state definition for use in all three Pythonic API styles.

    Args:
        name: State name. Auto-inferred from the class attribute
            name in ``StateMachine`` subclasses if left empty.
        initial: Whether this is the initial state among its
            siblings.
        final: Whether this is a final (terminal) state.
        parallel: Whether this is a parallel state.
        on: Event-to-target shorthand dict,
            e.g. ``{"CLICK": "active"}``.
        entry: List of entry action names.
        exit: List of exit action names.
        after: Delayed transition dict,
            e.g. ``{1000: "timeout"}``.
        invoke: Service invocation config (dict or list of
            dicts).
        on_done: Completion transition (string target or dict).
        always: Eventless transition config.
        context: Initial context dict (only meaningful at root
            level).
        states: List of child ``State`` objects for hierarchy.

    Raises:
        InvalidConfigError: If ``final`` and ``parallel`` are
            both True.
    """

    def __init__(
        self,
        name: str = "",
        *,
        initial: bool = False,
        final: bool = False,
        parallel: bool = False,
        on: Optional[Dict[str, Any]] = None,
        entry: Optional[List[str]] = None,
        exit: Optional[List[str]] = None,
        after: Optional[Dict[int, Any]] = None,
        invoke: Optional[Union[Dict, List]] = None,
        on_done: Optional[Union[str, Dict]] = None,
        always: Optional[Union[str, Dict, List]] = None,
        context: Optional[Dict] = None,
        states: Optional[List["State"]] = None,
    ) -> None:
        if final and parallel:
            raise InvalidConfigError(
                f"State '{name}' cannot be both final " f"and parallel"
            )
        self.name = name
        self.initial = initial
        self.final = final
        self.parallel = parallel
        self.on = on
        self.entry = entry or []
        self.exit = exit or []
        self.after = after
        self.invoke = invoke
        self.on_done = on_done
        self.always = always
        self.context = context
        self.states = states or []
        # 📝 Internal: tracks functions registered via decorators
        self._enter_decorators: List[Callable] = []
        self._exit_decorators: List[Callable] = []

    def __init_subclass__(
        cls,
        *,
        initial: bool = False,
        final: bool = False,
        parallel: bool = False,
        **kwargs: Any,
    ) -> None:
        """Support ``class MyState(State, parallel=True):``."""
        super().__init_subclass__(**kwargs)
        cls._xsm_initial = initial
        cls._xsm_final = final
        cls._xsm_parallel = parallel

    def to(
        self,
        target: "State",
        *,
        event: Optional[str] = None,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
        reenter: bool = False,
    ) -> "Transition":  # noqa: F821
        """Create a transition from this state to a target.

        Args:
            target: The destination ``State`` object.
            event: The event name that triggers this transition.
            guard: Optional guard function name.
            actions: Optional list of action names.
            reenter: Force exit/re-entry on self-transitions.

        Returns:
            A ``Transition`` object.

        Raises:
            InvalidConfigError: If ``event`` is not provided.
        """
        if event is None:
            raise InvalidConfigError(
                "State.to() requires an 'event' argument. "
                "For eventless transitions, use the 'always' "
                "parameter on State()"
            )
        return Transition(  # noqa: F821
            source=self,
            target=target,
            event=event,
            guard=guard,
            actions=actions or [],
            reenter=reenter,
            internal=False,
        )

    def internal(
        self,
        event: str,
        *,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
    ) -> "Transition":  # noqa: F821
        """Create an internal transition (no state change).

        Args:
            event: The event name.
            guard: Optional guard function name.
            actions: Optional list of action names.

        Returns:
            A ``Transition`` object with ``internal=True``.
        """
        return Transition(  # noqa: F821
            source=self,
            target=None,
            event=event,
            guard=guard,
            actions=actions or [],
            reenter=False,
            internal=True,
        )

    def enter(self, fn: Callable) -> Callable:
        """Decorator to register a function as an entry action.

        Only valid inside a ``StateMachine`` class definition.

        Args:
            fn: The function to register.

        Returns:
            The original function, with ``_xsm_type`` and
            ``_xsm_name`` markers attached.
        """
        name = _snake_to_camel(fn.__name__)
        fn._xsm_type = "action"
        fn._xsm_name = name
        fn._xsm_state_enter = self
        self._enter_decorators.append(fn)
        if name not in self.entry:
            self.entry.append(name)
        return fn

    def _exit_decorator(self, fn: Callable) -> Callable:
        """Decorator to register a function as an exit action.

        Only valid inside a ``StateMachine`` class definition.

        Args:
            fn: The function to register.

        Returns:
            The original function, with ``_xsm_type`` and
            ``_xsm_name`` markers attached.
        """
        name = _snake_to_camel(fn.__name__)
        fn._xsm_type = "action"
        fn._xsm_name = name
        fn._xsm_state_exit = self
        self._exit_decorators.append(fn)
        if name not in self.exit:
            self.exit.append(name)
        return fn
