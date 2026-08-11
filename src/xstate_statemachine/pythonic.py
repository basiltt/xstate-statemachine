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
import copy
import functools
import inspect
import logging
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .exceptions import InvalidConfigError, NotSupportedError
from .factory import create_machine as _original_create_machine
from .machine_logic import MachineLogic
from .models import MachineNode

# 📝 Decorators below return the SAME function, so a TypeVar keeps them
#    transparent to type checkers. Without it mypy --strict reports
#    "Untyped decorator makes function ... untyped" for every stub in
#    generated code -- and for every hand-written one too.
_DecoratedF = TypeVar("_DecoratedF", bound=Callable[..., Any])


# -------------------------------------------------------------------------
# 🛠️ Internal Helpers
# -------------------------------------------------------------------------


@functools.lru_cache(maxsize=256)
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
        history: Marks this as a history pseudo-state. Pass
            ``"shallow"`` or ``"deep"``.
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
        tags: Optional list of string tags for this state.
        meta: Optional metadata dict attached to this state.

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
        history: Optional[str] = None,
        on: Optional[Dict[str, Any]] = None,
        entry: Optional[List[str]] = None,
        exit: Optional[List[str]] = None,
        # 📝 Keys are a delay in ms OR a NAMED delay resolved from
        #    MachineLogic.delays at runtime. Typing this as
        #    Dict[int, Any] wrongly rejected named delays, which the
        #    engine has always supported.
        after: Optional[Dict[Union[int, str], Any]] = None,
        invoke: Optional[Union[Dict, List]] = None,
        on_done: Optional[Union[str, Dict]] = None,
        always: Optional[Union[str, Dict, List]] = None,
        context: Optional[Dict] = None,
        states: Optional[List["State"]] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        if final and parallel:
            raise InvalidConfigError(
                f"State '{name}' cannot be both final " f"and parallel"
            )
        self.name = name
        self.initial = initial
        self.final = final
        self.parallel = parallel
        self.history = history
        self.on = on
        self.entry = entry or []
        self._exit_actions: List[str] = exit or []
        self.after = after
        self.invoke = invoke
        self.on_done = on_done
        self.always = always
        self.context = context
        self.states = states or []
        self.tags = list(tags) if tags else []
        self.meta = dict(meta) if meta else None
        # 📝 Internal: tracks functions registered via decorators
        self._enter_decorators: List[Callable] = []
        self._exit_decorators: List[Callable] = []

    @property
    def exit_actions(self) -> List[str]:
        """The list of exit action names for this state."""
        return self._exit_actions

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

    def __repr__(self) -> str:
        """Provide a readable representation for debugging."""
        flags = []
        if self.initial:
            flags.append("initial")
        if self.final:
            flags.append("final")
        if self.parallel:
            flags.append("parallel")
        flag_str = ", " + ", ".join(flags) if flags else ""
        return f"State({self.name!r}{flag_str})"

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

    def exit(self, fn: Callable) -> Callable:
        """Decorator to register a function as an exit action.

        Only valid inside a ``StateMachine`` class definition.
        Use ``@state.exit`` to decorate exit actions.

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
        if name not in self._exit_actions:
            self._exit_actions.append(name)
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
        if not isinstance(other, Transition):
            return NotImplemented
        return TransitionGroup([self, other])

    def __repr__(self) -> str:
        """Provide a readable representation for debugging."""
        src = self.source.name if self.source else "?"
        tgt = self.target.name if self.target else "(internal)"
        return f"Transition({src!r} --{self.event!r}--> " f"{tgt!r})"


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
        if not isinstance(other, Transition):
            return NotImplemented
        return TransitionGroup(self.transitions + [other])

    def __repr__(self) -> str:
        """Provide a readable representation for debugging."""
        return f"TransitionGroup({len(self.transitions)} " f"transitions)"


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


@overload
def action(fn_or_name: _DecoratedF) -> _DecoratedF: ...
@overload
def action(
    fn_or_name: Optional[str] = None,
) -> Callable[[_DecoratedF], _DecoratedF]: ...
def action(fn_or_name: Any = None) -> Any:
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

        def decorator(fn: _DecoratedF) -> _DecoratedF:
            fn._xsm_type = "action"
            fn._xsm_name = name
            return fn

        return decorator


@overload
def guard(fn_or_name: _DecoratedF) -> _DecoratedF: ...
@overload
def guard(
    fn_or_name: Optional[str] = None,
) -> Callable[[_DecoratedF], _DecoratedF]: ...
def guard(fn_or_name: Any = None) -> Any:
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

        def decorator(fn: _DecoratedF) -> _DecoratedF:
            if inspect.iscoroutinefunction(fn):
                raise NotSupportedError(
                    f"Guard '{fn.__name__}' must be "
                    f"synchronous (guards cannot be async)"
                )
            fn._xsm_type = "guard"
            fn._xsm_name = name
            return fn

        return decorator


@overload
def service(fn_or_name: _DecoratedF) -> _DecoratedF: ...
@overload
def service(
    fn_or_name: Optional[str] = None,
) -> Callable[[_DecoratedF], _DecoratedF]: ...
def service(fn_or_name: Any = None) -> Any:
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

        def decorator(fn: _DecoratedF) -> _DecoratedF:
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
    parent_parallel: bool = False,
) -> Dict[str, Any]:
    """Compile a single State into a JSON config dict entry."""
    # 📝 Validate: a final state cannot have CHILDREN.
    #
    # 🛡️ Outgoing transitions on a final state are deliberately allowed.
    #    The JSON engine accepts them (real Stately exports ship final
    #    states with an "undo" transition), and rejecting them here made the
    #    Pythonic API stricter than the config format it mirrors — which in
    #    turn made those machines impossible to code-generate.
    if state.final and state.states:
        raise InvalidConfigError(
            f"Final state '{state.name}' cannot have child states"
        )

    # 📝 Validate: child of parallel parent should not be initial
    if parent_parallel and state.initial:
        raise InvalidConfigError(
            f"State '{state.name}' is a child of a parallel "
            f"state and should not have initial=True. "
            f"All parallel regions are active simultaneously."
        )

    config: Dict[str, Any] = {}

    # 📝 Type
    if state.final:
        config["type"] = "final"
    elif state.parallel:
        config["type"] = "parallel"
    elif state.history:
        # 🕰️ History pseudo-state: remembers the previously active
        #    child of its parent. Without this the node degrades to a plain
        #    atomic state and the machine silently loses its memory.
        config["type"] = "history"
        config["history"] = state.history

    # 📝 Entry / Exit actions (defensive copy to avoid
    # mutating State objects shared across builds)
    entry = list(state.entry) if state.entry else []
    exit_acts = list(state._exit_actions) if state._exit_actions else []
    if entry:
        config["entry"] = entry[0] if len(entry) == 1 else entry
    if exit_acts:
        config["exit"] = exit_acts[0] if len(exit_acts) == 1 else exit_acts

    # 📝 On (event transitions from State.on dict)
    # Defensive deep copy to avoid mutating shared State objects
    if state.on:
        config["on"] = {
            k: (v if not isinstance(v, dict) else dict(v))
            for k, v in state.on.items()
        }

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

    # 🏷️ Tags & metadata — carried through so `matches()`/tag queries and
    #    round-tripped JSON keep working. Previously dropped entirely, which
    #    made full-fidelity code generation impossible.
    if state.tags:
        config["tags"] = list(state.tags)
    if state.meta:
        config["meta"] = dict(state.meta)

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
                child,
                all_states_by_name,
                parent_parallel=state.parallel,
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
            # 🛡️ The engine only WARNS for a compound state with no initial
            #    (real Stately exports ship them). Raising here would make
            #    the Pythonic API stricter than the JSON it mirrors, and
            #    would make such a machine impossible to code-generate.
            logging.getLogger(__name__).warning(
                "⚠️ Compound state '%s' has %d child state(s) but no "
                "initial=True. Starting this machine will fail.",
                state.name,
                len(state.states),
            )

    return config


def _compile_config(
    machine_id: str,
    states: List[State],
    transitions: List[Union[Transition, TransitionGroup]],
    context: Optional[Dict] = None,
    root: Optional[State] = None,
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
    # 🔍 Build flat lookup of all states by name
    # Uses dot-path keys to avoid collisions between
    # states with the same name at different hierarchy levels
    all_states_by_name: Dict[str, State] = {}

    def _register_states(
        state_list: List[State],
        prefix: str = "",
    ) -> None:
        for s in state_list:
            key = f"{prefix}.{s.name}" if prefix else s.name
            all_states_by_name[key] = s
            # Also register the bare name for transition
            # source lookups (backward compat)
            all_states_by_name[s.name] = s
            if s.states:
                _register_states(s.states, prefix=key)

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

    root_is_parallel = root is not None and root.parallel
    if (
        not has_parallel_root
        and not root_is_parallel
        and initial_state is None
        and len(states) > 0
    ):
        logging.getLogger(__name__).warning(
            "⚠️ Machine '%s' has %d top-level state(s) but none is marked "
            "initial=True. Starting this machine will fail.",
            machine_id,
            len(states),
        )

    # 🔍 Flatten all transitions
    flat_transitions: List[Transition] = []
    for t in transitions:
        if isinstance(t, TransitionGroup):
            flat_transitions.extend(t.transitions)
        else:
            flat_transitions.append(t)

    # 🔍 Validate transition sources exist and are not final
    for t in flat_transitions:
        if t.source.name not in all_states_by_name:
            raise InvalidConfigError(
                f"Transition source "
                f"'{t.source.name}' "
                f"is not a defined state"
            )
        src = all_states_by_name[t.source.name]
        if src.final and src.states:
            raise InvalidConfigError(
                f"Final state '{t.source.name}' cannot have child states"
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
    if context is not None:
        result["context"] = context

    # 🌳 Root-level properties. Real-world machines routinely declare
    #    `on`, `entry`, `exit`, `tags` and even `type: parallel` at the top
    #    level; without this they are silently dropped and a machine-wide
    #    escape transition simply stops existing.
    if root is not None:
        if root.parallel:
            result["type"] = "parallel"
        if root.on:
            result["on"] = dict(root.on)
        if root.always is not None:
            result.setdefault("on", {})[""] = root.always
        if root.entry:
            result["entry"] = list(root.entry)
        if root.exit_actions:
            result["exit"] = list(root.exit_actions)
        if root.after:
            result["after"] = dict(root.after)
        if root.invoke:
            result["invoke"] = root.invoke
        if root.on_done is not None:
            result["onDone"] = (
                {"target": root.on_done}
                if isinstance(root.on_done, str)
                else root.on_done
            )
        if root.tags:
            result["tags"] = list(root.tags)
        if root.meta:
            result["meta"] = dict(root.meta)

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

    Raises:
        InvalidConfigError: If any function was decorated
            with ``@state.enter`` or ``@state.exit``, which
            are only valid inside a ``StateMachine`` class.
    """
    action_dict: Dict[str, Callable] = {}
    guard_dict: Dict[str, Callable] = {}
    service_dict: Dict[str, Callable] = {}

    all_fns = list(actions) + list(guards) + list(services)
    for fn in all_fns:
        if hasattr(fn, "_xsm_state_enter"):
            raise InvalidConfigError(
                f"@{fn._xsm_state_enter.name}.enter "
                f"decorator is only valid inside a "
                f"StateMachine class"
            )
        if hasattr(fn, "_xsm_state_exit"):
            raise InvalidConfigError(
                f"@{fn._xsm_state_exit.name}.exit "
                f"decorator is only valid inside a "
                f"StateMachine class"
            )

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
    action_dict: Dict[str, Any] = {}
    guard_dict: Dict[str, Any] = {}
    service_dict: Dict[str, Any] = {}

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
    id: str,  # noqa: A002 — shadows builtin intentionally
    states: List[State],
    transitions: Optional[List[Union[Transition, TransitionGroup]]] = None,
    actions: Optional[List[Callable]] = None,
    guards: Optional[List[Callable]] = None,
    services: Optional[List[Callable]] = None,
    context: Optional[Dict] = None,
    root: Optional[State] = None,
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
        root: Optional ``State`` carrying machine-level ``on``/``entry``/
            ``exit``/``tags``/``parallel`` properties.

    Returns:
        A ``MachineNode`` ready for use with ``Interpreter``
        or ``SyncInterpreter``.
    """
    machine_id = id
    config = _compile_config(
        machine_id=machine_id,
        states=states,
        transitions=transitions or [],
        context=context,
        root=root,
    )
    logic = _compile_logic_from_functions(
        actions=actions or [],
        guards=guards or [],
        services=services or [],
    )
    return _original_create_machine(config, logic=logic)


# -------------------------------------------------------------------------
# Builder API: MachineBuilder
# -------------------------------------------------------------------------


class MachineBuilder:
    """Fluent builder for constructing state machines.

    Example::

        machine = (
            MachineBuilder("myMachine")
            .context({"count": 0})
            .state("idle", initial=True)
            .state("running")
            .transition("idle", "START", "running")
            .action("logIt", my_action_fn)
            .build()
        )

    Args:
        machine_id: The machine's ID string.
    """

    def __init__(self, machine_id: str) -> None:
        self._machine_id = machine_id
        self._context: Optional[Dict] = None
        self._states: Dict[str, Dict[str, Any]] = {}
        self._initial_state: Optional[str] = None
        self._transitions: List[Dict[str, Any]] = []
        self._root: Dict[str, Any] = {}
        self._actions: Dict[str, Callable] = {}
        self._guards: Dict[str, Callable] = {}
        self._services: Dict[str, Callable] = {}

    def __repr__(self) -> str:
        """Provide a readable representation for debugging."""
        return (
            f"MachineBuilder({self._machine_id!r}, "
            f"{len(self._states)} states, "
            f"{len(self._transitions)} transitions)"
        )

    def context(self, ctx: Dict) -> "MachineBuilder":
        """Set the initial context."""
        self._context = ctx
        return self

    def state(
        self,
        name: str,
        *,
        initial: bool = False,
        final: bool = False,
        parallel: bool = False,
        on: Optional[Dict] = None,
        entry: Optional[List] = None,
        exit: Optional[List] = None,
        after: Optional[Dict] = None,
        invoke: Optional[Union[Dict, List]] = None,
        on_done: Optional[Union[str, Dict]] = None,
        always: Optional[Union[str, Dict, List]] = None,
        history: Optional[str] = None,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "MachineBuilder":
        """Add a state to the machine.

        Raises:
            InvalidConfigError: If ``name`` is already defined,
                or ``final`` and ``parallel`` are both True.
        """
        if name in self._states:
            raise InvalidConfigError(f"Duplicate state name '{name}'")
        if final and parallel:
            raise InvalidConfigError(
                f"State '{name}' cannot be both " f"final and parallel"
            )
        config: Dict[str, Any] = {}
        if final:
            config["type"] = "final"
        if parallel:
            config["type"] = "parallel"
        if history:
            config["type"] = "history"
            config["history"] = history
        if on:
            config["on"] = on
        if entry:
            config["entry"] = entry
        if exit:
            config["exit"] = exit
        if after:
            config["after"] = after
        if invoke:
            config["invoke"] = invoke
        if tags:
            config["tags"] = list(tags)
        if meta:
            config["meta"] = dict(meta)
        if on_done is not None:
            if isinstance(on_done, str):
                config["onDone"] = {"target": on_done}
            else:
                config["onDone"] = on_done
        if always is not None:
            if "on" not in config:
                config["on"] = {}
            config["on"][""] = always
        if initial:
            self._initial_state = name
        self._states[name] = config
        return self

    def transition(
        self,
        source: str,
        event: str,
        target: str,
        *,
        guard: Optional[str] = None,
        actions: Optional[List[str]] = None,
        reenter: bool = False,
        internal: bool = False,
    ) -> "MachineBuilder":
        """Add a transition between states."""
        self._transitions.append(
            {
                "source": source,
                "event": event,
                "target": target,
                "guard": guard,
                "actions": actions,
                "reenter": reenter,
                "internal": internal,
            }
        )
        return self

    def child_states(
        self,
        parent: str,
        *,
        initial: Optional[str] = None,
        states: Optional[Dict[str, Dict]] = None,
        parallel: bool = False,
    ) -> "MachineBuilder":
        """Add child states to an existing state."""
        if parent not in self._states:
            raise InvalidConfigError(
                f"Parent state '{parent}' not found. "
                f"Add it with .state() first"
            )
        parent_config = self._states[parent]
        if parallel:
            parent_config["type"] = "parallel"
        if states:
            parent_config["states"] = states
        if initial and not parallel:
            parent_config["initial"] = initial
        return self

    def action(self, name: str, fn: Callable) -> "MachineBuilder":
        """Register an action function.

        The explicitly provided ``name`` is always used as the
        registration key, regardless of any ``_xsm_name``
        attribute on ``fn``.
        """
        self._actions[name] = fn
        return self

    def root(self, **properties: Any) -> "MachineBuilder":
        """Set machine-level (root) properties.

        Real-world machines routinely declare a global escape transition
        such as ``on={"EMERGENCY": "shutdown"}`` at the top level, or mark
        the whole machine ``type="parallel"``. Use JSON key spellings
        (``onDone``, not ``on_done``).

        Args:
            **properties: Root config keys such as ``on``, ``entry``,
                ``exit``, ``tags``, ``meta`` or ``type``.

        Returns:
            This builder, for chaining.
        """
        self._root.update(properties)
        return self

    def guard(self, name: str, fn: Callable) -> "MachineBuilder":
        """Register a guard function.

        The explicitly provided ``name`` is always used as the
        registration key.
        """
        self._guards[name] = fn
        return self

    def service(self, name: str, fn: Callable) -> "MachineBuilder":
        """Register a service function.

        The explicitly provided ``name`` is always used as the
        registration key.
        """
        self._services[name] = fn
        return self

    def build(self, context: Optional[Dict] = None) -> MachineNode:
        """Build and return the MachineNode.

        This method is idempotent — it can be called multiple
        times on the same builder (e.g. with different context
        overrides) without corrupting internal state.

        Args:
            context: Optional context override.

        Returns:
            A ``MachineNode`` ready for interpreter use.

        Raises:
            InvalidConfigError: If no initial state is defined
                and the machine has more than one non-parallel
                state, or if a transition source is invalid.
        """
        # Validate initial state is defined (unless single
        # parallel root or single state)
        has_parallel_root = (
            len(self._states) == 1
            and next(iter(self._states.values())).get("type") == "parallel"
        )
        root_is_parallel = self._root.get("type") == "parallel"
        if (
            not has_parallel_root
            and not root_is_parallel
            and self._initial_state is None
            and len(self._states) > 1
        ):
            # 🛡️ Warn, don't raise — see _compile_config for the rationale.
            #    The JSON engine accepts this and so must the builder.
            logging.getLogger(__name__).warning(
                "⚠️ Machine '%s' has %d top-level state(s) but none is "
                "marked initial=True. Starting this machine will fail.",
                self._machine_id,
                len(self._states),
            )

        # Deep-copy states so repeated builds don't corrupt
        states_copy = copy.deepcopy(self._states)

        # Merge transitions into the copied state configs
        for t in self._transitions:
            source = t["source"]
            if source not in states_copy:
                raise InvalidConfigError(
                    f"Transition source '{source}' " f"is not a defined state"
                )
            state_config = states_copy[source]
            if "on" not in state_config:
                state_config["on"] = {}
            entry: Dict[str, Any] = {}
            if not t["internal"]:
                entry["target"] = t["target"]
            if t["guard"]:
                entry["guard"] = t["guard"]
            if t["actions"]:
                entry["actions"] = t["actions"]
            if t["reenter"]:
                entry["reenter"] = True
            event = t["event"]
            if event in state_config["on"]:
                existing = state_config["on"][event]
                if isinstance(existing, list):
                    existing.append(entry)
                else:
                    state_config["on"][event] = [
                        existing,
                        entry,
                    ]
            else:
                state_config["on"][event] = entry

        config: Dict[str, Any] = {
            "id": self._machine_id,
            "states": states_copy,
        }
        if self._initial_state:
            config["initial"] = self._initial_state
        ctx = context if context is not None else self._context
        if ctx is not None:
            config["context"] = ctx

        # 🌳 Machine-level properties (see MachineBuilder.root).
        if self._root:
            config.update(copy.deepcopy(self._root))

        logic = MachineLogic(
            actions=dict(self._actions),
            guards=dict(self._guards),
            services=dict(self._services),
        )
        return _original_create_machine(config, logic=logic)


# -------------------------------------------------------------------------
# Class-Based API: StateMachine + Metaclass
# -------------------------------------------------------------------------


class _StateMachineMeta(type):
    """Metaclass for ``StateMachine`` that collects States,
    Transitions, and decorated methods at class-definition time.
    """

    def __new__(mcs, name, bases, namespace):
        # Skip processing for the base StateMachine class
        if name == "StateMachine" and not any(
            hasattr(b, "_xsm_is_base") for b in bases
        ):
            cls = super().__new__(mcs, name, bases, namespace)
            cls._xsm_is_base = True
            return cls

        states: List[State] = []
        transitions: List[Union[Transition, TransitionGroup]] = []
        decorated: List[Callable] = []

        for attr_name, attr_value in list(namespace.items()):
            if attr_name.startswith("_"):
                continue

            # Collect nested State subclasses
            if (
                isinstance(attr_value, type)
                and issubclass(attr_value, State)
                and attr_value is not State
            ):
                child_states = []
                for (
                    child_attr_name,
                    child_attr_value,
                ) in vars(attr_value).items():
                    if child_attr_name.startswith("_"):
                        continue
                    if isinstance(child_attr_value, State):
                        if not child_attr_value.name:
                            child_attr_value.name = child_attr_name
                        child_states.append(child_attr_value)
                state_obj = State(
                    name=attr_name,
                    initial=getattr(
                        attr_value,
                        "_xsm_initial",
                        False,
                    ),
                    final=getattr(attr_value, "_xsm_final", False),
                    parallel=getattr(
                        attr_value,
                        "_xsm_parallel",
                        False,
                    ),
                    states=(child_states if child_states else None),
                )
                states.append(state_obj)
                continue

            # Collect State instances
            if isinstance(attr_value, State):
                # 🌳 `machine_root` carries machine-level properties
                #    (on/entry/exit/tags/parallel) rather than being a
                #    state of the machine. Keep it out of `states`.
                if attr_name == "machine_root":
                    continue
                if not attr_value.name:
                    attr_value.name = attr_name
                states.append(attr_value)
                continue

            # Collect Transitions / TransitionGroups
            if isinstance(attr_value, (Transition, TransitionGroup)):
                transitions.append(attr_value)
                continue

            # Collect decorated methods
            if callable(attr_value) and hasattr(attr_value, "_xsm_type"):
                decorated.append(attr_value)

        cls = super().__new__(mcs, name, bases, namespace)
        cls._xsm_states = states
        cls._xsm_transitions = transitions
        cls._xsm_decorated = decorated
        return cls


class StateMachine(metaclass=_StateMachineMeta):
    """Base class for defining state machines using class syntax.

    Subclass this and define ``State`` attributes, transitions,
    and decorated action/guard/service methods.

    Class Attributes:
        machine_id: Optional machine ID (defaults to class
            name).
        initial_context: Optional initial context dict.

    Example::

        class Light(StateMachine):
            off = State(initial=True)
            on = State()
            toggle = (
                off.to(on, event="TOGGLE")
                | on.to(off, event="TOGGLE")
            )

        machine = Light.create_machine()
    """

    machine_id: Optional[str] = None
    initial_context: Optional[Dict] = None
    machine_root: Optional[State] = None

    @classmethod
    def create_machine(cls, context=None):
        """Create a ``MachineNode`` from this class.

        Args:
            context: Optional context override.

        Returns:
            A ``MachineNode`` ready for interpreter use.
        """
        mid = cls.machine_id or cls.__name__
        ctx = context if context is not None else cls.initial_context

        config = _compile_config(
            machine_id=mid,
            states=cls._xsm_states,
            transitions=cls._xsm_transitions,
            context=ctx,
            root=getattr(cls, "machine_root", None),
        )

        instance = cls()
        logic = _compile_logic_from_instance(
            instance=instance,
            decorated=cls._xsm_decorated,
        )

        return _original_create_machine(config, logic=logic)
