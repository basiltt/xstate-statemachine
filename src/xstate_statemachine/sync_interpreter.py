# src/xstate_statemachine/sync_interpreter.py

# -----------------------------------------------------------------------------
# ⛓️ Synchronous Interpreter
# -----------------------------------------------------------------------------
# This module provides the `SyncInterpreter`, a fully synchronous engine for
# executing state machines. It inherits from `BaseInterpreter` and implements
# a synchronous event processing model.
#
# This interpreter is designed for use cases where asynchronous programming is
# not necessary or desired. It does not support timed transitions (`after`)
# or long-running asynchronous services (`invoke`), as these are fundamentally
# asynchronous operations. It overrides the core async methods from the base
# class to provide a purely blocking execution flow.
# -----------------------------------------------------------------------------

import logging
import asyncio
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Union, overload, Callable

from .base_interpreter import BaseInterpreter
from .events import AfterEvent, DoneEvent, Event
from .exceptions import NotSupportedError, ImplementationMissingError
from .models import (
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TEvent,
)
from .resolver import resolve_target_state

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# ⛓️ SyncInterpreter Class Definition
# -----------------------------------------------------------------------------


class SyncInterpreter(BaseInterpreter[TContext, TEvent]):
    """
    Brings a state machine definition to life by interpreting its behavior
    synchronously.

    The `SyncInterpreter` manages the machine's state and processes events
    sequentially and immediately within the `send` method call. It is suitable
    for simpler, blocking workflows.

    **Limitations**: This interpreter does not support features that require
    a background event loop, such as:
    - Timed `after` transitions.
    - Asynchronous `invoke` services that run in the background.
    - Spawning child actors (`spawn_` actions).

    An attempt to use a machine with these features will result in a
    `NotSupportedError`.

    Attributes:
        _event_queue (Deque): A deque used to manage the event processing sequence.
        _is_processing (bool): A flag to prevent re-entrant event processing.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]):
        """
        Initializes a new synchronous Interpreter instance.

        Args:
            machine (MachineNode[TContext, TEvent]): The machine definition
                (`MachineNode` instance) that this interpreter will run.
        """
        super().__init__(machine, interpreter_class=SyncInterpreter)
        logger.info("⛓️ Initializing Synchronous Interpreter...")
        self._event_queue: Deque[Union[Event, AfterEvent, DoneEvent]] = deque()
        self._is_processing: bool = False
        logger.info("Synchronous Interpreter '%s' initialized.", self.id)

    # -------------------------------------------------------------------------
    # Public API (Sync Implementation)
    # -------------------------------------------------------------------------

    def start(self) -> "SyncInterpreter":
        """
        Starts the interpreter by transitioning to the initial state.

        Unlike the async version, this does not start a background event loop.
        It simply sets the machine to its entry state.

        Returns:
            SyncInterpreter: The interpreter instance for method chaining.
        """
        if self.status != "uninitialized":
            logger.info(
                "⛓️ Interpreter '%s' already running or stopped. Skipping start.",
                self.id,
            )
            return self

        logger.info("🏁 Starting sync interpreter '%s'...", self.id)
        self.status = "running"
        for plugin in self._plugins:
            plugin.on_interpreter_start(self)
        self._enter_states([self.machine])
        logger.info(
            "✅ Sync interpreter '%s' started. Current states: %s",
            self.id,
            self.current_state_ids,
        )
        return self

    def stop(self) -> None:
        """
        Stops the interpreter by updating its status.

        This prevents further events from being processed.
        """
        if self.status != "running":
            return
        logger.info("🛑 Stopping sync interpreter '%s'...", self.id)
        self.status = "stopped"
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)
        logger.info("✅ Sync interpreter '%s' stopped successfully.", self.id)

    @overload
    def send(self, event_type: str, **payload: Any) -> None: ...  # noqa: E704

    # ✅ FIX: Updated overload to include DoneEvent and AfterEvent
    @overload
    def send(  # noqa
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None: ...  # noqa: E704

    def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> None:
        """
        Sends an event to the machine for immediate, synchronous processing.

        This method processes the given event and any subsequent events (like
        `onDone`) that are generated during the transition, all within this
        single, blocking call.

        Args:
            event_or_type (Union[str, Dict, Event, DoneEvent, AfterEvent]): The
                event to send.
            **payload (Any): Optional keyword arguments for the event's payload
                if `event_or_type` is a string.

        Raises:
            TypeError: If an unsupported type is passed for the event.
        """
        if self.status != "running":
            logger.warning("⚠️ Cannot send event. Interpreter is not running.")
            return

        event_obj: Union[Event, DoneEvent, AfterEvent]
        if isinstance(event_or_type, str):
            event_obj = Event(type=event_or_type, payload=payload)
        elif isinstance(event_or_type, dict):
            local_payload = event_or_type.copy()
            event_type = local_payload.pop("type", "UnnamedEvent")
            event_obj = Event(type=event_type, payload=local_payload)
        elif isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            event_obj = event_or_type
        else:
            raise TypeError(
                f"Unsupported event type passed to send(): {type(event_or_type)}"
            )

        self._event_queue.append(event_obj)
        if self._is_processing:
            return

        self._is_processing = True
        try:
            while self._event_queue:
                event = self._event_queue.popleft()
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)
                self._process_event(event)
        finally:
            self._is_processing = False

    # -------------------------------------------------------------------------
    # Synchronous Overrides of Core Logic
    # -------------------------------------------------------------------------

    def _process_event(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """Synchronously finds and executes a transition."""
        transition = self._find_optimal_transition(event)
        if not transition:
            return
        if not transition.target_str:
            self._execute_actions(transition.actions, event)
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    self._active_state_nodes,
                    self._active_state_nodes,
                    transition,
                )
            return

        from_states_snapshot = self._active_state_nodes.copy()
        domain = self._find_transition_domain(transition)
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain) and s != domain
        }
        self._exit_states(
            sorted(list(states_to_exit), key=lambda s: len(s.id), reverse=True)
        )
        self._execute_actions(transition.actions, event)
        target_state_node = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_enter = self._get_path_to_state(
            target_state_node, stop_at=domain
        )
        self._enter_states(path_to_enter)
        for plugin in self._plugins:
            plugin.on_transition(
                self,
                from_states_snapshot,
                self._active_state_nodes,
                transition,
            )

    def _enter_states(self, states_to_enter: List[StateNode]) -> None:
        """Synchronously enters a list of states."""
        for state in states_to_enter:
            self._active_state_nodes.add(state)
            self._execute_actions(state.entry, Event(f"entry.{state.id}"))
            if state.type == "final":
                self._check_and_fire_on_done(state)
            if state.type == "compound" and state.initial:
                if state.initial in state.states:
                    self._enter_states([state.states[state.initial]])
                else:
                    logger.error(
                        "❌ Initial state '%s' not found.", state.initial
                    )
            elif state.type == "parallel":
                self._enter_states(list(state.states.values()))
            self._schedule_state_tasks(state)

    def _exit_states(self, states_to_exit: List[StateNode]) -> None:
        """Synchronously exits a list of states."""
        for state in states_to_exit:
            self._cancel_state_tasks(state)
            self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            self._active_state_nodes.discard(state)

    def _check_and_fire_on_done(self, final_state: StateNode) -> None:
        """Synchronously checks for and fires onDone events."""
        current_ancestor = final_state.parent
        while current_ancestor:
            if current_ancestor.on_done:
                is_done = False
                if current_ancestor.type == "compound":
                    if any(
                        s.type == "final"
                        for s in self._active_state_nodes
                        if s.parent == current_ancestor
                    ):
                        is_done = True
                elif current_ancestor.type == "parallel":
                    if all(
                        any(
                            s.type == "final"
                            for s in self._active_state_nodes
                            if self._is_descendant(s, r)
                        )
                        for r in current_ancestor.states.values()
                    ):
                        is_done = True
                if is_done:
                    self.send(Event(f"done.state.{current_ancestor.id}"))
                    return
            current_ancestor = current_ancestor.parent

    # -------------------------------------------------------------------------
    # Internal Execution and Unsupported Feature Handling
    # -------------------------------------------------------------------------

    def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """Synchronously executes actions, forbidding async callables."""
        if not actions:
            return
        for action_def in actions:
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)
            if action_def.type.startswith("spawn_"):
                self._spawn_actor(action_def, event)
                continue
            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' not implemented."
                )
            if asyncio.iscoroutinefunction(action_callable):
                raise NotSupportedError(
                    f"Action '{action_def.type}' is async."
                )
            action_callable(self, self.context, event, action_def)

    def _spawn_actor(self, action_def: ActionDefinition, event: Event) -> None:
        """Actors are not supported in the synchronous interpreter."""
        raise NotSupportedError(
            "Actor spawning is not supported by SyncInterpreter."
        )

    def _cancel_state_tasks(self, state: StateNode) -> None:
        """No-op, as the sync interpreter has no background tasks."""
        pass

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """`after` transitions are not supported."""
        raise NotSupportedError(
            "`after` transitions are not supported by SyncInterpreter."
        )

    def _invoke_service(
        self, invocation: InvokeDefinition, service: Callable, owner_id: str
    ) -> None:
        """Handles invoked services, supporting only synchronous callables."""
        if asyncio.iscoroutinefunction(service):
            raise NotSupportedError(f"Service '{invocation.src}' is async.")
        logger.info(
            "📞 Invoking sync service '%s' (ID: '%s')...",
            invocation.src,
            invocation.id,
        )
        try:
            invoke_event = Event(
                f"invoke.{invocation.id}", {"input": invocation.input or {}}
            )
            result = service(self, self.context, invoke_event)
            self.send(
                DoneEvent(
                    f"done.invoke.{invocation.id}",
                    data=result,
                    src=invocation.id,
                )
            )
            logger.info("✅ Sync service '%s' completed.", invocation.src)
        except Exception as e:
            logger.error(
                "💥 Sync service '%s' failed: %s",
                invocation.src,
                e,
                exc_info=True,
            )
            self.send(
                DoneEvent(
                    f"error.platform.{invocation.id}",
                    data=e,
                    src=invocation.id,
                )
            )
