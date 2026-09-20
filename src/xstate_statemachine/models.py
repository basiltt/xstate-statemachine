# /src/xstate_statemachine/models.py
# -----------------------------------------------------------------------------
# 🏛️ State Machine Model Definitions
# -----------------------------------------------------------------------------
# This module defines the core data structures that represent a state machine's
# configuration in memory. It uses a class-based, object-oriented approach to
# parse and build a traversable tree from a JSON or dictionary configuration,
# adhering to XState conventions.
#
# The primary classes (`StateNode` and `MachineNode`) implement the "Composite"
# design pattern. This allows a tree of state objects to be composed, where
# both individual states (leaves) and groups of states (composites) can be
# treated uniformly. This is fundamental to modeling hierarchical and parallel
# statecharts.
#
# This structured in-memory representation enables robust validation, easy
# introspection, and serves as the foundation for the interpreter to execute
# the machine's logic.
# -----------------------------------------------------------------------------
"""
Defines the object-oriented data models for the state machine.

This module is responsible for parsing a state machine configuration dictionary
and building a traversable graph of `StateNode` objects. It also defines the
data-holding classes for dynamic parts of the machine like actions, transitions,
and invoked services.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import copy
import inspect
import logging
from enum import Enum
from typing import (
    cast,
    Mapping,
    FrozenSet,
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .actions import BUILTIN_ACTION_PARAM_SPEC, resolve_builtin
from .events import ENGINE_EVENT_SHAPES, Event
from .exceptions import InvalidConfigError, StateNotFoundError
from .machine_logic import MachineLogic
from .resolver import resolve_target_state

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🧬 Type Variables & Generics
# -----------------------------------------------------------------------------
# `TContext` (see _typing.py) allows for creating generic machine
# definitions. This provides a foundation for full static type checking of a
# machine's context and events, leading to more robust and self-documenting code.
# -----------------------------------------------------------------------------

from ._typing import TContext  # noqa: E402

# Define a specific type for state types for clarity and reuse.
StateType = Literal["atomic", "compound", "parallel", "final", "history"]

# -----------------------------------------------------------------------------
# 🛡️ Failure Policies
# -----------------------------------------------------------------------------
# Each policy's FIRST value is the 0.7.x behaviour and remains the default.
# -----------------------------------------------------------------------------

#: What to do when a user-supplied action raises mid-transition.
#:   continue — skip remaining actions, commit the transition, report it.
#:   rollback — abort the transition; restore configuration and context.
#:   fail     — roll back, then stop the interpreter with status "error".
ACTION_ERROR_POLICIES: Tuple[str, ...] = ("continue", "rollback", "fail")

#: What a raising guard evaluates to.
#:   false — the guard is treated as not satisfied (0.7.x behaviour).
#:   true  — the guard is treated as satisfied.
#:   raise — the exception propagates to the caller of `send()`.
GUARD_ERROR_POLICIES: Tuple[str, ...] = ("false", "true", "raise")

#: What to do with an event that selects no transition.
#:   ignore — drop it, firing `on_unhandled_event` (XState semantics).
#:   defer  — hold it and replay it after the next successful transition.
#:   error  — raise `UnhandledEventError`.
UNHANDLED_EVENT_POLICIES: Tuple[str, ...] = ("ignore", "defer", "error")


def _validated_policy(
    config: Dict[str, Any],
    key: str,
    allowed: Tuple[str, ...],
    default: str,
) -> str:
    """Read a policy string from *config*, rejecting anything unrecognised.

    🛡️ A policy typo (`"rollbak"`) that silently fell back to the default
    would recreate the very failure mode these policies exist to remove.
    """
    value = config.get(key, default)
    if value not in allowed:
        raise InvalidConfigError(
            f"Machine '{config.get('id', '?')}': '{key}' must be one of "
            f"{list(allowed)}, got {value!r}."
        )
    return str(value)


# 👶 Prefixes marking an action as a built-in actor-spawning directive.
#
# ⚠️ Order matters: `spawn_blocking_` must be tested before `spawn_`, since the
# latter is a prefix of the former.
class OverflowPolicy(str, Enum):
    """What ``send()`` does when a bounded inbox is full (#38).

    * ``RAISE`` -- default once a bound is set. `send()` raises
      `QueueOverflowError`; the gateway sheds load and alarms.
    * ``BLOCK`` -- `await send()` suspends until the consumer frees a slot.
      For trusted in-process producers that can be slowed.
    * ``DROP_NEWEST`` -- the incoming event is discarded with a WARNING and
      `PluginBase.on_event_dropped`. The only policy that can lose an event;
      never the default. For telemetry where staleness beats backlog.
    """

    RAISE = "raise"
    BLOCK = "block"
    DROP_NEWEST = "drop_newest"


SPAWN_BLOCKING_PREFIX = "spawn_blocking_"
#: Default upper bound (ms) a `spawn_blocking_<key>` waits for its child
#: when the machine sets no `spawnBlockingTimeout`. Generous enough for any
#: realistic child, short enough that a child with no final state cannot
#: wedge its parent silently (review F2). 30 s.
DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS = 30_000.0
SPAWN_PREFIX = "spawn_"


def is_spawn_action(action_type: str) -> bool:
    """Reports whether an action type is a built-in spawn directive.

    Args:
        action_type (str): The action's `type` string.

    Returns:
        bool: `True` for `spawn_*` and `spawn_blocking_*` action types.
    """
    return action_type.startswith(SPAWN_PREFIX)


def spawn_service_key(action_type: str) -> str:
    """Derives the `services` key that a spawn action refers to.

    🏛️ Architecture decision: this is the single source of truth for spawn key
    derivation, shared by `LogicLoader` (which decides what to *require*) and
    by both interpreters (which decide what to *look up*). Previously the three
    sites disagreed:

    - `Interpreter` used `type.replace("spawn_", "")` — unanchored and global,
      so `spawn_blocking_worker` became `blocking_worker` and
      `spawn_respawn_handler` became `rehandler`.
    - `SyncInterpreter` used `type.split("_", 2)[-1]`, so any multi-word key
      lost everything but its last segment: `spawn_my_worker` became `worker`.

    Both silently resolved the wrong service (or none at all). Deriving the key
    in one place makes discovery and lookup agree by construction.

    Args:
        action_type (str): The action's `type` string, e.g. `spawn_my_worker`.

    Returns:
        str: The service key, e.g. `my_worker`. Returns the input unchanged if
        it carries no spawn prefix.

    Example:
        >>> spawn_service_key("spawn_my_worker")
        'my_worker'
        >>> spawn_service_key("spawn_blocking_my_worker")
        'my_worker'
        >>> spawn_service_key("spawn_respawn_handler")
        'respawn_handler'
    """
    if action_type.startswith(SPAWN_BLOCKING_PREFIX):
        return action_type[len(SPAWN_BLOCKING_PREFIX) :]
    if action_type.startswith(SPAWN_PREFIX):
        return action_type[len(SPAWN_PREFIX) :]
    return action_type


# -----------------------------------------------------------------------------
# 🎬 Action, Transition, and Invoke Models (Data Transfer Objects)
# -----------------------------------------------------------------------------
# These classes are simple, immutable data structures for representing the
# executable parts of the state machine. They provide a standardized,
# object-oriented way to interact with the parsed JSON configuration.
# -----------------------------------------------------------------------------


class ActionDefinition:
    """Represents a single action to be executed.

    This class standardizes the representation of an action defined in the
    machine's configuration, accommodating both shorthand string definitions
    (e.g., `"myAction"`) and more detailed object definitions that can include
    static parameters.

    Attributes:
        type: The name or type identifier of the action.
        params: An optional dictionary of static parameters associated with
                the action, defined directly in the JSON.
    """

    type: str
    params: Optional[Dict[str, Any]]

    def __init__(self, config: Union[str, Dict[str, Any]]):
        """Initializes the ActionDefinition from its configuration.

        Args:
            config: The action configuration from the machine definition.
                    It can be a simple `str` (the action name) or a `Dict`
                    (e.g., `{"type": "myAction", "params": {...}}`).

        Raises:
            InvalidConfigError: If the config is not a string or dictionary.
        """
        if isinstance(config, str):
            # 📝 Handle shorthand string definition: "myAction"
            logger.debug(
                "🔧 Parsing action definition from string: '%s'", config
            )
            self.type = config
            self.params = None
        elif isinstance(config, dict):
            # 📝 Handle object definition: {"type": "myAction", ...}
            logger.debug("🔧 Parsing action definition from dict: %s", config)
            self.type = config.get("type", "UnknownAction")
            self.params = config.get("params")
            self._validate_builtin_params(config)
        else:
            # ❌ Reject invalid definitions
            logger.error(
                "❌ Invalid action configuration type: %s (expected str or dict)",
                type(config),
            )
            raise InvalidConfigError(
                f"Action definition must be a string or a dictionary, got {type(config)}"
            )

    def _validate_builtin_params(self, config: Dict[str, Any]) -> None:
        """Reject a built-in action whose required params are missing.

        🏛️ #32: this is the ONE place every action dict is parsed -- entry,
        exit, transition actions, invoke onDone/onError, both engines -- so
        one check here covers all of them. When the required keys are found
        at the TOP level of the dict instead of under ``params`` (the
        natural mistake), the error says so explicitly.
        """
        canonical = resolve_builtin(self.type)
        if canonical is None:
            return
        spec = BUILTIN_ACTION_PARAM_SPEC.get(canonical)
        if spec is None or callable(self.params):
            return
        required, optional = spec
        supplied = set(self.params or {})
        missing = required - supplied
        if not missing:
            return
        stray = set(config) - {"type", "params"}
        hint = ""
        if stray & (required | optional):
            hint = (
                f" Found {sorted(stray & (required | optional))} at the top "
                f"level of the action -- built-in action parameters must be "
                f"nested under 'params'."
            )
        raise InvalidConfigError(
            f"Built-in action '{self.type}' is missing required param(s) "
            f"{sorted(missing)}.{hint}"
        )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Action(type='{self.type}')"


# -----------------------------------------------------------------------------
# 🛡️ Guard Definition
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: guards are normalised into a dedicated object
# rather than kept as the raw config value. Three problems motivated this:
#
#   1. The XState object form `{"type": "g", "params": {...}}` was stored raw
#      and then used as a dictionary key, raising
#      `TypeError: unhashable type: 'dict'` from inside the event loop.
#   2. Higher-order guards (`and` / `or` / `not`) need a recursive structure.
#   3. The v4 spelling `cond` was ignored entirely, so guarded transitions
#      written that way fired unconditionally.
#
# A `GuardDefinition` is hashable, recursive, and carries its params.
# -----------------------------------------------------------------------------

#: Guard `type` values handled natively by the interpreter rather than looked
#: up in `MachineLogic.guards`.
COMPOSITE_GUARD_TYPES = frozenset({"and", "or", "not"})
STATE_IN_GUARD_TYPE = "stateIn"


class GuardDefinition:
    """A normalised, hashable representation of a transition guard.

    Supports every guard form XState accepts:

    - ``"isReady"`` — a named predicate resolved from ``MachineLogic.guards``.
    - ``{"type": "isReady", "params": {...}}`` — a parameterised predicate.
    - ``{"type": "and", "children": [...]}`` — higher-order composition
      (``and`` / ``or`` / ``not``).
    - ``{"type": "stateIn", "params": {"state": "#m.a.b"}}`` — a built-in
      guard satisfied when the given state is active.

    Attributes:
        type (str): The guard's type name.
        params (Optional[Any]): Parameters for the guard. May be a callable,
            which is resolved against ``(context, event)`` at evaluation time.
        children (List[GuardDefinition]): Nested guards for composite types.
        is_composite (bool): `True` for `and` / `or` / `not`.
        is_state_in (bool): `True` for the built-in `stateIn` guard.
    """

    __slots__ = ("type", "params", "children", "is_composite", "is_state_in")

    type: str
    params: Optional[Dict[str, Any]]
    children: List["GuardDefinition"]
    is_composite: bool
    is_state_in: bool

    def __init__(self, config: Union[str, Dict[str, Any], "GuardDefinition"]):
        """Normalises any supported guard configuration.

        Args:
            config: The raw guard value from the machine definition.

        Raises:
            InvalidConfigError: If the configuration shape is not supported,
                or a composite guard declares no children.
        """
        if isinstance(config, GuardDefinition):
            # 🔁 Idempotent: re-wrapping an already-normalised guard is a no-op.
            self.type = config.type
            self.params = config.params
            self.children = config.children
            self.is_composite = config.is_composite
            self.is_state_in = config.is_state_in
            return

        children_cfg: List[Any] = []
        if isinstance(config, str) and config.startswith("!") and config[1:]:
            # 🚫 `"!name"` is Stately's shorthand for a negated guard --
            #    sugar for `{"type": "not", "children": ["name"]}`. Treated
            #    literally it demanded a guard CALLED `!name`, which no
            #    implementation can be registered under; three of the 104
            #    real-world corpus machines failed at start() on it. It
            #    desugars here, so the rest of the engine sees one shape.
            self.type = "not"
            self.params = None
            children_cfg = [config[1:]]
        elif isinstance(config, str):
            self.type = config
            self.params = None
        elif isinstance(config, dict):
            guard_type = config.get("type")
            if not isinstance(guard_type, str) or not guard_type:
                raise InvalidConfigError(
                    "❌ Guard object must have a non-empty string 'type', "
                    f"got: {config!r}"
                )
            self.type = guard_type
            self.params = config.get("params")
            # 🌳 Composite guards accept their operands under `children`, or
            #    (as XState's helpers emit) inside `params`.
            children_cfg = config.get("children") or []
            if not children_cfg and isinstance(self.params, dict):
                children_cfg = (
                    self.params.get("guards")
                    or self.params.get("children")
                    or []
                )
            if not children_cfg and self.type in COMPOSITE_GUARD_TYPES:
                # `not` is commonly written {"type": "not", "params": {...}}
                # with a single nested guard.
                nested = (
                    self.params.get("guard")
                    if isinstance(self.params, dict)
                    else None
                )
                if nested is not None:
                    children_cfg = [nested]
        else:
            raise InvalidConfigError(
                "❌ Guard must be a string or a dictionary, "
                f"got {type(config).__name__}"
            )

        # 🏛️ Architecture decision: a *bare string* guard is always a user
        # predicate, never a composite. Only the object form
        # (`{"type": "and", ...}`) declares composition. Without this a user
        # who legitimately names a guard `and`, `or` or `not` could not use
        # it at all — the parser demanded nested children it would never have.
        self.is_composite = self.type in COMPOSITE_GUARD_TYPES and (
            not isinstance(config, str)
            or bool(children_cfg)  # the `"!name"` sugar desugared above
        )
        self.is_state_in = self.type == STATE_IN_GUARD_TYPE
        self.children = [GuardDefinition(c) for c in children_cfg]

        if self.is_composite and not self.children:
            raise InvalidConfigError(
                f"❌ Composite guard '{self.type}' requires at least one "
                "nested guard (via 'children', or 'params.guards')."
            )
        if (
            self.is_composite
            and self.type == "not"
            and len(self.children) != 1
        ):
            raise InvalidConfigError(
                "❌ Guard 'not' requires exactly one nested guard, got "
                f"{len(self.children)}."
            )

    @property
    def is_builtin(self) -> bool:
        """Whether the interpreter evaluates this guard without user logic.

        Returns:
            bool: `True` for composite and `stateIn` guards.
        """
        return self.is_composite or self.is_state_in

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        if self.is_composite:
            return f"Guard({self.type}, children={self.children!r})"
        return f"Guard(type='{self.type}')"


class TransitionDefinition:
    """Represents a potential transition between states for a given event.

    This class holds all information about a transition, including its target
    state, the actions to execute, and any conditional guard.

    Attributes:
        event: The name of the event that triggers this transition.
        source: The source `StateNode` where this transition originates.
        target_str: The string representation of the target state.
        actions: A list of `ActionDefinition` objects to execute.
        guard: The name of the guard condition to evaluate.
        reenter: A flag indicating if a self-transition should exit and
                 re-enter its source state. Defaults to `False`.
    """

    def __init__(
        self,
        event: str,
        config: Dict[str, Any],
        source: "StateNode",
        actions: Optional[List[ActionDefinition]] = None,
    ):
        """Initializes the TransitionDefinition.

        Args:
            event: The name of the event that triggers this transition.
            config: The dictionary defining the transition's properties
                    (e.g., `target`, `guard`, `reenter`).
            source: The `StateNode` where this transition is defined.
            actions: A list of `ActionDefinition` objects to be executed.
        """
        if _PARSE_DEBUG():  # ⚡ once per transition per build
            logger.debug(
                "🔧 Creating transition for event '%s' from config: %s",
                event,
                config,
            )
        self.event: str = event
        self.source: "StateNode" = source
        self.target_str: Optional[str] = config.get("target")
        self.actions: List[ActionDefinition] = actions or []
        #: ⚡ Perf: the target `StateNode`, resolved ONCE at build time by
        #: `validation.validate_machine` (which already has to resolve it to
        #: reject bad targets). The runtime read this back per transition
        #: through the full multi-strategy resolver -- ~15% of a flat
        #: macrostep -- for an answer that cannot change after the tree is
        #: built. `None` means "not resolved at build" (targetless, or an
        #: unresolvable target kept alive by `strict_targets=False`), and the
        #: runtime falls back to resolving live. The resolver stays the single
        #: authority: this only memoises its result.
        self.resolved_target: Optional["StateNode"] = None
        #: ⚡ Perf: static transition GEOMETRY, memoised on first execution
        #: by `BaseInterpreter._transition_geometry`. For a given resolved
        #: target the domain (LCCA) and the entry path from the domain down
        #: to the target depend only on the immutable tree, yet were rebuilt
        #: on every event (~6 us of a 21 us flat macrostep). Keyed on the
        #: target's identity so a live-resolved (`strict_targets=False`)
        #: transition that resolves differently is not served a stale answer.
        #: The EXIT set stays dynamic -- it depends on the live configuration.
        self._geometry: Optional[Tuple[int, Any, Tuple["StateNode", ...]]] = (
            None
        )

        # 🛡️ Guard resolution.
        #
        # 🏛️ Architecture decision: the guard is normalised here into a
        # `GuardDefinition` rather than stored raw. Previously the raw value was
        # used directly as a dict key, so the standard XState object form
        # (`{"type": ..., "params": ...}`) and every higher-order guard raised
        # `TypeError: unhashable type: 'dict'` from deep inside the event loop.
        #
        # `cond` is accepted as an alias for `guard`. It is the XState v4
        # spelling and still appears throughout older configs and tutorials.
        # Previously only `guard` was read, so a transition written with `cond`
        # silently ran **unguarded** — the predicate was never called and the
        # transition always fired. That is the most dangerous class of defect
        # a statechart library can have, so the alias is supported rather than
        # rejected.
        raw_guard = config.get("guard", config.get("cond"))
        self.guard_def: Optional[GuardDefinition] = (
            GuardDefinition(raw_guard) if raw_guard is not None else None
        )
        # 🔁 `reenter` (XState v5) with `internal` (v4) as an alias:
        #    `internal: False` means "exit and re-enter", i.e. `reenter: True`.
        #    Before 0.8.0 `internal` was silently dropped, so a migrating
        #    user's explicit opt-in vanished with no validation error (#29).
        if "internal" in config:
            self.reenter: bool = not bool(config["internal"])
        else:
            self.reenter = bool(config.get("reenter", False))
        #: Marks an explicitly forbidden transition (``on: {"E": None}``).
        #: Selecting it consumes the event without changing state, which stops
        #: the upward walk from reaching an ancestor's handler.
        self.forbidden: bool = bool(config.get("__forbidden__", False))

    @property
    def guard(self) -> Optional[str]:
        """The guard's type name, or `None` when the transition is unguarded.

        📝 Retained for backward compatibility: `transition.guard` was a plain
        string before guards gained object and composite forms. Code needing
        params or nested guards should use :attr:`guard_def`.

        Returns:
            Optional[str]: The guard type name.
        """
        return self.guard_def.type if self.guard_def else None

        logger.debug(
            "✅ Created TransitionDefinition: event='%s', target='%s', actions=%d, guard='%s', reenter=%s",
            self.event,
            self.target_str,
            len(self.actions),
            self.guard or "None",
            self.reenter,
        )

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return (
            f"Transition(event='{self.event}', "
            f"target='{self.target_str}', reenter={self.reenter})"
        )


def _required_positional_arity(fn: Any) -> Optional[int]:
    """Number of REQUIRED positional parameters, or None if unknowable.

    🏛️ `len(signature.parameters)` mis-classified ``def f(args, debug=False)``
    as the two-positional form and raised `ValueError` outright for
    builtins like ``dict`` (review F10). Only parameters with no default
    decide the calling convention; anything un-introspectable falls back
    to the XState single-mapping form.
    """
    try:
        params = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        return None
    return sum(
        1
        for p in params
        if p.default is inspect.Parameter.empty
        and p.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    )


def _call_input_factory(fn: Any, context: Any, event: Any) -> Any:
    """Invoke an ``input`` factory using the arity it actually requires.

    * 2+ required positionals -> ``fn(context, event)``
    * exactly 1               -> ``fn({"context", "event"})`` (XState form)
    * 0                       -> ``fn()``
    * un-introspectable (C builtins such as ``dict``) -> ``fn()``: the one
      call that cannot silently mis-bind arguments. A builtin that needs
      arguments raises a clear `TypeError` from its own call.
    """
    arity = _required_positional_arity(fn)
    if arity is None or arity == 0:
        return fn()
    if arity >= 2:
        return fn(context, event)
    return fn({"context": context, "event": event})


class InvokeDefinition:
    """Represents an invoked service or child actor within a state.

    Attributes:
        id: The unique identifier for this invocation instance.
        src: The name of the service to be invoked.
        input: Static data to pass to the invoked service.
        on_done: A list of transitions to take on successful completion.
        on_error: A list of transitions to take on failure.
        source: The `StateNode` that hosts this invocation.
    """

    def __init__(
        self,
        invoke_id: str,
        config: Dict[str, Any],
        source: "StateNode",
        on_done: List[TransitionDefinition],
        on_error: List[TransitionDefinition],
    ):
        """Initializes the InvokeDefinition.

        Args:
            invoke_id: The pre-calculated unique ID for the invocation.
            config: The raw dictionary from the `invoke` key in the JSON.
            source: The `StateNode` that hosts this invocation.
            on_done: A pre-parsed list of 'onDone' transitions.
            on_error: A pre-parsed list of 'onError' transitions.
        """
        logging.debug(
            "🔧 Creating invoke definition for state '%s' with config: %s",
            source.id,
            config,
        )
        self.id: str = invoke_id
        self.src: Optional[str] = config.get("src")
        #: Input for the invoked child. Either a static value or a
        #: callable resolved per spawn by `resolve_input()` (#42).
        self.input: Any = config.get("input")
        #: True when the user DECLARED an `id`. The parser defaults an
        #: omitted id to the hosting state's id, which every anonymous
        #: invoke in that state shares -- so a bare `self.id` is not safe
        #: to use as a unique actor address (#40).
        self.id_is_explicit: bool = "id" in config
        #: Registers the child in the actor system so `sendTo` can address
        #: it by this name from anywhere in the tree. Was silently dropped
        #: at parse time before 0.8.0.
        self.system_id: Optional[str] = config.get("systemId")
        self.source: "StateNode" = source
        self.on_done: List[TransitionDefinition] = on_done
        self.on_error: List[TransitionDefinition] = on_error

        # ⚠️ Warn if the service source is missing, as it's a common error.
        if not self.src:
            logging.warning(
                "⚠️ Invoke definition in state '%s' is missing a 'src' property.",
                self.source.id,
            )
        logging.debug("✅ Created InvokeDefinition with ID '%s'", self.id)

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"Invoke(id='{self.id}', src='{self.src}')"

    def resolve_input(self, context: Any, event: Any) -> Any:
        """Resolve this invoke's ``input`` against the parent's state (#42).

        🏛️ Architecture decision: XState v5 defines
        ``input: ({context, event}) => value`` -- computed PER SPAWN, so a
        child can be parameterised by the parent's live context. Before
        0.8.0 a callable was stored verbatim (the child received the
        function object) and, for a child MACHINE, `input` was never
        forwarded at all. Both engines call this one method so they cannot
        disagree.

        Accepted callable arities, mirroring `MachineLogic` conventions:

        * ``fn(args)`` -- one mapping ``{"context", "event"}`` (XState form)
        * ``fn(context, event)`` -- the two-positional form

        Returns:
            Any: A DEEP COPY of the resolved value, so the child never
            aliases the parent's context. ``None`` when no input is declared.
        """
        raw = self.input
        if raw is None:
            return None
        if callable(raw):
            raw = _call_input_factory(raw, context, event)
        return copy.deepcopy(raw)


# -----------------------------------------------------------------------------
# 🌳 Core State Tree Models (Composite Pattern)
# -----------------------------------------------------------------------------
# The `StateNode` and `MachineNode` classes implement the Composite design
# pattern to build a traversable graph (a tree) of the state machine's
# structure from the parsed JSON configuration.
# -----------------------------------------------------------------------------


#: Order of the tuple `_prefetch_node_keys` returns.
_NODE_KEYS: Tuple[str, ...] = (
    "states",
    "type",
    "initial",
    "tags",
    "meta",
    "entry",
    "exit",
    "on",
    "always",
    "onDone",
    "after",
    "invoke",
)
_NODE_KEY_INDEX: Dict[str, int] = {k: i for i, k in enumerate(_NODE_KEYS)}


def _prefetch_node_keys(config: Dict[str, Any]) -> List[Any]:
    """⚡ Read every optional `StateNode` key in ONE pass over the config.

    A state config typically has 1-3 keys; probing all twelve optional keys
    with `.get` cost ~45% more than a single `items()` pass that routes each
    present key into its slot. Absent keys are `None`.
    """
    out: List[Any] = [None] * len(_NODE_KEYS)
    idx = _NODE_KEY_INDEX
    for k, v in config.items():
        i = idx.get(k)
        if i is not None:
            out[i] = v
    return out


def _PARSE_DEBUG() -> bool:
    """⚡ One level check for the parser's per-node / per-transition DEBUG
    records. The previous per-record `logger.debug` calls were ~1.6 gated
    calls per node on every build."""
    return logger.isEnabledFor(logging.DEBUG)


#: 🛡️ #136: ids of the config dicts on the CURRENT construction descent.
#: Module-level (not per-instance) because `StateNode.__init__` recurses
#: before the parent exists; cleared on every unwind, so it is empty
#: between `create_machine()` calls. Not thread-safe across concurrent
#: machine builds, which is acceptable: a false positive here would be a
#: typed error naming the state, never a wrong machine.
_config_stack: Set[int] = set()


class StateNode(Generic[TContext]):
    """Represents a single state in the state machine graph.

    A `StateNode` can be atomic, compound, parallel, or final. It encapsulates
    all its own behavior, including transitions, actions, services, and child states.
    This class is the core of the in-memory representation of the statechart.
    """

    # ✅ FIX: Pre-declare all instance attributes at the class level.
    # This makes the class structure explicit for static analysis tools,
    # resolving the "Unresolved attribute reference" warnings in IDEs.
    id: str
    key: str
    parent: Optional["StateNode"]
    machine: "MachineNode"
    type: StateType
    initial: Optional[str]
    on: Dict[str, List[TransitionDefinition]]
    on_done: Optional[TransitionDefinition]
    # 🐛 [Issue #60] Keys may be int (ms delays) or str (named delays,
    # e.g. "TIMEOUT"), matching what `_parse_after` actually returns and
    # assigns to `self.after` below -- keeps this in sync with mypy.
    after: Dict[Union[int, str], List[TransitionDefinition]]
    entry: List[ActionDefinition]
    exit: List[ActionDefinition]
    invoke: List[InvokeDefinition]
    states: Dict[str, "StateNode"]

    def __init__(
        self,
        machine: "MachineNode",
        config: Dict[str, Any],
        key: str,
        parent: Optional["StateNode"] = None,
    ):
        """Initializes a StateNode and its subtree from a configuration.

        This constructor recursively parses a piece of the configuration
        dictionary and builds the corresponding node and all of its children,
        linking them together to form the statechart tree.

        Args:
            machine: The root machine node.
            config: The configuration dictionary for *this specific state*.
            key: The key for this state within its parent's `states` object.
            parent: The parent state node, if any.
        """
        # ⚡ Two debug records per node add up on a 1,000-machine build;
        #    gate them on the level once instead of formatting args each time.
        _dbg = _PARSE_DEBUG()
        if _dbg:
            logger.debug(
                "🚀 Initializing StateNode: key='%s', parent_id='%s'",
                key,
                parent.id if parent else "ROOT",
            )
        # ⚡ Perf (single-pass parse): every optional key is read from the
        #    config exactly ONCE, here, and handed to the `_parse_*` helpers.
        #    Each helper used to re-probe the dict for its own keys -- on a
        #    7-node machine that was 21 `dict.get` calls per node for a
        #    config with ~2 keys per node, and the parse was ~48% of
        #    `create_machine()`.
        #    A single `items()` pass over the (typically 1-3 key) config is
        #    ~45% cheaper than probing all 16 optional keys with `.get`.
        cfg_get = config.get
        (
            raw_states,
            cfg_type,
            raw_initial,
            raw_tags,
            raw_meta,
            raw_entry,
            raw_exit,
            raw_on,
            raw_always,
            raw_on_done,
            raw_after,
            raw_invoke,
        ) = _prefetch_node_keys(config)
        # 🧍‍♂️ Core Properties
        #
        self.key = key
        self.parent = parent
        self.machine = machine
        self.id = f"{parent.id}.{key}" if parent else key

        # 🏷️ Custom `id`. XState lets a state declare its own id so distant
        #    branches can target it as `#myId` without spelling out a path —
        #    a core cross-branch idiom used by 37 of the 104 real-world
        #    Stately machines in the test corpus. The key was previously read
        #    only on the machine ROOT, so every such target raised
        #    `StateNotFoundError`. The structural `self.id` stays the
        #    canonical path (snapshots and `matches()` depend on it); the
        #    custom name is recorded separately and registered on the machine
        #    for `#` lookups.
        self.custom_id: Optional[str] = None
        if parent is not None:
            declared_id = cfg_get("id")
            if declared_id is not None:
                if not isinstance(declared_id, str) or not declared_id:
                    raise InvalidConfigError(
                        f"State '{self.id}' has an invalid 'id'. Expected a "
                        f"non-empty string, got {declared_id!r}."
                    )
                self.custom_id = declared_id
                registry = getattr(machine, "_custom_ids", None)
                if registry is not None:
                    existing = registry.get(declared_id)
                    if existing is not None:
                        raise InvalidConfigError(
                            f"Duplicate state id '{declared_id}' declared by "
                            f"both '{existing.id}' and '{self.id}'. Custom "
                            f"ids must be unique within a machine."
                        )
                    registry[declared_id] = self

        # 📏 Tree depth, cached at construction time.
        #
        # 🏛️ Architecture decision: depth is stored as an integer rather than
        # derived from `id` at comparison time. The SCXML transition-selection
        # rule ("the deepest active state wins") requires a true structural
        # depth. A previous implementation approximated this with `len(self.id)`,
        # which silently ranked a shallow state with a verbose name above a
        # genuinely deeper state with a terse one. Caching an int also removes
        # repeated string work from the hot event-processing path.
        self.depth: int = parent.depth + 1 if parent else 0

        # ⚙️ Determine and strictly type the state's `type` attribute.
        self.type = self._determine_state_type(raw_states, cfg_type)
        if _dbg:
            logger.debug(
                "  -> StateNode '%s' identified as type: '%s'",
                self.id,
                self.type,
            )

        # ⚙️ Parse all properties from the configuration dictionary.
        # This encapsulates the parsing logic within the model itself.
        self.initial = self._parse_initial(raw_initial, raw_states)

        # 🏷️ Metadata keys. Previously all three were dropped at parse time,
        #    so `tags` (UI-state modelling) and `meta` (arbitrary annotation)
        #    were silently unavailable to users who had declared them.
        if raw_tags is None:
            raw_tags = []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        # ⚠️ Validate rather than let `set()` decide. A bare `set(raw_tags)`
        #    turned `tags: 123` into an opaque "'int' object is not iterable"
        #    with no hint as to WHICH state was malformed, and silently
        #    accepted `tags: {"a": 1}` as the tag set {"a"} by iterating the
        #    mapping's keys — a config typo that produced working-looking
        #    nonsense.
        if isinstance(raw_tags, (dict, bytes)) or not isinstance(
            raw_tags, (list, tuple, set, frozenset)
        ):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'tags' value of type "
                f"'{type(raw_tags).__name__}'. Expected a string or a list "
                f"of strings."
            )
        non_strings = [tag for tag in raw_tags if not isinstance(tag, str)]
        if non_strings:
            raise InvalidConfigError(
                f"State '{self.id}' has non-string tag(s): {non_strings!r}. "
                f"Every tag must be a string."
            )
        self.tags: Set[str] = set(raw_tags)

        raw_meta = raw_meta or {}
        if not isinstance(raw_meta, dict):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'meta' value of type "
                f"'{type(raw_meta).__name__}'. Expected an object/dict."
            )
        self.meta: Dict[str, Any] = raw_meta
        self.description: Optional[str] = cfg_get("description")

        # 🏁 Final states may declare `output` (a.k.a. "done data"), which is
        #    surfaced on the `done.state.*` / `done.invoke.*` event.
        self.output: Any = cfg_get("output")

        # 🕰️ History configuration. `history` is "shallow" (restore the
        #    immediate child) or "deep" (restore the full nested
        #    configuration). XState defaults to shallow.
        self.history: Optional[str] = None
        if self.type == "history":
            history_kind = cfg_get("history", "shallow")
            if history_kind not in ("shallow", "deep"):
                logger.warning(
                    "⚠️ Invalid 'history' value '%s' on state '%s'. "
                    "Defaulting to 'shallow'.",
                    history_kind,
                    self.id,
                )
                history_kind = "shallow"
            self.history = history_kind
        #: Default target used when a history state has nothing recorded yet.
        self.target_str: Optional[str] = cfg_get("target")

        self.entry = self._parse_actions(raw_entry)
        self.exit = self._parse_actions(raw_exit)
        #: ⚡ #27: does this node OR any descendant declare entry/exit
        #: actions? Set by `MachineNode._mark_subtree_actions` once the
        #: tree is complete; conservatively True until then.
        self.on = self._parse_on(raw_on, raw_always)
        # ⚡ #55 part 2: precompiled descriptor index. `_matching_descriptors`
        #    used to scan every `on` key per event to find partials; for a
        #    typical machine there are none, so the scan was pure overhead
        #    on the hottest path. Built ONCE here.
        # ⚡ Perf: the partial-wildcard table is only non-empty when some
        #    `on` key ends in ".*"; skip the generator + sorted() otherwise
        #    (it ran on every node, sorting an empty list 6 times in 7).
        self._on_partials: List[Tuple[str, str]] = (
            sorted(
                (
                    (key, key[:-2])
                    for key in self.on
                    if key != "*" and key.endswith(".*")
                ),
                key=lambda kv: len(kv[0]),
                reverse=True,
            )
            if any(k.endswith(".*") for k in self.on)
            else []
        )
        self._on_has_wildcard: bool = "*" in self.on
        self.on_done = self._parse_on_done(raw_on_done)
        self.after = self._parse_after(raw_after)
        self.invoke = self._parse_invoke(raw_invoke)
        #: ⚡ Can this state ever OWN a scheduled task (an `after` deadline
        #: or an invoked service/child)? Decided once here so `_enter_states`
        #: / `_exit_states` skip the schedule/cancel round-trip -- two
        #: method calls, a dict pop and (async) a TaskManager cancel -- for
        #: the majority of states that declare neither. Delayed `sendTo`s
        #: are owned by the machine ROOT, which is handled separately.
        self.owns_tasks: bool = bool(self.after or self.invoke)

        # 🌳 Recursively build child states, forming the Composite pattern.
        #
        # 🛡️ Validate shapes before traversing. Handing a non-mapping straight
        #    to `.items()` / `.get()` surfaced as a raw
        #    "'str' object has no attribute 'items'" from library internals,
        #    naming neither the offending state nor the offending key — the
        #    user had no way to locate a typo in a large config.
        if raw_states is None:
            raw_states = {}
        if not isinstance(raw_states, dict):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'states' value of type "
                f"'{type(raw_states).__name__}'. Expected an object/dict "
                f"mapping state names to definitions."
            )
        for state_key, state_config in raw_states.items():
            if not isinstance(state_config, dict):
                raise InvalidConfigError(
                    f"State '{self.id}.{state_key}' must be an object/dict, "
                    f"got '{type(state_config).__name__}'."
                )

            # 🚫 A '.' in a state key collides with the id separator: a flat
            #    state "x.y" and a nested x > y build the SAME fully-qualified
            #    id, so `matches()`, snapshots and target resolution cannot
            #    tell them apart — targeting "x.y" silently entered the nested
            #    state and ran the wrong entry actions.
            #
            # 🏛️ Architecture decision: reject only the AMBIGUOUS case, where
            #    the key's first segment is also a real sibling. Rejecting
            #    every dot would break configs that work correctly today — a
            #    key like "v1.0" or "api.v2" is unambiguous unless a sibling
            #    is named "v1"/"api" — which is too aggressive for a patch
            #    release. The rest warn, so the latent hazard stays visible.
            if "." in state_key:
                head = state_key.split(".", 1)[0]
                if head in raw_states:
                    raise InvalidConfigError(
                        f"State key '{state_key}' in '{self.id}' is "
                        f"ambiguous: its first segment '{head}' is also a "
                        f"sibling state, so both resolve to the id "
                        f"'{self.id}.{state_key}'. Rename one (for example "
                        f"'{state_key.replace('.', '_')}')."
                    )
                logger.warning(
                    "⚠️ State key '%s' in '%s' contains '.', the state-id "
                    "separator. Accepted because no sibling shadows it, but "
                    "renaming avoids ambiguity.",
                    state_key,
                    self.id,
                )

        # 🛡️ #136: a hand-built config dict that contains ITSELF as a
        #    descendant (aliased cycle -- impossible in JSON, easy in Python)
        #    used to blow the call stack with a bare RecursionError. Track
        #    the ids of every config dict on the current descent and refuse
        #    with a typed error naming the state instead.
        # 🌳 Post-order tree facts, accumulated as children finish (⚡ this
        #    replaces two whole-tree walks that ran after the parse):
        #    * subtree_has_actions -- this node or any descendant declares
        #      entry/exit (#27 rollback checkpoint gate);
        #    * _subtree_has_history / _subtree_has_always -- feed the
        #      machine-level `has_history_states` / `has_always_transitions`.
        has_actions = bool(self.entry or self.exit)
        has_history = self.type == "history"
        has_always = "" in self.on
        self.states = {}
        for state_key, state_config in raw_states.items():
            if id(state_config) in _config_stack:
                raise InvalidConfigError(
                    f"State '{self.id}.{state_key}' is defined by a config "
                    f"dict that is already one of its own ancestors (an "
                    f"aliased cycle). Each state must have its own config "
                    f"object; copy the template instead of reusing it."
                )
            _config_stack.add(id(state_config))
            try:
                child = self.states[state_key] = StateNode(
                    machine, state_config, state_key, self
                )
            finally:
                _config_stack.discard(id(state_config))
            has_actions = has_actions or child.subtree_has_actions
            has_history = has_history or child._subtree_has_history
            has_always = has_always or child._subtree_has_always
        self.subtree_has_actions: bool = has_actions
        self._subtree_has_history: bool = has_history
        self._subtree_has_always: bool = has_always
        if _dbg:
            logger.debug(
                "✅ StateNode '%s' and its children initialized.", self.id
            )

    # -------------------------------------------------------------------------
    # Internal Parsing Methods (Encapsulated Logic)
    # -------------------------------------------------------------------------

    def _determine_state_type(
        self, raw_states: Any, cfg_type: Any
    ) -> StateType:
        """Determines the type of the state based on its configuration."""
        if raw_states is not None:
            # A state with children is either compound or parallel
            state_type = "compound" if cfg_type is None else cfg_type
            if state_type in ("compound", "parallel"):
                return state_type  # type: ignore
            else:
                logger.warning(
                    "⚠️ Invalid 'type' ('%s') for state '%s' with children. "
                    "Defaulting to 'compound'.",
                    state_type,
                    self.id,
                )
                return "compound"
        elif cfg_type == "final":
            return "final"
        elif cfg_type == "history":
            # 🕰️ A history pseudo-state. It has no children and is never
            #    "entered" in the ordinary sense — targeting it restores the
            #    remembered configuration of its parent instead.
            return "history"
        else:
            return "atomic"

    def _parse_initial(self, initial: Any, raw_states: Any) -> Optional[str]:
        """Parses the initial state key, inferring it where unambiguous.

        🏛️ Architecture decision: a compound state with no `initial` used to
        emit a warning and then start with an **empty** active configuration —
        `current_state_ids` was `set()` and every event was silently dropped, a
        dead machine with no error. That silence is the real defect, not the
        missing key.

        Rather than hard-failing (which would break the long-standing and
        reasonable "single child needs no `initial`" shorthand), resolution is:

        1. exactly one non-history child → infer it, and say so at DEBUG;
        2. several children → raise, because there is no safe guess;
        3. no children at all → leave `None`; the state is effectively atomic.

        Returns:
            Optional[str]: The initial child key, explicit or inferred.

        Raises:
            InvalidConfigError: If a compound state has several children and
                no way to choose between them.
        """
        # 🛡️ `initial` names a child state, so it must be a string. A non-string
        #    was accepted and then never matched any child, producing a machine
        #    that started with an empty configuration and dropped every event.
        if initial is not None and not isinstance(initial, str):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'initial' value of type "
                f"'{type(initial).__name__}'. Expected the name of a child "
                f"state as a string."
            )
        if self.type != "compound" or initial:
            return initial

        # 🕰️ History pseudo-states are never a valid initial target.
        candidates = [
            key
            for key, child in (raw_states or {}).items()
            if not (isinstance(child, dict) and child.get("type") == "history")
        ]

        if len(candidates) == 1:
            inferred = candidates[0]
            logger.debug(
                "🧭 Compound state '%s' has no 'initial'; inferring its only "
                "child '%s'.",
                self.id,
                inferred,
            )
            return inferred

        if len(candidates) > 1:
            # ⚠️ Warn rather than raise. `create_machine` is also used purely
            #    to *inspect* a configuration (diagram export, CLI codegen,
            #    tests), where never starting an interpreter is legitimate.
            #    The failure is therefore reported when the machine is
            #    actually started — see `BaseInterpreter._enter_states`, which
            #    raises if a compound state resolves to no child.
            logger.warning(
                "⚠️ Compound state '%s' is missing an 'initial' state and has "
                "%d children (%s), so one cannot be inferred. Starting this "
                "machine will fail.",
                self.id,
                len(candidates),
                ", ".join(sorted(candidates)),
            )

        return initial

    def _parse_actions(self, config: Optional[Any]) -> List[ActionDefinition]:
        """Parses an action or list of actions from config."""
        if not config:
            return []
        return [ActionDefinition(a) for a in self._ensure_list(config)]

    def _parse_on(
        self, raw_on: Any, always_config: Any
    ) -> Dict[str, List[TransitionDefinition]]:
        """Parses all event transitions from the 'on' property.

        Also folds in the top-level ``always`` key. XState v5 spells eventless
        (transient) transitions as a sibling of ``on``; this library models
        them internally as the empty-string event, which is the v4 spelling
        (``on: {"": ...}``). Both are accepted and merged here — previously
        ``always`` was dropped entirely, so a v5 config's transient
        transitions silently never fired.
        """
        on_map: Dict[str, List[TransitionDefinition]] = {}
        if raw_on is None:
            raw_on = {}
        if not isinstance(raw_on, dict):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'on' value of type "
                f"'{type(raw_on).__name__}'. Expected an object/dict mapping "
                f"event names to transitions."
            )
        for event, transitions_config in raw_on.items():
            normalized_configs = self._normalize_transitions(
                transitions_config
            )
            on_map[event] = [
                self._create_transition(event, t_config)
                for t_config in normalized_configs
            ]

        # ⚡ Merge `always` into the transient ("") bucket.
        if always_config is not None:
            always_transitions = [
                self._create_transition("", t_config)
                for t_config in self._normalize_transitions(always_config)
            ]
            on_map.setdefault("", []).extend(always_transitions)

        return on_map

    def _parse_on_done(
        self, on_done_config: Any
    ) -> Optional[TransitionDefinition]:
        """Parses the 'onDone' transition for a compound/parallel state."""
        if not on_done_config:
            return None

        normalized_list = self._normalize_transitions(on_done_config)
        if not normalized_list:
            return None

        # There can be only one onDone transition, so we take the first.
        transition = self._create_transition(
            f"done.state.{self.id}", normalized_list[0]
        )
        logger.debug(
            "  -> Parsed onDone transition with target: '%s'",
            transition.target_str,
        )
        return transition

    def _parse_after(
        self, raw_after: Any
    ) -> Dict[Union[int, str], List[TransitionDefinition]]:
        """Parses all delayed transitions from the 'after' property.

        📝 Keys may be a numeric duration in milliseconds *or* a symbolic
        name resolved at runtime from `MachineLogic.delays`. Previously every
        key was coerced with `int()`, so a named delay such as
        ``after: {"TIMEOUT": ...}`` raised a bare `ValueError` at parse time
        with no indication that named delays were the intended feature.
        """
        after_map: Dict[Union[int, str], List[TransitionDefinition]] = {}
        if raw_after is None:
            raw_after = {}
        if not isinstance(raw_after, dict):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'after' value of type "
                f"'{type(raw_after).__name__}'. Expected an object/dict "
                f"mapping delays to transitions."
            )
        for delay, transitions_config in raw_after.items():
            normalized_configs = self._normalize_transitions(
                transitions_config
            )
            try:
                key: Union[int, str] = int(delay)
            except (TypeError, ValueError):
                # 🏷️ A symbolic delay name; resolved by the interpreter.
                key = str(delay)
            after_map[key] = [
                self._create_transition(f"after.{delay}.{self.id}", t_config)
                for t_config in normalized_configs
            ]
        return after_map

    def _parse_invoke(self, raw_invoke: Any) -> List[InvokeDefinition]:
        """Parses all invoked services from the 'invoke' property."""
        invoke_configs = self._ensure_list(
            [] if raw_invoke is None else raw_invoke
        )
        invokes: List[InvokeDefinition] = []
        for i_config in invoke_configs:
            # 🛡️ Reject rather than skip. Silently ignoring a malformed
            #    `invoke` produced a state that simply never called its
            #    service — no error, no log, just a machine that hangs.
            if not isinstance(i_config, dict):
                raise InvalidConfigError(
                    f"State '{self.id}' has an invalid 'invoke' entry of "
                    f"type '{type(i_config).__name__}'. Expected an "
                    f"object/dict (or a list of them)."
                )

            # The invoke ID defaults to the state's ID if not provided.
            invoke_id = i_config.get("id", self.id)

            on_done_transitions = [
                self._create_transition(f"done.invoke.{invoke_id}", t)
                for t in self._normalize_transitions(
                    i_config.get("onDone", [])
                )
            ]
            on_error_transitions = [
                self._create_transition(f"error.platform.{invoke_id}", t)
                for t in self._normalize_transitions(
                    i_config.get("onError", [])
                )
            ]
            invokes.append(
                InvokeDefinition(
                    invoke_id=invoke_id,
                    config=i_config,
                    source=self,
                    on_done=on_done_transitions,
                    on_error=on_error_transitions,
                )
            )
        return invokes

    def _create_transition(
        self, event: str, config: Dict[str, Any]
    ) -> TransitionDefinition:
        """A factory method to create a TransitionDefinition."""
        actions = self._parse_actions(config.get("actions"))
        return TransitionDefinition(
            event=event, config=config, source=self, actions=actions
        )

    # -------------------------------------------------------------------------
    # Static Helpers for Configuration Normalization
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_transitions(config: Any) -> List[Dict[str, Any]]:
        """Ensures transition configs are always a list of dictionaries.

        This handles XState's various shorthands for defining transitions.

        📝 `None` denotes a *forbidden* transition (``on: {"E": None}``) — the
        event is explicitly consumed at this level so no ancestor handler
        runs. It is normalised to a single targetless, action-less transition
        carrying the `forbidden` marker. Previously it produced an empty list,
        so the key disappeared and the ancestor's handler fired anyway.
        """
        if config is None:
            return [{"__forbidden__": True}]
        if isinstance(config, str):
            # Shorthand: "on": { "EVENT": "target_state" }
            return [{"target": config}]
        if isinstance(config, dict):
            # Standard: "on": { "EVENT": { "target": ... } }
            return [config]
        if isinstance(config, list):
            # List of transitions for multiple potential targets
            normalized_list: List[Dict[str, Any]] = []
            for item in config:
                if isinstance(item, str):
                    normalized_list.append({"target": item})
                elif isinstance(item, dict):
                    normalized_list.append(item)
                else:
                    raise InvalidConfigError(
                        f"❌ Invalid transition item in list: {item}. "
                        "Must be a string or dictionary."
                    )
            return normalized_list
        if config is not None:
            raise InvalidConfigError(
                f"❌ Invalid transition config: {config}. "
                "Must be a string, dictionary, or list."
            )
        return []

    @staticmethod
    def _ensure_list(config_item: Any) -> List[Any]:
        """A simple helper to ensure a configuration item is always a list."""
        if config_item is None:
            return []
        return config_item if isinstance(config_item, list) else [config_item]

        # -------------------------------------------------------------------------
        # Tree Traversal Helpers
        # -------------------------------------------------------------------------

    def _get_ancestors(self) -> Set["StateNode"]:
        """Gets a set of all ancestors of a node, including the node itself."""
        ancestors: Set["StateNode"] = set()
        # FIX: Changed 'node' back to 'self' to act as an instance method.
        current: Optional[StateNode] = self
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    def _is_descendant(  # noqa
        self, node: "StateNode", ancestor: Optional["StateNode"]
    ) -> bool:
        """Checks if a node is a descendant of a specified ancestor."""
        # The 'self' parameter is unused here, but the method is part of the
        # class's public contract and called from instances.
        if not ancestor:
            return True
        return node == ancestor or node.id.startswith(f"{ancestor.id}.")

    def _get_path_to_state(  # noqa
        self,
        to_state: "StateNode",
        *,
        stop_at: Optional["StateNode"] = None,
    ) -> List["StateNode"]:
        """Builds the list of states to enter to reach a target state."""
        path: List[StateNode] = []
        current: Optional[StateNode] = to_state
        while current and current is not stop_at:
            path.append(current)
            current = current.parent
        path.reverse()
        return path

    # -------------------------------------------------------------------------
    # Public Properties & Representations
    # -------------------------------------------------------------------------

    @property
    def is_atomic(self) -> bool:
        """Returns `True` if the state has no child states."""
        return self.type == "atomic"

    @property
    def is_final(self) -> bool:
        """Returns `True` if the state is a final state."""
        return self.type == "final"

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"StateNode(id='{self.id}', type='{self.type}')"


class MachineNode(StateNode[TContext]):
    """The root node of a state machine, with added machine-wide utilities.

    This class extends `StateNode` and acts as the entry point to the entire
    statechart tree. It holds the machine's logic and initial context and
    provides helpful methods for introspection and testing.

    Attributes:
        logic: The `MachineLogic` instance containing the implementation
               for the machine's actions, guards, and services.
        initial_context: The initial context of the machine, which will be
                         deep-copied for each new interpreter instance.
    """

    # ✅ FIX: Pre-declare instance attributes for this subclass as well.
    logic: MachineLogic[TContext]
    initial_context: TContext

    def __init__(self, config: Dict[str, Any], logic: MachineLogic[TContext]):
        """Initializes the root MachineNode and builds the state tree.

        Args:
            config: The root JSON configuration of the machine.
            logic: The implementation of the machine's business logic.

        Raises:
            InvalidConfigError: If the machine configuration lacks a root 'id'.
        """
        # 🛡️ The root of any machine must have a non-empty ID.
        if not config.get("id"):
            raise InvalidConfigError(
                "❌ Machine configuration must have a root 'id'."
            )
        self.logic = logic
        raw_context = config.get("context", {})
        # 🛡️ Context is a mapping by contract — `assign` and every action
        #    subscript it by key. A list or scalar failed much later with an
        #    opaque TypeError from inside a user action.
        #    A CALLABLE is also valid: XState v5 allows a context factory,
        #    resolved per-interpreter with the machine `input`.
        #
        # 🧩 Real Stately.ai exports ship an unresolved template placeholder
        #    such as `"context": "{{initialContext}}"`. Nine machines in the
        #    bundled corpus do exactly this. Hard-failing would break the
        #    library's headline promise — running XState JSON unmodified — so
        #    a string is downgraded to a warning and treated as empty context.
        if isinstance(raw_context, str):
            logger.warning(
                "⚠️ Machine '%s' declares a string 'context' (%r), which is "
                "usually an unresolved template placeholder. Starting with an "
                "empty context.",
                config["id"],
                raw_context[:40],
            )
            raw_context = {}
        elif not isinstance(raw_context, dict) and not callable(raw_context):
            raise InvalidConfigError(
                f"Machine '{config['id']}' has an invalid 'context' of type "
                f"'{type(raw_context).__name__}'. Expected an object/dict, "
                f"or a callable returning one."
            )
        # 🧷 `raw_context` is whatever the config held (a dict, or the
        #    factory's result); it IS the machine's TContext by construction.
        self.initial_context = cast(TContext, raw_context)
        #: Lazily computed structural fingerprint; see `structure_hash`.
        self._structure_hash: Optional[str] = None
        #: Upper bound on microsteps when settling transient ("always")
        #: transitions, mirroring XState's `maxIterations` (v5.31.0).
        self.max_iterations: int = int(config.get("maxIterations", 1000))
        #: 🛡️ #51: `strict` from config; an interpreter may also opt in.
        self.strict: bool = bool(config.get("strict", False))
        #: Payload validators keyed by event type; set by `create_machine`.
        self.event_schemas: Dict[str, Any] = {}
        #: Lazily built descriptor set; see `known_events`.
        self._known_events: Optional[FrozenSet[str]] = None
        #: ⚡ Perf: does ANY state in this machine declare a `history` child?
        #: Filled in by `_index_history()` after the tree is built. When
        #: False the interpreter skips `_record_history` entirely -- it was
        #: walking every exiting state's ancestor chain and scanning each
        #: one's children on every transition, to find nothing, in the
        #: overwhelmingly common machine with no history states.
        self.has_history_states: bool = False
        #: ⚡ Perf: does ANY state declare an `always` (eventless) transition?
        #: When False, both engines skip the transient-settle pass that ran a
        #: full `_select_transitions` after EVERY event -- half of all
        #: selection work on a machine that has nothing to settle.
        self.has_always_transitions: bool = False
        #: Upper bound (ms) a `spawn_blocking_<key>` waits for the child to
        #: finish on the async engine; `None` waits indefinitely (#41).
        raw_timeout = config.get("spawnBlockingTimeout")
        self.spawn_blocking_timeout_ms: Optional[float] = (
            None if raw_timeout is None else float(raw_timeout)
        )
        #: Machine-level output declaration, resolved when a top-level final
        #: state is reached.
        self.machine_output: Any = config.get("output")

        # 🛡️ Failure policies (0.8.0).
        #
        # 🏛️ Architecture decision: before 0.8.0 every one of these failures
        #    degraded to a *silent* no-op — a raising action still committed
        #    the transition, a raising guard became `False`, an unknown event
        #    vanished. Each is a defensible default for a UI widget and a
        #    money-losing one for an order lifecycle. Rather than pick one
        #    audience, the behaviour is a per-machine policy. The 0.7.x
        #    behaviour remains the default for every policy, so upgrading is
        #    safe; strict users opt in. Read from config so the policy
        #    travels WITH the machine definition, and validated here so a
        #    typo is a build-time error rather than a runtime surprise.
        self.action_error_policy: str = _validated_policy(
            config, "actionErrorPolicy", ACTION_ERROR_POLICIES, "continue"
        )
        #: True until the user sets the policy explicitly. Drives a one-shot
        #: DeprecationWarning ahead of the 1.0 default change.
        self.action_error_policy_is_default: bool = (
            "actionErrorPolicy" not in config
        )
        self.guard_error_policy: str = _validated_policy(
            config, "guardErrorPolicy", GUARD_ERROR_POLICIES, "false"
        )
        self.on_unhandled: str = _validated_policy(
            config, "onUnhandled", UNHANDLED_EVENT_POLICIES, "ignore"
        )
        #: When True, transition targets are resolved strictly: a plain
        #: identifier must name a sibling or ancestor-scope state, never an
        #: unrelated state elsewhere in the tree that merely shares the last
        #: id segment. Default False preserves 0.7.x resolution.
        #: Disables the sibling fallback for `.child` targets (opt-in via the
        #: `strictTargets` config key). Distinct from `create_machine`'s
        #: `strict_targets=` kwarg, which governs UNRESOLVABLE targets.
        self.strict_targets: bool = bool(config.get("strictTargets", False))

        #: Custom `id` → node registry, populated by `StateNode.__init__` as
        #: the tree is built. Must exist BEFORE `super().__init__` recurses
        #: into the children that register themselves here.
        self._custom_ids: Dict[str, StateNode] = {}

        # 🚀 Call the parent constructor to build the entire state tree.
        super().__init__(self, config, config["id"])
        # ⚡ Tree is complete: one walk to learn whether history bookkeeping
        #    is ever needed (see `has_history_states`).
        # ⚡ Perf: accumulated post-order during the parse (see
        #    `StateNode.__init__`) instead of a second whole-tree walk.
        self.has_history_states = self._subtree_has_history
        self.has_always_transitions = self._subtree_has_always
        #: ⚡ Perf: can ANY action run on this machine? `False` means no
        #: state or transition anywhere declares an action (entry / exit /
        #: `on` / `after` / `always` / `onDone` / invoke `onDone`-`onError`),
        #: so nothing the engine does can mutate `context` -- and a
        #: `Receipt` need not deep-copy it to decide `changed`. Distinct
        #: from `subtree_has_actions`, which covers entry/exit only.
        self._context_is_immutable: Optional[bool] = None  # lazy, see property
        #: ⚡ Is `initial_context` a plain dict whose values are all immutable
        #: scalars? Then a per-interpreter `dict()` copy is as good as a
        #: `deepcopy` (see `BaseInterpreter._build_initial_context`).
        raw_ctx = self.initial_context
        self.context_is_flat: bool = isinstance(raw_ctx, dict) and all(
            isinstance(v, (str, int, float, bool, bytes, type(None)))
            for v in raw_ctx.values()
        )
        #: ⚡ Memo for `LogicLoader.required_names()`: the (actions, guards,
        #: services) the config references. Auto-discovery and alias
        #: resolution both need it; the tree is walked once, not twice.
        self._required_logic: Optional[Tuple[Set[str], Set[str], Set[str]]] = (
            None
        )
        # (subtree_has_actions is set per node during the parse.)

    def _mark_subtree_actions(node: "StateNode") -> bool:
        """Post-order walk setting `StateNode.subtree_has_actions` (#27).

        True when *node* or any descendant declares `entry` / `exit`
        actions. `_execute_transition` uses it to skip the rollback
        context checkpoint when no user action can run -- the checkpoint
        cost ~22% throughput on an idle `rollback` machine.
        """
        flag = bool(node.entry or node.exit)
        for child in node.states.values():
            if MachineNode._mark_subtree_actions(child):
                flag = True
        node.subtree_has_actions = flag
        return flag

    @property
    def context_is_immutable(self) -> bool:
        """⚡ ``True`` when no state or transition declares any action.

        Nothing the engine does can then mutate ``context``, so a
        `Receipt` need not deep-copy it to decide ``changed``. Computed
        lazily on first use (a build-time walk would tax every
        `create_machine()`, but only ``send(wait=True)`` needs the answer)
        and cached: the tree is immutable once built.
        """
        if self._context_is_immutable is None:
            self._context_is_immutable = not self._tree_declares_actions(self)
        return self._context_is_immutable

    @staticmethod
    def _tree_declares_actions(root: "StateNode") -> bool:
        """True if any state in the tree declares an action anywhere.

        Walks entry/exit, every `on` / `after` / `onDone` transition and
        every invoke's `onDone` / `onError`. Built-in creators (`assign`,
        `raise`, …) count: they mutate context or produce events, so the
        machine is not inert.
        """
        stack = [root]
        while stack:
            node = stack.pop()
            if node.entry or node.exit:
                return True
            transitions = [t for tl in node.on.values() for t in tl]
            transitions += [t for tl in node.after.values() for t in tl]
            if node.on_done is not None:
                transitions.append(node.on_done)
            for inv in node.invoke:
                transitions += list(inv.on_done) + list(inv.on_error)
            if any(t.actions for t in transitions):
                return True
            stack.extend(node.states.values())
        return False

    def _scan_tree_features(root: "StateNode") -> Tuple[bool, bool]:
        """One walk: (any history child anywhere, any `always` anywhere)."""
        history = False
        always = "" in root.on
        stack = [root]
        while stack:
            current = stack.pop()
            for child in current.states.values():
                if child.type == "history":
                    history = True
                if "" in child.on:
                    always = True
                stack.append(child)
        return history, always

    @property
    def known_events(self) -> FrozenSet[str]:
        """Every event descriptor this machine declares, anywhere (#51).

        Built once, lazily, from every state's ``on`` keys (including
        partial ``"a.b.*"`` and bare ``"*"`` descriptors), every ``after``
        delay's generated type, and every ``invoke``'s generated
        ``done.invoke.<id>`` / ``error.platform.<id>``. This is the set
        `strict` mode checks a sent event against.
        """
        if self._known_events is None:
            from .validation import walk

            # 🏷️ #51: explicit element type avoids a mypy var-annotated
            # error since the mixed .update()/.add() calls below don't
            # let mypy infer the element type on their own.
            found: Set[str] = set()
            for node in walk(self):
                found.update(node.on.keys())
                for group in node.after.values():
                    found.update(t.event for t in group)
                for inv in node.invoke:
                    found.add(f"done.invoke.{inv.id}")
                    found.add(f"error.platform.{inv.id}")
            found.discard("")  # the eventless (`always`) key
            self._known_events = frozenset(found)
        return self._known_events

    def is_known_event(
        self,
        event_type: str,
        *,
        user_sent: bool = False,
        wildcard_matches: bool = False,
    ) -> bool:
        """True if *event_type* is a DECLARED event name (#51).

        Answers "is this name declared?", not "would some handler match?":
        an exact key, or a partial ``"prefix.*"`` whose prefix matches by
        dot-segment. Engine-synthesised events (``done.``, ``error.``,
        ``after.``, ``xstate.``, the init sentinel) are always known.

        🛡️ #190: the bare ``"*"`` wildcard does NOT make every name known.
        It used to, so one ``"*": {...}`` handler anywhere in the chart --
        common defensive scaffolding -- silently disabled ``strict`` event-
        name enforcement for the whole machine: a typo'd ``"CANCLE"`` was
        accepted and routed through the wildcard instead of rejected. The
        wildcard is a DISPATCH rule; `strict` is a DECLARATION rule. Dispatch
        is unchanged: with ``strict`` off the wildcard still catches
        undeclared events.

        Args:
            event_type: The event name to test.
            user_sent: ``True`` when the caller already knows the event is
                user traffic (a `strict` interpreter); engine name-shapes
                are then not implicitly known (#79/#98).
            wildcard_matches: ``True`` asks the DISPATCH question -- "would
                some handler catch this?" -- where a bare ``"*"`` counts.
                Used by the build-time ``raise`` validator, whose concern
                is a raised event nobody handles.
        """
        known = self.known_events
        if wildcard_matches and "*" in known:
            return True
        if event_type in known and event_type != "*":
            return True
        # 🏛️ #79/#98: engine shapes are implicitly known ONLY when the
        #    caller is asking about a name in the abstract (`user_sent=False`,
        #    e.g. build-time `raise` validation). A `strict` interpreter
        #    passes `user_sent=True` because it already knows the event is
        #    user traffic (provenance) -- and a user's `done.invoke.NEVER` or
        #    `___xstate_forged` is then an undeclared name like any other.
        if not user_sent and event_type.startswith(ENGINE_EVENT_SHAPES):
            return True
        for key in known:
            if key.endswith(".*"):
                prefix = key[:-2]
                if event_type == prefix or event_type.startswith(prefix + "."):
                    return True
        return False

    @property
    def structure_hash(self) -> str:
        """A 16-hex-char fingerprint of this machine's behavioural structure.

        Stable across `meta` / `description` edits and key reordering;
        changes when a state, transition, guard NAME, action NAME, invoke or
        `after` delay is added, removed or renamed. Written into every
        snapshot as ``machine_hash`` and checked on restore (#45).
        """
        if self._structure_hash is None:
            from .persistence import structure_hash

            self._structure_hash = structure_hash(self)
        return self._structure_hash

    def state_ids_by_bare_name(self, bare: str) -> List[str]:
        """Every state id in the machine whose last segment is *bare* (#132)."""
        out: List[str] = []
        stack: List[StateNode] = [self]
        while stack:
            node = stack.pop()
            if node is not self and node.key == bare:
                out.append(node.id)
            stack.extend(node.states.values())
        return out

    def get_state_by_id(self, state_id: str) -> Optional[StateNode]:
        """Finds a state node by its fully qualified ID.

        This method traverses the state tree to find a specific node.

        Args:
            state_id: The fully qualified ID of the state to find
                      (e.g., "myMachine.parent.child").

        Returns:
            The `StateNode` if found, otherwise `None`.
        """
        logger.debug("🔍 Searching for state with ID: '%s'", state_id)
        path_segments = state_id.split(".")

        # 🛡️ The path must start with the machine's own ID.
        if not path_segments or path_segments[0] != self.key:
            logger.warning(
                "⚠️ State ID '%s' does not start with machine ID '%s'. "
                "Lookup will fail.",
                state_id,
                self.key,
            )
            return None

        # 🌳 Traverse the tree segment by segment.
        node: StateNode = self
        for key in path_segments[1:]:
            if key not in node.states:
                logger.warning(
                    "❌ State not found. Could not find key '%s' in state '%s'.",
                    key,
                    node.id,
                )
                return None
            node = node.states[key]

        logger.debug("✅ Found state: %s", node)
        return node

    # -------------------------------------------------------------------------
    # 🧪 Testing Utilities
    # -------------------------------------------------------------------------

    def get_next_state(
        self, from_state_id: str, event: Event
    ) -> Optional[Set[str]]:
        """Calculates the target state(s) for an event without side effects.

        This is a pure function intended for **testing** your machine's flow
        logic. It finds the first valid transition by bubbling up the state
        hierarchy from a given state.

        Note:
            This utility does **not** evaluate guards. It assumes any guard
            would pass to show the potential transition target.

        Args:
            from_state_id: The fully qualified ID of the starting state.
            event: The `Event` object to process.

        Returns:
            A set containing the target state ID(s), or `None` if no
            transition is found for that event from that state.
        """
        from_node = self.get_state_by_id(from_state_id)
        if not from_node:
            return None

        current: Optional[StateNode] = from_node
        while current:
            if event.type in current.on:
                for transition in current.on[event.type]:
                    # Return the first valid transition found
                    if transition.target_str:
                        try:
                            target_node = resolve_target_state(
                                transition.target_str, current
                            )
                            return {target_node.id}
                        except StateNotFoundError:
                            # This can happen if a target is valid but the guard
                            # is what makes it take a different path. Ignore.
                            pass
            current = current.parent

        return None

    # -------------------------------------------------------------------------
    # 🎨 Visualization Utilities
    # -------------------------------------------------------------------------

    def to_plantuml(self) -> str:
        """Generates a PlantUML string representation of the state machine.

        This can be used to automatically generate diagrams from your machine
        configuration, ensuring your documentation always stays in sync.

        Returns:
            A string formatted for rendering with PlantUML.
        """
        content = ["@startuml", "hide empty description"]

        def build_puml_states(node: StateNode, level: int):
            indent = "  " * level
            safe_id = node.id.replace(".", "_")
            if node.states:
                content.append(f'{indent}state "{node.key}" as {safe_id} {{')
                if node.initial and node.states.get(node.initial):
                    initial_target_id = node.states[node.initial].id.replace(
                        ".", "_"
                    )
                    content.append(f"{indent}  [*] --> {initial_target_id}")
                for child in node.states.values():
                    build_puml_states(child, level + 1)
                content.append(f"{indent}}}")
            else:
                content.append(f'{indent}state "{node.key}" as {safe_id}')

        build_puml_states(self, 0)

        def build_puml_transitions(node: StateNode):
            source_id = node.id.replace(".", "_")
            for event, transitions in node.on.items():
                for t in transitions:
                    if t.target_str:
                        try:
                            target_node = resolve_target_state(
                                t.target_str, node
                            )
                            target_id = target_node.id.replace(".", "_")
                            content.append(
                                f"{source_id} --> {target_id} : {event}"
                            )
                        except StateNotFoundError:
                            pass
            if node.on_done and node.on_done.target_str:
                try:
                    target_node = resolve_target_state(
                        node.on_done.target_str, node
                    )
                    target_id = target_node.id.replace(".", "_")
                    content.append(f"{source_id} --> {target_id} : onDone")
                except StateNotFoundError:
                    pass
            for child in node.states.values():
                build_puml_transitions(child)

        if self.initial and self.states.get(self.initial):
            initial_id = self.states[self.initial].id.replace(".", "_")
            content.append(f"[*] --> {initial_id}")
        build_puml_transitions(self)

        content.append("@enduml")
        return "\n".join(content)

    def to_mermaid(self) -> str:
        """Generates a Mermaid.js string representation of the state machine.

        This can be used to automatically generate diagrams in markdown files
        (e.g., on GitHub, or with tools like MkDocs).

        Returns:
            A string formatted for rendering with Mermaid.js.
        """
        content = ["stateDiagram-v2"]

        def build_mmd_states(node: StateNode, level: int):
            indent = "    " * level
            if node.states:
                content.append(f'{indent}state "{node.key}" as {node.key} {{')
                if node.initial and node.states.get(node.initial):
                    initial_key = node.states[node.initial].key
                    content.append(f"{indent}    [*] --> {initial_key}")
                for child in node.states.values():
                    build_mmd_states(child, level + 1)
                content.append(f"{indent}}}")

        def build_mmd_transitions(node: StateNode):
            for event, transitions in node.on.items():
                for t in transitions:
                    if t.target_str:
                        try:
                            target_node = resolve_target_state(
                                t.target_str, node
                            )
                            content.append(
                                f"{node.key} --> {target_node.key} : {event}"
                            )
                        except StateNotFoundError:
                            pass
            if node.on_done and node.on_done.target_str:
                try:
                    target_node = resolve_target_state(
                        node.on_done.target_str, node
                    )
                    content.append(
                        f"{node.key} --> {target_node.key} : onDone"
                    )
                except StateNotFoundError:
                    pass
            for child in node.states.values():
                build_mmd_transitions(child)

        if self.initial and self.states.get(self.initial):
            content.append(f"[*] --> {self.states[self.initial].key}")
        build_mmd_states(self, 0)
        build_mmd_transitions(self)

        return "\n".join(content)
