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
from .models import MachineNode

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


# -----------------------------------------------------------------
# ⚙️ Config Compiler
# -----------------------------------------------------------------


def _compile_state(
    state: State,
    all_states_by_name: Dict[str, State],
) -> Dict[str, Any]:
    """Compile a single State into a JSON config dict entry."""
    config: Dict[str, Any] = {}

    # 📝 Type
    if state.final:
        config["type"] = "final"
    elif state.parallel:
        config["type"] = "parallel"

    # 📝 Entry / Exit actions
    if state.entry:
        config["entry"] = (
            state.entry[0] if len(state.entry) == 1 else state.entry
        )
    if state.exit:
        config["exit"] = state.exit[0] if len(state.exit) == 1 else state.exit

    # 📝 On (event transitions from State.on dict)
    if state.on:
        config["on"] = dict(state.on)

    # 📝 Always → compiled to "on": {"": ...}
    if state.always is not None:
        if "on" not in config:
            config["on"] = {}
        config["on"][""] = state.always

    # 📝 After (delayed transitions)
    if state.after:
        config["after"] = state.after

    # 📝 Invoke (services)
    if state.invoke:
        config["invoke"] = state.invoke

    # 📝 onDone (completion transition)
    if state.on_done is not None:
        if isinstance(state.on_done, str):
            config["onDone"] = {"target": state.on_done}
        else:
            config["onDone"] = state.on_done

    # 📝 Child states (recurse)
    if state.states:
        child_configs = {}
        initial_child = None
        child_names: set = set()
        for child in state.states:
            if child.name in child_names:
                raise InvalidConfigError(
                    f"Duplicate state name "
                    f"'{child.name}' "
                    f"at the same level"
                )
            child_names.add(child.name)
            child_configs[child.name] = _compile_state(
                child, all_states_by_name
            )
            if child.initial:
                if initial_child is not None:
                    raise InvalidConfigError(
                        f"Multiple initial states: "
                        f"{initial_child}, "
                        f"{child.name}. "
                        f"Exactly one allowed"
                    )
                initial_child = child.name
        config["states"] = child_configs
        if not state.parallel and initial_child:
            config["initial"] = initial_child
        elif not state.parallel and not initial_child and state.states:
            raise InvalidConfigError(
                "No initial state defined. Exactly one "
                "state must have initial=True"
            )

    return config


def _compile_config(
    machine_id: str,
    states: List[State],
    transitions: List[Union[Transition, TransitionGroup]],
    context: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Compile State and Transition objects into a config dict.

    Args:
        machine_id: The machine identifier string.
        states: List of top-level ``State`` objects.
        transitions: List of ``Transition`` or
            ``TransitionGroup`` objects.
        context: Optional initial context dict.

    Returns:
        A JSON-compatible config dict suitable for
        ``create_machine()``.

    Raises:
        InvalidConfigError: On duplicate states, missing
            initial state, or unknown transition sources.
    """
    from collections import defaultdict

    # 🔍 Build flat lookup of all states by name
    all_states_by_name: Dict[str, State] = {}

    def _register_states(
        state_list: List[State],
    ) -> None:
        for s in state_list:
            all_states_by_name[s.name] = s
            if s.states:
                _register_states(s.states)

    _register_states(states)

    # 🔍 Validate top-level: duplicates, initial
    top_names: set = set()
    initial_state = None
    has_parallel_root = len(states) == 1 and states[0].parallel

    for s in states:
        if s.name in top_names:
            raise InvalidConfigError(
                f"Duplicate state name '{s.name}' " f"at the same level"
            )
        top_names.add(s.name)
        if s.initial:
            if initial_state is not None:
                raise InvalidConfigError(
                    f"Multiple initial states: "
                    f"{initial_state}, {s.name}. "
                    f"Exactly one allowed"
                )
            initial_state = s.name

    if not has_parallel_root and initial_state is None and len(states) > 0:
        raise InvalidConfigError(
            "No initial state defined. Exactly one "
            "state must have initial=True"
        )

    # 🔍 Flatten all transitions
    flat_transitions: List[Transition] = []
    for t in transitions:
        if isinstance(t, TransitionGroup):
            flat_transitions.extend(t.transitions)
        else:
            flat_transitions.append(t)

    # 🔍 Validate transition sources exist
    for t in flat_transitions:
        if t.source.name not in all_states_by_name:
            raise InvalidConfigError(
                f"Transition source "
                f"'{t.source.name}' "
                f"is not a defined state"
            )

    # ⚙️ Compile each top-level state
    state_configs: Dict[str, Any] = {}
    for s in states:
        state_configs[s.name] = _compile_state(s, all_states_by_name)

    # ⚙️ Merge transitions into state configs
    trans_by_source_event: Dict[str, Dict[str, List[Transition]]] = (
        defaultdict(lambda: defaultdict(list))
    )

    for t in flat_transitions:
        trans_by_source_event[t.source.name][t.event].append(t)

    def _merge_transitions_into(
        state_name: str,
        state_config: Dict[str, Any],
    ) -> None:
        if state_name in trans_by_source_event:
            if "on" not in state_config:
                state_config["on"] = {}
            for event, t_list in trans_by_source_event[state_name].items():
                compiled = []
                for t in t_list:
                    entry: Dict[str, Any] = {}
                    if not t.internal and t.target is not None:
                        entry["target"] = t.target.name
                    if t.guard:
                        entry["guard"] = t.guard
                    if t.actions:
                        entry["actions"] = t.actions
                    if t.reenter:
                        entry["reenter"] = True
                    compiled.append(entry)
                if len(compiled) == 1:
                    state_config["on"][event] = compiled[0]
                else:
                    state_config["on"][event] = compiled
        # 📝 Recurse into child states
        if "states" in state_config:
            for child_name, child_config in state_config["states"].items():
                _merge_transitions_into(child_name, child_config)

    for sname, sconfig in state_configs.items():
        _merge_transitions_into(sname, sconfig)

    # ⚙️ Assemble top-level config
    result: Dict[str, Any] = {
        "id": machine_id,
        "states": state_configs,
    }
    if initial_state:
        result["initial"] = initial_state
    if context:
        result["context"] = context

    return result


# -----------------------------------------------------------------
# ⚙️ Logic Compiler
# -----------------------------------------------------------------


def _compile_logic_from_functions(
    actions: List[Callable],
    guards: List[Callable],
    services: List[Callable],
) -> MachineLogic:
    """Compile decorated/raw callables into a MachineLogic.

    For each callable, uses the ``_xsm_name`` attribute if
    present (set by ``@action``/``@guard``/``@service``),
    otherwise falls back to ``_snake_to_camel(fn.__name__)``.

    Args:
        actions: List of action callables.
        guards: List of guard callables.
        services: List of service callables.

    Returns:
        A ``MachineLogic`` instance with populated dicts.
    """
    action_dict: Dict[str, Callable] = {}
    guard_dict: Dict[str, Callable] = {}
    service_dict: Dict[str, Callable] = {}

    for fn in actions:
        name = getattr(fn, "_xsm_name", _snake_to_camel(fn.__name__))
        action_dict[name] = fn
    for fn in guards:
        name = getattr(fn, "_xsm_name", _snake_to_camel(fn.__name__))
        guard_dict[name] = fn
    for fn in services:
        name = getattr(fn, "_xsm_name", _snake_to_camel(fn.__name__))
        service_dict[name] = fn

    return MachineLogic(
        actions=action_dict,
        guards=guard_dict,
        services=service_dict,
    )


def _compile_logic_from_instance(
    instance: object,
    decorated: List[Callable],
) -> MachineLogic:
    """Compile class instance methods into a MachineLogic.

    Uses ``functools.partial(method, instance)`` to bind
    ``self`` so the resulting callables match the expected
    signatures (without an explicit ``self`` parameter).

    Args:
        instance: The object instance whose methods are
            being compiled.
        decorated: List of unbound decorated methods
            (with ``_xsm_type`` and ``_xsm_name``).

    Returns:
        A ``MachineLogic`` instance with bound callables.
    """
    action_dict: Dict[str, Callable] = {}
    guard_dict: Dict[str, Callable] = {}
    service_dict: Dict[str, Callable] = {}

    for fn in decorated:
        name = fn._xsm_name
        xsm_type = fn._xsm_type
        bound = functools.partial(fn, instance)
        if xsm_type == "action":
            action_dict[name] = bound
        elif xsm_type == "guard":
            guard_dict[name] = bound
        elif xsm_type == "service":
            service_dict[name] = bound

    return MachineLogic(
        actions=action_dict,
        guards=guard_dict,
        services=service_dict,
    )


# -------------------------------------------------------------------------
# Functional API: build_machine()
# -------------------------------------------------------------------------


def build_machine(
    *,
    id: str,
    states: List[State],
    transitions: Optional[List[Union[Transition, TransitionGroup]]] = None,
    actions: Optional[List[Callable]] = None,
    guards: Optional[List[Callable]] = None,
    services: Optional[List[Callable]] = None,
    context: Optional[Dict] = None,
) -> "MachineNode":
    """Build a state machine from Python objects (functional API).

    This is the simplest API style -- define ``State`` objects and
    ``Transition`` objects at module level, then call this function.

    Args:
        id: Machine ID string.
        states: List of ``State`` objects.
        transitions: Optional list of transitions.
        actions: Optional list of action callables.
        guards: Optional list of guard callables.
        services: Optional list of service callables.
        context: Optional initial context dict.

    Returns:
        A ``MachineNode`` ready for use with ``Interpreter``
        or ``SyncInterpreter``.
    """
    config = _compile_config(
        machine_id=id,
        states=states,
        transitions=transitions or [],
        context=context,
    )
    logic = _compile_logic_from_functions(
        actions=actions or [],
        guards=guards or [],
        services=services or [],
    )
    return _original_create_machine(config, logic=logic)
