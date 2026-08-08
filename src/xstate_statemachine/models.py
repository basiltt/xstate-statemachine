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
import logging
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    TypeVar,
    Union,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import Event
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
# Using TypeVars for TContext and TEvent allows for creating generic machine
# definitions. This provides a foundation for full static type checking of a
# machine's context and events, leading to more robust and self-documenting code.
# -----------------------------------------------------------------------------

TContext = TypeVar("TContext", bound=Dict[str, Any])
TEvent = TypeVar("TEvent", bound=Dict[str, Any])

# Define a specific type for state types for clarity and reuse.
StateType = Literal["atomic", "compound", "parallel", "final", "history"]

# 👶 Prefixes marking an action as a built-in actor-spawning directive.
#
# ⚠️ Order matters: `spawn_blocking_` must be tested before `spawn_`, since the
# latter is a prefix of the former.
SPAWN_BLOCKING_PREFIX = "spawn_blocking_"
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
            self.type: str = config
            self.params: Optional[Dict[str, Any]] = None
        elif isinstance(config, dict):
            # 📝 Handle object definition: {"type": "myAction", ...}
            logger.debug("🔧 Parsing action definition from dict: %s", config)
            self.type: str = config.get("type", "UnknownAction")
            self.params: Optional[Dict[str, Any]] = config.get("params")
        else:
            # ❌ Reject invalid definitions
            logger.error(
                "❌ Invalid action configuration type: %s (expected str or dict)",
                type(config),
            )
            raise InvalidConfigError(
                f"Action definition must be a string or a dictionary, got {type(config)}"
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
        if isinstance(config, str):
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

        self.is_composite = self.type in COMPOSITE_GUARD_TYPES
        self.is_state_in = self.type == STATE_IN_GUARD_TYPE
        self.children = [GuardDefinition(c) for c in children_cfg]

        if self.is_composite and not self.children:
            raise InvalidConfigError(
                f"❌ Composite guard '{self.type}' requires at least one "
                "nested guard (via 'children', or 'params.guards')."
            )
        if self.type == "not" and len(self.children) != 1:
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
        logger.debug(
            "🔧 Creating transition for event '%s' from config: %s",
            event,
            config,
        )
        self.event: str = event
        self.source: "StateNode" = source
        self.target_str: Optional[str] = config.get("target")
        self.actions: List[ActionDefinition] = actions or []

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
        self.reenter: bool = config.get("reenter", False)
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
        self.input: Optional[Dict[str, Any]] = config.get("input")
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


# -----------------------------------------------------------------------------
# 🌳 Core State Tree Models (Composite Pattern)
# -----------------------------------------------------------------------------
# The `StateNode` and `MachineNode` classes implement the Composite design
# pattern to build a traversable graph (a tree) of the state machine's
# structure from the parsed JSON configuration.
# -----------------------------------------------------------------------------


class StateNode(Generic[TContext, TEvent]):
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
    after: Dict[int, List[TransitionDefinition]]
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
        logger.debug(
            "🚀 Initializing StateNode: key='%s', parent_id='%s'",
            key,
            parent.id if parent else "ROOT",
        )
        # 🧍‍♂️ Core Properties
        self.key = key
        self.parent = parent
        self.machine = machine
        self.id = f"{parent.id}.{key}" if parent else key

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
        self.type = self._determine_state_type(config)
        logger.debug(
            "  -> StateNode '%s' identified as type: '%s'", self.id, self.type
        )

        # ⚙️ Parse all properties from the configuration dictionary.
        # This encapsulates the parsing logic within the model itself.
        self.initial = self._parse_initial(config)

        # 🏷️ Metadata keys. Previously all three were dropped at parse time,
        #    so `tags` (UI-state modelling) and `meta` (arbitrary annotation)
        #    were silently unavailable to users who had declared them.
        raw_tags = config.get("tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        self.tags: Set[str] = set(raw_tags)
        self.meta: Dict[str, Any] = config.get("meta") or {}
        self.description: Optional[str] = config.get("description")

        # 🏁 Final states may declare `output` (a.k.a. "done data"), which is
        #    surfaced on the `done.state.*` / `done.invoke.*` event.
        self.output: Any = config.get("output")

        # 🕰️ History configuration. `history` is "shallow" (restore the
        #    immediate child) or "deep" (restore the full nested
        #    configuration). XState defaults to shallow.
        self.history: Optional[str] = None
        if self.type == "history":
            history_kind = config.get("history", "shallow")
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
        self.target_str: Optional[str] = config.get("target")

        self.entry = self._parse_actions(config.get("entry"))
        self.exit = self._parse_actions(config.get("exit"))
        self.on = self._parse_on(config)
        self.on_done = self._parse_on_done(config)
        self.after = self._parse_after(config)
        self.invoke = self._parse_invoke(config)

        # 🌳 Recursively build child states, forming the Composite pattern.
        self.states = {
            state_key: StateNode(machine, state_config, state_key, self)
            for state_key, state_config in config.get("states", {}).items()
        }
        logger.debug(
            "✅ StateNode '%s' and its children initialized.", self.id
        )

    # -------------------------------------------------------------------------
    # Internal Parsing Methods (Encapsulated Logic)
    # -------------------------------------------------------------------------

    def _determine_state_type(self, config: Dict[str, Any]) -> StateType:
        """Determines the type of the state based on its configuration."""
        if "states" in config:
            # A state with children is either compound or parallel
            state_type = config.get("type", "compound")
            if state_type in ["compound", "parallel"]:
                return state_type  # type: ignore
            else:
                logger.warning(
                    "⚠️ Invalid 'type' ('%s') for state '%s' with children. "
                    "Defaulting to 'compound'.",
                    state_type,
                    self.id,
                )
                return "compound"
        elif config.get("type") == "final":
            return "final"
        elif config.get("type") == "history":
            # 🕰️ A history pseudo-state. It has no children and is never
            #    "entered" in the ordinary sense — targeting it restores the
            #    remembered configuration of its parent instead.
            return "history"
        else:
            return "atomic"

    def _parse_initial(self, config: Dict[str, Any]) -> Optional[str]:
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
        initial = config.get("initial")
        if self.type != "compound" or initial:
            return initial

        # 🕰️ History pseudo-states are never a valid initial target.
        candidates = [
            key
            for key, child in config.get("states", {}).items()
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
        self, config: Dict[str, Any]
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
        for event, transitions_config in config.get("on", {}).items():
            normalized_configs = self._normalize_transitions(
                transitions_config
            )
            on_map[event] = [
                self._create_transition(event, t_config)
                for t_config in normalized_configs
            ]

        # ⚡ Merge `always` into the transient ("") bucket.
        always_config = config.get("always")
        if always_config is not None:
            always_transitions = [
                self._create_transition("", t_config)
                for t_config in self._normalize_transitions(always_config)
            ]
            on_map.setdefault("", []).extend(always_transitions)

        return on_map

    def _parse_on_done(
        self, config: Dict[str, Any]
    ) -> Optional[TransitionDefinition]:
        """Parses the 'onDone' transition for a compound/parallel state."""
        on_done_config = config.get("onDone")
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
        self, config: Dict[str, Any]
    ) -> Dict[int, List[TransitionDefinition]]:
        """Parses all delayed transitions from the 'after' property."""
        after_map: Dict[int, List[TransitionDefinition]] = {}
        for delay, transitions_config in config.get("after", {}).items():
            normalized_configs = self._normalize_transitions(
                transitions_config
            )
            after_map[int(delay)] = [
                self._create_transition(f"after.{delay}.{self.id}", t_config)
                for t_config in normalized_configs
            ]
        return after_map

    def _parse_invoke(self, config: Dict[str, Any]) -> List[InvokeDefinition]:
        """Parses all invoked services from the 'invoke' property."""
        invoke_configs = self._ensure_list(config.get("invoke", []))
        invokes: List[InvokeDefinition] = []
        for i_config in invoke_configs:
            if not isinstance(i_config, dict):
                continue

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


class MachineNode(StateNode[TContext, TEvent]):
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
    logic: MachineLogic[TContext, TEvent]
    initial_context: TContext

    def __init__(
        self, config: Dict[str, Any], logic: MachineLogic[TContext, TEvent]
    ):
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
        self.initial_context = config.get("context", {})

        # 🚀 Call the parent constructor to build the entire state tree.
        super().__init__(self, config, config["id"])

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
