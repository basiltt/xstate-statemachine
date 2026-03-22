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
import inspect
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
    ) -> "Transition":
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
        return Transition(
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
    ) -> "Transition":
        """Create an internal transition (no state change).

        Args:
            event: The event name.
            guard: Optional guard function name.
            actions: Optional list of action names.

        Returns:
            A ``Transition`` object with ``internal=True``.
        """
        return Transition(
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


# -------------------------------------------------------------------------
# 🔀 Transition & TransitionGroup
# -------------------------------------------------------------------------


class Transition:
    """A transition between two states, triggered by an event.

    Created by ``State.to()`` or the ``transition()`` function.
    Not typically instantiated directly by users.

    Attributes:
        source: The source ``State``.
        target: The target ``State`` (``None`` for internal
            transitions).
        event: The event name that triggers this transition.
        guard: Optional guard function name.
        actions: List of action names to execute.
        reenter: Whether to force exit/re-entry on
            self-transitions.
        internal: Whether this is an internal transition.
    """

    def __init__(
        self,
        source: State,
        target: Optional[State],
        event: str,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
        reenter: bool = False,
        internal: bool = False,
    ) -> None:
        self.source = source
        self.target = target
        self.event = event
        self.guard = guard
        self.actions = actions or []
        self.reenter = reenter
        self.internal = internal

    def __or__(
        self, other: "Union[Transition, TransitionGroup]"
    ) -> "TransitionGroup":
        """Combine transitions with the ``|`` operator."""
        if isinstance(other, TransitionGroup):
            return TransitionGroup([self] + other.transitions)
        return TransitionGroup([self, other])


class TransitionGroup:
    """A collection of ``Transition`` objects, created by ``|``.

    Users never instantiate this directly. It is created
    implicitly when combining transitions with ``|``.

    Attributes:
        transitions: The list of ``Transition`` objects in this
            group.
    """

    def __init__(self, transitions: List[Transition]) -> None:
        self.transitions = transitions

    def __or__(
        self, other: "Union[Transition, TransitionGroup]"
    ) -> "TransitionGroup":
        """Combine with another transition or group."""
        if isinstance(other, TransitionGroup):
            return TransitionGroup(self.transitions + other.transitions)
        return TransitionGroup(self.transitions + [other])


def transition(
    source: State,
    event: str,
    target: State,
    *,
    guard: Optional[str] = None,
    actions: Optional[List[str]] = None,
    reenter: bool = False,
    internal: bool = False,
) -> Transition:
    """Create a transition between two states (functional API).

    Equivalent to ``source.to(target, event=event, ...)``.

    Args:
        source: The source ``State``.
        event: The event name (required).
        target: The target ``State``.
        guard: Optional guard function name.
        actions: Optional list of action names.
        reenter: Whether to force exit/re-entry.
        internal: Whether this is an internal transition.

    Returns:
        A ``Transition`` object.
    """
    return Transition(
        source=source,
        target=target,
        event=event,
        guard=guard,
        actions=actions or [],
        reenter=reenter,
        internal=internal,
    )


# -------------------------------------------------------------------------
# 🏷️ Decorators
# -------------------------------------------------------------------------


def action(fn_or_name=None):
    """Decorator to mark a function as a state machine action.

    Can be used with or without arguments:
        - ``@action`` — auto-generates name from function name
        - ``@action("customName")`` — uses explicit name

    Args:
        fn_or_name: Either the function (when used as
            ``@action``) or a string name (when used as
            ``@action("name")``).

    Returns:
        The decorated function with ``_xsm_type`` and
        ``_xsm_name`` attributes set.
    """
    if callable(fn_or_name):
        # 📝 Used as @action (no parentheses)
        fn = fn_or_name
        fn._xsm_type = "action"
        fn._xsm_name = _snake_to_camel(fn.__name__)
        return fn
    else:
        # 📝 Used as @action("customName")
        name = fn_or_name

        def decorator(fn):
            fn._xsm_type = "action"
            fn._xsm_name = name
            return fn

        return decorator


def guard(fn_or_name=None):
    """Decorator to mark a function as a state machine guard.

    Guards MUST be synchronous. Async guards raise
    ``NotSupportedError``.

    Can be used with or without arguments:
        - ``@guard`` — auto-generates name from function name
        - ``@guard("customName")`` — uses explicit name

    Args:
        fn_or_name: Either the function or a string name.

    Returns:
        The decorated function with ``_xsm_type`` and
        ``_xsm_name`` attributes set.

    Raises:
        NotSupportedError: If the function is async.
    """
    if callable(fn_or_name):
        fn = fn_or_name
        if inspect.iscoroutinefunction(fn):
            raise NotSupportedError(
                f"Guard '{fn.__name__}' must be synchronous "
                f"(guards cannot be async)"
            )
        fn._xsm_type = "guard"
        fn._xsm_name = _snake_to_camel(fn.__name__)
        return fn
    else:
        name = fn_or_name

        def decorator(fn):
            if inspect.iscoroutinefunction(fn):
                raise NotSupportedError(
                    f"Guard '{fn.__name__}' must be "
                    f"synchronous (guards cannot be async)"
                )
            fn._xsm_type = "guard"
            fn._xsm_name = name
            return fn

        return decorator


def service(fn_or_name=None):
    """Decorator to mark a function as a state machine service.

    Services can be sync or async.

    Can be used with or without arguments:
        - ``@service`` — auto-generates name from function name
        - ``@service("customName")`` — uses explicit name

    Args:
        fn_or_name: Either the function or a string name.

    Returns:
        The decorated function with ``_xsm_type`` and
        ``_xsm_name`` attributes set.
    """
    if callable(fn_or_name):
        fn = fn_or_name
        fn._xsm_type = "service"
        fn._xsm_name = _snake_to_camel(fn.__name__)
        return fn
    else:
        name = fn_or_name

        def decorator(fn):
            fn._xsm_type = "service"
            fn._xsm_name = name
            return fn

        return decorator
