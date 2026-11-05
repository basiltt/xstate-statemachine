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
import math
import re
import threading
from enum import Enum
from typing import (
    cast,
    Container,
    Mapping,
    FrozenSet,
    Any,
    Callable,
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

from ._typing import TContext as TContext  # noqa: E402

# Define a specific type for state types for clarity and reuse.
StateType = Literal["atomic", "compound", "parallel", "final", "history"]
#: Every value `StateType` admits, for validating a config's `type`.
_STATE_TYPES: Tuple[str, ...] = (
    "atomic",
    "compound",
    "parallel",
    "final",
    "history",
)
#: The two kinds of history pseudo-state.
HistoryKind = Literal["shallow", "deep"]
#: An `after` key made only of digits: whole milliseconds (fast path).
_DIGITS_DELAY = re.compile(r"\s*\+?\d+\s*")
#: Any other NUMERIC-looking `after` key (``"1.5"``, ``"-5"``,
#: ``"1e3"``), which must still be whole, non-negative milliseconds.
_NUMERIC_DELAY = re.compile(r"\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?\s*")

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


def _config_bool(value: Any, key: str, where: str, default: bool) -> bool:
    """Read a boolean config flag, accepting only JSON ``true`` / ``false``.

    🛡️ ``bool(raw)`` made every non-empty string truthy, so ``"strict":
    "false"`` ENABLED strict mode and ``"reenter": "false"`` forced a
    re-entry: a mistyped flag silently did the opposite of what it said.
    The `[pydantic]` config gate already refuses non-bools (#266); the
    parser now agrees with it. ``None`` (JSON ``null``) means "not set".

    Args:
        value: The raw config value.
        key: The config key, for the error message.
        where: Who declares it (``"Machine 'm'"``, ``"Transition 'E' on
            state 'm.a'"``), for the error message.
        default: The value used when *value* is ``None``.

    Returns:
        bool: The flag.

    Raises:
        InvalidConfigError: *value* is neither a bool nor ``None``.
    """
    if value is None:
        return default
    if not isinstance(value, bool):
        raise InvalidConfigError(
            f"{where}: {key!r} must be true or false, got "
            f"{type(value).__name__} {value!r}."
        )
    return value


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


# 👶 Prefixes marking an action as a built-in actor-spawning directive.
#
# ⚠️ Order matters: `spawn_blocking_` must be tested before `spawn_`, since the
# latter is a prefix of the former.
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

    def __init__(
        self,
        config: Union[str, Dict[str, Any]],
        *,
        user_actions: Optional[Container[str]] = None,
    ) -> None:
        """Initializes the ActionDefinition from its configuration.

        Args:
            config: The action configuration from the machine definition.
                    It can be a simple `str` (the action name) or a `Dict`
                    (e.g., `{"type": "myAction", "params": {...}}`).
            user_actions: The action names the machine's `MachineLogic`
                implements, when known. A name found here is the USER's
                action even if it is spelled like a built-in, so the
                built-in's required-params check does not apply to it.

        Raises:
            InvalidConfigError: If the config is not a string or dictionary,
                its `type` is missing or not a non-empty string, its
                `params` is not an object or a callable, or a built-in
                action lacks a required param.
        """
        if isinstance(config, str):
            # 📝 Handle shorthand string definition: "myAction"
            if _PARSE_DEBUG():
                logger.debug(
                    "🔧 Parsing action definition from string: '%s'", config
                )
            self.type = config
            self.params = None
        elif isinstance(config, dict):
            # 📝 Handle object definition: {"type": "myAction", ...}
            if _PARSE_DEBUG():
                logger.debug(
                    "🔧 Parsing action definition from dict: %s", config
                )
            action_type = config.get("type")
            if not isinstance(action_type, str) or not action_type:
                # 🛡️ #266 battle: `{"type": 1}` escaped as a bare
                #    AttributeError from `startswith` deep in the parser.
                # 🛡️ A MISSING type used to become an action literally
                #    named "UnknownAction" -- a name nobody implements.
                raise InvalidConfigError(
                    "Action definition 'type' must be a non-empty string, "
                    f"got {type(action_type).__name__} {action_type!r}: "
                    f"{config!r}"
                )
            params = config.get("params")
            if params is not None and not (
                isinstance(params, dict) or callable(params)
            ):
                # 🛡️ `params: 5` escaped as a bare "'int' object is not
                #    iterable" from the built-in check below.
                raise InvalidConfigError(
                    f"Action '{action_type}': 'params' must be an object or "
                    f"a callable, got {type(params).__name__} {params!r}."
                )
            self.type = action_type
            self.params = params
            if user_actions is None or action_type not in user_actions:
                self._validate_builtin_params(config)
        else:
            # ❌ Reject invalid definitions
            raise InvalidConfigError(
                "Action definition must be a string or a dictionary, got "
                f"{type(config).__name__} {config!r}."
            )

    def _validate_builtin_params(self, config: Dict[str, Any]) -> None:
        """Reject a built-in action whose required params are missing.

        🏛️ #32: this is the ONE place every action dict is parsed -- entry,
        exit, transition actions, invoke onDone/onError, both engines -- so
        one check here covers all of them. When the required keys are found
        at the TOP level of the dict instead of under ``params`` (the
        natural mistake), the error says so explicitly.

        📝 Not called for a type the machine's logic implements (see
        ``user_actions``): user actions resolve BEFORE built-ins, so a user
        ``cancel`` / ``stop`` / ``log`` taking its own params must not be
        held to the built-in's signature (AGENTS.md).

        Args:
            config: The raw action dict, used to spot required keys written
                at its top level instead of under ``params``.

        Raises:
            InvalidConfigError: A required param of the built-in is missing.
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

    def __init__(
        self, config: Union[str, Dict[str, Any], "GuardDefinition"]
    ) -> None:
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
                    "Guard object must have a non-empty string 'type', "
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
                "Guard must be a string or a dictionary, "
                f"got {type(config).__name__} {config!r}."
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
                f"Composite guard '{self.type}' requires at least one "
                "nested guard (via 'children', or 'params.guards')."
            )
        if (
            self.is_composite
            and self.type == "not"
            and len(self.children) != 1
        ):
            raise InvalidConfigError(
                "Guard 'not' requires exactly one nested guard, got "
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
        target_str: The string representation of the target state (the
                    first one of a multi-target transition).
        target_strs: Every target string, in declaration order.
        actions: A list of `ActionDefinition` objects to execute.
        guard: The name of the guard condition to evaluate.
        reenter: A flag indicating if a self-transition should exit and
                 re-enter its source state. Defaults to `False`.
    """

    def __init__(
        self,
        event: str,
        config: Dict[str, Any],
        source: "StateNode[Any]",
        actions: Optional[List[ActionDefinition]] = None,
    ) -> None:
        """Initializes the TransitionDefinition.

        Args:
            event: The name of the event that triggers this transition.
            config: The dictionary defining the transition's properties
                    (e.g., `target`, `guard`, `reenter`).
            source: The `StateNode` where this transition is defined.
            actions: A list of `ActionDefinition` objects to be executed.

        Raises:
            InvalidConfigError: A malformed `target`, `guard`, `meta`,
                `reenter` or `internal`; the message names the event and
                the source state.
        """
        _dbg = getattr(getattr(source, "machine", None), "_parse_debug", None)
        if _dbg is None:
            _dbg = _PARSE_DEBUG()
        if _dbg:
            logger.debug(
                "🔧 Creating transition for event '%s' from config: %s",
                event,
                config,
            )
        self.event: str = event
        self.source: "StateNode[Any]" = source
        # ⚡ One pass over the transition's (typically 1-3) keys instead of
        #    seven `.get` probes; this runs for every transition of every
        #    build (#307 benchmark). `guard` wins over the v4 `cond` alias
        #    whenever the key is present, as `config.get("guard",
        #    config.get("cond"))` did.
        target = raw_guard = cond = internal = reenter = raw_meta = None
        has_guard = False
        forbidden = False
        for key, value in config.items():
            if key == "target":
                target = value
            elif key == "guard":
                raw_guard = value
                has_guard = True
            elif key == "cond":
                cond = value
            elif key == "reenter":
                reenter = value
            elif key == "internal":
                internal = value
            elif key == "meta":
                raw_meta = value
            elif key == "__forbidden__":
                forbidden = bool(value)
        if not has_guard:
            raw_guard = cond
        targets: Tuple[str, ...] = ()
        if isinstance(target, (list, tuple)):
            # 🎯 XState v5 multi-target: `target: ["#m.p.r1.x", "#m.p.r2.y"]`
            #    enters several states at once. The targets must lie in
            #    different regions of one parallel state; that is checked
            #    once they are resolved (`validation.multi_target_problem`).
            if not target or not all(
                isinstance(item, str) and item for item in target
            ):
                raise InvalidConfigError(
                    f"Transition '{event}' on state '{source.id}': a "
                    f"'target' list must hold one or more non-empty "
                    f"strings, got {list(target)!r}"
                )
            targets = tuple(target)
            target = targets[0]
        elif target is not None and not isinstance(target, str):
            # 🛡️ #266 battle: a number / dict target escaped as a bare
            #    AttributeError from the resolver; say what is accepted.
            raise InvalidConfigError(
                f"Transition '{event}' on state '{source.id}': 'target' "
                f"must be a string or a list of strings, got "
                f"{type(target).__name__}"
            )
        elif target == "":
            # 🛡️ An empty-string target (`on: {"E": ""}`) was falsy, so it
            #    silently became a TARGETLESS transition -- the event was
            #    consumed and nothing moved. Omit `target` for that.
            raise InvalidConfigError(
                f"Transition '{event}' on state '{source.id}': 'target' "
                f"is an empty string. Omit 'target' for a targetless "
                f"transition, or name the state to enter."
            )
        elif target:
            targets = (target,)
        #: The (first) target string. For a multi-target transition this is
        #: the FIRST target only -- every target is in `target_strs`.
        #: Diagram exports and the structural hash read this field.
        self.target_str: Optional[str] = target
        #: Every target string, in declaration order (``()`` when the
        #: transition is targetless).
        self.target_strs: Tuple[str, ...] = targets
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
        self.resolved_target: Optional["StateNode[Any]"] = None
        #: Every resolved target of a multi-target transition, in
        #: declaration order (``None`` for a single-target transition, or
        #: when one of them did not resolve at build time).
        self.resolved_targets: Optional[Tuple["StateNode[Any]", ...]] = None
        #: ⚡ Perf: static transition GEOMETRY, memoised on first execution
        #: by `BaseInterpreter._transition_geometry`. For a given resolved
        #: target the domain (LCCA) and the entry path from the domain down
        #: to the target depend only on the immutable tree, yet were rebuilt
        #: on every event (~6 us of a 21 us flat macrostep). Keyed on the
        #: target's identity so a live-resolved (`strict_targets=False`)
        #: transition that resolves differently is not served a stale answer.
        #: The EXIT set stays dynamic -- it depends on the live configuration.
        self._geometry: Optional[
            Tuple[Any, Any, Tuple["StateNode[Any]", ...]]
        ] = None

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
        self.guard_def: Optional[GuardDefinition] = None
        if raw_guard is not None:
            try:
                self.guard_def = GuardDefinition(raw_guard)
            except InvalidConfigError as exc:
                # 🧭 Name the transition: "Guard must be a string" alone
                #    gives no way to find the offender in a large chart.
                raise InvalidConfigError(
                    f"Transition '{event}' on state '{source.id}': "
                    f"invalid 'guard': {exc}"
                ) from exc
        # 🔁 `reenter` (XState v5) with `internal` (v4) as an alias:
        #    `internal: False` means "exit and re-enter", i.e. `reenter: True`.
        #    Before 0.8.0 `internal` was silently dropped, so a migrating
        #    user's explicit opt-in vanished with no validation error (#29).
        # 🛡️ Both flags go through `_config_bool`: ``bool("false")`` is
        #    True, so a string flag silently did the opposite of what it
        #    said (``"reenter": "false"`` re-ran entry/exit actions).
        if internal is None and reenter is None:
            self.reenter: bool = False  # ⚡ the default, no label needed
        else:
            where = f"Transition '{event}' on state '{source.id}'"
            if internal is not None:
                self.reenter = not _config_bool(
                    internal, "internal", where, False
                )
            else:
                self.reenter = _config_bool(reenter, "reenter", where, False)
        #: Marks an explicitly forbidden transition (``on: {"E": None}``).
        #: Selecting it consumes the event without changing state, which stops
        #: the upward walk from reaching an ancestor's handler.
        self.forbidden: bool = forbidden
        #: #293: transition-level ``meta`` (already an accepted key under
        #: ``strictConfig``). The EDA outbox reads ``meta.publish`` here.
        if raw_meta is not None and not isinstance(raw_meta, dict):
            raise InvalidConfigError(
                f"Transition '{event}' on '{source.id}' has an invalid "
                f"'meta' value of type '{type(raw_meta).__name__}'. "
                f"Expected an object/dict."
            )
        self.meta: Dict[str, Any] = raw_meta or {}

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

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        target: Any = (
            list(self.target_strs)
            if len(self.target_strs) > 1
            else f"'{self.target_str}'"
        )
        return (
            f"Transition(event='{self.event}', "
            f"target={target}, reenter={self.reenter})"
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


def event_payload(context: Any, event: Any) -> Dict[str, Any]:
    """An ``invoke.input`` factory that forwards the triggering event's payload.

    XState passes an invoked actor no input unless the chart declares one;
    this is the explicit, portable way to hand a service the fields of the
    event that entered the state -- the JSON equivalent is
    ``"input": ({event}) => event`` in XState. ``send("START", url=...)``
    then arrives as ``event.payload["input"]["url"]`` (or as a ``url``
    parameter with argument injection)::

        State(invoke={"src": "fetchUrl", "input": event_payload, "onDone": "done"})

        @loading.service(input=event_payload, on_done="done")
        def fetch_url(self, url): ...

    Args:
        context: The parent's context (unused).
        event: The event whose transition entered the invoking state.

    Returns:
        Dict[str, Any]: A copy of the event's payload (``{}`` when it has
        none, or when the state was entered without an event).
    """
    del context
    payload = getattr(event, "payload", None)
    return dict(payload) if isinstance(payload, dict) else {}


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
        source: "StateNode[Any]",
        on_done: List[TransitionDefinition],
        on_error: List[TransitionDefinition],
    ) -> None:
        """Initializes the InvokeDefinition.

        Args:
            invoke_id: The pre-calculated unique ID for the invocation.
            config: The raw dictionary from the `invoke` key in the JSON.
            source: The `StateNode` that hosts this invocation.
            on_done: A pre-parsed list of 'onDone' transitions.
            on_error: A pre-parsed list of 'onError' transitions.

        Raises:
            InvalidConfigError: `src` is not a service name, or `systemId`
                is not a non-empty string.
        """
        # 🪵 Module `logger`, never the `logging.*` helpers: those call
        #    `logging.basicConfig()` on an unconfigured root and so installed
        #    a stderr handler in the HOST application (MOD-01).
        if _PARSE_DEBUG():
            logger.debug(
                "🔧 Creating invoke definition for state '%s' with config: %s",
                source.id,
                config,
            )
        self.id: str = invoke_id
        raw_src = config.get("src")
        if raw_src is not None and not isinstance(raw_src, str):
            # 🛡️ #231: `src` NAMES a service; it is resolved by name from
            #    `MachineLogic.services` (or discovered). The XState-JS
            #    inline-machine dict is a natural thing to try and it used
            #    to die as `TypeError: unhashable type: 'dict'` inside
            #    `logic_loader` (a `set.add`), naming no machine, state or
            #    key. Refuse it here, where the value is read, before any
            #    consumer touches it -- a hard error like a non-dict
            #    `invoke` entry, whatever `strict_config` says.
            raise InvalidConfigError(
                f"State '{source.id}' invoke '{invoke_id}': 'src' must be "
                f"a service name (str), got {type(raw_src).__name__}. To "
                f"invoke a nested machine, build it with "
                f"create_machine(...) and register it under that name in "
                f"MachineLogic(services={{...}})."
            )
        self.src: Optional[str] = raw_src
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
        raw_system_id = config.get("systemId")
        if raw_system_id is not None and (
            not isinstance(raw_system_id, str) or not raw_system_id
        ):
            raise InvalidConfigError(
                f"State '{source.id}' invoke '{invoke_id}': 'systemId' must "
                f"be a non-empty string, got {type(raw_system_id).__name__} "
                f"{raw_system_id!r}."
            )
        self.system_id: Optional[str] = raw_system_id
        self.source: "StateNode[Any]" = source
        self.on_done: List[TransitionDefinition] = on_done
        self.on_error: List[TransitionDefinition] = on_error

        # ⚠️ Warn if the service source is missing, as it's a common error.
        if not self.src:
            logger.warning(
                "⚠️ Invoke definition in state '%s' is missing a 'src' "
                "property.",
                self.source.id,
            )
        if _PARSE_DEBUG():
            logger.debug("✅ Created InvokeDefinition with ID '%s'", self.id)

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
    # ⚡ The scalar keys too, so `StateNode.__init__` probes the dict once.
    "id",
    "description",
    "output",
    "history",
    "target",
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
#: between `create_machine()` calls.
#: 🐛 #264 battle: it was ONE set for every thread, so two threads
#:    building machines from the SAME config dict (a scanner pool's
#:    ``machine_for_key = lambda k: create_machine(CFG)``) saw each
#:    other's ids and raised a false "aliased cycle" -- 1 035 failures in
#:    2 400 builds over 8 threads. Per-thread now.
_config_stack_local = threading.local()


class _ConfigStack:
    """The calling thread's descent set (`set`-like: in / add / discard).

    🏛️ A facade over a `threading.local` slot rather than a bare module
    set: the set must be PER THREAD (#264 battle), and the facade keeps
    every caller from re-implementing the lazy per-thread creation.
    `StateNode.__init__` takes the set itself once per node through
    `descent()` (⚡ one thread-local lookup, not three per child).
    """

    @staticmethod
    def descent() -> Set[int]:
        """Return the calling thread's set, creating it on first use.

        Returns:
            Set[int]: ``id()`` of every config dict on the current descent.
        """
        s = getattr(_config_stack_local, "s", None)
        if s is None:
            s = _config_stack_local.s = set()
        return s

    def __contains__(self, item: int) -> bool:
        """Report whether config ``id`` *item* is on the current descent."""
        return item in self.descent()

    def add(self, item: int) -> None:
        """Push config ``id`` *item* onto the current descent."""
        self.descent().add(item)

    def discard(self, item: int) -> None:
        """Pop config ``id`` *item* from the current descent, if present."""
        self.descent().discard(item)


_config_stack = _ConfigStack()


class StateNode(Generic[TContext]):
    """Represents a single state in the state machine graph.

    A `StateNode` can be atomic, compound, parallel, or final. It encapsulates
    all its own behavior, including transitions, actions, services, and child states.
    This class is the core of the in-memory representation of the statechart.
    """

    # 📝 Every instance attribute is pre-declared at class level so the
    #    class structure is explicit to static analysis tools.
    id: str
    key: str
    parent: Optional["StateNode[Any]"]
    machine: "MachineNode[Any]"
    type: StateType
    initial: Optional[str]
    on: Dict[str, List[TransitionDefinition]]
    on_done: Optional[TransitionDefinition]
    #: Every state-level ``onDone`` transition, in declaration order.
    on_done_transitions: List[TransitionDefinition]
    # 🐛 [Issue #60] Keys may be int (ms delays) or str (named delays,
    # e.g. "TIMEOUT"), matching what `_parse_after` actually returns and
    # assigns to `self.after` below -- keeps this in sync with mypy.
    after: Dict[Union[int, str], List[TransitionDefinition]]
    entry: List[ActionDefinition]
    exit: List[ActionDefinition]
    invoke: List[InvokeDefinition]
    states: Dict[str, "StateNode[Any]"]
    doc_order: int

    def __init__(
        self,
        machine: "MachineNode[Any]",
        config: Dict[str, Any],
        key: str,
        parent: Optional["StateNode[Any]"] = None,
    ) -> None:
        """Initializes a StateNode and its subtree from a configuration.

        This constructor recursively parses a piece of the configuration
        dictionary and builds the corresponding node and all of its children,
        linking them together to form the statechart tree.

        Args:
            machine: The root machine node.
            config: The configuration dictionary for *this specific state*.
            key: The key for this state within its parent's `states` object.
            parent: The parent state node, if any.

        Raises:
            InvalidConfigError: Any malformed key of this state or of a
                descendant; the message names the state and the key.
        """
        # ⚡ Two debug records per node add up on a 1,000-machine build;
        #    gate them on the level once instead of formatting args each time.
        _dbg = getattr(machine, "_parse_debug", None)
        if _dbg is None:  # a bare `StateNode` built outside a MachineNode
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
            declared_id,
            raw_description,
            raw_output,
            raw_history,
            raw_target,
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

        # 📑 Document order: the node's position in a pre-order walk of the
        #    config (the root is 0, then each child before its own children,
        #    siblings in declaration order). XState / SCXML order the entry
        #    set by it and the exit set by its reverse, so parallel regions
        #    are entered and exited one whole region at a time, in the order
        #    the chart declares them. Assigned here, before the children are
        #    built, so the numbering is pre-order by construction.
        order = getattr(machine, "_doc_order_next", 0)
        self.doc_order: int = order
        machine._doc_order_next = order + 1

        # ⚙️ Determine and strictly type the state's `type` attribute.
        if cfg_type is None:
            # ⚡ The inferred type (the common case) without the method
            #    call; `_determine_state_type` keeps the validation of an
            #    explicit `type`. Same rule as there: children => compound.
            self.type: StateType = (
                "compound"
                if raw_states
                or (
                    raw_states is not None and not isinstance(raw_states, dict)
                )
                else "atomic"
            )
        else:
            self.type = self._determine_state_type(raw_states, cfg_type)
        if _dbg:
            logger.debug(
                "  -> StateNode '%s' identified as type: '%s'",
                self.id,
                self.type,
            )

        # ⚙️ Parse all properties from the configuration dictionary.
        # This encapsulates the parsing logic within the model itself.
        self.initial = (
            None  # ⚡ a leaf without `initial`: nothing to resolve
            if raw_initial is None and self.type != "compound"
            else self._parse_initial(raw_initial, raw_states)
        )

        # 🏷️ Metadata keys. Previously all three were dropped at parse time,
        #    so `tags` (UI-state modelling) and `meta` (arbitrary annotation)
        #    were silently unavailable to users who had declared them.
        if raw_tags is None:
            # ⚡ The overwhelmingly common case: no tags declared.
            self.tags: Set[str] = set()
        else:
            if isinstance(raw_tags, str):
                raw_tags = [raw_tags]
            # ⚠️ Validate rather than let `set()` decide. A bare
            #    `set(raw_tags)` turned `tags: 123` into an opaque "'int'
            #    object is not iterable" with no hint as to WHICH state was
            #    malformed, and silently accepted `tags: {"a": 1}` as the
            #    tag set {"a"} by iterating the mapping's keys — a config
            #    typo that produced working-looking nonsense.
            if isinstance(raw_tags, (dict, bytes)) or not isinstance(
                raw_tags, (list, tuple, set, frozenset)
            ):
                raise InvalidConfigError(
                    f"State '{self.id}' has an invalid 'tags' value of type "
                    f"'{type(raw_tags).__name__}'. Expected a string or a "
                    f"list of strings."
                )
            non_strings = [tag for tag in raw_tags if not isinstance(tag, str)]
            if non_strings:
                raise InvalidConfigError(
                    f"State '{self.id}' has non-string tag(s): "
                    f"{non_strings!r}. Every tag must be a string."
                )
            self.tags = set(raw_tags)

        if raw_meta is None:
            self.meta: Dict[str, Any] = {}
        else:
            if not isinstance(raw_meta, dict):
                raise InvalidConfigError(
                    f"State '{self.id}' has an invalid 'meta' value of type "
                    f"'{type(raw_meta).__name__}'. Expected an object/dict."
                )
            self.meta = raw_meta
        if raw_description is not None and not isinstance(
            raw_description, str
        ):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'description' of type "
                f"'{type(raw_description).__name__}'. Expected a string."
            )
        self.description: Optional[str] = raw_description

        # 🏁 Final states may declare `output` (a.k.a. "done data"), which is
        #    surfaced on the `done.state.*` / `done.invoke.*` event.
        self.output: Any = raw_output

        # 🕰️ History configuration. `history` is "shallow" (restore the
        #    immediate child) or "deep" (restore the full nested
        #    configuration). XState defaults to shallow.
        self.history: Optional[HistoryKind] = None
        if self.type == "history":
            history_kind = raw_history
            if history_kind is None:
                history_kind = "shallow"
            elif history_kind not in ("shallow", "deep"):
                # 🛡️ A typo (`"dep"`) used to fall back to shallow with a
                #    log line: a deep-history state silently restored only
                #    its immediate child.
                raise InvalidConfigError(
                    f"State '{self.id}': 'history' must be 'shallow' or "
                    f"'deep', got {history_kind!r}."
                )
            self.history = cast(HistoryKind, history_kind)
        #: Default target used when a history state has nothing recorded yet.
        if raw_target is not None and (
            not isinstance(raw_target, str) or not raw_target
        ):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'target' "
                f"{raw_target!r}. A history state's default 'target' must "
                f"be a non-empty state name."
            )
        self.target_str: Optional[str] = raw_target

        # ⚡ Each absent key short-circuits here instead of inside its
        #    `_parse_*` helper: most states declare one or two of these six
        #    keys, so the method calls for the other four or five were pure
        #    overhead on every node of every build (#307 benchmark).
        self.entry = (
            []
            if raw_entry is None
            else self._parse_actions(raw_entry, "entry")
        )
        self.exit = (
            [] if raw_exit is None else self._parse_actions(raw_exit, "exit")
        )
        self.on = (
            {}
            if raw_on is None and raw_always is None
            else self._parse_on(raw_on, raw_always)
        )
        # ⚡ #55 part 2: precompiled descriptor index. `_matching_descriptors`
        #    used to scan every `on` key per event to find partials; for a
        #    typical machine there are none, so the scan was pure overhead
        #    on the hottest path. Built ONCE here.
        # ⚡ Perf: the partial-wildcard table is only non-empty when some
        #    `on` key ends in ".*"; skip the generator + sorted() otherwise
        #    (it ran on every node, sorting an empty list 6 times in 7).
        on_map = self.on
        self._on_partials: List[Tuple[str, str]] = (
            sorted(
                (
                    (key, key[:-2])
                    for key in on_map
                    if key != "*" and key.endswith(".*")
                ),
                key=lambda kv: len(kv[0]),
                reverse=True,
            )
            if on_map and any(k.endswith(".*") for k in on_map)
            else []
        )
        self._on_has_wildcard: bool = "*" in on_map
        #: 🏁 XState v5 lets ``onDone`` be a LIST of guarded alternatives
        #:    (the bundled Stately corpus has one). All of them are kept in
        #:    `on_done_transitions`; `on_done` stays the FIRST one (or
        #:    ``None``) for the code that predates the list form.
        self.on_done_transitions = (
            [] if raw_on_done is None else self._parse_on_done(raw_on_done)
        )
        self.on_done = (
            self.on_done_transitions[0] if self.on_done_transitions else None
        )
        self.after = {} if raw_after is None else self._parse_after(raw_after)
        self.invoke = (
            [] if raw_invoke is None else self._parse_invoke(raw_invoke)
        )
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
            if not isinstance(state_key, str) or not state_key:
                # 🛡️ `""` built an id ending in '.', which no target can
                #    name; a non-string key cannot be addressed at all.
                raise InvalidConfigError(
                    f"State '{self.id}' has an invalid child state key "
                    f"{state_key!r}. State keys must be non-empty strings."
                )
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
        #    The facts are written once this node's children are complete;
        #    `subtree_has_actions` is therefore exact, never provisional.
        has_actions = bool(self.entry or self.exit)
        has_history = self.type == "history"
        has_always = "" in self.on
        self.states = {}
        # ⚡ One thread-local lookup per node, not three per child.
        descent: Set[int] = _config_stack.descent()
        for state_key, state_config in raw_states.items():
            cfg_id = id(state_config)
            if cfg_id in descent:
                raise InvalidConfigError(
                    f"State '{self.id}.{state_key}' is defined by a config "
                    f"dict that is already one of its own ancestors (an "
                    f"aliased cycle). Each state must have its own config "
                    f"object; copy the template instead of reusing it."
                )
            descent.add(cfg_id)
            try:
                child = self.states[state_key] = StateNode(
                    machine, state_config, state_key, self
                )
            finally:
                descent.discard(cfg_id)
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
        """Determines the type of the state based on its configuration.

        An explicit ``type`` must be one of `StateType`'s values and fit
        the node's shape; otherwise the type is inferred: ``compound`` when
        the state declares children, ``atomic`` when it does not.

        🛡️ A typo used to change the execution semantics silently: a leaf
        ``"type": "Final"`` built an ATOMIC state (no ``done.state.*``, so
        ``onDone`` never fired) and ``"paralel"`` on a parent built a
        compound one. `strictConfig` cannot catch it -- ``type`` is a known
        key -- so the value itself is validated here.

        Args:
            raw_states: The raw ``states`` value (``None`` when absent).
            cfg_type: The raw ``type`` value (``None`` when absent).

        Returns:
            StateType: The validated or inferred state type.

        Raises:
            InvalidConfigError: ``type`` is not a known state type, or a
                ``compound`` / ``parallel`` state declares no children. (An
                ``atomic`` / ``final`` / ``history`` state WITH children is
                built as ``compound`` with a WARNING, for compatibility.)
        """
        # 📝 An empty `states: {}` declares no children.
        has_children = bool(raw_states) or (
            raw_states is not None and not isinstance(raw_states, dict)
        )
        if cfg_type is None:
            return "compound" if has_children else "atomic"
        if cfg_type not in _STATE_TYPES:
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'type' {cfg_type!r}; "
                f"expected one of {list(_STATE_TYPES)}."
            )
        if has_children and cfg_type not in ("compound", "parallel"):
            # ⚠️ Kept as a compound state for compatibility: real Stately
            #    exports ship `"type": "final"` on a state WITH children
            #    (the bundled corpus has one), and 0.11 built those as
            #    compound. The warning names what is ignored.
            logger.warning(
                "⚠️ State '%s' is declared 'type': %r but has child "
                "'states'; only 'compound' and 'parallel' states may have "
                "children. Building it as 'compound' and IGNORING the "
                "declared type.",
                self.id,
                cfg_type,
            )
            return "compound"
        if not has_children and cfg_type in ("compound", "parallel"):
            raise InvalidConfigError(
                f"State '{self.id}' is declared 'type': {cfg_type!r} but "
                f"has no child 'states'."
            )
        # 📝 Membership in `_STATE_TYPES` proved it is a `StateType`.
        return cast(StateType, cfg_type)

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
        2. several children → warn, because there is no safe guess (start()
           then raises; see the comment below);
        3. no children at all → leave `None`; the state is effectively atomic.

        An explicit ``initial`` on a compound state must name one of its
        children: XState's ``createMachine`` refuses an unknown one, and
        here it used to surface only at ``start()``.

        Args:
            initial: The raw ``initial`` value (``None`` when absent).
            raw_states: The raw ``states`` value.

        Returns:
            Optional[str]: The initial child key, explicit or inferred.

        Raises:
            InvalidConfigError: ``initial`` is not a string, or names no
                child of this compound state.
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
        if self.type != "compound":
            return initial
        if initial:
            if isinstance(raw_states, dict) and initial not in raw_states:
                import difflib

                close = difflib.get_close_matches(
                    initial, [k for k in raw_states if isinstance(k, str)], 1
                )
                hint = f" Did you mean {close[0]!r}?" if close else ""
                raise InvalidConfigError(
                    f"State '{self.id}': 'initial' {initial!r} is not one of "
                    f"its child states {sorted(map(str, raw_states))}.{hint}"
                )
            return initial
        # 🛡️ #266 battle (B): a non-dict `states` reached `.items()` below
        #    as a bare AttributeError before the shape check in `__init__`
        #    could name it. Defer: that check raises InvalidConfigError.
        if not isinstance(raw_states, dict):
            return initial
        # 🕰️ History pseudo-states are never a valid initial target.
        candidates = [
            key
            for key, child in (raw_states or {}).items()
            if not (isinstance(child, dict) and child.get("type") == "history")
        ]

        if len(candidates) == 1:
            # 📝 keys of the user's `states` mapping are state names (str).
            inferred = cast(str, candidates[0])
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

    def _parse_actions(
        self, config: Optional[Any], where: str
    ) -> List[ActionDefinition]:
        """Parses an action or list of actions from config.

        Args:
            config: The raw ``entry`` / ``exit`` / ``actions`` value: an
                action, a list of actions, or ``None``.
            where: Which key this is (``"entry"``, ``"transition 'E'
                actions"``), named in any error.

        Returns:
            List[ActionDefinition]: The parsed actions (``[]`` for none).

        Raises:
            InvalidConfigError: A malformed action; the message names this
                state and *where*.
        """
        if config is None:
            return []
        if not isinstance(config, (str, dict, list)) or config == "":
            # 🛡️ `if not config` used to swallow `0` / `False` / `""` as
            #    "no actions" -- an action list that silently vanished.
            raise InvalidConfigError(
                f"State '{self.id}' {where}: expected an action name, an "
                f"action object or a list of them, got "
                f"{type(config).__name__} {config!r}."
            )
        if not config:
            return []
        # 📝 User actions resolve BEFORE built-ins (AGENTS.md), so a name the
        #    logic implements is exempt from the built-in params check.
        #    `logic` is duck-typed; anything without an `actions` mapping
        #    simply exempts nothing.
        user_actions = getattr(
            getattr(self.machine, "logic", None), "actions", None
        )
        if not isinstance(user_actions, Mapping):
            user_actions = None
        try:
            return [
                ActionDefinition(a, user_actions=user_actions)
                for a in self._ensure_list(config)
            ]
        except InvalidConfigError as exc:
            raise InvalidConfigError(
                f"State '{self.id}' {where}: {exc}"
            ) from exc

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
            if always_config is None:
                # ⚡ Neither `on` nor `always`: the shape of most leaf states.
                return on_map
            raw_on = {}
        if not isinstance(raw_on, dict):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'on' value of type "
                f"'{type(raw_on).__name__}'. Expected an object/dict mapping "
                f"event names to transitions."
            )
        create = self._create_transition
        for event, transitions_config in raw_on.items():
            # ⚡ The two overwhelmingly common shapes -- a target string and
            #    a single transition object -- are handled inline. Going
            #    through `_normalize_transitions` cost a method call plus an
            #    f-string label (used only in its error message) for every
            #    event of every build (#307 benchmark).
            if isinstance(transitions_config, str):
                on_map[event] = [create(event, {"target": transitions_config})]
            elif isinstance(transitions_config, dict):
                on_map[event] = [create(event, transitions_config)]
            else:
                normalized_configs = self._normalize_transitions(
                    transitions_config, f"State '{self.id}' on {event!r}"
                )
                on_map[event] = [
                    create(event, t_config) for t_config in normalized_configs
                ]

        # ⚡ Merge `always` into the transient ("") bucket.
        if always_config is not None:
            always_transitions = [
                self._create_transition("", t_config)
                for t_config in self._normalize_transitions(
                    always_config, f"State '{self.id}' always"
                )
            ]
            on_map.setdefault("", []).extend(always_transitions)

        return on_map

    def _parse_on_done(
        self, on_done_config: Any
    ) -> List[TransitionDefinition]:
        """Parses the 'onDone' transition(s) for a compound/parallel state.

        🛡️ Only the FIRST entry of a list used to be kept (the comment said
        "there can be only one onDone transition"), so with
        ``[{guard: g, target: b}, {target: c}]`` and ``g`` false the
        unguarded fallback was dropped and the machine parked. Every entry
        is parsed now, as for ``on`` and invoke ``onDone``.

        Args:
            on_done_config: The raw ``onDone`` value.

        Returns:
            List[TransitionDefinition]: The transitions, in order (``[]``
            when none is declared).

        Raises:
            InvalidConfigError: ``onDone`` is malformed.
        """
        if on_done_config is None or (
            isinstance(on_done_config, (dict, list)) and not on_done_config
        ):
            return []
        event = f"done.state.{self.id}"
        transitions = [
            self._create_transition(event, t_config, "onDone")
            for t_config in self._normalize_transitions(
                on_done_config, f"State '{self.id}' onDone"
            )
        ]
        if _PARSE_DEBUG():
            logger.debug(
                "  -> Parsed %d onDone transition(s) for '%s'",
                len(transitions),
                self.id,
            )
        return transitions

    def _parse_after(
        self, raw_after: Any
    ) -> Dict[Union[int, str], List[TransitionDefinition]]:
        """Parses all delayed transitions from the 'after' property.

        📝 Keys may be a numeric duration in milliseconds *or* a symbolic
        name resolved at runtime from `MachineLogic.delays`. Previously every
        key was coerced with `int()`, so a named delay such as
        ``after: {"TIMEOUT": ...}`` raised a bare `ValueError` at parse time
        with no indication that named delays were the intended feature.

        Args:
            raw_after: The raw ``after`` mapping (``None`` when absent).

        Returns:
            Dict[Union[int, str], List[TransitionDefinition]]: Transitions
            keyed by whole milliseconds (``int``) or delay name (``str``).

        Raises:
            InvalidConfigError: ``after`` is not a mapping, a key is not a
                valid delay (see `_normalize_delay_key`), or two keys name
                the same delay.
        """
        after_map: Dict[Union[int, str], List[TransitionDefinition]] = {}
        if raw_after is None:
            return after_map  # ⚡ no `after`: nothing to parse
        if not isinstance(raw_after, dict):
            raise InvalidConfigError(
                f"State '{self.id}' has an invalid 'after' value of type "
                f"'{type(raw_after).__name__}'. Expected an object/dict "
                f"mapping delays to transitions."
            )
        raw_keys: Dict[Union[int, str], Any] = {}
        for delay, transitions_config in raw_after.items():
            key = self._normalize_delay_key(delay)
            if key in raw_keys:
                # 🛡️ `{"100": ..., " 100": ...}` both coerced to 100 and
                #    the second silently replaced the first.
                raise InvalidConfigError(
                    f"State '{self.id}': 'after' keys {raw_keys[key]!r} and "
                    f"{delay!r} both name the delay {key!r}."
                )
            raw_keys[key] = delay
            normalized_configs = self._normalize_transitions(
                transitions_config, f"State '{self.id}' after[{delay!r}]"
            )
            after_map[key] = [
                self._create_transition(
                    f"after.{key}.{self.id}", t_config, "after", key
                )
                for t_config in normalized_configs
            ]
        return after_map

    def _normalize_delay_key(self, delay: Any) -> Union[int, str]:
        """Validate one ``after`` key: whole milliseconds, or a delay NAME.

        🛡️ ``int(delay)`` used to truncate ``1.5`` to ``1``, accept ``-5``
        (a deadline in the past) and read ``True`` as ``1``. A numeric key
        -- an ``int`` or a numeric string such as ``"500"`` -- must now be
        a whole, non-negative number of milliseconds; any other non-empty
        string is a named delay resolved from `MachineLogic.delays`.

        Args:
            delay: The raw key.

        Returns:
            Union[int, str]: Milliseconds, or the delay name.

        Raises:
            InvalidConfigError: The key is a bool, a fractional / negative /
                non-finite number, an empty string, or another type.
        """
        value: Any = None
        if isinstance(delay, bool) or not isinstance(delay, (int, float, str)):
            value = None
        elif isinstance(delay, str):
            if _DIGITS_DELAY.fullmatch(delay):
                return int(delay)  # ⚡ the common "500" case
            if _NUMERIC_DELAY.fullmatch(delay):
                value = float(delay)
            elif delay.strip():
                # 🏷️ A symbolic delay name; resolved by the interpreter.
                return delay
        else:
            value = delay
        if (
            value is None
            or not math.isfinite(value)
            or value < 0
            or value != int(value)
        ):
            raise InvalidConfigError(
                f"State '{self.id}': 'after' key {delay!r} is not a valid "
                f"delay. Use a whole, non-negative number of milliseconds "
                f"or the name of a delay in MachineLogic.delays."
            )
        return int(value)

    def _parse_invoke(self, raw_invoke: Any) -> List[InvokeDefinition]:
        """Parses all invoked services from the 'invoke' property.

        Args:
            raw_invoke: The raw ``invoke`` value: one object or a list.

        Returns:
            List[InvokeDefinition]: The parsed invocations.

        Raises:
            InvalidConfigError: An entry is not an object, or its ``id`` is
                not a non-empty string.
        """
        if raw_invoke is None:
            return []  # ⚡ no `invoke`: the shape of most states
        invoke_configs = self._ensure_list(raw_invoke)
        invokes: List[InvokeDefinition] = []
        for i_config in invoke_configs:
            # 🛡️ Reject rather than skip. Silently ignoring a malformed
            #    `invoke` produced a state that simply never called its
            #    service -- no error, no log, just a machine that hangs.
            if not isinstance(i_config, dict):
                raise InvalidConfigError(
                    f"State '{self.id}' has an invalid 'invoke' entry of "
                    f"type '{type(i_config).__name__}'. Expected an "
                    f"object/dict (or a list of them)."
                )

            # The invoke ID defaults to the state's ID if not provided.
            invoke_id = i_config.get("id", self.id)
            if not isinstance(invoke_id, str) or not invoke_id:
                # 🛡️ `id: 5` built `done.invoke.5` and an actor addressed
                #    by an int; `sendTo` and snapshots expect a string.
                raise InvalidConfigError(
                    f"State '{self.id}' has an invoke with an invalid 'id' "
                    f"{invoke_id!r}. Expected a non-empty string."
                )

            on_done_transitions = [
                self._create_transition(f"done.invoke.{invoke_id}", t, None)
                for t in self._normalize_transitions(
                    i_config.get("onDone", []),
                    f"State '{self.id}' invoke '{invoke_id}' onDone",
                )
            ]
            on_error_transitions = [
                self._create_transition(f"error.platform.{invoke_id}", t, None)
                for t in self._normalize_transitions(
                    i_config.get("onError", []),
                    f"State '{self.id}' invoke '{invoke_id}' onError",
                )
            ]
            invoke = InvokeDefinition(
                invoke_id=invoke_id,
                config=i_config,
                source=self,
                on_done=on_done_transitions,
                on_error=on_error_transitions,
            )
            invokes.append(invoke)
            # ⚡ Registered here, once `src` is known, so the validator's
            #    label can name the service (see `_create_transition`).
            pending = getattr(self.machine, "_targeted_transitions", None)
            if pending is not None:
                for t in on_done_transitions:
                    if t.target_strs:
                        pending.append((t, "invoke-done", invoke.src))
                for t in on_error_transitions:
                    if t.target_strs:
                        pending.append((t, "invoke-error", invoke.src))
        return invokes

    def _create_transition(
        self,
        event: str,
        config: Dict[str, Any],
        kind: Optional[str] = "on",
        extra: Any = None,
    ) -> TransitionDefinition:
        """A factory method to create a TransitionDefinition.

        Args:
            event: The event (or engine event type) the transition handles.
            config: One normalised transition dict.
            kind: Where the transition is declared, for the validator's
                finding labels: ``"on"`` (also ``always``), ``"onDone"``,
                ``"after"`` (*extra* is the delay key) or ``None`` when the
                caller registers the transition itself (invoke handlers).
            extra: Label detail for *kind* (see above).

        Returns:
            TransitionDefinition: The transition, with its actions parsed.

        Raises:
            InvalidConfigError: A malformed action, target or guard.
        """
        raw_actions = config.get("actions")
        # ⚡ Most transitions carry no actions: skip the call and the label
        #    f-string (only ever read in an error message) for them.
        actions = (
            []
            if raw_actions is None
            else self._parse_actions(
                raw_actions, f"transition {event!r} actions"
            )
        )
        transition = TransitionDefinition(
            event=event, config=config, source=self, actions=actions
        )
        if kind is not None and transition.target_strs:
            # ⚡ Hand the validator its work list as the tree is built
            #    (#307 benchmark): it used to re-walk the whole tree and
            #    filter every transition for a target.
            pending = getattr(self.machine, "_targeted_transitions", None)
            if pending is not None:
                pending.append((transition, kind, extra))
        return transition

    # -------------------------------------------------------------------------
    # Static Helpers for Configuration Normalization
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_transitions(
        config: Any, where: str = "Transition"
    ) -> List[Dict[str, Any]]:
        """Ensures transition configs are always a list of dictionaries.

        This handles XState's various shorthands for defining transitions.

        📝 `None` denotes a *forbidden* transition (``on: {"E": None}``): the
        event is explicitly consumed at this level so no ancestor handler
        runs. It is normalised to a single targetless, action-less transition
        carrying the `forbidden` marker. Previously it produced an empty list,
        so the key disappeared and the ancestor's handler fired anyway.

        Args:
            config: The raw transition value: a target string, a transition
                object, a list of either, or ``None``.
            where: The owning state and key, named in any error.

        Returns:
            List[Dict[str, Any]]: One dict per transition.

        Raises:
            InvalidConfigError: *config*, or an item of the list, is of an
                unsupported type.
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
                        f"{where}: invalid transition item in list: "
                        f"{type(item).__name__} {item!r}. Must be a string "
                        f"or dictionary."
                    )
            return normalized_list
        raise InvalidConfigError(
            f"{where}: invalid transition config: {type(config).__name__} "
            f"{config!r}. Must be a string, dictionary, or list."
        )

    @staticmethod
    def _ensure_list(config_item: Any) -> List[Any]:
        """Wrap a single configuration item in a list.

        Args:
            config_item: A value, a list of values, or ``None``.

        Returns:
            List[Any]: ``[]`` for ``None``, the list itself, or a one-item
            list holding *config_item*.
        """
        if config_item is None:
            return []
        return config_item if isinstance(config_item, list) else [config_item]

    # -------------------------------------------------------------------------
    # Tree Traversal Helpers
    # -------------------------------------------------------------------------

    def _is_descendant(
        self, node: "StateNode[Any]", ancestor: Optional["StateNode[Any]"]
    ) -> bool:
        """Checks if a node is a descendant of a specified ancestor."""
        # The 'self' parameter is unused here, but the method is part of the
        # class's public contract and called from instances.
        if not ancestor:
            return True
        return node == ancestor or node.id.startswith(f"{ancestor.id}.")

    def _get_path_to_state(
        self,
        to_state: "StateNode[Any]",
        *,
        stop_at: Optional["StateNode[Any]"] = None,
    ) -> List["StateNode[Any]"]:
        """Builds the list of states to enter to reach a target state."""
        path: List[StateNode[Any]] = []
        current: Optional[StateNode[Any]] = to_state
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


def _root_int(
    config: Dict[str, Any], key: str, default: int, minimum: int
) -> int:
    """Read a whole-number root option, naming the key on failure.

    🛡️ #266 battle (B): ``int(config["maxIterations"])`` escaped as a bare
    ``ValueError`` / ``TypeError`` for ``"abc"`` / ``[]``. Coercion stays as
    lenient as before for whole numbers (``"5"`` and ``5.0`` still work),
    but ``int()`` also TRUNCATED ``2.9`` to ``2``, read ``True`` as ``1``
    and accepted ``0`` / ``-3`` (a budget no chain can satisfy). Those are
    refused now, matching the `[pydantic]` gate (``ge=1``).

    Args:
        config: The root machine config.
        key: The option name.
        default: The value used when the key is absent.
        minimum: The smallest accepted value.

    Returns:
        int: The option value.

    Raises:
        InvalidConfigError: The value is not a whole number >= *minimum*.
    """
    raw = config.get(key, default)
    value: Optional[float] = None
    if not isinstance(raw, bool):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = None
    if (
        value is None
        or not math.isfinite(value)
        or value != int(value)
        or value < minimum
    ):
        raise InvalidConfigError(
            f"Machine '{config.get('id')}': {key!r} must be a whole number "
            f">= {minimum}, got {type(raw).__name__} {raw!r}."
        )
    return int(value)


def _root_float(config: Dict[str, Any], key: str) -> Optional[float]:
    """Read a non-negative, finite numeric root option (``None`` if absent).

    🛡️ ``float(raw)`` accepted ``"nan"`` (a timeout that never compares
    as elapsed), ``"inf"``, negatives and ``True``; the `[pydantic]` gate
    already demanded ``ge=0``.

    Args:
        config: The root machine config.
        key: The option name.

    Returns:
        Optional[float]: The value, or ``None`` when the key is absent.

    Raises:
        InvalidConfigError: The value is not a finite number >= 0.
    """
    raw = config.get(key)
    if raw is None:
        return None
    value: Optional[float] = None
    if not isinstance(raw, bool):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            value = None
    if value is None or not math.isfinite(value) or value < 0:
        raise InvalidConfigError(
            f"Machine '{config.get('id')}': {key!r} must be a finite "
            f"number >= 0, got {type(raw).__name__} {raw!r}."
        )
    return value


def _guarded_label(label: str, transition: TransitionDefinition) -> str:
    """Append ``[guard]`` to a diagram label when the transition is guarded.

    Args:
        label: The edge label without any guard annotation.
        transition: The transition whose guard (if any) is shown.

    Returns:
        The label, suffixed with ``" [guardName]"`` for guarded transitions.
    """
    guard = transition.guard
    return f"{label} [{guard}]" if guard else label


def _diagram_edges(node: StateNode[Any]) -> List[Tuple[StateNode[Any], str]]:
    """Collect the labelled outgoing edges of *node* for diagram export.

    📝 Shared by `to_mermaid` and `to_plantuml` so both renderers draw the
    same edges. Order: ``on`` events (eventless ``always`` transitions are
    labelled ``always``), the compound ``onDone``, delayed ``after``
    transitions, then ``invoke`` ``onDone`` / ``onError``. ``on`` and
    ``onDone`` labels are the bare event name; the newer edge kinds carry a
    ``[guard]`` suffix when guarded, because several guarded alternatives
    would otherwise be indistinguishable. Targetless transitions and
    targets that cannot be resolved are skipped.

    Args:
        node: The source state.

    Returns:
        ``(target_node, label)`` pairs in drawing order.
    """
    candidates: List[Tuple[TransitionDefinition, str]] = []
    for event, transitions in node.on.items():
        for t in transitions:
            label = _guarded_label("always", t) if event == "" else event
            candidates.append((t, label))
    for t in node.on_done_transitions:
        candidates.append((t, "onDone"))
    for delay, transitions in node.after.items():
        suffix = f"{delay}ms" if isinstance(delay, int) else str(delay)
        for t in transitions:
            candidates.append((t, _guarded_label(f"after {suffix}", t)))
    for invoke in node.invoke:
        for t in invoke.on_done:
            candidates.append((t, _guarded_label("invoke onDone", t)))
        for t in invoke.on_error:
            candidates.append((t, _guarded_label("invoke onError", t)))

    edges: List[Tuple[StateNode[Any], str]] = []
    for t, label in candidates:
        if not t.target_str:
            continue
        # ⚡ Reuse the target `validate_machine` already resolved; only a
        #    transition it could not resolve (or a hand-built tree that
        #    was never validated) goes through the resolver again.
        target = t.resolved_target
        if target is None:
            try:
                target = resolve_target_state(t.target_str, node)
            except StateNotFoundError:
                continue
        edges.append((target, label))
    return edges


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

    # 📝 Instance attributes pre-declared for static analysis, as above.
    logic: MachineLogic[TContext]
    initial_context: TContext
    #: Next free `StateNode.doc_order`; advanced while the tree is parsed.
    _doc_order_next: int

    def __init__(
        self, config: Dict[str, Any], logic: MachineLogic[TContext]
    ) -> None:
        """Initializes the root MachineNode and builds the state tree.

        Args:
            config: The root JSON configuration of the machine.
            logic: The implementation of the machine's business logic.

        Raises:
            InvalidConfigError: If the machine configuration lacks a root
                'id', or any root option or state is malformed (the message
                names the key and the state).
        """
        # 🛡️ The root of any machine must have a non-empty ID.
        if not config.get("id"):
            raise InvalidConfigError(
                "❌ Machine configuration must have a root 'id'."
            )
        self.logic = logic
        #: The config dict this machine was built from (by reference; never
        #: mutated by the library). Read by the live inspector (#274) for
        #: `@xstate.actor.definition`; ``{}``-safe for hand-built nodes.
        self.source_config: Dict[str, Any] = config
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
        self.max_iterations: int = _root_int(
            config, "maxIterations", 1000, minimum=1
        )
        #: 🛡️ #51: `strict` from config; an interpreter may also opt in.
        self.strict: bool = _config_bool(
            config.get("strict"),
            "strict",
            f"Machine '{config['id']}'",
            False,
        )
        #: Payload validators keyed by event type; set by `create_machine`.
        self.event_schemas: Dict[str, Any] = {}
        #: Lazily built descriptor set; see `known_events`.
        self._known_events: Optional[FrozenSet[str]] = None
        #: ⚡ Perf: does ANY state in this machine declare a `history` child?
        #: Filled in from the post-order `_subtree_has_history` fact once
        #: the tree is built. When
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
        self.spawn_blocking_timeout_ms: Optional[float] = _root_float(
            config, "spawnBlockingTimeout"
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
        self.strict_targets: bool = _config_bool(
            config.get("strictTargets"),
            "strictTargets",
            f"Machine '{config['id']}'",
            False,
        )

        #: 🏷️ #305: the machine's declared version, from the root ``"version"``
        #: key XState already allows. `validation.py` accepted the key but
        #: nothing read it -- silent acceptance -- so a persisted snapshot
        #: could not say which *revision* of a chart produced it. Snapshots
        #: now carry it as ``machine_version`` beside the structural hash;
        #: the hash detects drift, the label tells a human (and the
        #: migrator, #263) *which* revision. Coerced to `str`; ``None`` when
        #: the chart declares none.
        raw_version = config.get("version")
        self.version: Optional[str] = (
            None if raw_version is None else str(raw_version)
        )

        #: 🧪 #305: `create_machine(context_validator=)`. A callable
        #: ``(context) -> None`` that raises on an invalid context; both
        #: engines run it after any action that changed `context` and treat
        #: a raise as that action's failure (so `actionErrorPolicy`
        #: applies). ``None`` (default) costs one attribute read per action
        #: list. The seam the pydantic extra (#266) plugs into.
        self.context_validator: Optional[Callable[[Any], None]] = None

        #: Custom `id` → node registry, populated by `StateNode.__init__` as
        #: the tree is built. Must exist BEFORE `super().__init__` recurses
        #: into the children that register themselves here.
        self._custom_ids: Dict[str, StateNode[Any]] = {}
        #: ⚡ One DEBUG-level check per build, read by every node and
        #: transition of the parse instead of one `isEnabledFor` each.
        self._parse_debug: bool = _PARSE_DEBUG()
        #: ⚡ Every transition WITH a target, in parse (= document) order,
        #: as ``(transition, kind, extra)``; the build-time validator reads
        #: this list instead of walking the finished tree again, and clears
        #: it once it has run (`validation._pending_targets`).
        self._targeted_transitions: Optional[
            List[Tuple[TransitionDefinition, str, Any]]
        ] = []

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
        self._required_logic: Optional[
            Tuple[Set[str], Set[str], Set[str], Set[str]]
        ] = None
        # (subtree_has_actions is set per node during the parse.)

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
    def _tree_declares_actions(root: "StateNode[Any]") -> bool:
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
            transitions += node.on_done_transitions
            for inv in node.invoke:
                transitions += list(inv.on_done) + list(inv.on_error)
            if any(t.actions for t in transitions):
                return True
            stack.extend(node.states.values())
        return False

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
            # 🛡️ #195: the engine-generated names (`done.invoke.<id>`,
            #    `error.platform.<id>`, `after.<ms>.<state>`) are declared
            #    by the chart for the ENGINE to send. A caller asking about
            #    them as USER traffic (`user_sent=True`, i.e. a `strict`
            #    interpreter checking a hand-built `DoneEvent`) is an
            #    undeclared name like `done.invoke.NEVER`: only the engine
            #    may author a completion.
            if user_sent and event_type.startswith(ENGINE_EVENT_SHAPES):
                return False
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

        🔐 #205: a CHECKSUM against accidental drift -- a snapshot restored
        into a machine whose states or transitions have since changed --
        not an authentication tag. It is a public function of the config;
        anyone holding the config can compute it, and a party who controls
        a snapshot payload can write a matching one. To authenticate a
        snapshot, sign the whole payload outside the library and pass the
        fingerprint you hold as ``from_snapshot(expected_machine_hash=)``.

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
        stack: List[StateNode[Any]] = [self]
        while stack:
            node = stack.pop()
            if node is not self and node.key == bare:
                out.append(node.id)
            stack.extend(node.states.values())
        return out

    def get_state_by_id(self, state_id: str) -> Optional[StateNode[Any]]:
        """Finds a state node by its fully qualified ID.

        This method traverses the state tree to find a specific node.

        🔑 The machine id and state keys may themselves contain dots
        (``"my.machine"``, ``"v1.0"``) -- the parser and the resolver both
        allow it -- so the id is matched as a PREFIX and each level takes
        the run of segments that names a child, instead of a naive
        ``split(".")`` that could never find such a state. The shortest run
        is tried first; that is unambiguous because the parser rejects a
        dotted key whose first segment is also a sibling.

        Args:
            state_id: The fully qualified ID of the state to find
                      (e.g., "myMachine.parent.child").

        Returns:
            The `StateNode` if found, otherwise `None`.
        """
        if state_id == self.key:
            return self
        prefix = self.key + "."
        if not isinstance(state_id, str) or not state_id.startswith(prefix):
            logger.debug(
                "State ID %r does not start with machine ID %r.",
                state_id,
                self.key,
            )
            return None

        segments = state_id[len(prefix) :].split(".")
        node: StateNode[Any] = self
        index = 0
        while index < len(segments):
            # ⚡ Shortest match first: an ordinary key is found on the
            #    first probe.
            for end in range(index + 1, len(segments) + 1):
                child = node.states.get(".".join(segments[index:end]))
                if child is not None:
                    node = child
                    index = end
                    break
            else:
                logger.debug(
                    "State %r not found: no child of %r matches %r.",
                    state_id,
                    node.id,
                    segments[index],
                )
                return None
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

        current: Optional[StateNode[Any]] = from_node
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
                            # 📝 An unresolvable target (only possible when
                            #    the machine was built with
                            #    `strict_targets=False`): try the next one.
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

        ⚠️ Limitation: PlantUML aliases are the state ids with ``.``
        replaced by ``_``, so ids that differ only in that character
        (``a.b`` vs ``a_b``) share an alias and are drawn as one state.

        Returns:
            A string formatted for rendering with PlantUML.
        """
        content = ["@startuml", "hide empty description"]

        def build_puml_states(node: StateNode[Any], level: int) -> None:
            """Emit PlantUML state declarations for *node* and its descendants.

            Args:
                node: The state to render.
                level: Nesting depth used for indentation.
            """
            indent = "  " * level
            safe_id = node.id.replace(".", "_")
            if node.states:
                content.append(f'{indent}state "{node.key}" as {safe_id} {{')
                if node.initial and node.states.get(node.initial):
                    initial_target_id = node.states[node.initial].id.replace(
                        ".", "_"
                    )
                    content.append(f"{indent}  [*] --> {initial_target_id}")
                for index, child in enumerate(node.states.values()):
                    if index and node.type == "parallel":
                        # 🔀 `--` separates the concurrent regions.
                        content.append(f"{indent}  --")
                    build_puml_states(child, level + 1)
                content.append(f"{indent}}}")
            else:
                content.append(f'{indent}state "{node.key}" as {safe_id}')
                if node.type == "final" and node.parent is not None:
                    # 🏁 Final states terminate their enclosing region.
                    content.append(f"{indent}{safe_id} --> [*]")

        build_puml_states(self, 0)

        def build_puml_transitions(node: StateNode[Any]) -> None:
            """Emit PlantUML transition lines for *node* and its descendants.

            Transitions whose target cannot be resolved are skipped.

            Args:
                node: The state whose outgoing edges are rendered (see
                    `_diagram_edges`).
            """
            source_id = node.id.replace(".", "_")
            for target_node, label in _diagram_edges(node):
                target_id = target_node.id.replace(".", "_")
                content.append(f"{source_id} --> {target_id} : {label}")
            for child in node.states.values():
                build_puml_transitions(child)

        if self.initial and self.states.get(self.initial):
            initial_id = self.states[self.initial].id.replace(".", "_")
            content.append(f"[*] --> {initial_id}")
        build_puml_transitions(self)

        content.append("@enduml")
        return "\n".join(content)

    def to_json(self, *, indent: Optional[int] = None) -> str:
        """Serialise the machine's XState JSON configuration.

        The output is the config this machine was built from (the
        Pythonic DSL compiles to the same dict), so it loads back with
        ``create_machine()`` and pastes straight into the Stately editor.

        Args:
            indent: Passed to :func:`json.dumps`; ``None`` is compact.

        Returns:
            A JSON document for the machine.

        Raises:
            TypeError: The config holds a value JSON cannot represent (for
                example a ``datetime`` in ``context``). Silently stringifying
                it would produce a chart that no longer round-trips.
        """
        import json

        return json.dumps(self.source_config, indent=indent)

    def to_mermaid(self) -> str:
        """Generates a Mermaid.js string representation of the state machine.

        This can be used to automatically generate diagrams in markdown files
        (e.g., on GitHub, or with tools like MkDocs).

        Aliases remain local state keys for compatibility. Repeated keys in
        the state tree can collide in Mermaid; use distinct keys for an
        unambiguous diagram. ⚠️ Keys containing spaces, dots or hyphens are
        emitted verbatim and may not parse as Mermaid identifiers.

        Returns:
            A string formatted for rendering with Mermaid.js.
        """
        content = ["stateDiagram-v2"]

        def build_mmd_states(node: StateNode[Any], level: int) -> None:
            """Emit Mermaid state declarations for *node* and children.

            Args:
                node: The state to render.
                level: Nesting depth used for indentation.
            """
            indent = "    " * level
            if node.states:
                content.append(f'{indent}state "{node.key}" as {node.key} {{')
                if node.initial and node.states.get(node.initial):
                    initial_key = node.states[node.initial].key
                    content.append(f"{indent}    [*] --> {initial_key}")
                for index, child in enumerate(node.states.values()):
                    if index and node.type == "parallel":
                        # 🔀 A lone `--` line separates the concurrent
                        #    regions of a parallel state.
                        content.append(f"{indent}    --")
                    build_mmd_states(child, level + 1)
                content.append(f"{indent}}}")
            else:
                content.append(f'{indent}state "{node.key}" as {node.key}')
                if node.type == "final" and node.parent is not None:
                    # 🏁 Final states terminate their enclosing region.
                    content.append(f"{indent}{node.key} --> [*]")

        def build_mmd_transitions(node: StateNode[Any]) -> None:
            """Emit Mermaid transition lines for *node* and its descendants.

            Transitions whose target cannot be resolved are skipped.

            Args:
                node: The state whose outgoing edges are rendered (see
                    `_diagram_edges`).
            """
            for target_node, label in _diagram_edges(node):
                content.append(f"{node.key} --> {target_node.key} : {label}")
            for child in node.states.values():
                build_mmd_transitions(child)

        if self.initial and self.states.get(self.initial):
            content.append(f"[*] --> {self.key}")
        build_mmd_states(self, 0)
        build_mmd_transitions(self)

        return "\n".join(content)
