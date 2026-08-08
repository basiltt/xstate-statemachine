# /src/xstate_statemachine/base_interpreter.py
# -----------------------------------------------------------------------------
# 🏛️ Base State Machine Interpreter
# -----------------------------------------------------------------------------
# This module provides the `BaseInterpreter` class, which contains the
# core, mode-agnostic logic for state machine execution. It embodies the
# "Template Method" design pattern, where the overall algorithm for state
# transition is defined, but specific steps (like how actions are executed
# or events are dispatched) are deferred to subclasses.
#
# This design cleanly separates the fundamental statechart algorithm from
# the execution mode (synchronous vs. asynchronous), promoting code reuse
# and maintainability.
# -----------------------------------------------------------------------------
"""
Provides the foundational, mode-agnostic logic for interpreting a state machine.

This module contains the `BaseInterpreter` class, which should not be
instantiated directly. Instead, developers should use one of its concrete
subclasses, `Interpreter` for asynchronous operations or `SyncInterpreter` for
synchronous, blocking operations.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import copy
import inspect
import json
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Type,
    Union,
    overload,
    TypeVar,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import AfterEvent, DoneEvent, Event
from .exceptions import (
    ImplementationMissingError,
    InvalidConfigError,
    StateNotFoundError,
)
from .actions import (
    ASSIGN,
    CANCEL,
    CHOOSE,
    EMIT,
    ENQUEUE_ACTIONS,
    ESCALATE,
    FORWARD_TO,
    LOG,
    PURE,
    RAISE,
    SEND_PARENT,
    SEND_TO,
    SPAWN_CHILD,
    STOP_CHILD,
    ActionEnqueuer,
    resolve_builtin,
)
from .models import (
    ActionDefinition,
    GuardDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TEvent,
    TransitionDefinition,
)
from .plugins import PluginBase
from .resolver import resolve_target_state

# This TypeVar allows methods to return the specific subclass instance (self).
TInterpreter = TypeVar("TInterpreter", bound="BaseInterpreter")

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Establishes a logger for this module, allowing for detailed, context-aware
# logging that can be configured by the end-user's application.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ BaseInterpreter Class Definition
# -----------------------------------------------------------------------------


class ActorSystem:
    """A read-only view over the actor registry of one machine hierarchy.

    Mirrors XState's actor system: actors that declare a `systemId` can be
    looked up by that name from anywhere in the hierarchy, which is what makes
    sibling-to-sibling messaging possible.

    Attributes:
        _registry (Dict[str, BaseInterpreter]): The shared registry.
    """

    __slots__ = ("_registry",)

    def __init__(self, registry: Dict[str, "BaseInterpreter[Any, Any]"]):
        """Initializes the view.

        Args:
            registry: The root interpreter's live registry.
        """
        self._registry = registry

    def get(self, system_id: str) -> Optional["BaseInterpreter[Any, Any]"]:
        """Looks up an actor by its `systemId`.

        Args:
            system_id (str): The registered system id.

        Returns:
            Optional[BaseInterpreter]: The actor, or `None`.
        """
        return self._registry.get(system_id)

    def get_all(self) -> Dict[str, "BaseInterpreter[Any, Any]"]:
        """Returns every registered actor.

        Returns:
            Dict[str, BaseInterpreter]: A copy of the registry.
        """
        return dict(self._registry)

    def __contains__(self, system_id: object) -> bool:
        """Supports ``system_id in interpreter.system``."""
        return system_id in self._registry

    def __repr__(self) -> str:
        """Provides a developer-friendly string representation."""
        return f"ActorSystem(actors={sorted(self._registry)})"


class BaseInterpreter(Generic[TContext, TEvent]):
    """Provides the foundational logic for state machine interpretation.

    This abstract base class implements the "Template Method" design pattern.
    It defines the complete, final algorithm for processing events and
    transitioning between states (`_process_event`), but it defers the
    implementation of specific execution steps (like running actions or timers)
    to its concrete subclasses. This architecture cleanly separates the universal
    statechart algorithm from the execution strategy (e.g., synchronous vs.
    asynchronous).

    This class should not be instantiated directly. Use `Interpreter` (async)
    or `SyncInterpreter` (sync).

    Attributes:
        machine (MachineNode[TContext, TEvent]): The static `MachineNode`
            definition that represents the statechart's structure.
        context (TContext): The current extended state (context) of the
            machine, holding all dynamic data.
        status (str): The operational status of the interpreter:
            'uninitialized', 'running', or 'stopped'.
        id (str): A unique identifier for this interpreter instance, inherited
            from the machine's ID.
        parent (Optional[BaseInterpreter[Any, Any]]): A reference to the parent
            interpreter if this instance was spawned as part of an actor model,
            otherwise `None`.
    """

    #: Maximum depth of nested action expansion (`pure` / `choose` /
    #: `enqueueActions` returning further actions). Guards against a callback
    #: that re-enqueues itself.
    MAX_ACTION_DEPTH: int = 50

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        interpreter_class: Optional[Type["BaseInterpreter"]] = None,
        input: Optional[Any] = None,
    ) -> None:
        """Initializes the BaseInterpreter instance.

        Args:
            machine (MachineNode[TContext, TEvent]): The `MachineNode` instance
                that defines the statechart's structure, transitions, and
                logic references.
            interpreter_class (Optional[Type["BaseInterpreter"]]): The concrete
                class being instantiated (e.g., `Interpreter` or
                `SyncInterpreter`). This is used internally for correctly
                restoring an interpreter from a snapshot. If not provided, it
                defaults to the class of the current instance.
        """
        logger.info(
            "🧠 Initializing BaseInterpreter for machine '%s'...", machine.id
        )
        # 🧍‍♂️ Core Properties
        self.machine: MachineNode[TContext, TEvent] = machine
        #: Input supplied at creation, available to context factories and
        #: readable afterwards as `interpreter.input`.
        self.input: Optional[Any] = input
        self.context: TContext = self._build_initial_context(machine, input)
        self.status: str = "uninitialized"
        self.id: str = machine.id
        self.parent: Optional["BaseInterpreter[Any, Any]"] = None

        # 🌳 State & Actor Management
        self._active_state_nodes: Set[StateNode] = set()
        #: Remembered configurations for history pseudo-states, keyed by the
        #: *parent* state id. Recorded on exit, replayed when a transition
        #: targets a `type: "history"` child of that parent.
        self._history: Dict[str, List[StateNode]] = {}
        #: Listeners registered via :meth:`subscribe`.
        self._subscribers: List[Callable[[Any], None]] = []
        #: The machine's final output, set when a top-level final state is
        #: reached. `None` until then.
        self.output: Any = None
        #: The error that put the machine into the "error" status, if any.
        self.error: Optional[BaseException] = None
        #: Listeners registered via :meth:`on`, keyed by emitted event type.
        self._emit_listeners: Dict[str, List[Callable[[Any], None]]] = {}
        #: Cancellation callbacks for pending delayed sends, keyed by send id.
        self._scheduled_sends: Dict[str, Callable[[], None]] = {}
        #: Actor-system registry. Only the ROOT interpreter's copy is used;
        #: children reach it by walking up `parent`.
        self._system: Dict[str, "BaseInterpreter[Any, Any]"] = {}
        #: Snapshots of child actors that could not be rebuilt on restore
        #: (their service was not registered). Preserved rather than dropped
        #: so no data is lost and the caller can recover them.
        self._pending_actor_snapshots: Dict[str, Any] = {}
        #: Maps a spawned actor id to the `services` key it came from, so a
        #: snapshot can record enough to rebuild it.
        self._actor_sources: Dict[str, str] = {}
        #: Current nesting depth of action expansion.
        self._action_depth: int = 0
        self._actors: Dict[str, "BaseInterpreter[Any, Any]"] = {}

        # 🔗 Extensibility & Introspection
        self._plugins: List[PluginBase["BaseInterpreter[Any, Any]"]] = []
        self._interpreter_class: Type["BaseInterpreter[Any, Any]"] = (
            interpreter_class or self.__class__
        )

        logger.info(
            "✅ BaseInterpreter '%s' initialized. Status: '%s'.",
            self.id,
            self.status,
        )

    @staticmethod
    def _build_initial_context(
        machine: MachineNode[Any, Any], input: Optional[Any]
    ) -> Any:
        """Builds the starting context, resolving a factory if one is given.

        🏛️ Architecture decision: XState allows `context` to be a function of
        `{input}` so an actor can be parameterised at creation. Previously a
        callable was stored verbatim, so the runtime context *was* the
        function object — silent corruption that surfaced far from its cause
        as a `TypeError` on first subscript.

        Args:
            machine (MachineNode): The machine definition.
            input (Optional[Any]): Input supplied at creation.

        Returns:
            Any: A fresh, deep-copied context.
        """
        raw = machine.initial_context
        if callable(raw):
            produced = raw({"input": input})
            return copy.deepcopy(produced) if produced is not None else {}
        context = copy.deepcopy(raw)
        # 📥 Expose input to the machine even without a context factory.
        if input is not None and isinstance(context, dict):
            context.setdefault("input", input)
        return context

    # -------------------------------------------------------------------------
    # 🔍 Public Properties & Methods
    # -------------------------------------------------------------------------

    @property
    def current_state_ids(self) -> Set[str]:
        """Gets a set of the string IDs of all currently active atomic states.

        This property is the primary way to check the current state of the
        machine from outside the interpreter. Since a machine can be in
        multiple states at once (due to parallel states), this always
        returns a set of the most specific, leaf-node state identifiers.

        Returns:
            Set[str]: A set of unique string identifiers for the active atomic
            or final leaf states.
        """
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    @property
    def active_state_ids(self) -> Set[str]:
        """Alias of :attr:`current_state_ids`.

        🏛️ Architecture decision: this name is used throughout the README and
        the `docs/` guides, but was never implemented — every documented
        example raised `AttributeError`. Rather than rewrite ~130 published
        snippets (and break anyone who copied them), the documented name is
        provided as a first-class alias. `current_state_ids` remains the
        canonical spelling used internally.

        Returns:
            Set[str]: A set of unique string identifiers for the active atomic
            or final leaf states.
        """
        return self.current_state_ids

    @property
    def is_running(self) -> bool:
        """Indicates whether the interpreter is currently running.

        Convenience wrapper over :attr:`status`, matching the documented
        public API.

        Returns:
            bool: `True` between a successful `start()` and a `stop()`.
        """
        return self.status == "running"

    # -------------------------------------------------------------------------
    # 🔭 Observation & Introspection
    # -------------------------------------------------------------------------

    def matches(self, state_id: str) -> bool:
        """Reports whether a state is part of the active configuration.

        Accepts a fully-qualified id (``"machine.parent.child"``), the same id
        with a leading ``#``, or a trailing partial path (``"parent.child"``).
        Matching an ancestor returns `True` when any descendant is active,
        mirroring XState's ``snapshot.matches()``.

        Args:
            state_id (str): The state to test for.

        Returns:
            bool: `True` if the state or one of its descendants is active.
        """
        if not state_id:
            return False
        target = state_id[1:] if state_id.startswith("#") else state_id
        for node in self._active_state_nodes:
            if node.id == target or node.id.endswith("." + target):
                return True
        return False

    def has_tag(self, tag: str) -> bool:
        """Reports whether any active state declares the given tag.

        Args:
            tag (str): The tag to look for.

        Returns:
            bool: `True` if an active state carries the tag.
        """
        return any(tag in node.tags for node in self._active_state_nodes)

    @property
    def tags(self) -> Set[str]:
        """The union of tags across every active state.

        Returns:
            Set[str]: All tags currently in effect.
        """
        tags: Set[str] = set()
        for node in self._active_state_nodes:
            tags |= node.tags
        return tags

    def get_meta(self) -> Dict[str, Any]:
        """Collects the `meta` of every active state, keyed by state id.

        Returns:
            Dict[str, Any]: Mapping of state id to that state's `meta`.
        """
        return {
            node.id: node.meta
            for node in self._active_state_nodes
            if node.meta
        }

    def can(self, event: Union[str, Event, Dict[str, Any]]) -> bool:
        """Reports whether an event would cause a transition right now.

        Guards are evaluated, so this is an accurate prediction rather than a
        purely structural check. It has no side effects on the configuration.

        Args:
            event (Union[str, Event, Dict[str, Any]]): The event to test.

        Returns:
            bool: `True` if at least one transition would be taken.
        """
        event_obj = self._coerce_event(event)
        try:
            return bool(self._select_transitions(event_obj))
        except Exception:
            logger.exception(
                "🔥 can() failed while evaluating '%s'; reporting False.",
                event_obj.type,
            )
            return False

    @staticmethod
    def _coerce_event(
        event: Union[str, Event, Dict[str, Any], AfterEvent, DoneEvent],
    ) -> Union[Event, AfterEvent, DoneEvent]:
        """Normalises the accepted event spellings into an event object.

        Args:
            event: A type string, a mapping with a `type` key, or an event.

        Returns:
            Union[Event, AfterEvent, DoneEvent]: The normalised event.

        Raises:
            TypeError: If the value cannot be interpreted as an event.
        """
        if isinstance(event, (Event, AfterEvent, DoneEvent)):
            return event
        if isinstance(event, str):
            return Event(type=event)
        if isinstance(event, dict):
            event_type = event.get("type")
            if not isinstance(event_type, str):
                raise TypeError(
                    "❌ Event dict must contain a string 'type' key."
                )
            payload = {k: v for k, v in event.items() if k != "type"}
            return Event(type=event_type, payload=payload)
        raise TypeError(f"❌ Unsupported event type: {type(event).__name__}")

    def subscribe(
        self, listener: Callable[["BaseInterpreter[Any, Any]"], None]
    ) -> Callable[[], None]:
        """Registers a listener invoked after every settled change.

        Mirrors XState's ``actor.subscribe()``. The listener receives this
        interpreter, from which `current_state_ids`, `context` and `status`
        can be read.

        Args:
            listener (Callable): Called after each transition and on
                completion.

        Returns:
            Callable[[], None]: An unsubscribe function.
        """
        self._subscribers.append(listener)

        def _unsubscribe() -> None:
            """Removes the listener if it is still registered."""
            if listener in self._subscribers:
                self._subscribers.remove(listener)

        return _unsubscribe

    def _notify_subscribers(self) -> None:
        """Invokes every subscriber, isolating listener failures.

        📝 A listener raising must not corrupt the machine, so exceptions are
        logged and swallowed — the same contract XState adopted in v5.20.2 for
        emitted-event listeners.
        """
        for listener in list(self._subscribers):
            try:
                listener(self)
            except Exception:
                logger.exception(
                    "🔥 Subscriber raised while observing '%s'; ignoring.",
                    self.id,
                )

    @property
    def plugins(self) -> List[PluginBase["BaseInterpreter[Any, Any]"]]:
        """The list of plugin instances attached to this interpreter.

        Assigning to this property replaces the whole set of plugins, which is
        the form used in the documentation::

            interpreter.plugins = [LoggingInspector()]

        📝 Returns a shallow copy. Mutating the returned list does not affect
        the interpreter — use assignment or :meth:`use` to register plugins.
        Returning the live list would let `interpreter.plugins.append(...)`
        bypass the type validation performed by the setter.

        Returns:
            List[PluginBase]: A copy of the currently registered plugins.
        """
        return list(self._plugins)

    @plugins.setter
    def plugins(
        self, value: List[PluginBase["BaseInterpreter[Any, Any]"]]
    ) -> None:
        """Replaces the registered plugins.

        Args:
            value (List[PluginBase]): The plugins to register.

        Raises:
            TypeError: If `value` is not a list/tuple, or if any element does
                not implement the plugin hook interface.
        """
        if not isinstance(value, (list, tuple)):
            raise TypeError(
                "❌ 'plugins' must be assigned a list of plugin instances."
            )
        # 🛡️ Validate elements. Without this the failure surfaces later as an
        #    AttributeError from deep inside event processing, pointing at
        #    interpreter internals rather than the offending assignment.
        #
        # 🏛️ Architecture decision: the check is *structural* (does it provide
        # the hooks?) rather than a strict `isinstance(PluginBase)`. `use()`
        # has always accepted any duck-typed object exposing the hooks, and the
        # two entry points into `_plugins` must not disagree — otherwise
        # `interpreter.use(p)` would succeed where `interpreter.plugins = [p]`
        # raises, for the very same object.
        required_hooks = ("on_transition", "on_event_received")
        for item in value:
            if not all(
                callable(getattr(item, h, None)) for h in required_hooks
            ):
                raise TypeError(
                    "❌ 'plugins' elements must implement the plugin hook "
                    f"interface (e.g. subclass PluginBase); got "
                    f"{type(item).__name__}."
                )
        self._plugins = list(value)

    def use(
        self: TInterpreter, plugin: PluginBase["BaseInterpreter[Any, Any]"]
    ) -> TInterpreter:
        """Registers a plugin with the interpreter via the Observer pattern.

        Plugins hook into the interpreter's lifecycle (e.g., `on_transition`,
        `on_guard_evaluated`) to add cross-cutting concerns like logging,
        analytics, or state persistence without modifying the core interpreter
        logic. This promotes a clean and extensible architecture.

        Args:
            plugin: The plugin instance to register.

        Returns:
            The interpreter instance (`self`) with the correct subclass type
            to allow for convenient and type-safe method chaining.
        """
        self._plugins.append(plugin)
        logger.info(
            "🔌 Plugin '%s' registered with interpreter '%s'.",
            type(plugin).__name__,
            self.id,
        )
        return self

    # -------------------------------------------------------------------------
    # 📸 Snapshot & Persistence API (Memento Pattern)
    # -------------------------------------------------------------------------

    def get_snapshot(self) -> str:
        """Returns a JSON-serializable snapshot of the interpreter's state.

        This method implements the Memento design pattern by capturing the
        essential state of the interpreter (its status, context, and active
        states) without exposing its internal implementation details. The
        resulting JSON string can be persisted to a file, database, or sent
        over a network.

        Returns:
            str: A JSON string representing the interpreter's current state.
        """
        logger.info("📸 Capturing snapshot for interpreter '%s'...", self.id)
        snapshot = self.get_persisted_snapshot()
        # Use a default handler to gracefully handle non-serializable types.
        json_snapshot = json.dumps(snapshot, indent=2, default=str)
        logger.debug(
            "🖼️ Snapshot for '%s' captured: %s", self.id, json_snapshot
        )
        return json_snapshot

    def get_persisted_snapshot(self) -> Dict[str, Any]:
        """Returns a deep, JSON-serialisable snapshot as a dictionary.

        Mirrors XState's ``actor.getPersistedSnapshot()``. Unlike the earlier
        shallow form, this captures the *whole* actor hierarchy.

        🏛️ Architecture decision: child actors were previously omitted
        entirely. A parent with live children serialised to just
        ``{status, context, state_ids}`` and restoring produced an actor with
        zero children — silent, unrecoverable data loss for anyone persisting
        a workflow. Recording actors recursively (plus history and output)
        makes a snapshot a faithful representation of the machine.

        Returns:
            Dict[str, Any]: The persisted snapshot.
        """
        return {
            "status": self.status,
            "context": self.context,
            "state_ids": sorted(self.current_state_ids),
            # 🌳 Full configuration, so ancestors are restored exactly rather
            #    than re-derived from leaves.
            "configuration": sorted(
                node.id for node in self._active_state_nodes
            ),
            "output": self.output,
            "error": str(self.error) if self.error is not None else None,
            # 🕰️ Remembered history, so a restored machine can still honour a
            #    later transition to a history state.
            "history": {
                parent_id: sorted(node.id for node in nodes)
                for parent_id, nodes in self._history.items()
            },
            # 👶 Recursive child-actor snapshots, keyed by actor id.
            "actors": {
                actor_id: {
                    "machine_id": actor.machine.id,
                    # 🔑 Persist the originating service key. Deriving it from
                    #    the actor id is unreliable: an explicit `id` param
                    #    replaces the key segment entirely.
                    "src": self._actor_sources.get(actor_id),
                    "snapshot": actor.get_persisted_snapshot(),
                }
                for actor_id, actor in self._actors.items()
            },
        }

    def _resolve_actor_machine(
        self, service_key: Optional[str]
    ) -> Optional[MachineNode[Any, Any]]:
        """Finds the machine definition for a persisted child actor.

        Args:
            service_key (Optional[str]): The `services` key the actor was
                originally spawned from.

        Returns:
            Optional[MachineNode]: The child's machine definition, or `None`
            when the service is not registered on this interpreter.
        """
        source = self.machine.logic.services.get(service_key)
        if source is None:
            return None
        if isinstance(source, MachineNode):
            return source
        if callable(source):
            try:
                produced = source(
                    self, self.context, Event(type="__restore__")
                )
            except Exception:
                logger.exception(
                    "🔥 Actor factory for '%s' raised during restore.",
                    service_key,
                )
                return None
            if isinstance(produced, MachineNode):
                return produced
        return None

    @classmethod
    def from_snapshot(
        cls: Type["BaseInterpreter[Any, Any]"],
        snapshot_str: str,
        machine: MachineNode[TContext, TEvent],
    ) -> "BaseInterpreter[TContext, TEvent]":
        """Creates and restores an interpreter instance from a saved snapshot.

        This factory method reconstructs an interpreter's state from a JSON
        snapshot. It deserializes the snapshot, finds the corresponding state
        nodes in the provided machine definition, and sets the context and
        status, effectively restoring the machine to a previous point in time.

        Note:
            This method performs a static restoration. It does not re-run
            entry actions of the restored states or restart any invoked
            services or `after` timers that were active when the snapshot
            was taken.

        Args:
            snapshot_str (str): The JSON string previously generated by
                `get_snapshot()`.
            machine (MachineNode[TContext, TEvent]): The corresponding
                `MachineNode` definition that the snapshot belongs to.

        Returns:
            BaseInterpreter[TContext, TEvent]: A new interpreter instance
                restored to the snapshot's state.

        Raises:
            StateNotFoundError: If a state ID from the snapshot cannot be found
                in the provided machine definition.
            json.JSONDecodeError: If the snapshot string is not valid JSON.
        """
        logger.info(
            "🔄 Restoring interpreter for machine '%s' from snapshot...",
            machine.id,
        )
        try:
            snapshot = json.loads(snapshot_str)
        except json.JSONDecodeError as e:
            logger.error("❌ Invalid JSON in snapshot string: %s", e)
            raise

        # 🧪 Create a new instance of the correct interpreter class (sync/async)
        interpreter = cls(machine)
        interpreter.context = snapshot["context"]
        interpreter.status = snapshot["status"]

        # 🌳 Reconstruct the set of active state nodes from their IDs.
        #    Prefer the full `configuration` when present (it includes
        #    ancestors); fall back to leaf ids for snapshots written by
        #    older versions.
        interpreter._active_state_nodes.clear()
        restore_ids = snapshot.get("configuration") or snapshot["state_ids"]
        for state_id in restore_ids:
            node = machine.get_state_by_id(state_id)
            if node:
                interpreter._active_state_nodes.add(node)
                # 🌲 Ancestors must be active too, otherwise the transition
                #    algorithm cannot resolve domains correctly.
                ancestor = node.parent
                while ancestor is not None:
                    interpreter._active_state_nodes.add(ancestor)
                    ancestor = ancestor.parent
                logger.debug("    ↳ Restored active state: '%s'", state_id)
            else:
                logger.error(
                    "❌ State ID '%s' from snapshot not found in machine '%s'.",
                    state_id,
                    machine.id,
                )
                raise StateNotFoundError(target=state_id)

        # 🏁 Restore completion output and any recorded error.
        interpreter.output = snapshot.get("output")

        # 🕰️ Restore remembered history so a later transition to a history
        #    state still resolves after a restart.
        for parent_id, node_ids in (snapshot.get("history") or {}).items():
            nodes = [
                machine.get_state_by_id(nid)
                for nid in node_ids
                if machine.get_state_by_id(nid)
            ]
            if nodes:
                interpreter._history[parent_id] = nodes

        # 👶 Restore child actors. Their machine definitions are resolved from
        #    the parent's `services` registry, which is the same source the
        #    original spawn used.
        for actor_id, record in (snapshot.get("actors") or {}).items():
            child_machine = interpreter._resolve_actor_machine(
                record.get("src")
            )
            if child_machine is None:
                logger.warning(
                    "⚠️ Could not restore actor '%s': no matching service. "
                    "Its snapshot is preserved under _pending_actor_snapshots.",
                    actor_id,
                )
                interpreter._pending_actor_snapshots[actor_id] = record
                continue
            child = cls.from_snapshot(
                json.dumps(record["snapshot"], default=str), child_machine
            )
            child.parent = interpreter
            child.id = actor_id
            interpreter._actors[actor_id] = child
            if record.get("src"):
                interpreter._actor_sources[actor_id] = record["src"]

        logger.info(
            "✅ Interpreter '%s' restored. States: %s, Status: '%s'",
            interpreter.id,
            interpreter.current_state_ids,
            interpreter.status,
        )
        return interpreter

    # -------------------------------------------------------------------------
    # 📝 Abstract Methods (Template Method Hooks for Subclasses)
    # -------------------------------------------------------------------------
    # These methods define the "pluggable" parts of the state transition
    # algorithm. Concrete subclasses MUST override them to provide
    # mode-specific (synchronous or asynchronous) behavior.

    def start(
        self,
    ) -> Union[
        "BaseInterpreter[TContext, TEvent]",
        Awaitable["BaseInterpreter[TContext, TEvent]"],
    ]:
        """Starts the interpreter by entering the initial state.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass (e.g., `Interpreter`, `SyncInterpreter`).
        """
        raise NotImplementedError(
            "Subclasses must implement the 'start' method."
        )

    def stop(self) -> Union[None, Awaitable[None]]:
        """Stops the interpreter and cleans up resources.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the 'stop' method."
        )

    @overload
    def send(self, event_type: str, **payload: Any) -> Any: ...  # noqa

    @overload
    def send(  # noqa
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> Any: ...

    def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> Any:
        """Sends an event to the running interpreter for processing.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the 'send' method."
        )

    def send_events(
        self, events: List[Union[Dict[str, Any], Event, str]]
    ) -> Any:
        """Sends a list of events to the running interpreter for processing.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the 'send_events' method."
        )

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> Union[None, Awaitable[None]]:
        """Executes a list of action definitions.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass to handle sync/async execution.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_execute_actions' method."
        )

    def _cancel_state_tasks(
        self, state: StateNode
    ) -> Union[None, Awaitable[None]]:
        """Cancels all background tasks associated with a given state.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_cancel_state_tasks' method."
        )

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Handles a delayed event (`after` transition).

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_after_timer' method."
        )

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
        owner_id: str,
    ) -> Union[None, Awaitable[None]]:
        """Handles an invoked service.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_invoke_service' method."
        )

    def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> Union[None, Awaitable[None]]:
        """Handles the spawning of a child state machine actor.

        Raises:
            NotImplementedError: This method must be implemented by a concrete
                subclass.
        """
        raise NotImplementedError(
            "Subclasses must implement the '_spawn_actor' method."
        )

    # -------------------------------------------------------------------------
    # ✉️ Event Preparation Helper
    # -------------------------------------------------------------------------

    @staticmethod
    def _prepare_event(
        event_or_type: Union[str, Dict[str, Any], Any],
        **payload: Any,
    ) -> Union[Event, DoneEvent, AfterEvent]:
        """Normalizes various event inputs into a concrete `Event` object.

        This helper ensures that the interpreter can robustly handle events
        passed as strings, dictionaries, or `Event` instances. It uses
        duck-typing to handle a specific edge case where the library might be
        imported twice in a testing environment, resulting in two distinct
        `Event` class identities.

        Args:
            event_or_type (Union[str, Dict[str, Any], Any]): The event to be
                normalized. Can be:
                - A string (`"EVENT_TYPE"`)
                - A dictionary with a "type" key (`{"type": "EVENT_TYPE", ...}`)
                - An instance of `Event`, `DoneEvent`, or `AfterEvent`.
                - A duck-typed object with `.type` and `.payload` attributes.
            **payload (Any): Additional keyword arguments to be used as the
                event's payload if `event_or_type` is a string.

        Returns:
            Union[Event, DoneEvent, AfterEvent]: A concrete event object ready
            for processing.

        Raises:
            TypeError: If the input cannot be resolved into a valid event format.
        """
        # 1️⃣ Input is a simple string: create a new Event.
        if isinstance(event_or_type, str):
            return Event(type=event_or_type, payload=payload)

        # 2️⃣ Input is a dictionary: convert to an Event.
        if isinstance(event_or_type, dict):
            data = event_or_type.copy()
            event_type = data.pop("type", "UnnamedEvent")
            return Event(type=event_type, payload=data)

        # 3️⃣ Input is already a native Event instance: use as-is.
        if isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            return event_or_type

        # 4️⃣ Duck-typing: handle "foreign" Event objects (for testing robustness).
        if hasattr(event_or_type, "type") and hasattr(
            event_or_type, "payload"
        ):
            # Trust and forward as-is to preserve any subclass information.
            return event_or_type  # type: ignore[return-value]

        # 5️⃣ Anything else is an unsupported format.
        raise TypeError(
            f"Unsupported event type passed to send(): {type(event_or_type)}"
        )

    # -------------------------------------------------------------------------
    # ⚙️ Core State Transition Logic (The Template Method)
    # -------------------------------------------------------------------------

    def _resolve_target_state_node(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """Resolves a transition's target string to a concrete StateNode."""
        root = self.machine
        parent = transition.source.parent
        target_str = transition.target_str

        if not target_str:
            return None

        logger.debug(
            "🔄 Resolving target state '%s' from source '%s'.",
            target_str,
            transition.source.id,
        )

        target_state: Optional[StateNode] = None

        # Standard resolution attempts
        resolution_attempts = [
            (target_str, transition.source),
            (target_str, parent) if parent else None,
            (target_str, root),
            (f"{root.id}.{target_str}", root),
        ]

        for tgt, ref in filter(None, resolution_attempts):
            try:
                target_state = resolve_target_state(tgt, ref)
                # This side effect is important for logging and debugging.
                transition.target_str = tgt
                logger.debug(
                    "✅ Resolved via standard method: '%s'", target_state.id
                )
                break
            except StateNotFoundError:
                logger.debug(
                    "    ↳ Failed standard resolution of '%s' from '%s'",
                    tgt,
                    ref.id,
                )
                continue

        if target_state:
            return target_state

        # Fallback 1: Direct attribute lookup on root
        if hasattr(root, target_str):
            candidate = getattr(root, target_str)
            if isinstance(candidate, StateNode):
                logger.debug(
                    "✅ Resolved via root attribute lookup: '%s'", candidate.id
                )
                return candidate

        # Fallback 2: Lookup in root's `states` dict
        if hasattr(root, "states"):
            states_dict = getattr(root, "states", {})
            if target_str in states_dict:
                target_state = states_dict[target_str]
                logger.debug(
                    "✅ Resolved via root states dict (exact match): '%s'",
                    target_state.id,
                )
                return target_state
            for state in states_dict.values():
                if state.id.split(".")[-1] == target_str:
                    logger.debug(
                        "✅ Resolved via root states dict (local name): '%s'",
                        state.id,
                    )
                    return state

        # Fallback 3: Exhaustive tree walk
        def _walk(node):
            yield node
            if hasattr(node, "states"):
                for child in node.states.values():
                    yield from _walk(child)

        for candidate in _walk(root):
            if candidate.id.split(".")[-1] == target_str:
                logger.debug(
                    "✅ Resolved via full tree walk: '%s'", candidate.id
                )
                return candidate

        available = list(getattr(root, "states", {}).keys())
        logger.error(
            "🚫 All resolution attempts failed for target: '%s'", target_str
        )
        logger.error(
            "📂 Available top-level states in machine '%s': %s",
            root.id,
            available,
        )
        return None

    async def _process_event(
        self, event: Union[Event, DoneEvent, AfterEvent]
    ) -> None:
        """Executes a single, complete "step" of the SCXML algorithm.

        Selects the optimal transition set for `event` — one transition per
        orthogonal region — and executes each in turn.

        Args:
            event (Union[Event, DoneEvent, AfterEvent]): The event to process.
        """
        # 1. Select every transition this event triggers (one per region).
        transitions = self._select_transitions(event)
        if not transitions:
            logger.debug("🍃 No transition found for event '%s'.", event.type)
            return

        # 2. Execute each selected transition in isolation. A transition may
        #    be invalidated by an earlier one in the same macrostep (its source
        #    is no longer active), so re-check liveness before executing.
        for transition in transitions:
            if (
                len(transitions) > 1
                and transition.source not in self._active_state_nodes
            ):
                logger.debug(
                    "⏭️  Skipping stale transition from '%s'.",
                    transition.source.id,
                )
                continue
            await self._execute_transition(transition, event)

    # -------------------------------------------------------------------------
    # 🎬 Built-in Action Support
    # -------------------------------------------------------------------------

    def _resolve_event_spec(
        self, spec: Any, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Event:
        """Turns an event specification from action params into an `Event`.

        Accepts a plain type string, a mapping with a `type` key, an existing
        event object, or a callable of `{context, event}` returning one of
        those.

        Args:
            spec (Any): The declared event specification.
            event (Union[Event, AfterEvent, DoneEvent]): The triggering event,
                used to resolve callables.

        Returns:
            Event: The concrete event to dispatch.

        Raises:
            TypeError: If the specification cannot be interpreted.
        """
        if callable(spec):
            spec = spec({"context": self.context, "event": event})
        resolved = self._coerce_event(spec)
        if isinstance(resolved, Event):
            return resolved
        # 🔁 Normalise AfterEvent/DoneEvent into a plain Event for re-sending.
        return Event(
            type=resolved.type, payload=getattr(resolved, "data", {}) or {}
        )

    def _resolve_actor_target(
        self, spec: Any, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional["BaseInterpreter[Any, Any]"]:
        """Resolves a `sendTo`/`forwardTo` target to a live interpreter.

        Lookup order: the actor system registry (`system_id`), then this
        interpreter's own children, then a suffix match on child ids — actor
        ids are namespaced (`parent:key:uuid`), so users naturally refer to
        the bare key.

        Args:
            spec (Any): The declared target: an id string, a callable
                resolving one, or an interpreter instance.
            event (Union[Event, AfterEvent, DoneEvent]): The triggering event.

        Returns:
            Optional[BaseInterpreter]: The resolved actor, or `None`.
        """
        if callable(spec) and not isinstance(spec, BaseInterpreter):
            spec = spec(
                {
                    "context": self.context,
                    "event": event,
                    "system": self.system,
                }
            )
        if isinstance(spec, BaseInterpreter):
            return spec
        if not isinstance(spec, str):
            return None

        # 🌐 Actor-system registration wins: it is the explicit, stable name.
        registry = self._system_registry()
        if spec in registry:
            return registry[spec]
        if spec in self._actors:
            return self._actors[spec]
        # 🔑 Actor ids are namespaced as `parent:key` or `parent:key:uuid`, so
        #    a bare service key must match the MIDDLE segment too. Matching
        #    only the suffix silently missed every auto-id actor (the uuid is
        #    the last segment), so `send_to("worker", ...)` dropped the event.
        matches = [
            actor
            for actor_id, actor in self._actors.items()
            if spec in actor_id.split(":")[1:]
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            logger.warning(
                "⚠️ Actor key '%s' is ambiguous (%d matches). Use an explicit "
                "`id` or `systemId` to disambiguate; event dropped.",
                spec,
                len(matches),
            )
            return None
        # 🗺️ Fall back to the originating service key recorded at spawn time.
        for actor_id, source_key in self._actor_sources.items():
            if source_key == spec and actor_id in self._actors:
                return self._actors[actor_id]
        if spec in ("parent", "#parent") and self.parent is not None:
            return self.parent
        return None

    def _system_registry(self) -> Dict[str, "BaseInterpreter[Any, Any]"]:
        """Returns the actor-system registry shared by the whole hierarchy.

        🏛️ Architecture decision: the registry lives on the *root* interpreter
        so `system_id` is global to one machine hierarchy, exactly like
        XState's actor system. Children reach it by walking up `parent`.

        Returns:
            Dict[str, BaseInterpreter]: Mapping of `system_id` to actor.
        """
        root: "BaseInterpreter[Any, Any]" = self
        while root.parent is not None:
            root = root.parent
        return root._system

    @property
    def system(self) -> "ActorSystem":
        """The actor system this interpreter belongs to.

        Returns:
            ActorSystem: A view exposing `get()` and `get_all()`.
        """
        return ActorSystem(self._system_registry())

    def _register_in_system(
        self, system_id: Optional[str], actor: "BaseInterpreter[Any, Any]"
    ) -> None:
        """Registers an actor under a `system_id`, if one was declared.

        Args:
            system_id (Optional[str]): The requested system id.
            actor (BaseInterpreter): The actor to register.
        """
        if not system_id:
            return
        registry = self._system_registry()
        if system_id in registry and registry[system_id] is not actor:
            logger.warning(
                "⚠️ systemId '%s' is already registered to actor '%s'; the "
                "new actor replaces it. systemIds must be unique within a "
                "machine hierarchy.",
                system_id,
                registry[system_id].id,
            )
        registry[system_id] = actor

    def _resolve_delay(self, spec: Any, event: Any) -> Optional[float]:
        """Resolves a delay specification to milliseconds.

        Accepts a number, a callable of `{context, event}`, or a named delay
        resolved from `MachineLogic.delays`.

        Args:
            spec (Any): The declared delay.
            event (Any): The triggering event.

        Returns:
            Optional[float]: The delay in milliseconds, or `None`.
        """
        if spec is None:
            return None
        if callable(spec):
            spec = spec({"context": self.context, "event": event})
        if isinstance(spec, (int, float)):
            return float(spec)
        if isinstance(spec, str):
            named = self.machine.logic.delays.get(spec)
            if named is None:
                logger.warning(
                    "⚠️ Named delay '%s' is not defined in MachineLogic."
                    " Treating as no delay.",
                    spec,
                )
                return None
            if callable(named):
                named = named(self.context, event)
            return float(named) if named is not None else None
        return None

    def _emit(self, event: Event) -> None:
        """Publishes an emitted event to registered listeners.

        Args:
            event (Event): The event to publish.
        """
        listeners = self._emit_listeners.get(event.type, [])
        wildcard = self._emit_listeners.get("*", [])
        for listener in list(listeners) + list(wildcard):
            try:
                listener(event)
            except Exception:
                # 📝 A listener failure must not disturb the machine — the
                #    same contract XState adopted in v5.20.2.
                logger.exception(
                    "🔥 Emit listener for '%s' raised; ignoring.", event.type
                )

    def on(
        self, event_type: str, listener: Callable[[Event], None]
    ) -> Callable[[], None]:
        """Registers a listener for events published via the `emit` action.

        Args:
            event_type (str): The emitted event type, or `"*"` for all.
            listener (Callable[[Event], None]): The callback.

        Returns:
            Callable[[], None]: An unsubscribe function.
        """
        self._emit_listeners.setdefault(event_type, []).append(listener)

        def _off() -> None:
            """Removes the listener if still registered."""
            bucket = self._emit_listeners.get(event_type, [])
            if listener in bucket:
                bucket.remove(listener)

        return _off

    def _apply_assign(
        self, params: Any, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """Applies an `assign` action to the machine context.

        Args:
            params (Any): The action's params, carrying `assignment`.
            event (Union[Event, AfterEvent, DoneEvent]): The triggering event.
        """
        assignment = (
            params.get("assignment") if isinstance(params, dict) else params
        )
        if assignment is None:
            return
        args = {"context": self.context, "event": event}
        if callable(assignment):
            produced = assignment(args)
            if isinstance(produced, dict):
                self.context.update(produced)
            return
        if isinstance(assignment, dict):
            for key, value in assignment.items():
                self.context[key] = value(args) if callable(value) else value

    def _collect_builtin_followups(
        self,
        canonical: str,
        action_def: ActionDefinition,
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> List[Any]:
        """Handles a built-in action, returning any actions it produced.

        This is the engine-agnostic half of built-in action execution. Effects
        that need to await (sending, spawning) are returned as follow-up work
        for the concrete interpreter, so the sync and async engines share one
        implementation of the semantics.

        Args:
            canonical (str): The canonical built-in action name.
            action_def (ActionDefinition): The action being executed.
            event (Union[Event, AfterEvent, DoneEvent]): The triggering event.

        Returns:
            List[Any]: Nested action definitions to execute next.
        """
        params = self._resolve_params(action_def.params, event) or {}

        # 🛟 Bound nested action expansion. `pure`, `choose` and
        #    `enqueueActions` all return further actions, so a callback that
        #    (directly or indirectly) enqueues itself recurses until Python
        #    raises RecursionError — which, being a BaseException subclass in
        #    older versions and an Exception here, previously left the machine
        #    in an indeterminate state. A depth counter turns an authoring
        #    mistake into a clear, contained log message.
        depth = getattr(self, "_action_depth", 0)
        if depth > self.MAX_ACTION_DEPTH:
            logger.error(
                "🔁 Nested action expansion exceeded %d levels while handling "
                "'%s'. Aborting this branch; check for an enqueueActions or "
                "pure callback that re-enqueues itself.",
                self.MAX_ACTION_DEPTH,
                action_def.type,
            )
            return []

        if canonical == ASSIGN:
            self._apply_assign(params, event)
            return []

        if canonical == LOG:
            expr = params.get("expr", "") if isinstance(params, dict) else ""
            label = params.get("label") if isinstance(params, dict) else None
            message = (
                expr({"context": self.context, "event": event})
                if callable(expr)
                else expr
            )
            logger.info("📝 %s%s", f"[{label}] " if label else "", message)
            return []

        if canonical == EMIT:
            self._emit(self._resolve_event_spec(params.get("event"), event))
            return []

        if canonical == PURE:
            getter = params.get("get") if isinstance(params, dict) else None
            if not callable(getter):
                return []
            produced = getter({"context": self.context, "event": event})
            if produced is None:
                return []
            return produced if isinstance(produced, list) else [produced]

        if canonical == CHOOSE:
            conditions = (
                params.get("conditions", [])
                if isinstance(params, dict)
                else []
            )
            for branch in conditions:
                guard_cfg = branch.get("guard", branch.get("cond"))
                if guard_cfg is None or self._is_guard_satisfied(
                    GuardDefinition(guard_cfg), event
                ):
                    chosen = branch.get("actions", [])
                    return chosen if isinstance(chosen, list) else [chosen]
            return []

        if canonical == ENQUEUE_ACTIONS:
            callback = (
                params.get("callback") if isinstance(params, dict) else None
            )
            if not callable(callback):
                return []
            enqueue = ActionEnqueuer(self, event)

            def _check(guard_cfg: Any) -> bool:
                """Evaluates a guard from inside the callback."""
                return self._is_guard_satisfied(
                    GuardDefinition(guard_cfg), event
                )

            callback(
                {
                    "context": self.context,
                    "event": event,
                    "enqueue": enqueue,
                    "check": _check,
                    "self": self,
                    "system": self.system,
                }
            )
            return enqueue.items

        if canonical == CANCEL:
            send_id = (
                params.get("sendId") if isinstance(params, dict) else None
            )
            if send_id:
                self._cancel_scheduled_send(str(send_id))
            return []

        # 📨 Remaining built-ins need interpreter-specific delivery and are
        #    handled by the concrete engines.
        return []

    def _cancel_scheduled_send(self, send_id: str) -> None:
        """Cancels a pending delayed send.

        Args:
            send_id (str): The identifier given to the original send.
        """
        canceller = self._scheduled_sends.pop(send_id, None)
        if canceller is None:
            logger.debug("🤷 No pending send with id '%s' to cancel.", send_id)
            return
        try:
            canceller()
            logger.info("🚫 Cancelled scheduled send '%s'.", send_id)
        except Exception:  # pragma: no cover - defensive
            logger.exception("🔥 Failed to cancel send '%s'.", send_id)

    async def _execute_transition(
        self,
        transition: TransitionDefinition,
        event: Union[Event, DoneEvent, AfterEvent],
    ) -> None:
        """Executes one selected transition, mutating the active configuration.

        Args:
            transition (TransitionDefinition): The transition to execute.
            event (Union[Event, DoneEvent, AfterEvent]): The triggering event.

        Raises:
            StateNotFoundError: If the transition's target cannot be resolved.
        """
        # 1. A "targetless" transition only executes actions without changing state.
        if not transition.target_str:
            logger.debug(
                "🎬 Executing targetless transition for event '%s'.",
                event.type,
            )
            await self._execute_actions(transition.actions, event)
            for plug in self._plugins:
                plug.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # 2. Resolve the target state node using a multi-stage process.
        target_state = self._resolve_target_state_node(transition)
        if target_state is None:
            raise StateNotFoundError(transition.target_str, self.machine.id)

        # 3. A self-transition without `reenter: True` is an "internal" transition.
        # It executes actions but does not exit or re-enter the source state.
        if target_state == transition.source and not transition.reenter:
            logger.debug(
                "🎬 Executing internal self-transition for event '%s'.",
                event.type,
            )
            await self._execute_actions(transition.actions, event)
            for plug in self._plugins:
                plug.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        # 4. All other transitions are "external" and will cause a state change.
        snapshot_before = self._active_state_nodes.copy()
        domain = self._find_transition_domain(transition, target_state)

        states_to_exit = self._compute_states_to_exit(domain, target_state)

        path_to_enter = self._get_path_to_state(target_state, stop_at=domain)

        # 🕰️ A history pseudo-state is never entered itself. Replace it with
        #    the remembered configuration (or the default), computed *before*
        #    exiting so the recorded history is the pre-transition one.
        history_targets: List[StateNode] = []
        if target_state.type == "history":
            history_targets = self._resolve_history_target(target_state)
            # Enter down to the history node's parent, then the remembered
            # set. The parent is entered as part of each remembered node's own
            # path, so entering it here as well would trigger its default
            # `initial` descent and activate the wrong child alongside the
            # restored one.
            path_to_enter = []

        # 5. Execute the transition sequence in the correct SCXML order.
        #
        # 🏛️ Architecture decision: `_exit_states` and `_enter_states` are the
        # sole authorities on `_active_state_nodes` membership — they discard
        # and add as they go. A previous implementation additionally applied
        # `difference_update(states_to_exit)` *after* entry, which removed the
        # initial children that `_enter_states` had just recursively entered
        # (those children were themselves members of `states_to_exit`). The
        # machine was left on a non-atomic ancestor with no active leaf,
        # rendering it permanently unresponsive. Do not reintroduce that step.
        await self._exit_states(
            sorted(list(states_to_exit), key=lambda s: s.depth, reverse=True),
            event,
        )
        await self._execute_actions(transition.actions, event)
        await self._enter_states(path_to_enter, event)

        # 🕰️ Restore the remembered configuration for a history target. Each
        #    remembered node is entered along its own path from the history
        #    node's parent, so ancestors are re-entered correctly.
        if target_state.type == "history":
            for node in history_targets:
                await self._enter_states(
                    self._get_path_to_state(node, stop_at=domain), event
                )

        # 6. Notify plugins and subscribers of the completed transition.
        for plug in self._plugins:
            plug.on_transition(
                self,
                snapshot_before,
                self._active_state_nodes.copy(),
                transition,
            )
        self._notify_subscribers()

    # -------------------------------------------------------------------------
    # ⏯️ State Management Sub-Routines
    # -------------------------------------------------------------------------

    async def _enter_states(
        self, states_to_enter: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Enters a list of states in order, running actions and tasks.

        This method follows the SCXML algorithm for state entry. For each
        state, it:
        1.  Adds the state to the active configuration.
        2.  Executes all 'entry' actions.
        3.  Schedules any `after` timers or `invoke` services defined on the state.
        4.  If the state is a final state, it checks if its parent is now "done".
        5.  Recursively enters the initial substate of a compound state or all
            substates of a parallel state.

        Args:
            states_to_enter (List[StateNode]): An ordered list of states to
                enter, from the outermost ancestor to the innermost child.
            event (Optional[Event]): The event that triggered this state entry.
        """
        trigger_event = event or Event(type="___xstate_statemachine_init___")

        # 🗺️ Index the remaining path so a compound state can tell whether the
        #    caller already named which child to descend into.
        #
        # 🏛️ Architecture decision: `_enter_states` used to descend into a
        # compound's `initial` child unconditionally, *in addition* to walking
        # the explicit entry path. When the path already named a deeper sibling
        # (e.g. an external transition targeting `B.b2` while `B.initial` is
        # `b1`), both `b1` and `b2` ended up active — two simultaneously active
        # leaves inside one non-parallel region, which SCXML forbids. The
        # phantom leaf then participated in the next selection pass and could
        # win, executing the wrong transition and duplicating its actions.
        explicit_children = {
            state.parent.id: state
            for state in states_to_enter
            if state.parent is not None
        }
        explicit_child_ids = {
            state.id for state in states_to_enter if state.parent is not None
        }

        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug("➡️  Entering state: '%s'.", state.id)

            # ⚙️ Run entry actions and schedule background tasks.
            await self._execute_actions(state.entry, trigger_event)
            self._schedule_state_tasks(state)

            # 🎉 If we entered a final state, check if its parent is now complete.
            if state.is_final:
                await self._check_and_fire_on_done(state)

            # 🗺️ Handle automatic entry into child states.
            if state.type == "compound" and state.initial:
                # ⏭️ Skip the default descent when the entry path already
                #    specifies which child of this state to enter.
                if state.id in explicit_children:
                    continue
                initial_child = state.states.get(state.initial)
                if initial_child:
                    await self._enter_states([initial_child], trigger_event)
                else:
                    raise InvalidConfigError(
                        f"❌ Initial state '{state.initial}' not found in "
                        f"compound state '{state.id}'."
                    )
            elif state.type == "compound" and state.states:
                # 🚨 A compound state with children but no resolvable
                #    `initial` cannot produce an active leaf. Left unchecked
                #    the machine starts "successfully" with an empty
                #    configuration and silently drops every event.
                raise InvalidConfigError(
                    f"❌ Compound state '{state.id}' has no 'initial' state, "
                    "so entering it yields no active leaf. Declare "
                    "'initial' explicitly."
                )
            elif state.type == "parallel":
                # For parallel states, enter all child regions simultaneously.
                # 🌐 Enter every region EXCEPT one already named by the entry
                #    path (that region is walked explicitly, and entering
                #    it again would trigger its default `initial` descent
                #    and activate the wrong child alongside the target).
                #    History pseudo-states are never entered as regions.
                regions = [
                    child
                    for child in state.states.values()
                    if child.type != "history"
                    and child.id not in explicit_child_ids
                ]
                if regions:
                    await self._enter_states(regions, trigger_event)

    def _record_history(self, states_to_exit: List[StateNode]) -> None:
        """Remembers the active configuration of states being exited.

        Called immediately before exit actions run. For every state that owns
        at least one `type: "history"` child, the currently active descendants
        are stored so a later transition targeting that history node can
        restore them.

        🏛️ Architecture decision: history is keyed by the *parent* id rather
        than by the history node itself. A parent may declare both a shallow
        and a deep history child, and both must see the same recorded
        configuration — the shallow/deep distinction is applied at restore
        time, not at record time.

        Args:
            states_to_exit (List[StateNode]): The states about to be exited.
        """
        exiting = set(states_to_exit)
        # 🕰️ Candidates are the exiting states *and* their ancestors: a
        #    transition out of a nested leaf exits the leaf and its parents,
        #    and it is the history-owning ancestor whose configuration must be
        #    remembered. Walking up from each exiting node covers both the
        #    "parent is exiting too" and "only descendants are exiting" cases.
        candidates: Set[StateNode] = set()
        for node in exiting:
            current: Optional[StateNode] = node
            while current is not None:
                candidates.add(current)
                current = current.parent

        for state in candidates:
            # 🕰️ Only parents that actually declare a history child matter.
            if not any(
                child.type == "history" for child in state.states.values()
            ):
                continue
            remembered = [
                node
                for node in self._active_state_nodes
                if node is not state and self._is_descendant(node, state)
            ]
            if remembered:
                self._history[state.id] = remembered
                logger.debug(
                    "🕰️ Recorded history for '%s': %s",
                    state.id,
                    [n.id for n in remembered],
                )

    def _resolve_history_target(
        self, history_node: StateNode
    ) -> List[StateNode]:
        """Expands a history pseudo-state into the states to actually enter.

        Args:
            history_node (StateNode): A node whose `type` is `"history"`.

        Returns:
            List[StateNode]: The states to enter. Falls back to the parent's
            default `initial` child when nothing has been recorded yet, which
            matches XState and SCXML semantics for an unvisited history state.
        """
        parent = history_node.parent
        if parent is None:  # pragma: no cover - a root history node is invalid
            return []

        remembered = self._history.get(parent.id)

        if not remembered:
            # 🌱 Never visited: fall back to the declared default target, or
            #    the parent's initial child.
            default_target = history_node.target_str
            if default_target:
                resolved = self._resolve_state_by_target(
                    default_target, history_node
                )
                if resolved:
                    return [resolved]
            if parent.initial and parent.initial in parent.states:
                return [parent.states[parent.initial]]
            return []

        if history_node.history == "deep":
            # 🌊 Deep history restores the full nested configuration; entering
            #    the deepest leaves re-enters their ancestors on the way.
            leaves = [
                node
                for node in remembered
                if node.is_atomic or node.is_final or not node.states
            ]
            return leaves or remembered

        # 🏖️ Shallow history restores only the parent's immediate child; its
        #    own `initial` chain then applies below that.
        shallow = [node for node in remembered if node.parent is parent]
        return shallow or remembered

    def _resolve_state_by_target(
        self, target: str, reference: StateNode
    ) -> Optional[StateNode]:
        """Resolves a target string relative to a reference node.

        Args:
            target (str): The target expression (e.g. `"#m.a.b"` or `"b"`).
            reference (StateNode): The node the target is written relative to.

        Returns:
            Optional[StateNode]: The resolved node, or `None`.
        """
        try:
            return resolve_target_state(target, reference)
        except StateNotFoundError:
            logger.warning(
                "⚠️ Could not resolve history default target '%s' on '%s'.",
                target,
                reference.id,
            )
            return None

    async def _exit_states(
        self, states_to_exit: List[StateNode], event: Optional[Event] = None
    ) -> None:
        """Exits a list of states in order, canceling tasks and running actions.

        This method follows the SCXML algorithm for state exit. For each state, it:
        1.  Cancels any running tasks (`after` timers, `invoke` services)
            owned by the state.
        2.  Executes all 'exit' actions.
        3.  Removes the state from the active configuration.

        Args:
            states_to_exit (List[StateNode]): An ordered list of states to
                exit, from the innermost child to the outermost ancestor.
            event (Optional[Event]): The event that triggered the state exit.
        """
        trigger_event = event or Event(type="___xstate_statemachine_exit___")

        # 🕰️ Record history *before* anything is removed, so the remembered
        #    configuration reflects the state of the machine as it was.
        self._record_history(states_to_exit)

        for state in states_to_exit:
            logger.debug("⬅️  Exiting state: '%s'.", state.id)
            # 🛑 Crucially, cancel tasks before running exit actions.
            await self._cancel_state_tasks(state)
            # ⚙️ Then, run the synchronous exit actions.
            await self._execute_actions(state.exit, trigger_event)
            # 🗑️ Finally, remove from the active set.
            self._active_state_nodes.discard(state)

    # -------------------------------------------------------------------------
    # 🔎 State Evaluation & Pathfinding Helpers
    # -------------------------------------------------------------------------

    def _is_state_done(self, state_node: StateNode) -> bool:
        """Recursively determines if a compound or parallel state is "done".

        This is a key part of the SCXML algorithm for `onDone` transitions.
        - A state with `type: 'final'` is always done.
        - A `compound` state is done if its currently active child state is done.
        - A `parallel` state is done only if ALL of its child regions are done.

        Args:
            state_node (StateNode): The state to check for completion.

        Returns:
            bool: `True` if the state is considered "done", otherwise `False`.
        """
        # 🏁 Base case: A final state is inherently "done".
        if state_node.is_final:
            return True

        # 🧠 Compound state: Its "doneness" is determined by its active child.
        if state_node.type == "compound":
            active_child = next(
                (
                    s
                    for s in self._active_state_nodes
                    if s.parent == state_node
                ),
                None,
            )
            # If no child is active, it cannot be done.
            if not active_child:
                return False
            # Recursively check the child, handling nested complex states.
            return self._is_state_done(active_child)

        # 🌐 Parallel state: All child regions must be independently "done".
        if state_node.type == "parallel":
            for region in state_node.states.values():
                active_in_region = [
                    d
                    for d in self._active_state_nodes
                    if self._is_descendant(d, region)
                ]
                # If a region is not active, the parallel state is not done.
                if not active_in_region:
                    return False
                # The region itself is "done" if any of its active states are done.
                if not any(self._is_state_done(d) for d in active_in_region):
                    return False
            # If all regions passed the check, the parallel state is done.
            return True

        # For atomic, non-final states.
        return False

    async def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Bubbles up from a final state to fire parent `onDone` transitions.

        When a state machine enters a `final` state, this method is called to
        check if the parent (or any ancestor) is now considered "done"
        according to `_is_state_done`. If so, it dispatches the corresponding
        `done.state.*` event to trigger the `onDone` transition.

        Args:
            final_state (StateNode): The final state that was just entered.
        """
        ancestor = final_state.parent
        while ancestor:
            if ancestor.on_done and self._is_state_done(ancestor):
                logger.info(
                    "🎉 State '%s' is done, firing onDone event.", ancestor.id
                )
                # 📨 Create and send the synthetic `done.state.*` event,
                #    carrying the final state's `output` as done data.
                done_event = DoneEvent(
                    type=f"done.state.{ancestor.id}",
                    data=self._resolve_output(final_state),
                    src=ancestor.id,
                )
                await self.send(done_event)
                # Per SCXML, only fire for the first completed ancestor.
                return
            ancestor = ancestor.parent

        # 🏁 A top-level final state completes the machine itself.
        if final_state.parent is self.machine or final_state.parent is None:
            self._complete(self._resolve_output(final_state))

    def _resolve_output(self, final_state: StateNode) -> Any:
        """Computes the done data contributed by a final state.

        `output` may be a literal or a callable of ``{context, event}``,
        matching XState's dynamic-output form.

        Args:
            final_state (StateNode): The final state that was entered.

        Returns:
            Any: The resolved output, or `None` when none is declared.
        """
        output = final_state.output
        if output is None:
            return None
        if callable(output):
            try:
                return output({"context": self.context, "event": None})
            except Exception:
                logger.exception(
                    "🔥 Output function on '%s' raised; using None.",
                    final_state.id,
                )
                return None
        return output

    def _has_error_handler(self, invocation: Any) -> bool:
        """Reports whether an invocation declares any `onError` handler.

        🏛️ Architecture decision: this asks whether a handler was *declared*,
        not whether one would currently fire. A guarded `onError` whose guard
        happens to be false still means the author considered the failure and
        chose to handle it conditionally — treating that as an unhandled crash
        would be surprising and would break existing machines. Only a total
        absence of `onError` counts as unhandled.

        Args:
            invocation (Any): The `InvokeDefinition` that failed.

        Returns:
            bool: `True` if any `onError` transition is declared.
        """
        return bool(getattr(invocation, "on_error", None))

    def _fail(self, error: BaseException) -> None:
        """Puts the machine into the terminal `error` status.

        🏛️ Architecture decision: `status` previously only ever moved between
        `uninitialized`, `running` and `stopped`. An invoked service that
        failed with no `onError` handler logged a message and the machine kept
        running as though nothing had happened — the failure was invisible to
        any caller. XState models this as an error snapshot, so a distinct
        `"error"` status plus `interpreter.error` makes it observable.

        Args:
            error (BaseException): The unhandled error.
        """
        if self.status not in ("running", "uninitialized"):
            return
        self.status = "error"
        self.error = error
        logger.error(
            "🚨 Machine '%s' entered the error state: %r", self.id, error
        )
        for plugin in self._plugins:
            hook = getattr(plugin, "on_error", None)
            if callable(hook):
                hook(self, error)
        self._notify_subscribers()

    def _complete(self, output: Any) -> None:
        """Marks the machine as finished and records its output.

        🏛️ Architecture decision: `status` previously only ever moved between
        `uninitialized`, `running` and `stopped`, so reaching a top-level final
        state was **unobservable** from the public API. That blocked any
        `to_promise()`-style "await completion" helper. A distinct `"done"`
        status makes completion a first-class, checkable outcome.

        Args:
            output (Any): The machine's final output, if any.
        """
        if self.status != "running":
            return
        self.status = "done"
        self.output = output
        logger.info(
            "🏁 Machine '%s' reached a top-level final state. Output: %r",
            self.id,
            output,
        )
        for plugin in self._plugins:
            hook = getattr(plugin, "on_done", None)
            if callable(hook):
                hook(self, output)

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """Finds the most specific, eligible transition for an event.

        This implements the SCXML rule for transition selection: choose the
        transition defined on the most deeply nested active state that matches
        the event and satisfies its guard condition. This ensures that child
        states can override the behavior of their parents.

        Args:
            event (Union[Event, AfterEvent, DoneEvent]): The event being processed.

        Returns:
            Optional[TransitionDefinition]: The highest-priority transition
            that should be taken, or `None` if no eligible transition is found.
        """
        eligible_transitions: List[TransitionDefinition] = []

        # 1️⃣ Sort active states by true tree depth (most specific first).
        sorted_nodes = sorted(
            list(self._active_state_nodes),
            key=lambda s: s.depth,
            reverse=True,
        )

        # 2️⃣ Determine if we should check for transient ("always") transitions.
        is_transient_check = not event.type.startswith(
            ("done.", "error.", "after.")
        )
        is_explicit_transient_event = event.type == ""

        # 3️⃣ Traverse up the tree from each active leaf node.
        for state in sorted_nodes:
            current: Optional[StateNode] = state
            while current:
                # Check standard `on` event transitions (incl. descriptors).
                if not is_explicit_transient_event:
                    blocked = False
                    for key in self._matching_descriptors(
                        current.on, event.type
                    ):
                        for t in current.on[key]:
                            if t.forbidden:
                                blocked = True
                                break
                            if self._is_guard_satisfied(t.guard_def, event):
                                eligible_transitions.append(t)
                        if blocked:
                            break
                    if blocked:
                        break

                # Check transient `""` (always) transitions.
                if is_transient_check and "" in current.on:
                    for t in current.on[""]:
                        if self._is_guard_satisfied(t.guard_def, event):
                            eligible_transitions.append(t)

                # Check `onDone` transitions for compound/parallel states.
                if current.on_done and current.on_done.event == event.type:
                    if self._is_guard_satisfied(
                        current.on_done.guard_def, event
                    ):
                        eligible_transitions.append(current.on_done)

                # Check `after` transitions for timed events.
                if isinstance(event, AfterEvent):
                    for transitions in current.after.values():
                        for t in transitions:
                            if (
                                t.event == event.type
                                and self._is_guard_satisfied(
                                    t.guard_def, event
                                )
                            ):
                                eligible_transitions.append(t)

                # Check `onDone`/`onError` for invoked services.
                if isinstance(event, DoneEvent):
                    for inv in current.invoke:
                        if event.src == inv.id:
                            for t in inv.on_done + inv.on_error:
                                if (
                                    t.event == event.type
                                    and self._is_guard_satisfied(
                                        t.guard_def, event
                                    )
                                ):
                                    eligible_transitions.append(t)
                current = current.parent

        if not eligible_transitions:
            return None

        # 🏆 The winning transition is the one defined on the deepest state.
        return max(eligible_transitions, key=lambda t: t.source.depth)  # noqa

    @staticmethod
    def _matching_descriptors(
        on_map: Dict[str, List[TransitionDefinition]], event_type: str
    ) -> List[str]:
        """Finds the `on` keys that match an event type, most specific first.

        Implements XState's event-descriptor matching:

        - an exact key (``"mouse.click"``) wins outright;
        - partial descriptors match by dot-segment prefix, longest first
          (``"mouse.click.*"`` beats ``"mouse.*"``);
        - the bare wildcard ``"*"`` matches anything and is always last.

        🏛️ Architecture decision: previously the lookup was a single exact
        dict test, so ``"*"`` and ``"mouse.*"`` keys never matched anything —
        a valid XState config that silently did nothing. Ordering matters:
        SCXML and XState both require the most specific descriptor to win, and
        the fallback ordering was itself a bug fixed upstream in v5.32.2.

        Args:
            on_map (Dict[str, List[TransitionDefinition]]): A state's `on` map.
            event_type (str): The event type being dispatched.

        Returns:
            List[str]: Matching keys ordered most-specific first.
        """
        if not on_map or not event_type:
            return []

        matches: List[str] = []
        # 🎯 Exact match is always the most specific.
        if event_type in on_map:
            matches.append(event_type)

        # 🔒 Internal lifecycle events are NEVER caught by a wildcard or a
        #    partial descriptor.
        #
        # 🏛️ Architecture decision: `done.invoke.*`, `done.state.*`,
        # `error.platform.*` and `after.*` are synthetic events the engine
        # raises to drive `onDone`, `onError` and `after`. A user writing
        # `on: {"*": ...}` means "any event I might receive", not "also
        # swallow my own timers and service results". Without this guard a
        # single wildcard silently breaks every invoke and delayed transition
        # in that state — XState draws the same line.
        if event_type.startswith(("done.", "error.", "after.", "xstate.")):
            return matches

        # 🌓 Partial descriptors: "a.b.*" matches "a.b.c" and "a.b".
        partials: List[str] = []
        for key in on_map:
            if key == "*" or not key.endswith(".*"):
                continue
            prefix = key[:-2]
            if event_type == prefix or event_type.startswith(prefix + "."):
                partials.append(key)
        # 🔽 Longest prefix wins.
        partials.sort(key=len, reverse=True)
        matches.extend(partials)

        # 🃏 The bare wildcard is the last resort.
        if "*" in on_map:
            matches.append("*")

        return matches

    def _collect_eligible_transitions(
        self,
        state: StateNode,
        event: Union[Event, AfterEvent, DoneEvent],
        guard_cache: Optional[Dict[int, bool]] = None,
    ) -> List[TransitionDefinition]:
        """Collects every eligible transition on one state's ancestor chain.

        Walks from `state` up to the machine root, gathering transitions that
        match `event` and whose guard is satisfied. This is the per-leaf half
        of transition selection; callers decide how to rank the results.

        Args:
            state (StateNode): The active state to start the upward walk from.
            event (Union[Event, AfterEvent, DoneEvent]): The event being
                processed.
            guard_cache (Optional[Dict[int, bool]]): Memo of guard results for
                the current selection pass, keyed by transition identity. When
                several parallel regions share an ancestor, this ensures that
                ancestor's guard is evaluated exactly once. Pass `None` to
                disable memoisation.

        Returns:
            List[TransitionDefinition]: Eligible transitions, ordered from the
            deepest source state upward.
        """
        eligible: List[TransitionDefinition] = []

        def _passes(transition: TransitionDefinition) -> bool:
            """Evaluates a transition's guard, memoised per selection pass.

            🏛️ Architecture decision: guards are documented as pure predicates,
            but in practice users write ones with side effects (counters,
            metrics, logging). Evaluating a shared ancestor's guard once per
            region would multiply those side effects by the region count and
            fire `on_guard_evaluated` plugin hooks N times for a single logical
            decision. Memoising keeps evaluation count independent of the
            machine's parallel width.
            """
            if guard_cache is None:
                return self._is_guard_satisfied(transition.guard_def, event)
            key = id(transition)
            if key not in guard_cache:
                guard_cache[key] = self._is_guard_satisfied(
                    transition.guard_def, event
                )
            return guard_cache[key]

        # 🧭 Determine which transition flavours are in play for this event.
        is_transient_check = not event.type.startswith(
            ("done.", "error.", "after.")
        )
        is_explicit_transient_event = event.type == ""

        current: Optional[StateNode] = state
        while current:
            # 📨 Standard `on` event transitions, including wildcard and
            #    partial descriptors, most specific first.
            if not is_explicit_transient_event:
                blocked = False
                for key in self._matching_descriptors(current.on, event.type):
                    for t in current.on[key]:
                        # 🚫 A forbidden transition consumes the event here so
                        #    no ancestor handler can see it.
                        if t.forbidden:
                            blocked = True
                            break
                        if _passes(t):
                            eligible.append(t)
                    if blocked:
                        break
                if blocked:
                    logger.debug(
                        "🚫 Event '%s' forbidden at '%s'; stopping upward "
                        "search.",
                        event.type,
                        current.id,
                    )
                    break

            # ⚡ Transient `""` ("always") transitions.
            if is_transient_check and "" in current.on:
                for t in current.on[""]:
                    if _passes(t):
                        eligible.append(t)

            # 🏁 `onDone` transitions for compound/parallel states.
            if current.on_done and current.on_done.event == event.type:
                if _passes(current.on_done):
                    eligible.append(current.on_done)

            # ⏰ `after` transitions for timed events.
            if isinstance(event, AfterEvent):
                for transitions in current.after.values():
                    for t in transitions:
                        if t.event == event.type and _passes(t):
                            eligible.append(t)

            # 🤖 `onDone`/`onError` for invoked services.
            if isinstance(event, DoneEvent):
                for inv in current.invoke:
                    if event.src == inv.id:
                        for t in inv.on_done + inv.on_error:
                            if t.event == event.type and _passes(t):
                                eligible.append(t)

            current = current.parent

        return eligible

    def _select_transitions(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> List[TransitionDefinition]:
        """Selects the optimal transition set for an event, one per region.

        Implements the SCXML `selectTransitions` rule. For each active atomic
        state, the most deeply nested eligible transition is chosen. Because
        orthogonal (parallel) regions each contribute their own active leaf,
        this naturally yields one transition *per region* rather than a single
        winner for the whole machine.

        🏛️ Architecture decision: a previous implementation returned a single
        `max(...)` across the entire configuration, so an event handled by two
        parallel regions advanced only one of them. Selecting per leaf and then
        de-duplicating fixes that while preserving the single-fire behaviour
        for a transition defined on a shared ancestor — the same object is
        selected by several leaves but executed only once.

        Args:
            event (Union[Event, AfterEvent, DoneEvent]): The event being
                processed.

        Returns:
            List[TransitionDefinition]: The transitions to execute, ordered
            deepest-source-first and free of duplicates.
        """
        # 🍃 Only atomic/final leaves seed selection; ancestors are reached by
        #    the upward walk inside `_collect_eligible_transitions`.
        leaves = [
            s
            for s in self._active_state_nodes
            if s.is_atomic or s.is_final or not s.states
        ]
        # 🛟 Fallback: if the configuration has no leaf (defensive), consider
        #    every active node so behaviour degrades gracefully.
        if not leaves:
            leaves = list(self._active_state_nodes)

        selected: List[TransitionDefinition] = []
        seen: Set[int] = set()
        # 🧠 Memo shared across all leaves in this pass, so a transition on an
        #    ancestor common to several regions is guard-evaluated exactly once.
        guard_cache: Dict[int, bool] = {}

        # 🔽 Deterministic ordering: deepest leaves first, then by id.
        for leaf in sorted(leaves, key=lambda s: (-s.depth, s.id)):
            eligible = self._collect_eligible_transitions(
                leaf, event, guard_cache
            )
            if not eligible:
                continue

            # 🏆 This leaf's winner is the transition on its deepest ancestor.
            winner = max(eligible, key=lambda t: t.source.depth)

            # 🧹 De-duplicate by identity so an ancestor transition shared by
            #    several regions fires exactly once.
            if id(winner) not in seen:
                seen.add(id(winner))
                selected.append(winner)

        # 🔽 Execute deepest-source-first for predictable action ordering.
        selected.sort(key=lambda t: -t.source.depth)
        return selected

    def _compute_states_to_exit(
        self, domain: Optional[StateNode], target_state: StateNode
    ) -> Set[StateNode]:
        """Determines which active states an external transition must exit.

        Normally every active descendant of the transition domain is exited.
        When the domain is a `parallel` state, that would sweep up the *sibling*
        regions as well — but only the branch containing the target is re-entered
        by `_get_path_to_state`, so the siblings would be exited and never
        restored, silently killing them.

        🏛️ Architecture decision: this is why the exit set is scoped to the
        domain's child that actually contains the target whenever the domain is
        parallel. Orthogonal regions are independent by definition: a transition
        inside one region must not disturb the others unless it exits the
        parallel state itself (in which case the domain is an ancestor of the
        parallel node, not the node itself, and the full sweep is correct).

        Args:
            domain (Optional[StateNode]): The transition domain (LCCA), or
                `None` when the machine root is the domain.
            target_state (StateNode): The resolved target of the transition.

        Returns:
            Set[StateNode]: The active states to exit, innermost-first ordering
            applied by the caller.
        """
        candidates = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s is not domain
        }

        # 🌐 Scope to one region when the domain is a parallel state, so
        #    orthogonal siblings are left untouched.
        if domain is not None and domain.type == "parallel":
            branch: Optional[StateNode] = target_state
            while branch is not None and branch.parent is not domain:
                branch = branch.parent
            if branch is not None:
                candidates = {
                    s
                    for s in candidates
                    if s is branch or self._is_descendant(s, branch)
                }

        return candidates

    def _find_transition_domain(
        self, transition: TransitionDefinition, target_state: StateNode
    ) -> Optional[StateNode]:
        """Calculates the transition domain (LCCA) for an external transition.

        The "domain" is the least common compound ancestor (LCCA) of the source
        and target states. It determines which states are exited and entered.

        For a self-transition (including re-entering ones), the domain is
        always the parent state, which ensures the source state is correctly
        exited and re-entered.

        Args:
            transition (TransitionDefinition): The external transition to analyze.
            target_state (StateNode): The pre-resolved target state node.

        Returns:
            Optional[StateNode]: The state node that is the LCCA, or None if the
            root is the domain.
        """
        parent = transition.source.parent or self.machine

        # For any self-transition, the domain is the parent. This forces an
        # exit/re-entry cycle for the source state.
        if target_state == transition.source:
            return parent

        # Standard case: Compute the Least Common Compound Ancestor (LCCA).
        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)
        common_ancestors = source_ancestors & target_ancestors

        # 🎯 When the target is an ancestor of the source, the LCCA *is* the
        # target. Using it directly as the domain would make
        # `_get_path_to_state(target, stop_at=domain)` return an empty path,
        # so the machine would exit down to the target and never re-enter it —
        # left on a non-atomic ancestor with no active leaf.
        #
        # 🏛️ Architecture decision: step up to the target's PARENT rather than
        # discarding the target from the candidate set. Discarding re-ran
        # `max()` over the remaining common ancestors, which for a region of a
        # `parallel` state selected the parallel node itself — placing every
        # *sibling* region in `states_to_exit` while the entry path only
        # re-entered the targeted region. The siblings were exited and never
        # restored, permanently killing them. The parent is the correct domain:
        # it exits and re-enters exactly the target subtree.
        if target_state in source_ancestors:
            return target_state.parent or self.machine

        if not common_ancestors:
            # Fallback to parent (or machine root) if no commonality is found.
            return parent

        # The LCCA is the deepest common ancestor.
        return max(common_ancestors, key=lambda n: n.depth)

    @staticmethod
    def _get_path_to_state(
        to_state: StateNode, *, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """Builds the ordered list of states to enter to reach a target.

        This method traces the ancestry from the target state (`to_state`) up
        to, but not including, a specified `stop_at` ancestor (typically the
        transition domain). The resulting path is then reversed to provide the
        correct parent-to-child entry order.

        Args:
            to_state (StateNode): The destination state.
            stop_at (Optional[StateNode]): The ancestor at which to stop
                traversing.

        Returns:
            List[StateNode]: A list of states to be entered, from outermost
            to innermost.
        """
        path: List[StateNode] = []
        current: Optional[StateNode] = to_state
        while current and current is not stop_at:
            path.append(current)
            current = current.parent
        # Reverse to get parent -> child order for correct state entry.
        path.reverse()
        return path

    @staticmethod
    def _get_ancestors(node: StateNode) -> Set[StateNode]:
        """Gets the set of all ancestors of a node, including the node itself.

        Args:
            node (StateNode): The node from which to find ancestors.

        Returns:
            Set[StateNode]: A set containing the node and all of its parents.
        """
        ancestors: Set[StateNode] = set()
        current: Optional[StateNode] = node
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(node: StateNode, ancestor: Optional[StateNode]) -> bool:
        """Checks if a node is a descendant of a specified ancestor.

        A node is considered a descendant of another if its ID starts with the
        ancestor's ID followed by a dot, or if it is the ancestor itself.

        Args:
            node (StateNode): The potential descendant node.
            ancestor (Optional[StateNode]): The potential ancestor node. If
                `None`, it represents the machine root, and this method will
                always return `True`.

        Returns:
            bool: `True` if `node` is a descendant of `ancestor`.
        """
        # If no ancestor is specified, it's the machine root, so all nodes are descendants.
        if not ancestor:
            return True
        # Check for self or if the ID indicates a child relationship.
        return node.id.startswith(f"{ancestor.id}.") or node == ancestor

    # -------------------------------------------------------------------------
    # 🛡️ Task & Guard Management
    # -------------------------------------------------------------------------

    def _schedule_state_tasks(self, state: StateNode) -> None:
        """Schedules `after` and `invoke` tasks for a state upon its entry.

        This method dispatches to the abstract `_after_timer` and
        `_invoke_service` methods, which are implemented by the concrete
        sync/async subclasses to handle the actual execution.

        Args:
            state (StateNode): The state being entered.
        """
        # 🕒 Schedule `after` timers.
        for delay_ms, transitions in state.after.items():
            # 🏷️ Symbolic delays resolve through MachineLogic.delays.
            resolved_ms = self._resolve_delay(delay_ms, None)
            if resolved_ms is None:
                logger.warning(
                    "⚠️ Skipping 'after' transition on '%s': delay %r could "
                    "not be resolved.",
                    state.id,
                    delay_ms,
                )
                continue
            for t_def in transitions:
                delay_sec = float(resolved_ms) / 1000.0
                after_event = AfterEvent(type=t_def.event)
                self._after_timer(delay_sec, after_event, owner_id=state.id)
                logger.debug(
                    "🕒 Scheduled 'after' event '%s' in %.2fs for state '%s'.",
                    t_def.event,
                    delay_sec,
                    state.id,
                )

        # 📞 Schedule `invoke` services.
        for invocation in state.invoke:
            service_callable = self.machine.logic.services.get(invocation.src)
            # 💥 Fail-fast if the service implementation is missing.
            if service_callable is None:
                # FIX: Reverted error message to match test suite expectations.
                raise ImplementationMissingError(
                    f"Service '{invocation.src}' referenced by "
                    f"state '{state.id}' is not registered."
                )
            self._invoke_service(
                invocation, service_callable, owner_id=state.id
            )
            logger.debug(
                "📞 Invoking service '%s' for state '%s'.",
                invocation.src,
                state.id,
            )

    def _is_guard_satisfied(
        self,
        guard: Optional[Union[str, "GuardDefinition"]],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> bool:
        """Evaluates a transition guard in any of its supported forms.

        Handles the four shapes XState accepts:

        - a named predicate (``"isReady"``),
        - a parameterised predicate (``{"type": ..., "params": ...}``),
        - a higher-order composition (``and`` / ``or`` / ``not``),
        - the built-in ``stateIn`` guard.

        Args:
            guard (Optional[Union[str, GuardDefinition]]): The guard to
                evaluate. `None` means the transition is unguarded.
            event (Union[Event, AfterEvent, DoneEvent]): The current event,
                passed to user predicates.

        Returns:
            bool: `True` if the guard passes or there is no guard. A guard
            that raises is treated as `False`.

        Raises:
            ImplementationMissingError: If a named guard has no implementation
                in the machine's logic.
        """
        # ✅ A transition without a guard is always allowed.
        if guard is None:
            return True

        # 🔁 Accept a bare string for backward compatibility with callers that
        #    still pass `transition.guard`.
        if isinstance(guard, str):
            guard = GuardDefinition(guard)

        # 🌳 Composite guards recurse and short-circuit, exactly like XState's
        #    `and()` / `or()` / `not()` helpers.
        if guard.is_composite:
            if guard.type == "and":
                return all(
                    self._is_guard_satisfied(child, event)
                    for child in guard.children
                )
            if guard.type == "or":
                return any(
                    self._is_guard_satisfied(child, event)
                    for child in guard.children
                )
            # `not` is validated at parse time to have exactly one child.
            return not self._is_guard_satisfied(guard.children[0], event)

        # 📍 The built-in `stateIn` guard is answered from the active
        #    configuration; it needs no user implementation.
        if guard.is_state_in:
            return self._is_state_in(guard, event)

        # 🔍 Find the guard function in the machine's logic.
        guard_callable = self.machine.logic.guards.get(guard.type)
        if not guard_callable:
            # FIX: Reverted error message to match test suite expectations.
            raise ImplementationMissingError(
                f"Guard '{guard.type}' not implemented."
            )

        # 🏃 Execute the guard function.
        #
        # 🏛️ Architecture decision: a guard is a *predicate supplied by the
        # user*, so a raised exception is a defect in that predicate rather
        # than a machine-level failure. Per the documented contract it
        # evaluates to `False`, blocking this transition while leaving the
        # machine responsive and allowing any lower-priority transition (e.g.
        # an unguarded fallback in the same `on` array) to be considered.
        # A *missing* guard still raises above — that is a configuration
        # error, not a runtime condition, and must fail loudly.
        try:
            params = self._resolve_params(guard.params, event)
            result = bool(
                self._call_with_optional_params(
                    guard_callable, self.context, event, params
                )
            )
        except Exception:
            logger.exception(
                "🔥 Guard '%s' raised an exception while evaluating event "
                "'%s'; treating it as False.",
                guard.type,
                event.type,
            )
            result = False

        logger.info(
            "🛡️  Evaluating guard '%s': %s",
            guard.type,
            "✅ Passed" if result else "❌ Failed",
        )

        # 🔔 Notify any registered plugins about the evaluation.
        for plugin in self._plugins:
            plugin.on_guard_evaluated(self, guard.type, event, result)

        return result

    def _is_state_in(
        self,
        guard: "GuardDefinition",
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> bool:
        """Evaluates the built-in ``stateIn`` guard.

        Satisfied when the named state is part of the active configuration —
        either as an active leaf or as an ancestor of one.

        Args:
            guard (GuardDefinition): The `stateIn` guard, whose params carry
                the state id under `state` (or `value`).
            event (Union[Event, AfterEvent, DoneEvent]): The current event,
                used only to resolve callable params.

        Returns:
            bool: `True` when the named state is active.
        """
        params = self._resolve_params(guard.params, event)
        target = None
        if isinstance(params, dict):
            target = params.get("state", params.get("value"))
        elif isinstance(params, str):
            target = params
        if not isinstance(target, str) or not target:
            logger.warning(
                "⚠️ 'stateIn' guard has no state id in its params; "
                "treating as False."
            )
            return False

        # 🎯 Accept both '#machine.a.b' and 'machine.a.b' spellings.
        normalised = target[1:] if target.startswith("#") else target
        for node in self._active_state_nodes:
            if node.id == normalised or node.id.endswith("." + normalised):
                return True
        return False

    def _resolve_params(
        self, params: Any, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Any:
        """Resolves action/guard params, invoking them if they are callable.

        🏛️ Architecture decision: XState v5 allows `params` to be a function of
        `{context, event}`, evaluated fresh on every use. Previously a callable
        was passed through verbatim, so user code received a raw function
        object where it expected a dict — silent corruption that surfaced far
        from its cause.

        Args:
            params (Any): The declared params, possibly a callable.
            event (Union[Event, AfterEvent, DoneEvent]): The triggering event.

        Returns:
            Any: The resolved params.
        """
        if callable(params):
            return params({"context": self.context, "event": event})
        return params

    @staticmethod
    def _call_with_optional_params(
        fn: Callable[..., Any],
        context: Any,
        event: Union[Event, AfterEvent, DoneEvent],
        params: Any,
    ) -> Any:
        """Calls a guard, passing `params` only if it accepts a third argument.

        📝 Guards have always been `(context, event)`. Parameterised guards
        need a third argument, but existing two-argument guards must keep
        working unchanged, so the arity is inspected once per call.

        Args:
            fn (Callable[..., Any]): The guard implementation.
            context (Any): The interpreter's context.
            event (Union[Event, AfterEvent, DoneEvent]): The current event.
            params (Any): Resolved params, or `None`.

        Returns:
            Any: Whatever the guard returns.
        """
        if params is None:
            return fn(context, event)
        try:
            signature = inspect.signature(fn)
            accepts = len(
                [
                    p
                    for p in signature.parameters.values()
                    if p.kind
                    in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                ]
            )
            has_varargs = any(
                p.kind is inspect.Parameter.VAR_POSITIONAL
                for p in signature.parameters.values()
            )
        except (TypeError, ValueError):  # pragma: no cover - builtins
            return fn(context, event)

        if has_varargs or accepts >= 3:
            return fn(context, event, params)
        return fn(context, event)
