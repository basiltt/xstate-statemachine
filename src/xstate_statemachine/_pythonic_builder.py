# src/xstate_statemachine/_pythonic_builder.py
"""
🔗 Fluent ``MachineBuilder`` for the Pythonic DSL.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import copy
import logging
from typing import Any, Callable, Dict, List, Optional, Union

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .exceptions import InvalidConfigError
from .factory import create_machine as _original_create_machine
from .machine_logic import (
    ActionCallable,
    GuardCallable,
    MachineLogic,
    ServiceCallable,
)
from .models import MachineNode

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
        self._context: Optional[Dict[str, Any]] = None
        self._states: Dict[str, Dict[str, Any]] = {}
        self._initial_state: Optional[str] = None
        self._transitions: List[Dict[str, Any]] = []
        self._root: Dict[str, Any] = {}
        self._actions: Dict[str, ActionCallable] = {}
        self._guards: Dict[str, GuardCallable] = {}
        self._services: Dict[str, ServiceCallable] = {}

    def __repr__(self) -> str:
        """Provide a readable representation for debugging."""
        return (
            f"MachineBuilder({self._machine_id!r}, "
            f"{len(self._states)} states, "
            f"{len(self._transitions)} transitions)"
        )

    def context(self, ctx: Dict[str, Any]) -> "MachineBuilder":
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
        on: Optional[Dict[str, Any]] = None,
        entry: Optional[List[Any]] = None,
        exit: Optional[List[Any]] = None,
        after: Optional[Dict[Union[int, str], Any]] = None,
        invoke: Optional[Union[Dict[str, Any], List[Any]]] = None,
        on_done: Optional[Union[str, Dict[str, Any]]] = None,
        always: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
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
        states: Optional[Dict[str, Dict[str, Any]]] = None,
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

    def action(self, name: str, fn: Callable[..., Any]) -> "MachineBuilder":
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

    def guard(self, name: str, fn: Callable[..., Any]) -> "MachineBuilder":
        """Register a guard function.

        The explicitly provided ``name`` is always used as the
        registration key.
        """
        self._guards[name] = fn
        return self

    def service(self, name: str, fn: Callable[..., Any]) -> "MachineBuilder":
        """Register a service function.

        The explicitly provided ``name`` is always used as the
        registration key.
        """
        self._services[name] = fn
        return self

    def build(
        self, context: Optional[Dict[str, Any]] = None
    ) -> MachineNode[Any]:
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

        logic: MachineLogic[Any] = MachineLogic(
            actions=dict(self._actions),
            guards=dict(self._guards),
            services=dict(self._services),
        )
        return _original_create_machine(config, logic=logic)
