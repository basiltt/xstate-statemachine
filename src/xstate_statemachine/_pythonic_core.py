# src/xstate_statemachine/_pythonic_core.py
"""
🐍 Pythonic DSL core: ``State``, ``Transition``, decorators, compilers.

Shared by the functional API (``build_machine``), the fluent
``MachineBuilder`` and the class-based ``StateMachine``. Import the public
names from ``xstate_statemachine.pythonic``.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import copy
import functools
import inspect
import logging
import re
from collections import defaultdict
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
    overload,
)

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from ._pythonic_runtime import adapt_callable
from .exceptions import InvalidConfigError, NotSupportedError
from .factory import create_machine as _original_create_machine
from .machine_logic import (
    ActionCallable,
    GuardCallable,
    MachineLogic,
    ServiceCallable,
)
from .models import MachineNode

logger = logging.getLogger(__name__)

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


#: A word boundary inside a camelCase / PascalCase identifier: lower or
#: digit followed by upper (``slowDown``), or the last capital of an
#: acronym that starts a new word (``HTTPError`` → ``HTTP|Error``).
_WORD_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


@functools.lru_cache(maxsize=256)
def _attr_to_event(attr_name: str) -> str:
    """Infer an event type from a transition's attribute name.

    ``cycle`` → ``CYCLE``, ``slow_down`` → ``SLOW_DOWN`` and ``slowDown``
    → ``SLOW_DOWN``: the JSON convention is SCREAMING_SNAKE_CASE, and the
    inferred name must match what ``send("...")`` callers write.

    An attribute already written in SCREAMING_SNAKE (``START_NOW``) is
    kept as is, and acronyms stay together (``HTTPError`` →
    ``HTTP_ERROR``, ``parseXML`` → ``PARSE_XML``). Before 0.12.0 every
    capital started a new word, so ``START_NOW`` became
    ``S_T_A_R_T__N_O_W``.

    Args:
        attr_name: The class attribute the transition is assigned to.

    Returns:
        The SCREAMING_SNAKE_CASE event type.
    """
    if attr_name.isupper():
        return attr_name
    return _WORD_BOUNDARY.sub("_", attr_name).upper()


def _as_action_list(value: Any) -> List[Any]:
    """Normalise ``entry`` / ``exit`` / ``actions`` to a list.

    A bare string or a single ``{"type": ...}`` dict is one action, as in
    XState JSON. Before 0.12.0 a string here was iterated character by
    character and compiled into nonsense action names.
    """
    if not value:
        return []
    if isinstance(value, (str, dict)):
        return [value]
    return list(value)


def _tag(fn: Callable[..., Any], kind: str, name: Any) -> None:
    """Mark *fn* as a DSL ``action`` / ``guard`` / ``service`` named *name*.

    Shared by the decorators and the ``State`` decorator methods so the
    checks live in one place.

    Args:
        fn: The callable to mark.
        kind: ``"action"``, ``"guard"`` or ``"service"``.
        name: The name the chart refers to it by.

    Raises:
        InvalidConfigError: *name* is not a non-empty string, *fn* is
            already marked as a different kind (``@action`` stacked on
            ``@guard`` silently changed its kind before 0.12.0), or *fn*
            does not accept attributes (a bound method or a builtin).
    """
    if not isinstance(name, str) or not name:
        raise InvalidConfigError(
            f"@{kind} name must be a non-empty string, not {name!r}."
        )
    previous = getattr(fn, "_xsm_type", None)
    if previous is not None and previous != kind:
        raise InvalidConfigError(
            f"{getattr(fn, '__name__', fn)!r} is already marked as a "
            f"{previous}; one callable cannot also be a {kind}. Use two "
            f"functions."
        )
    try:
        setattr(fn, "_xsm_type", kind)
        setattr(fn, "_xsm_name", name)
    except (AttributeError, TypeError) as exc:
        raise InvalidConfigError(
            f"@{kind} cannot mark {fn!r}: it does not accept attributes. "
            f"Decorate the plain function instead."
        ) from exc


def _explicit_name(value: Any, kind: str) -> Optional[str]:
    """Validate the argument of ``@{kind}(...)``.

    Args:
        value: The decorator argument (``None`` for ``@{kind}()``).
        kind: ``"action"``, ``"guard"`` or ``"service"``.

    Returns:
        The explicit name, or ``None`` to use the function's own name.

    Raises:
        InvalidConfigError: *value* is neither ``None`` nor a non-empty
            string (``@action(123)`` and ``@action("")`` were accepted
            before 0.12.0 and failed later as a missing implementation).
    """
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise InvalidConfigError(
            f"@{kind} name must be a non-empty string, not {value!r}."
        )
    return value


def _callable_name(fn: Callable[..., Any], kind: str) -> str:
    """The name *fn* registers under: ``_xsm_name``, else its camelCased
    ``__name__``.

    Args:
        fn: A callable handed to the functional API.
        kind: Its kind, for the error message.

    Returns:
        The registration name.

    Raises:
        InvalidConfigError: *fn* has neither an explicit name nor a
            ``__name__`` (a ``functools.partial``, a callable object).
    """
    explicit = getattr(fn, "_xsm_name", None)
    if explicit:
        return str(explicit)
    plain = getattr(fn, "__name__", None)
    if not plain:
        raise InvalidConfigError(
            f"Cannot tell which {kind} name {fn!r} implements: it has no "
            f"__name__. Decorate it with @{kind}('name') or wrap it in a "
            f"named function."
        )
    return _snake_to_camel(plain)


#: Attribute names a ``StateMachine`` subclass may not use for a state
#: or transition: they are the instance façade's own API. ``start`` and
#: ``stop`` are deliberately NOT in this set -- they are common event
#: names (timers, jobs, media players) and real Stately exports use them.
#: A transition may be called ``start`` / ``stop``; it simply gets no
#: event-method sugar, because the lifecycle methods keep their meaning.
#: See ``_LIFECYCLE_NAMES`` in ``_pythonic_class``.
_RESERVED_NAMES: FrozenSet[str] = frozenset(
    {
        "send",
        "state",
        "configuration",
        "context",
        "status",
        "can",
        "matches",
        "allowed_events",
        "machine",
        "interpreter",
        "engine",
        "strict",
        "plugins",
        "validate_logic",
        "create_machine",
        "machine_id",
        "initial_context",
        "machine_root",
    }
)


#: Keywords the nested-class form ``class X(State, ...)`` forwards to the
#: compiled ``State``. ``name`` comes from the attribute, ``states`` from
#: the class body, and ``context`` only makes sense at the root.
_NESTED_CLASS_KWARGS: FrozenSet[str] = frozenset(
    {
        "history",
        "on",
        "entry",
        "exit",
        "after",
        "invoke",
        "on_done",
        "always",
        "tags",
        "meta",
    }
)


# -------------------------------------------------------------------------
# 🏗️ State
# -------------------------------------------------------------------------


class _StateMeta(type):
    """Lets a nested ``class paid(State): ...`` act as a transition source.

    ``paid.to(x)`` on the *class* would otherwise resolve to the unbound
    instance method and misread ``x`` as ``self``. These are properties so
    they are data descriptors and win over the class-dict function for
    class-level access, while instances still see ``State.to``.
    """

    @property
    def to(cls) -> Callable[..., "Transition"]:  # noqa: N805
        """``State.to`` with the nested class itself as the source."""
        # 📝 `vars(State)` rather than `State.to`: the latter would hit this
        #    very property and recurse.
        return functools.partial(vars(State)["to"], cls)

    @property
    def internal(cls) -> Callable[..., "Transition"]:  # noqa: N805
        """``State.internal`` with the nested class itself as the source."""
        return functools.partial(vars(State)["internal"], cls)

    def __get__(cls, instance: Any, owner: Any = None) -> Any:  # noqa: N805
        """``sm.paid.is_active`` for a nested ``class paid(State)``."""
        if instance is None or not hasattr(instance, "_xsm_interp"):
            return cls
        resolved = getattr(type(instance), "_xsm_resolved", {})
        state = resolved.get(cls)
        if state is None:
            return cls
        return BoundState(state, instance)


class State(metaclass=_StateMeta):
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

    #: Aliases for the nested-class form, mirroring the vocabulary of
    #: other statechart libraries: ``class paid(State.Compound): ...``
    #: and ``class fulfil(State.Parallel): ...``. Assigned below.
    Compound: type
    Parallel: type

    def __init__(
        self,
        name: str = "",
        *,
        initial: bool = False,
        final: bool = False,
        parallel: bool = False,
        history: Optional[str] = None,
        on: Optional[Dict[str, Any]] = None,
        entry: Optional[List[Any]] = None,
        exit: Optional[List[Any]] = None,
        # 📝 Keys are a delay in ms OR a NAMED delay resolved from
        #    MachineLogic.delays at runtime. Typing this as
        #    Dict[int, Any] wrongly rejected named delays, which the
        #    engine has always supported.
        after: Optional[Dict[Union[int, str], Any]] = None,
        invoke: Optional[Union[Dict[str, Any], List[Any]]] = None,
        on_done: Optional[Union[str, Dict[str, Any]]] = None,
        always: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
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
        # 📝 XState allows a single action as a bare string; so do we.
        self.entry: List[Any] = _as_action_list(entry)
        self._exit_actions: List[Any] = _as_action_list(exit)
        self.after = after
        self.invoke = invoke
        self.on_done = on_done
        self.always = always
        self.context = context
        self.states = states or []
        self.tags = list(tags) if tags else []
        self.meta = dict(meta) if meta else None
        # 📝 Internal: tracks functions registered via decorators
        self._enter_decorators: List[Callable[..., Any]] = []
        self._exit_decorators: List[Callable[..., Any]] = []

    @property
    def exit_actions(self) -> List[Any]:
        """The list of exit action names for this state."""
        return self._exit_actions

    # 🧷 Set by `__init_subclass__` for the `class MyState(State, ...)` form.
    _xsm_initial: bool = False
    _xsm_final: bool = False
    _xsm_parallel: bool = False
    _xsm_state_kwargs: Dict[str, Any] = {}

    def __init_subclass__(
        cls,
        *,
        initial: Optional[bool] = None,
        final: Optional[bool] = None,
        parallel: Optional[bool] = None,
        **state_kwargs: Any,
    ) -> None:
        """Support ``class MyState(State, parallel=True, after={...}):``.

        Every keyword ``State(...)`` accepts (except ``name``, ``states``
        and ``context``) is accepted here too and applied to the state
        the nested class compiles to. Flags left unset are inherited, so
        ``class fulfil(State.Parallel)`` stays parallel.
        """
        super().__init_subclass__()
        if initial is not None:
            cls._xsm_initial = initial
        if final is not None:
            cls._xsm_final = final
        if parallel is not None:
            cls._xsm_parallel = parallel
        unknown = set(state_kwargs) - _NESTED_CLASS_KWARGS
        if unknown:
            raise InvalidConfigError(
                f"class {cls.__name__}(State, ...): unknown keyword(s) "
                f"{sorted(unknown)}. Allowed: "
                f"{sorted(_NESTED_CLASS_KWARGS)}."
            )
        merged = dict(getattr(cls, "_xsm_state_kwargs", {}))
        merged.update(state_kwargs)
        cls._xsm_state_kwargs = merged

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        """On a running ``StateMachine`` instance, expose runtime queries.

        ``Light.green`` (class access) is this definition object, exactly
        as before. ``light.green`` (instance access) is a :class:`BoundState`
        that answers ``is_active`` against that instance's interpreter.
        """
        if instance is None or not hasattr(instance, "_xsm_interp"):
            return self
        return BoundState(self, instance)

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
        target: "Union[State, type]",
        *,
        event: Optional[str] = None,
        guard: Optional[str] = None,
        actions: Optional[List[Any]] = None,
        reenter: bool = False,
    ) -> "Transition":
        """Create a transition from this state to a target.

        Args:
            target: The destination ``State`` object, or a nested
                ``class X(State)`` of the same machine.
            event: The event name that triggers this transition. Inside
                a ``StateMachine`` class it may be omitted: the attribute
                the transition is assigned to names the event
                (``cycle = green.to(yellow)`` → ``CYCLE``).
            guard: Optional guard function name.
            actions: Optional list of action names.
            reenter: Force exit/re-entry on self-transitions.

        Returns:
            A ``Transition`` object.
        """
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
        event: Optional[str] = None,
        *,
        guard: Optional[str] = None,
        actions: Optional[List[Any]] = None,
    ) -> "Transition":
        """Create an internal transition (no state change).

        Args:
            event: The event name. May be omitted inside a
                ``StateMachine`` class (inferred from the attribute).
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

    def enter(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        """Decorator to register a function as an entry action.

        Only valid inside a ``StateMachine`` class definition.

        Args:
            fn: The function to register.

        Returns:
            The original function, with ``_xsm_type`` and
            ``_xsm_name`` markers attached.
        """
        name = _snake_to_camel(fn.__name__)
        _tag(fn, "action", name)
        setattr(fn, "_xsm_state_enter", self)
        self._enter_decorators.append(fn)
        if name not in self.entry:
            self.entry.append(name)
        return fn

    def exit(self, fn: Callable[..., Any]) -> Callable[..., Any]:
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
        _tag(fn, "action", name)
        setattr(fn, "_xsm_state_exit", self)
        self._exit_decorators.append(fn)
        if name not in self._exit_actions:
            self._exit_actions.append(name)
        return fn

    def service(
        self,
        fn: Optional[Callable[..., Any]] = None,
        *,
        on_done: Optional[Union[str, Dict[str, Any]]] = None,
        on_error: Optional[Union[str, Dict[str, Any]]] = None,
        id: Optional[str] = None,  # noqa: A002 -- mirrors the JSON key
        input: Optional[Any] = None,  # noqa: A002 -- mirrors the JSON key
    ) -> Any:
        """Decorator: invoke this method while the state is active.

        The decorated method becomes a ``@service`` AND the state gains an
        ``invoke`` entry pointing at it, so the two can no longer drift
        apart (``invoke={"src": "fetchUrl", ...}`` on the state plus a
        ``@service def fetch_url`` elsewhere). Only valid inside a
        ``StateMachine`` class.

        Example::

            class Fetch(StateMachine):
                idle = State(initial=True)
                loading = State()
                done = State()
                failed = State()
                start = idle.to(loading)

                @loading.service(on_done="done", on_error="failed")
                async def fetch_url(self, url):
                    ...

        As in XState, the service receives no input unless ``input`` is
        given; pass ``input=event_payload`` to forward the triggering
        event's payload (``url`` above then comes from ``sm.start(url=...)``).

        Args:
            fn: The method, when used bare as ``@state.service``.
            on_done: Target (or transition dict) for ``done.invoke``.
            on_error: Target (or transition dict) for ``error.platform``.
            id: Optional invoke id (defaults to the state id).
            input: Optional static input or ``fn(context, event)`` factory.

        Returns:
            The decorated method, or a decorator when called with keywords.
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            name = _snake_to_camel(func.__name__)
            _tag(func, "service", name)
            setattr(func, "_xsm_state_service", self)
            entry: Dict[str, Any] = {"src": name}
            if id is not None:
                entry["id"] = id
            if input is not None:
                entry["input"] = input
            if on_done is not None:
                entry["onDone"] = (
                    {"target": on_done}
                    if isinstance(on_done, str)
                    else on_done
                )
            if on_error is not None:
                entry["onError"] = (
                    {"target": on_error}
                    if isinstance(on_error, str)
                    else on_error
                )
            if self.invoke is None:
                self.invoke = entry
            elif isinstance(self.invoke, list):
                self.invoke.append(entry)
            else:
                self.invoke = [self.invoke, entry]
            return func

        if fn is not None:
            return decorator(fn)
        return decorator


class _Compound(State):
    """``class paid(State.Compound): ...`` -- a state with children."""


class _Parallel(State, parallel=True):
    """``class fulfil(State.Parallel): ...`` -- orthogonal regions."""


State.Compound = _Compound
State.Parallel = _Parallel


class BoundState:
    """A ``State`` seen through a running ``StateMachine`` instance.

    Returned by ``sm.green``; answers ``is_active`` for that instance and
    otherwise behaves like the definition it wraps.
    """

    __slots__ = ("_state", "_sm")

    def __init__(self, state: State, sm: Any) -> None:
        """Wrap *state* for the running instance *sm*.

        Args:
            state: The ``State`` definition.
            sm: The ``StateMachine`` instance (``Any``: that class lives
                in ``_pythonic_class``, which imports this module).
        """
        self._state = state
        self._sm = sm

    @property
    def definition(self) -> State:
        """The underlying ``State`` definition."""
        return self._state

    @property
    def name(self) -> str:
        """The state's name (its last path segment)."""
        return self._state.name

    @property
    def path(self) -> str:
        """Dot path from the machine root, e.g. ``"paid.packing"``."""
        paths: Dict[int, str] = type(self._sm)._xsm_paths
        return paths.get(id(self._state), self._state.name)

    @property
    def id(self) -> str:
        """Absolute state id, e.g. ``"order.paid.packing"``."""
        return f"{self._sm.machine.id}.{self.path}"

    @property
    def is_active(self) -> bool:
        """``True`` while this state (or one of its descendants) is active."""
        return bool(self._sm.interpreter.matches(self.path))

    def __getattr__(self, item: str) -> Any:
        if item.startswith("_"):
            # 📝 `copy.copy` / pickling probe dunders before `_state` exists.
            raise AttributeError(item)
        return getattr(self._state, item)

    def __repr__(self) -> str:
        flag = "active" if self.is_active else "inactive"
        return f"BoundState({self.path!r}, {flag})"


# -------------------------------------------------------------------------
# 🔀 Transition & TransitionGroup
# -------------------------------------------------------------------------


class _EventSender:
    """What ``sm.cycle`` resolves to: a callable that sends the event.

    Keyword arguments become the event payload. Positional arguments are
    refused so a payload can never be mis-ordered silently.
    """

    __slots__ = ("_sm", "_event_types")

    def __init__(self, sm: Any, event_types: Set[str]) -> None:
        """Bind the sender to an instance and the attribute's events.

        Args:
            sm: The running ``StateMachine`` instance.
            event_types: The events the attribute's transitions use.
        """
        self._sm = sm
        self._event_types = event_types

    def __call__(self, *args: Any, **payload: Any) -> Any:
        if args:
            raise TypeError(
                "Event methods take keyword arguments only, e.g. "
                f"sm.{self._display()}(amount=3); got positional {args!r}."
            )
        if len(self._event_types) != 1:
            raise TypeError(
                "This attribute combines transitions for several events "
                f"({sorted(self._event_types)}); call sm.send(<event>) "
                "with the one you mean."
            )
        return self._sm.send(next(iter(self._event_types)), **payload)

    def _display(self) -> str:
        return next(iter(self._event_types)).lower()

    def __repr__(self) -> str:
        return f"<event sender for {sorted(self._event_types)}>"


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
        source: Any,
        target: Any,
        event: Optional[str],
        guard: Optional[str] = None,
        actions: Optional[List[Any]] = None,
        reenter: bool = False,
        internal: bool = False,
    ) -> None:
        """Record one transition (see the class docstring for the fields).

        Raises:
            InvalidConfigError: ``internal=True`` together with a target.
                An internal transition never changes state, so the
                target used to be dropped without a word.
        """
        if internal and target is not None:
            raise InvalidConfigError(
                f"Transition {_state_display_name(source)!r} -> "
                f"{_state_display_name(target)!r}: internal=True takes no "
                f"target (an internal transition stays in its state). "
                f"Drop the target, or drop internal=True."
            )
        self.source = source
        self.target = target
        self.event = event
        self.guard = guard
        self.actions: List[Any] = _as_action_list(actions)
        self.reenter = reenter
        self.internal = internal

    @property
    def event_types(self) -> Set[str]:
        """The declared event (empty when it is inferred later)."""
        return {self.event} if self.event else set()

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        """``Light.cycle`` is this definition; ``light.cycle`` sends."""
        if instance is None or not hasattr(instance, "_xsm_interp"):
            return self
        return _EventSender(instance, _resolved_event_types(self, instance))

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
        src = _state_display_name(self.source)
        tgt = (
            _state_display_name(self.target)
            if self.target is not None
            else "(internal)"
        )
        return f"Transition({src!r} --{self.event!r}--> " f"{tgt!r})"


def _resolved_event_types(
    value: "Union[Transition, TransitionGroup]", instance: Any
) -> Set[str]:
    """Event types of *value* as seen by *instance*'s class, including
    names inferred from the attribute (recorded on the class overlay)."""
    overlay = getattr(type(instance), "_xsm_overlay", None)
    members = (
        value.transitions if isinstance(value, TransitionGroup) else [value]
    )
    out: Set[str] = set()
    for t in members:
        event = overlay.event_of(t) if overlay is not None else t.event
        if event:
            out.add(event)
    return out


def _state_display_name(state: Any) -> str:
    """Name of a ``State`` or of a nested ``class X(State)``."""
    if isinstance(state, type):
        return state.__name__
    return getattr(state, "name", None) or "?"


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

    @property
    def event_types(self) -> Set[str]:
        """The declared events of the members (inferred ones excluded)."""
        return {t.event for t in self.transitions if t.event}

    def __get__(self, instance: Any, owner: Any = None) -> Any:
        """``Light.cycle`` is this group; ``light.cycle`` sends."""
        if instance is None or not hasattr(instance, "_xsm_interp"):
            return self
        return _EventSender(instance, _resolved_event_types(self, instance))

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
    target: Optional[State],
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
        target: The target ``State``; ``None`` for an internal
            transition.
        guard: Optional guard function name.
        actions: Optional list of action names.
        reenter: Whether to force exit/re-entry.
        internal: Whether this is an internal transition.

    Returns:
        A ``Transition`` object.

    Raises:
        InvalidConfigError: ``internal=True`` with a target.
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
def action(fn_or_name: _DecoratedF) -> _DecoratedF: ...  # noqa: E704


@overload
def action(  # noqa: E704
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
        _tag(fn, "action", _snake_to_camel(fn.__name__))
        return fn
    else:
        # 📝 Used as @action("customName")
        name = _explicit_name(fn_or_name, "action")

        def decorator(fn: _DecoratedF) -> _DecoratedF:
            """Tag *fn* as an action registered under the chosen name."""
            _tag(fn, "action", name or _snake_to_camel(fn.__name__))
            return fn

        return decorator


@overload
def guard(fn_or_name: _DecoratedF) -> _DecoratedF: ...  # noqa: E704


@overload
def guard(  # noqa: E704
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
        _tag(fn, "guard", _snake_to_camel(fn.__name__))
        return fn
    else:
        name = _explicit_name(fn_or_name, "guard")

        def decorator(fn: _DecoratedF) -> _DecoratedF:
            """Tag *fn* as a guard under the chosen name.

            Raises:
                NotSupportedError: If *fn* is a coroutine function.
            """
            if inspect.iscoroutinefunction(fn):
                raise NotSupportedError(
                    f"Guard '{fn.__name__}' must be "
                    f"synchronous (guards cannot be async)"
                )
            _tag(fn, "guard", name or _snake_to_camel(fn.__name__))
            return fn

        return decorator


@overload
def service(fn_or_name: _DecoratedF) -> _DecoratedF: ...  # noqa: E704


@overload
def service(  # noqa: E704
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
        _tag(fn, "service", _snake_to_camel(fn.__name__))
        return fn
    else:
        name = _explicit_name(fn_or_name, "service")

        def decorator(fn: _DecoratedF) -> _DecoratedF:
            """Tag *fn* as a service registered under the chosen name."""
            _tag(fn, "service", name or _snake_to_camel(fn.__name__))
            return fn

        return decorator


# -----------------------------------------------------------------
# ⚙️ Config Compiler
# -----------------------------------------------------------------


class CompileOverlay:
    """Per-machine additions the compiler applies WITHOUT mutating the
    ``State`` / ``Transition`` objects it compiles.

    The class-based DSL derives entry/exit actions, transition actions and
    event names from a class body (naming-convention hooks, attribute-name
    events). Module-level ``State`` objects are routinely shared between
    machines, so those derivations live here, keyed by ``id(obj)``, and are
    merged in at compile time.

    ⚠️ ``id()`` keys are only stable while the objects live: the owning
    ``StateMachine`` class keeps every keyed ``State`` / ``Transition``
    alive (``_xsm_states`` / ``_xsm_transitions``), so an overlay must
    never outlive its class or be fed objects the class does not hold.

    What the overlay does NOT cover (by design, documented so nobody
    relies on more): a ``State`` takes its attribute name on first use
    in a class body, and ``@state.enter`` / ``@state.exit`` /
    ``@state.service`` register on the ``State`` object itself.
    """

    __slots__ = ("entry", "exit", "actions", "events")

    def __init__(self) -> None:
        self.entry: Dict[int, List[Any]] = {}
        self.exit: Dict[int, List[Any]] = {}
        self.actions: Dict[int, List[Any]] = {}
        self.events: Dict[int, str] = {}

    def event_of(self, t: "Transition") -> Optional[str]:
        """The declared event of *t*, else the one inferred for it."""
        return t.event if t.event is not None else self.events.get(id(t))

    def entry_of(self, state: State) -> List[Any]:
        """Overlay entry actions, then the state's own (a fresh list)."""
        return list(self.entry.get(id(state), [])) + list(state.entry)

    def exit_of(self, state: State) -> List[Any]:
        """Overlay exit actions, then the state's own (a fresh list)."""
        return list(self.exit.get(id(state), [])) + list(state._exit_actions)

    def actions_of(self, t: "Transition") -> List[Any]:
        """Overlay actions, then the transition's own (a fresh list)."""
        return list(self.actions.get(id(t), [])) + list(t.actions)


_NO_OVERLAY = CompileOverlay()


def _compile_state(
    state: State,
    all_states_by_name: Dict[str, State],
    parent_parallel: bool = False,
    overlay: CompileOverlay = _NO_OVERLAY,
) -> Dict[str, Any]:
    """Compile a single State into a JSON config dict entry.

    Args:
        state: The state to compile (recursively, with its children).
        all_states_by_name: Unused here; forwarded to children for the
            historical signature.
        parent_parallel: The parent is a parallel state.
        overlay: Class-derived entry/exit/transition additions.

    Returns:
        The state's config dict.

    Raises:
        InvalidConfigError: A final state with children, an initial
            child of a parallel state, duplicate child names or several
            initial children.
    """
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

    # 📝 Entry / Exit actions (the overlay returns fresh lists, so
    #    nothing below aliases a State object shared across builds)
    entry = overlay.entry_of(state)
    exit_acts = overlay.exit_of(state)
    if entry:
        config["entry"] = entry[0] if len(entry) == 1 else entry
    if exit_acts:
        config["exit"] = exit_acts[0] if len(exit_acts) == 1 else exit_acts

    # 📝 On (event transitions from State.on dict). Deep copies here and
    #    below: the config is handed to the parser and to callers, and a
    #    later in-place edit of it must never reach a State object that
    #    another machine shares.
    if state.on:
        config["on"] = copy.deepcopy(state.on)

    # 📝 Always → compiled to "on": {"": ...}
    if state.always is not None:
        if "on" not in config:
            config["on"] = {}
        config["on"][""] = copy.deepcopy(state.always)

    # 📝 After (delayed transitions)
    if state.after:
        config["after"] = copy.deepcopy(state.after)

    # 📝 Invoke (services). One level only: an entry's ``input`` may be a
    #    factory or a live object, which must reach the engine as is.
    if state.invoke:
        config["invoke"] = (
            [dict(e) if isinstance(e, dict) else e for e in state.invoke]
            if isinstance(state.invoke, list)
            else dict(state.invoke)
        )

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
        child_names: Set[Any] = set()
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
                overlay=overlay,
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
    context: Optional[Dict[str, Any]] = None,
    root: Optional[State] = None,
    overlay: CompileOverlay = _NO_OVERLAY,
) -> Dict[str, Any]:
    """Compile State and Transition objects into a config dict.

    Args:
        machine_id: The machine identifier string.
        states: List of top-level ``State`` objects.
        transitions: List of ``Transition`` or
            ``TransitionGroup`` objects.
        context: Optional initial context dict.
        root: Optional ``State`` carrying machine-level properties
            (see `_apply_root_properties`).
        overlay: Class-derived additions (inferred events, convention
            actions) merged in without mutating the objects.

    Returns:
        A JSON-compatible config dict suitable for
        ``create_machine()``.

    Raises:
        InvalidConfigError: On duplicate or multiple-initial states at
            one level, a transition without an event, an unknown
            transition source, or a ``State`` outside the tree whose
            name matches several states in it. A missing initial state
            only logs a warning (the engine accepts such charts).
    """
    # 🔍 Build flat lookup of all states by name
    # Uses dot-path keys to avoid collisions between
    # states with the same name at different hierarchy levels
    all_states_by_name: Dict[str, State] = {}
    # 🗺️ State object -> its dot-path from the machine root. Used to emit
    #    UNAMBIGUOUS transition targets: before 0.8.0 a nested target such
    #    as `moving.up` was written as the bare `"up"`, which only ever
    #    resolved through the runtime's fuzzy last-segment fallback (#34)
    #    and fails outright under build-time target validation (#30).
    path_of: Dict[int, str] = {}
    #: bare name -> every path carrying it (for `State` objects that are
    #: not part of the tree, see `_path_for`).
    paths_by_name: Dict[str, List[str]] = defaultdict(list)

    def _register_states(
        state_list: List[State],
        prefix: str = "",
    ) -> None:
        for s in state_list:
            key = f"{prefix}.{s.name}" if prefix else s.name
            all_states_by_name[key] = s
            path_of[id(s)] = key
            # Also register the bare name for transition
            # source lookups (backward compat)
            all_states_by_name[s.name] = s
            paths_by_name[s.name].append(key)
            if s.states:
                _register_states(s.states, prefix=key)

    _register_states(states)

    def _path_for(state: State, role: str) -> Optional[str]:
        """Path of *state*: by identity, else by a bare name that is
        unique in the tree (``None`` when no state has that name).

        🏛️ The bare-name fallback predates identity resolution and is
        kept for ``State`` objects built outside the tree, but only when
        it is unambiguous: before 0.12.0 a duplicated name silently bound
        to whichever state was registered last.
        """
        path = path_of.get(id(state))
        if path is not None:
            return path
        candidates = paths_by_name.get(state.name, [])
        if len(candidates) > 1:
            raise InvalidConfigError(
                f"Transition {role} '{state.name}' is not a state of this "
                f"machine and its name is ambiguous: {sorted(candidates)}. "
                f"Use the State object from the tree itself."
            )
        return candidates[0] if candidates else None

    # 🔍 Validate top-level: duplicates, initial
    top_names: Set[Any] = set()
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
        if overlay.event_of(t) is None:
            raise InvalidConfigError(
                f"Transition {_state_display_name(t.source)!r} -> "
                f"{_state_display_name(t.target)!r} has no event. Pass "
                f"event=... to State.to(), or assign the transition to a "
                f"class attribute of a StateMachine so the attribute "
                f"name becomes the event."
            )
        if isinstance(t.source, type) or isinstance(t.target, type):
            raise InvalidConfigError(
                "A nested `class X(State)` can only be used as a "
                "transition source or target inside the StateMachine "
                "class that defines it."
            )
        # 🗺️ Resolve the source by IDENTITY first (two states may share a
        #    name under different parents); fall back to the bare name for
        #    `State` objects built outside this tree.
        src_path = _path_for(t.source, "source")
        if src_path is None:
            raise InvalidConfigError(
                f"Transition source "
                f"'{t.source.name}' "
                f"is not a defined state"
            )
        if t.target is not None:
            _path_for(t.target, "target")
        src = all_states_by_name[src_path]
        if src.final and src.states:
            raise InvalidConfigError(
                f"Final state '{t.source.name}' cannot have child states"
            )

    # ⚙️ Compile each top-level state
    state_configs: Dict[str, Any] = {}
    for s in states:
        state_configs[s.name] = _compile_state(
            s, all_states_by_name, overlay=overlay
        )

    # ⚙️ Merge transitions into state configs, keyed by the source's path
    #    so same-named states under different parents stay apart.
    trans_by_source_event: Dict[str, Dict[str, List[Transition]]] = (
        defaultdict(lambda: defaultdict(list))
    )

    for t in flat_transitions:
        # 📝 validated non-None in the loop above.
        src_path = str(_path_for(t.source, "source"))
        # 📝 the event is validated non-None above.
        event_name = str(overlay.event_of(t))
        trans_by_source_event[src_path][event_name].append(t)

    def _config_at(path: str) -> Dict[str, Any]:
        node: Dict[str, Any] = {"states": state_configs}
        for segment in path.split("."):
            node = node["states"][segment]
        return node

    for src_path, by_event in trans_by_source_event.items():
        state_config = _config_at(src_path)
        if "on" not in state_config:
            state_config["on"] = {}
        for event, t_list in by_event.items():
            compiled = []
            for t in t_list:
                entry: Dict[str, Any] = {}
                if not t.internal and t.target is not None:
                    path = _path_for(t.target, "target") or t.target.name
                    # A top-level target keeps its bare name (the
                    # established output format). A NESTED target is
                    # emitted as an absolute `#machine.path`, which is
                    # the only form that resolves unambiguously from
                    # any source (and passes build-time validation).
                    entry["target"] = (
                        f"#{machine_id}.{path}" if "." in path else path
                    )
                if t.guard:
                    entry["guard"] = t.guard
                actions = overlay.actions_of(t)
                if actions:
                    entry["actions"] = actions
                if t.reenter:
                    entry["reenter"] = True
                compiled.append(entry)
            # 🏛️ Merge rule (pythonic-api spec): Transition objects REPLACE a
            #    `State(on=)` entry for the same event -- `.to()` is the
            #    more specific API. Pinned by TestMergeRules.
            if len(compiled) == 1:
                state_config["on"][event] = compiled[0]
            else:
                state_config["on"][event] = compiled

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
    _apply_root_properties(result, root)

    return result


def _apply_root_properties(
    config: Dict[str, Any],
    root: Optional[State],
) -> None:
    """Merge machine-level (root) properties into *config* in place.

    🏛️ Extracted from ``_compile_config`` rather than inlined: eleven
    independent branches pushed that function past the project's
    complexity gate, and none of them interact with the state-compilation
    logic around them.

    Real machines routinely declare a global escape transition such as
    ``on: {EMERGENCY: ...}`` at the top level. Before v0.7.0 these were
    dropped, so the generated machine simply could not be escaped.
    """
    if root is None:
        return

    if root.parallel:
        config["type"] = "parallel"
    if root.on:
        config["on"] = dict(root.on)
    if root.always is not None:
        config.setdefault("on", {})[""] = root.always
    if root.entry:
        config["entry"] = list(root.entry)
    if root.exit_actions:
        config["exit"] = list(root.exit_actions)
    if root.after:
        config["after"] = dict(root.after)
    if root.invoke:
        config["invoke"] = root.invoke
    if root.on_done is not None:
        config["onDone"] = (
            {"target": root.on_done}
            if isinstance(root.on_done, str)
            else root.on_done
        )
    if root.tags:
        config["tags"] = list(root.tags)
    if root.meta:
        config["meta"] = dict(root.meta)


# -----------------------------------------------------------------
# ⚙️ Logic Compiler
# -----------------------------------------------------------------


def _register_once(
    table: Dict[str, Any], name: str, fn: Callable[..., Any], kind: str
) -> None:
    """Add *fn* to *table* under *name*, refusing a second registration.

    Args:
        table: The action / guard / service table being filled.
        name: The registration name.
        fn: The (adapted) callable.
        kind: Its kind, for the error message.

    Raises:
        InvalidConfigError: *name* is already registered. Before 0.12.0
            the later callable silently replaced the earlier one.
    """
    if name in table:
        raise InvalidConfigError(
            f"Two {kind}s are registered as '{name}'; give one of them "
            f"a different name (@{kind}('otherName'))."
        )
    table[name] = fn


def _compile_logic_from_functions(
    actions: List[Callable[..., Any]],
    guards: List[Callable[..., Any]],
    services: List[Callable[..., Any]],
) -> MachineLogic[Any]:
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
        InvalidConfigError: If any function was decorated with
            ``@state.enter``, ``@state.exit`` or ``@state.service``
            (only valid inside a ``StateMachine`` class), a callable
            decorated as one kind is passed as another, two callables
            register the same name, or a callable has no name at all.
    """
    action_dict: Dict[str, ActionCallable] = {}
    guard_dict: Dict[str, GuardCallable] = {}
    service_dict: Dict[str, ServiceCallable] = {}

    all_fns = list(actions) + list(guards) + list(services)
    for fn in all_fns:
        if hasattr(fn, "_xsm_state_service"):
            owner = getattr(fn, "_xsm_state_service").name
            raise InvalidConfigError(
                f"@{owner}.service "
                f"decorator is only valid inside a "
                f"StateMachine class"
            )
        if hasattr(fn, "_xsm_state_enter"):
            owner = getattr(fn, "_xsm_state_enter").name
            raise InvalidConfigError(
                f"@{owner}.enter "
                f"decorator is only valid inside a "
                f"StateMachine class"
            )
        if hasattr(fn, "_xsm_state_exit"):
            owner = getattr(fn, "_xsm_state_exit").name
            raise InvalidConfigError(
                f"@{owner}.exit "
                f"decorator is only valid inside a "
                f"StateMachine class"
            )

    for kind, fns, table in (
        ("action", actions, action_dict),
        ("guard", guards, guard_dict),
        ("service", services, service_dict),
    ):
        for fn in fns:
            marked = getattr(fn, "_xsm_type", None)
            if marked is not None and marked != kind:
                raise InvalidConfigError(
                    f"{fn!r} is decorated with @{marked} but was passed "
                    f"in {kind}s=[...]; pass it in {marked}s=[...]."
                )
            name = _callable_name(fn, kind)
            _register_once(table, name, adapt_callable(fn, kind), kind)

    return MachineLogic(
        actions=action_dict,
        guards=guard_dict,
        services=service_dict,
    )


def _compile_logic_from_instance(
    instance: object,
    decorated: List[Callable[..., Any]],
    sink: Optional[List[Any]] = None,
) -> MachineLogic[Any]:
    """Compile class instance methods into a MachineLogic.

    Uses ``functools.partial(method, instance)`` to bind
    ``self``, then wraps each callable with the signature-based
    argument adapter so a method may declare only the parameters it
    needs (see ``_pythonic_runtime.adapt_callable``).

    Args:
        instance: The object instance whose methods are
            being compiled.
        decorated: List of unbound decorated methods
            (with ``_xsm_type`` and ``_xsm_name``).
        sink: Optional list collecting action return values, so the
            instance façade can hand them back from ``send()``.

    Returns:
        A ``MachineLogic`` instance with bound callables.

    Raises:
        InvalidConfigError: Two different methods register the same
            name for one kind, or a method carries an unknown kind.
    """
    action_dict: Dict[str, Any] = {}
    guard_dict: Dict[str, Any] = {}
    service_dict: Dict[str, Any] = {}

    tables = {
        "action": action_dict,
        "guard": guard_dict,
        "service": service_dict,
    }
    seen: Dict[int, None] = {}
    for fn in decorated:
        if id(fn) in seen:
            # 📝 One function under two attribute names (`b = a`).
            continue
        seen[id(fn)] = None
        name = getattr(fn, "_xsm_name")
        xsm_type = getattr(fn, "_xsm_type")
        table = tables.get(xsm_type)
        if table is None:
            raise InvalidConfigError(
                f"{fn!r} is marked with an unknown kind {xsm_type!r}; "
                f"use @action, @guard or @service."
            )
        bound = adapt_callable(
            functools.partial(fn, instance), xsm_type, sink=sink
        )
        _register_once(table, name, bound, xsm_type)

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
    actions: Optional[List[Callable[..., Any]]] = None,
    guards: Optional[List[Callable[..., Any]]] = None,
    services: Optional[List[Callable[..., Any]]] = None,
    context: Optional[Dict[str, Any]] = None,
    root: Optional[State] = None,
) -> "MachineNode[Any]":
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
