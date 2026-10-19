# src/xstate_statemachine/_pythonic_class.py
"""
🏛️ Class-based Pythonic DSL: ``StateMachine`` and its metaclass.

Collects states, transitions and callbacks from a class body, binds
naming-convention hooks, and provides the instance façade
(``sm = Machine(); sm.cycle(); sm.state``).

Nothing here mutates the ``State`` / ``Transition`` objects a class body
declares: everything derived from the body (inferred event names,
convention-bound actions) is recorded in a `CompileOverlay` that belongs
to the class, so module-level ``State`` objects can be shared between
machines safely.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import collections
import copy
import functools
import inspect
import logging
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    FrozenSet,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from ._pythonic_core import (
    _RESERVED_NAMES,
    CompileOverlay,
    State,
    Transition,
    TransitionGroup,
    _attr_to_event,
    _compile_config,
    _compile_logic_from_instance,
    _Compound,
    _Parallel,
    _snake_to_camel,
    _state_display_name,
)
from ._pythonic_runtime import ConventionHooksPlugin, adapt_callable
from .events import Event
from .exceptions import (
    ImplementationMissingError,
    InterpreterStoppedError,
    InvalidConfigError,
    TransitionNotAllowedError,
    UnknownEventError,
)
from .factory import create_machine as _original_create_machine
from .models import MachineNode

logger = logging.getLogger("xstate_statemachine.pythonic")

#: How many action return values `send()` keeps between folds. Sends made
#: directly on `sm.interpreter` also feed the sink; the bound stops a
#: long-running machine from growing it without limit.
RESULT_SINK_MAXLEN = 1024

#: Lifecycle methods of the instance façade that a transition attribute
#: may legitimately share a name with. The transition is kept (the event
#: exists, `sm.send("STOP")` works) but it gets no `sm.stop()` sugar: the
#: method always stops the machine. Letting the event win would turn a
#: documented shutdown call into a silent no-op shutdown, which is the
#: failure mode this project refuses.
_LIFECYCLE_NAMES = frozenset({"start", "stop"})

_GENERIC_HOOKS = (
    "on_enter_state",
    "on_exit_state",
    "on_transition",
    "before_transition",
    "after_transition",
)


# -------------------------------------------------------------------------
# 🧺 Collecting a class body
# -------------------------------------------------------------------------


def _is_nested_state_class(value: Any) -> bool:
    """``class paid(State): ...`` in a machine or state body."""
    return (
        isinstance(value, type)
        and issubclass(value, State)
        and value not in (State, _Compound, _Parallel)
    )


def _is_plain_function(value: Any) -> bool:
    """A method defined in the class body that carries no DSL marker."""
    return inspect.isfunction(value) and not hasattr(value, "_xsm_type")


def _members(value: Union[Transition, TransitionGroup]) -> List[Transition]:
    return value.transitions if isinstance(value, TransitionGroup) else [value]


class _Collected:
    """Everything a class body (plus its bases) contributes."""

    def __init__(self) -> None:
        #: top-level states by attribute name (a subclass overrides a base)
        self.state_attrs: Dict[str, State] = {}
        #: transitions by attribute name
        self.transition_attrs: Dict[
            str, Union[Transition, TransitionGroup]
        ] = {}
        self.decorated: Dict[str, Callable[..., Any]] = {}
        self.plain: Dict[str, Callable[..., Any]] = {}
        #: nested ``class X(State)`` → the ``State`` it compiled to
        self.resolved: Dict[type, State] = {}
        #: every transition declared inside a nested class body
        self.nested: List[Union[Transition, TransitionGroup]] = []
        #: the first nested transition per attribute name (exposed as an
        #: event method on the machine)
        self.nested_attrs: Dict[str, Union[Transition, TransitionGroup]] = {}
        #: transition attributes that collide with a lifecycle method and
        #: must be removed from the class namespace so the method wins
        self.shadowing: Set[str] = set()
        self.overlay = CompileOverlay()

    # Convenience views -------------------------------------------------
    @property
    def states(self) -> List[State]:
        return list(self.state_attrs.values())

    @property
    def transitions(self) -> List[Union[Transition, TransitionGroup]]:
        return list(self.transition_attrs.values()) + list(self.nested)

    def flat(self) -> List[Transition]:
        out: List[Transition] = []
        for t in self.transitions:
            out.extend(_members(t))
        return out

    def event_types(self, attr_name: str) -> Set[str]:
        value = self.transition_attrs.get(attr_name) or self.nested_attrs.get(
            attr_name
        )
        if value is None:
            return set()
        return {
            e for e in (self.overlay.event_of(t) for t in _members(value)) if e
        }

    def inherit(self, base: "_Collected") -> None:
        """Start from a base class's collection (subclass wins on names)."""
        self.state_attrs.update(base.state_attrs)
        self.transition_attrs.update(base.transition_attrs)
        self.decorated.update(base.decorated)
        self.plain.update(base.plain)
        self.resolved.update(base.resolved)
        self.nested.extend(t for t in base.nested if t not in self.nested)
        self.nested_attrs.update(base.nested_attrs)
        self.overlay.events.update(base.overlay.events)


def _infer_events(
    value: Union[Transition, TransitionGroup],
    attr_name: str,
    overlay: CompileOverlay,
) -> None:
    """Record a missing ``event`` from the attribute the transition is
    assigned to (``cycle = green.to(yellow)`` → ``CYCLE``)."""
    for t in _members(value):
        if t.event is None and id(t) not in overlay.events:
            overlay.events[id(t)] = _attr_to_event(attr_name)


def _build_nested_state(
    attr_name: str, klass: type, c: _Collected, cls_name: str
) -> State:
    """Compile ``class attr_name(State, ...)`` into a ``State``.

    Child ``State`` instances, nested classes and transitions declared
    inside the body are all honoured; before 0.12.0 the transitions
    were silently dropped.
    """
    children: List[State] = []
    for child_name, child_value in vars(klass).items():
        if child_name.startswith("_"):
            continue
        if _is_nested_state_class(child_value):
            children.append(
                _build_nested_state(child_name, child_value, c, cls_name)
            )
        elif isinstance(child_value, State):
            if not child_value.name:
                child_value.name = child_name
            children.append(child_value)
        elif isinstance(child_value, (Transition, TransitionGroup)):
            _infer_events(child_value, child_name, c.overlay)
            c.nested.append(child_value)
            c.nested_attrs.setdefault(child_name, child_value)
        elif callable(child_value):
            logger.warning(
                "⚠️ %s.%s.%s: callables inside a nested state class are "
                "ignored; define hooks and @action methods on the "
                "StateMachine class itself.",
                cls_name,
                attr_name,
                child_name,
            )
    kwargs = dict(getattr(klass, "_xsm_state_kwargs", {}))
    state = State(
        name=attr_name,
        initial=getattr(klass, "_xsm_initial", False),
        final=getattr(klass, "_xsm_final", False),
        parallel=getattr(klass, "_xsm_parallel", False),
        states=children or None,
        **kwargs,
    )
    c.resolved[klass] = state
    return state


def _check_reserved(attr_name: str, what: str) -> None:
    if attr_name in _RESERVED_NAMES:
        raise InvalidConfigError(
            f"'{attr_name}' is reserved: it is part of the StateMachine "
            f"instance API and cannot name a {what}. Rename the attribute "
            f"(use event=... on the transition to keep the event name)."
        )


def _collect_namespace(
    namespace: Dict[str, Any], c: _Collected, cls_name: str
) -> None:
    """Walk a ``StateMachine`` subclass body into *c*."""
    for attr_name, attr_value in list(namespace.items()):
        if attr_name.startswith("_"):
            continue
        if _is_nested_state_class(attr_value):
            _check_reserved(attr_name, "state")
            c.state_attrs[attr_name] = _build_nested_state(
                attr_name, attr_value, c, cls_name
            )
        elif isinstance(attr_value, State):
            # 🌳 `machine_root` carries machine-level properties
            #    (on/entry/exit/tags/parallel) rather than being a
            #    state of the machine. Keep it out of `states`.
            #
            # 🛡️ A user may legitimately want a STATE called
            #    "machine_root". Silently dropping it would be exactly
            #    the invisible data loss this API exists to avoid, so
            #    the two cases are told apart by whether an explicit
            #    name was given, and the ambiguous case is reported.
            if attr_name == "machine_root":
                if attr_value.name == "machine_root":
                    raise InvalidConfigError(
                        "'machine_root' is reserved for machine-level "
                        "properties and cannot also be a state name. "
                        "Rename the state, or leave machine_root's "
                        "name empty to use it as the machine root."
                    )
                continue
            _check_reserved(attr_name, "state")
            if not attr_value.name:
                attr_value.name = attr_name
            c.state_attrs[attr_name] = attr_value
        elif isinstance(attr_value, (Transition, TransitionGroup)):
            _check_reserved(attr_name, "transition")
            _infer_events(attr_value, attr_name, c.overlay)
            c.transition_attrs[attr_name] = attr_value
            if attr_name in _LIFECYCLE_NAMES:
                c.shadowing.add(attr_name)
                events = sorted(
                    e
                    for t in _members(attr_value)
                    for e in [c.overlay.event_of(t)]
                    if e
                )
                logger.warning(
                    "⚠️ %s.%s is a transition, but %s() is the machine's "
                    "lifecycle method and keeps that meaning: sm.%s() will "
                    "%s the machine, not send %s. Send the event with "
                    "sm.send(%r).",
                    cls_name,
                    attr_name,
                    attr_name,
                    attr_name,
                    attr_name,
                    "/".join(events) or "the event",
                    events[0] if events else attr_name.upper(),
                )
        elif callable(attr_value) and hasattr(attr_value, "_xsm_type"):
            c.decorated[attr_name] = attr_value
            c.plain.pop(attr_name, None)
        elif _is_plain_function(attr_value):
            c.plain[attr_name] = attr_value
            c.decorated.pop(attr_name, None)


def _resolve_class_refs(c: _Collected) -> None:
    """Replace nested-class sources/targets with their ``State``."""
    for t in c.flat():
        for attr in ("source", "target"):
            ref = getattr(t, attr)
            if isinstance(ref, type):
                if ref not in c.resolved:
                    raise InvalidConfigError(
                        f"Transition {t!r} refers to nested state class "
                        f"'{ref.__name__}', which is not defined in this "
                        f"StateMachine."
                    )
                setattr(t, attr, c.resolved[ref])


def _drop_leaked_children(c: _Collected) -> None:
    """A ``State`` listed in another state's ``states=[...]`` is a child,
    even when it is also a class attribute. Before 0.12.0 it was compiled
    twice, once at the root."""
    descendants: Set[int] = set()

    def _walk(s: State) -> None:
        for child in s.states:
            descendants.add(id(child))
            _walk(child)

    for s in c.states:
        _walk(s)
    c.state_attrs = {
        k: v for k, v in c.state_attrs.items() if id(v) not in descendants
    }


def _all_states(states: List[State]) -> Dict[str, List[State]]:
    """Every state in the tree, grouped by (non-unique) name."""
    out: Dict[str, List[State]] = collections.defaultdict(list)

    def _walk(s: State) -> None:
        out[s.name].append(s)
        for child in s.states:
            _walk(child)

    for s in states:
        _walk(s)
    return out


def _state_paths(states: List[State]) -> Dict[int, str]:
    paths: Dict[int, str] = {}

    def _walk(s: State, prefix: str) -> None:
        path = f"{prefix}.{s.name}" if prefix else s.name
        paths[id(s)] = path
        for child in s.states:
            _walk(child, path)

    for s in states:
        _walk(s, "")
    return paths


# -------------------------------------------------------------------------
# 🪝 Naming-convention hooks
# -------------------------------------------------------------------------


class _Conventions:
    """``before``/``after`` hooks keyed by event type (``"*"`` = every
    transition); ``bound`` is the set of attribute names consumed."""

    def __init__(self) -> None:
        self.before: Dict[str, List[Callable[..., Any]]] = (
            collections.defaultdict(list)
        )
        self.after: Dict[str, List[Callable[..., Any]]] = (
            collections.defaultdict(list)
        )


def _mark_action(fn: Callable[..., Any]) -> str:
    """Tag a convention hook as an action; returns its registered name."""
    name = _snake_to_camel(fn.__name__)
    setattr(fn, "_xsm_type", "action")
    setattr(fn, "_xsm_name", name)
    return name


def _prepend(table: Dict[int, List[Any]], key: int, item: Any) -> None:
    table.setdefault(key, []).insert(0, item)


def _reject_async_hook(fn: Callable[..., Any], cls_name: str) -> None:
    if inspect.iscoroutinefunction(fn):
        raise InvalidConfigError(
            f"{cls_name}.{fn.__name__}: before_/after_ hooks run from "
            f"plugin callbacks and cannot be `async def`. Use a plain "
            f"`def`, or an `on_<event>` / entry action for async work."
        )


def _apply_specific_hook(
    attr_name: str,
    fn: Callable[..., Any],
    c: _Collected,
    conv: _Conventions,
    by_name: Dict[str, List[State]],
    cls_name: str,
) -> None:
    """Bind ``on_enter_<state>`` / ``on_<event>`` / ``before_<event>`` /
    ``after_<event>``; unmatched suffixes warn (state hooks, before/after)
    or are left alone (``on_<anything>`` is too generic to warn about)."""

    def _warn(kind: str, suffix: str) -> None:
        logger.warning(
            "⚠️ %s.%s looks like a %s hook but '%s' is not a %s of this "
            "machine; it will never run.",
            cls_name,
            attr_name,
            kind,
            suffix,
            kind,
        )

    if attr_name.startswith(("on_enter_", "on_exit_")):
        is_enter = attr_name.startswith("on_enter_")
        suffix = attr_name[len("on_enter_" if is_enter else "on_exit_") :]
        targets = by_name.get(suffix)
        if not targets:
            _warn("state", suffix)
            return
        name = _mark_action(fn)
        c.decorated[attr_name] = fn
        table = c.overlay.entry if is_enter else c.overlay.exit
        for s in targets:
            _prepend(table, id(s), name)
        return

    all_events = {e for t in c.flat() for e in [c.overlay.event_of(t)] if e}
    lower_events = {e.lower(): e for e in all_events}
    for prefix in ("before_", "after_", "on_"):
        if not attr_name.startswith(prefix):
            continue
        suffix = attr_name[len(prefix) :]
        evs = c.event_types(suffix) or (
            {lower_events[suffix]} if suffix in lower_events else set()
        )
        if not evs:
            if prefix != "on_":
                _warn("event", suffix)
            return
        if prefix == "on_":
            name = _mark_action(fn)
            c.decorated[attr_name] = fn
            for t in c.flat():
                if c.overlay.event_of(t) in evs:
                    _prepend(c.overlay.actions, id(t), name)
            return
        _reject_async_hook(fn, cls_name)
        hooks = conv.before if prefix == "before_" else conv.after
        for ev in evs:
            hooks[ev].append(fn)
        return


def _apply_generic_hook(
    attr_name: str,
    fn: Callable[..., Any],
    c: _Collected,
    conv: _Conventions,
    by_name: Dict[str, List[State]],
    cls_name: str,
) -> None:
    if attr_name in ("on_enter_state", "on_exit_state"):
        name = _mark_action(fn)
        c.decorated[attr_name] = fn
        table = (
            c.overlay.entry
            if attr_name == "on_enter_state"
            else c.overlay.exit
        )
        for group in by_name.values():
            for s in group:
                _prepend(
                    table, id(s), {"type": name, "params": {"state": s.name}}
                )
    elif attr_name == "on_transition":
        name = _mark_action(fn)
        c.decorated[attr_name] = fn
        for t in c.flat():
            tgt = t.target if t.target is not None else t.source
            _prepend(
                c.overlay.actions,
                id(t),
                {
                    "type": name,
                    "params": {
                        "source": _state_display_name(t.source),
                        "target": _state_display_name(tgt),
                    },
                },
            )
    else:
        _reject_async_hook(fn, cls_name)
        hooks = conv.before if attr_name == "before_transition" else conv.after
        hooks["*"].append(fn)


def _apply_conventions(c: _Collected, cls_name: str) -> _Conventions:
    """Bind naming-convention methods to the chart via the overlay.

    Specific hooks are applied first and generic hooks last; because each
    binding is PREPENDED, the resulting order inside a slot is generic,
    then specific, then explicitly listed actions -- the python-statemachine
    order, independent of where the methods sit in the class body.
    """
    conv = _Conventions()
    by_name = _all_states(c.states)
    specific = {k: v for k, v in c.plain.items() if k not in _GENERIC_HOOKS}
    generic = {k: v for k, v in c.plain.items() if k in _GENERIC_HOOKS}
    for attr_name, fn in specific.items():
        _apply_specific_hook(attr_name, fn, c, conv, by_name, cls_name)
    for attr_name, fn in generic.items():
        _apply_generic_hook(attr_name, fn, c, conv, by_name, cls_name)
    return conv


# -------------------------------------------------------------------------
# 🏛️ Metaclass
# -------------------------------------------------------------------------


class _StateMachineMeta(type):
    """Metaclass for ``StateMachine`` that collects States,
    Transitions, and decorated methods at class-definition time.
    """

    def __new__(
        mcs, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]
    ) -> Any:
        # Skip processing for the base StateMachine class
        if name == "StateMachine" and not any(
            hasattr(b, "_xsm_is_base") for b in bases
        ):
            cls = super().__new__(mcs, name, bases, namespace)
            setattr(cls, "_xsm_is_base", True)
            return cls

        c = _Collected()
        # 🧬 A subclass of a machine class inherits its chart and callbacks;
        #    attributes it redefines win. Before 0.12.0 the base's states
        #    were silently dropped and the subclass compiled to an empty
        #    machine.
        for base in reversed(bases):
            parent = getattr(base, "_xsm_collected", None)
            if isinstance(parent, _Collected):
                c.inherit(parent)
        _collect_namespace(namespace, c, name)
        _resolve_class_refs(c)
        _drop_leaked_children(c)
        # 🔗 Expose nested-class transitions as event methods on the
        #    machine itself; a top-level attribute of the same name wins,
        #    and lifecycle / reserved names are never shadowed.
        for attr_name, value in c.nested_attrs.items():
            if (
                attr_name not in namespace
                and attr_name not in _RESERVED_NAMES
                and attr_name not in _LIFECYCLE_NAMES
            ):
                namespace[attr_name] = value
        # 🚦 A transition called `start` / `stop` stays in the chart but
        #    leaves the class namespace, so `sm.start()` / `sm.stop()`
        #    resolve to the lifecycle methods on `StateMachine`.
        for attr_name in c.shadowing:
            namespace.pop(attr_name, None)
        conventions = _apply_conventions(c, name)

        cls = super().__new__(mcs, name, bases, namespace)
        setattr(cls, "_xsm_collected", c)
        setattr(cls, "_xsm_states", c.states)
        setattr(cls, "_xsm_transitions", c.transitions)
        setattr(cls, "_xsm_decorated", list(c.decorated.values()))
        setattr(cls, "_xsm_overlay", c.overlay)
        setattr(cls, "_xsm_resolved", dict(c.resolved))
        setattr(cls, "_xsm_before", dict(conventions.before))
        setattr(cls, "_xsm_after", dict(conventions.after))
        setattr(cls, "_xsm_paths", _state_paths(c.states))
        setattr(
            cls,
            "_xsm_has_async",
            any(
                inspect.iscoroutinefunction(fn) for fn in c.decorated.values()
            ),
        )
        setattr(cls, "_xsm_config_cache", None)
        return cls


# -------------------------------------------------------------------------
# 🚦 StateMachine
# -------------------------------------------------------------------------


class StateMachine(metaclass=_StateMachineMeta):
    """Base class for defining state machines using class syntax.

    Subclass this and define ``State`` attributes, transitions, and
    callbacks. The attribute a transition is assigned to names its
    event, callbacks may be bound by naming convention
    (``on_enter_<state>``, ``on_<event>``, ``before_<event>``, ...) or
    with the ``@action`` / ``@guard`` / ``@service`` decorators, and
    each callback declares only the arguments it needs.

    Instantiating the class gives a **running machine**::

        class Light(StateMachine):
            green = State(initial=True)
            yellow = State()
            cycle = green.to(yellow) | yellow.to(green)

            def on_enter_yellow(self):
                print("slow down")

        with Light() as light:     # started, in `green`; stopped on exit
            light.cycle()          # same as light.send("CYCLE")
            light.state            # 'yellow'
            light.yellow.is_active # True

    ``Light.create_machine()`` still returns the bare ``MachineNode`` for
    use with your own ``Interpreter`` / ``SyncInterpreter``.

    **Lifecycle.** ``with Machine() as sm:`` (``async with`` on the
    asyncio engine) is the recommended idiom: it stops the machine on
    exit, exceptions included, and does not depend on method names. For
    an instance that outlives a block, ``sm.interpreter.start()`` /
    ``sm.interpreter.stop()`` are the explicit escape hatch; ``sm.start()``
    / ``sm.stop()`` are conveniences with the same effect. They are always
    the lifecycle: a transition may be *named* ``start`` or ``stop`` --
    common event names, and real charts use them -- but it then gets no
    ``sm.stop()`` sugar; send it with ``sm.send("STOP")``. A warning is
    logged when the class is defined so the collision is never a surprise
    at run time. Names that would break the façade itself (``send``,
    ``state``, ``context``, ``status``, ...) raise ``InvalidConfigError``
    instead; see ``_RESERVED_NAMES``.

    Class Attributes:
        machine_id: Optional machine ID (defaults to class name).
        initial_context: Optional initial context dict.
        machine_root: Optional ``State`` carrying machine-level
            ``on`` / ``entry`` / ``exit`` / ``tags`` / ``parallel``.
        engine: ``"sync"``, ``"async"`` or ``"auto"`` (default). Auto
            picks the asyncio engine when any callback is ``async def``.
            On an instance this reads as the engine actually chosen.
        strict: Refuse undeclared events (``UnknownEventError``) and
            declared events no active state will take right now
            (``TransitionNotAllowedError``) at the ``send()`` call site.
            On an instance this reads as the effective setting.
        validate_logic: When instantiating, check that every guard,
            action and service the chart names is implemented (default
            on). ``create_machine(validate=True)`` applies the same check
            to a bare ``MachineNode``.
    """

    machine_id: Optional[str] = None
    initial_context: Optional[Dict[str, Any]] = None
    machine_root: Optional[State] = None
    engine: str = "auto"
    strict: bool = False
    validate_logic: bool = True

    # 🧷 Collected by `_StateMachineMeta` when the subclass body runs.
    _xsm_collected: _Collected
    _xsm_states: List[State]
    _xsm_transitions: List[Union[Transition, TransitionGroup]]
    _xsm_decorated: List[Callable[..., Any]]
    _xsm_overlay: CompileOverlay
    _xsm_resolved: Dict[type, State]
    _xsm_before: Dict[str, List[Callable[..., Any]]]
    _xsm_after: Dict[str, List[Callable[..., Any]]]
    _xsm_paths: Dict[int, str]
    _xsm_has_async: bool
    _xsm_config_cache: Optional[Dict[str, Any]]

    # ------------------------------------------------------------------
    # 🏗️ Construction
    # ------------------------------------------------------------------
    def __init__(
        self,
        context: Optional[Dict[str, Any]] = None,
        *,
        state: Union[None, str, List[str]] = None,
        engine: Optional[str] = None,
        strict: Optional[bool] = None,
        plugins: Optional[List[Any]] = None,
        clock: Optional[Any] = None,
    ) -> None:
        """Build and (for the sync engine) start a machine instance.

        Args:
            context: Initial context, overriding ``initial_context``.
            state: Start already IN this state (a dot path relative to the
                machine root, e.g. ``"paid.packing"``, or several for
                parallel regions) without running entry actions -- the
                "state string stored on a model row" case. Compound states
                are completed to their initial leaves. See
                ``BaseInterpreter.from_state``.
            engine: ``"sync"`` / ``"async"``; defaults to the class's
                ``engine`` attribute.
            strict: Overrides the class's ``strict`` attribute.
            plugins: Extra ``PluginBase`` instances to attach.
            clock: A ``Clock`` for ``after`` timers; pass a
                ``SimulatedClock`` in tests and drive it with
                ``clock.increment(ms)``.
        """
        if getattr(self, "_xsm_logic_only", False):
            # 📝 `create_machine()` only needs `self` to bind callbacks.
            return
        cls = type(self)
        chosen = engine or cls.engine
        if chosen == "auto":
            chosen = "async" if cls._xsm_has_async else "sync"
        if chosen not in ("sync", "async"):
            raise InvalidConfigError(
                f"engine must be 'sync', 'async' or 'auto', not {chosen!r}"
            )
        self.engine = chosen
        self.strict = cls.strict if strict is None else strict
        self._xsm_results: Deque[Any] = collections.deque(
            maxlen=RESULT_SINK_MAXLEN
        )
        self._xsm_send_lock: Optional[asyncio.Lock] = None
        machine = cls._build_machine(
            instance=self,
            context=context,
            sink=self._xsm_results,
            validate=cls.validate_logic,
        )
        self._xsm_machine: MachineNode[Any] = machine

        if chosen == "async":
            from .interpreter import Interpreter

            engine_cls: Any = Interpreter
        else:
            from .sync_interpreter import SyncInterpreter

            engine_cls = SyncInterpreter

        if state is None:
            interp: Any = engine_cls(machine, strict=self.strict, clock=clock)
        else:
            # 🗃️ Restore semantics: the configuration is applied without
            #    entry actions, as a snapshot restore would. `from_state`
            #    builds the interpreter itself, so `strict` is set after.
            interp = engine_cls.from_state(
                machine, state, context=context, clock=clock
            )
            interp.strict = self.strict

        if cls._xsm_before or cls._xsm_after:
            interp.use(
                ConventionHooksPlugin(
                    before=self._bind_hooks(cls._xsm_before),
                    after=self._bind_hooks(cls._xsm_after),
                )
            )
        for plugin in plugins or []:
            interp.use(plugin)
        self._xsm_interp: Any = interp
        if chosen == "sync":
            interp.start()

    def _bind_hooks(
        self, hooks: Dict[str, List[Callable[..., Any]]]
    ) -> Dict[str, List[Callable[..., Any]]]:
        return {
            event: [
                adapt_callable(functools.partial(fn, self), "action")
                for fn in fns
            ]
            for event, fns in hooks.items()
        }

    @classmethod
    def _compiled_config(cls) -> Dict[str, Any]:
        """The context-free XState config, compiled once per class."""
        cached = cls.__dict__.get("_xsm_config_cache")
        if cached is None:
            cached = _compile_config(
                machine_id=cls.machine_id or cls.__name__,
                states=cls._xsm_states,
                transitions=cls._xsm_transitions,
                context=None,
                root=getattr(cls, "machine_root", None),
                overlay=cls._xsm_overlay,
            )
            cls._xsm_config_cache = cached
        return copy.deepcopy(cached)

    @classmethod
    def _build_machine(
        cls,
        instance: Any,
        context: Optional[Dict[str, Any]],
        sink: Optional[Any],
        validate: bool,
    ) -> MachineNode[Any]:
        config = cls._compiled_config()
        ctx = context if context is not None else cls.initial_context
        if ctx is not None:
            config["context"] = copy.deepcopy(ctx)
        logic = _compile_logic_from_instance(
            instance=instance, decorated=cls._xsm_decorated, sink=sink
        )
        machine = _original_create_machine(config, logic=logic)
        if validate:
            _validate_logic(machine, cls.__name__)
        return machine

    @classmethod
    def create_machine(
        cls,
        context: Optional[Dict[str, Any]] = None,
        *,
        validate: bool = False,
    ) -> MachineNode[Any]:
        """Create a ``MachineNode`` from this class.

        Use this when you want to drive the machine with your own
        ``Interpreter`` / ``SyncInterpreter`` (snapshots, custom clocks,
        actor systems), or when you only need the chart itself
        (``to_json()``, diagrams, code generation) and no logic at all.
        ``before_*`` / ``after_*`` naming-convention hooks need the
        instance façade and are reported if present.

        Args:
            context: Optional context override.
            validate: Raise ``ImplementationMissingError`` now for every
                guard, action or service the chart names but the class
                does not implement. Off by default here because a bare
                ``MachineNode`` is a legitimate static artifact; it is on
                by default when the class is instantiated to run.

        Returns:
            A ``MachineNode`` ready for interpreter use.
        """
        if cls._xsm_before or cls._xsm_after:
            names = sorted(
                fn.__name__
                for group in list(cls._xsm_before.values())
                + list(cls._xsm_after.values())
                for fn in group
            )
            logger.warning(
                "⚠️ %s.create_machine(): the before_/after_ hooks %s only "
                "run on an instance (sm = %s()); a MachineNode driven by "
                "your own interpreter will not call them.",
                cls.__name__,
                names,
                cls.__name__,
            )
        instance = cls.__new__(cls)
        object.__setattr__(instance, "_xsm_logic_only", True)
        instance.__init__()  # type: ignore[misc]
        return cls._build_machine(
            instance=instance, context=context, sink=None, validate=validate
        )

    # ------------------------------------------------------------------
    # 🚦 Lifecycle
    # ------------------------------------------------------------------
    @property
    def machine(self) -> MachineNode[Any]:
        """The compiled ``MachineNode``."""
        return self._xsm_machine

    @property
    def interpreter(self) -> Any:
        """The underlying ``SyncInterpreter`` / ``Interpreter``."""
        return self._xsm_interp

    @property
    def status(self) -> str:
        return str(self._xsm_interp.status)

    def start(self) -> Any:
        """Start the machine. Sync: returns ``self``. Async: awaitable.

        Always the lifecycle method, even when the chart has a transition
        called ``start``; send that event with ``sm.send("START")``.
        """
        if self.engine == "async":
            return self._astart()
        self._xsm_interp.start()
        return self

    async def _astart(self) -> "StateMachine":
        await self._xsm_interp.start()
        return self

    def stop(self) -> Any:
        """Stop the machine. Sync: returns ``None``. Async: awaitable.

        Always the lifecycle method, even when the chart has a transition
        called ``stop``; send that event with ``sm.send("STOP")``.
        """
        if self.engine == "async":
            return self._xsm_interp.stop()
        self._xsm_interp.stop()
        return None

    def __enter__(self) -> "StateMachine":
        if self.engine == "async":
            raise TypeError("Use `async with` for an async-engine machine.")
        return self

    def __exit__(self, *exc: Any) -> None:
        self._xsm_interp.stop()

    async def __aenter__(self) -> "StateMachine":
        if self.engine != "async":
            raise TypeError("Use a plain `with` for a sync-engine machine.")
        await self._xsm_interp.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._xsm_interp.stop()

    # ------------------------------------------------------------------
    # 📨 Sending events
    # ------------------------------------------------------------------
    def send(self, event: Union[str, Event], /, **payload: Any) -> Any:
        """Send an event.

        Returns the return value(s) of the actions that ran: ``None``
        when none returned anything, the value when exactly one did, a
        list otherwise. On the async engine this is a coroutine.

        Raises:
            InterpreterStoppedError: ``strict`` and the machine is no
                longer running (lenient mode logs a drop instead).
            UnknownEventError: ``strict`` and the event is not declared.
            TransitionNotAllowedError: ``strict`` and no active state
                takes the event right now (guards included). The event
                is not dispatched and the configuration is unchanged.
        """
        ev = self._coerce(event, payload)
        if self.engine == "async":
            return self._asend(ev)
        if self.strict:
            self._strict_check(ev)
        self._xsm_results.clear()
        self._xsm_interp.send(ev)
        return self._fold_results()

    async def _asend(self, ev: Event) -> Any:
        # 🔒 Concurrent `gather(sm.go(), sm.next())` must not interleave
        #    their result sinks; the interpreter processes sends in order
        #    anyway, so serialising here costs nothing observable.
        if self._xsm_send_lock is None:
            self._xsm_send_lock = asyncio.Lock()
        async with self._xsm_send_lock:
            if self.strict:
                self._strict_check(ev)
            self._xsm_results.clear()
            await self._xsm_interp.send(ev, wait=True)
            return self._fold_results()

    @staticmethod
    def _coerce(event: Union[str, Event], payload: Dict[str, Any]) -> Event:
        if isinstance(event, Event):
            if payload:
                merged = {**(event.payload or {}), **payload}
                return Event(type=event.type, payload=merged)
            return event
        return Event(type=str(event), payload=dict(payload))

    def _strict_check(self, ev: Event) -> None:
        machine = self._xsm_machine
        if self._xsm_interp.status != "running":
            raise InterpreterStoppedError(
                f"{type(self).__name__} is {self._xsm_interp.status}; event "
                f"'{ev.type}' was not sent (strict mode)."
            )
        if not machine.is_known_event(ev.type, user_sent=True):
            raise UnknownEventError(
                ev.type, machine.id, sorted(machine.known_events)
            )
        if not self._xsm_interp.can(ev):
            raise TransitionNotAllowedError(ev.type, self.configuration)

    def _fold_results(self) -> Any:
        results = list(self._xsm_results)
        self._xsm_results.clear()
        if not results:
            return None
        if len(results) == 1:
            return results[0]
        return results

    # ------------------------------------------------------------------
    # 🔎 Introspection
    # ------------------------------------------------------------------
    def _relative(self, state_id: str) -> str:
        prefix = f"{self._xsm_machine.id}."
        if state_id.startswith(prefix):
            return state_id[len(prefix) :]
        return state_id

    @property
    def configuration(self) -> FrozenSet[str]:
        """Active leaf states as dot paths relative to the machine root."""
        return frozenset(
            self._relative(s) for s in self._xsm_interp.current_state_ids
        )

    @property
    def state(self) -> str:
        """The single active leaf state as a dot path.

        Raises:
            ValueError: Several leaves are active (parallel regions);
                read ``configuration`` instead.
        """
        leaves = self.configuration
        if len(leaves) != 1:
            raise ValueError(
                f"{type(self).__name__} has {len(leaves)} active states "
                f"{sorted(leaves)}; use .configuration for parallel "
                f"machines."
            )
        return next(iter(leaves))

    @property
    def context(self) -> Any:
        """The live context object."""
        return self._xsm_interp.context

    def matches(self, state: Union[str, Dict[str, Any]]) -> bool:
        """``True`` if the given state (path or value) is active."""
        return bool(self._xsm_interp.matches(state))

    def can(self, event: Union[str, Event], /, **payload: Any) -> bool:
        """Would this event cause a transition right now (guards included)?"""
        return bool(self._xsm_interp.can(self._coerce(event, payload)))

    @property
    def allowed_events(self) -> FrozenSet[str]:
        """Events the active states declare a handler for (guards are
        not evaluated; use ``can()`` for that)."""
        machine = self._xsm_machine
        out: Set[str] = set()
        for leaf in self._xsm_interp.current_state_ids:
            node = machine.get_state_by_id(leaf)
            while node is not None:
                out.update(e for e in node.on if e)
                node = getattr(node, "parent", None)
        return frozenset(out)

    def __repr__(self) -> str:
        leaves = sorted(self.configuration)
        shown: Any = leaves[0] if len(leaves) == 1 else leaves
        return (
            f"{type(self).__name__}(state={shown!r}, "
            f"context={self.context!r})"
        )


def _validate_logic(machine: MachineNode[Any], cls_name: str) -> None:
    """Fail at build time if the chart names logic nobody implemented.

    Before 0.12.0 a missing guard surfaced at the first ``send()`` that
    reached it, one name at a time. ``spawn_<service>`` actions are
    engine-provided for every registered service and are not reported.
    """
    from .testing_utils import logic_names

    actions, guards, services = logic_names(machine)
    logic = machine.logic
    have_services = set(logic.services)
    missing = []
    for kind, wanted, have in (
        ("action", actions, set(logic.actions)),
        ("guard", guards, set(logic.guards)),
        ("service", services, have_services),
    ):
        for name in sorted(wanted - have):
            if (
                kind == "action"
                and name.startswith("spawn_")
                and name[len("spawn_") :] in have_services
            ):
                continue
            missing.append(f"{kind} '{name}'")
    if missing:
        raise ImplementationMissingError(
            f"{cls_name} references logic that is not implemented: "
            f"{', '.join(missing)}. Define a method with that name (or "
            f"decorate one with @action / @guard / @service), or set "
            f"validate_logic = False to defer the check to runtime."
        )
