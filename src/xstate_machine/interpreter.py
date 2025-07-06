# src/xstate_machine/interpreter.py
import asyncio
from typing import List, Set, Optional, overload, Union, Dict, Any

from .models import (
    MachineNode,
    StateNode,
    TransitionDefinition,
    ActionDefinition,
)
from .events import Event, AfterEvent, DoneEvent
from .resolver import resolve_target_state
from .task_manager import TaskManager
from .logger import logger
from .exceptions import ImplementationMissingError


class Interpreter:
    """
    Brings a state machine definition to life. It manages the current state,
    processes events, executes actions, and handles the full state transition
    lifecycle, including async operations.
    """

    def __init__(self, machine: MachineNode):
        self.machine = machine
        self.task_manager = TaskManager()
        self.context = machine.initial_context.copy()
        self.status: str = "uninitialized"

        self._event_queue: asyncio.Queue[
            Union[Event, AfterEvent, DoneEvent]
        ] = asyncio.Queue()
        self._active_state_nodes: Set[StateNode] = set()
        self._event_loop_task: Optional[asyncio.Task] = None

    @property
    def current_state_ids(self) -> Set[str]:
        """A set of the string IDs of all currently active states."""
        return {
            s.id for s in self._active_state_nodes if s.is_atomic or s.is_final
        }

    async def start(self) -> "Interpreter":
        """Starts the interpreter and its event loop."""
        if self.status != "uninitialized":
            return self

        logger.info(
            f"🏁 Starting interpreter for machine '{self.machine.id}'..."
        )
        self.status = "running"
        self._event_loop_task = asyncio.create_task(self._run_event_loop())

        # Initial transition
        self._enter_states([self.machine])
        return self

    async def stop(self):
        """Stops the interpreter and cleans up all background tasks."""
        if self.status != "running":
            return

        logger.info(f" gracefully stopping interpreter '{self.machine.id}'...")
        self.status = "stopped"
        await self.task_manager.cancel_all()
        if self._event_loop_task:
            self._event_loop_task.cancel()
            await asyncio.gather(self._event_loop_task, return_exceptions=True)
        logger.info(f"✅ Interpreter '{self.machine.id}' stopped.")

    # -----------------------------------------------------------------------------
    # ✨ Overloaded `send` method for better DX and full type support
    # -----------------------------------------------------------------------------
    @overload
    async def send(self, event_type: str, **payload: Any) -> None:
        """
        Sends an event to the machine with a string type and keyword arguments.

        Example:
            await interpreter.send("USER_UPDATE", name="John", age=30)
        """
        ...

    @overload
    async def send(
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None:
        """
        Sends a pre-structured event object or dictionary to the machine.

        Example:
            await interpreter.send({"type": "TAKEOFF"})
        """
        ...

    async def send(
        self,
        event_or_type: Union[str, Dict, Event, DoneEvent, AfterEvent],
        **payload: Any,
    ) -> None:
        """
        Sends an event to the machine's event queue. This method is overloaded
        to provide a flexible and type-safe API.
        """
        event_obj: Union[Event, DoneEvent, AfterEvent]

        if isinstance(event_or_type, str):
            # Called as: send("EVENT_TYPE", key="value")
            event_obj = Event(type=event_or_type, payload=payload)
        elif isinstance(event_or_type, dict):
            # Called as: send({"type": "EVENT_TYPE", "key": "value"})
            payload = event_or_type.copy()
            event_type = payload.pop("type", "UnnamedEvent")
            event_obj = Event(type=event_type, payload=payload)
        elif isinstance(event_or_type, (Event, DoneEvent, AfterEvent)):
            # Called with a pre-constructed event object (internal use)
            event_obj = event_or_type
        else:
            raise TypeError(
                f"Unsupported event type passed to send(): {type(event_or_type)}"
            )

        await self._event_queue.put(event_obj)

    # -----------------------------------------------------------------------------

    async def _run_event_loop(self):
        """The main loop that processes events from the queue."""
        while self.status == "running":
            try:
                event = await self._event_queue.get()
                await self._process_event(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"💥 Unhandled error in event loop: {e}", exc_info=True
                )
        logger.debug("Event loop finished.")

    async def _process_event(self, event: Union[Event, AfterEvent, DoneEvent]):
        """Finds and executes a transition based on the given event."""
        transition = self._find_optimal_transition(event)

        if not transition:
            logger.debug(
                f"🤷 No transition found for event '{event.type}' in states {self.current_state_ids}"
            )
            return

        logger.info(
            f"⚡ Transitioning on event '{event.type}' from '{transition.source.id}' to '{transition.target_str}'"
        )

        # Core SCXML algorithm:
        # 1. Find the transition domain (least common compound ancestor)
        domain = self._find_transition_domain(transition)

        # 2. Exit states from current config down to the domain
        states_to_exit = {
            s
            for s in self._active_state_nodes
            if self._is_descendant(s, domain)
        }
        self._exit_states(
            sorted(list(states_to_exit), key=lambda s: len(s.id), reverse=True)
        )

        # 3. Execute transition actions
        await self._execute_actions(transition.actions, event)

        # 4. Resolve target and enter states from domain up to the target
        target_state = resolve_target_state(
            transition.target_str, transition.source
        )
        path_to_target = self._get_path_to_state(target_state, stop_at=domain)
        self._enter_states(path_to_target)

    def _find_optimal_transition(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> Optional[TransitionDefinition]:
        """Finds the best transition to take, prioritizing deeper states."""
        eligible_transitions = []
        for state in self._active_state_nodes:
            current = state
            while current:
                if event.type in current.on:
                    for transition in current.on[event.type]:
                        if self._is_guard_satisfied(transition.guard, event):
                            eligible_transitions.append(transition)
                current = current.parent

        if not eligible_transitions:
            return None

        # The optimal transition is the one defined on the deepest state
        return max(eligible_transitions, key=lambda t: len(t.source.id))

    def _enter_states(self, states_to_enter: List[StateNode]):
        """Enters a list of states and executes entry actions."""
        for state in states_to_enter:
            self._active_state_nodes.add(state)
            logger.debug(f"➡️  Entering state: {state.id}")
            asyncio.create_task(
                self._execute_actions(state.entry, Event(f"entry.{state.id}"))
            )

            # Handle initial child states
            if state.type == "compound" and state.initial:
                initial_child = state.states[state.initial]
                self._enter_states([initial_child])
            # Handle parallel child states
            elif state.type == "parallel":
                self._enter_states(list(state.states.values()))

            # Start `after` timers and `invoke` services
            self._schedule_state_tasks(state)

    def _exit_states(self, states_to_exit: List[StateNode]):
        """Exits a list of states and executes exit actions."""
        for state in states_to_exit:
            logger.debug(f"⬅️  Exiting state: {state.id}")
            self._cancel_state_tasks(state)
            asyncio.create_task(
                self._execute_actions(state.exit, Event(f"exit.{state.id}"))
            )
            self._active_state_nodes.discard(state)

    def _schedule_state_tasks(self, state: StateNode):
        """Create background tasks for `after` and `invoke` definitions."""
        # `after` timers
        for delay, transitions in state.after.items():
            event_type = transitions[0].event
            task = asyncio.create_task(
                self._after_timer(delay / 1000.0, AfterEvent(event_type))
            )
            self.task_manager.add(task)

        # `invoke` services
        if state.invoke:
            invoke_def = state.invoke
            service_callable = self.machine.logic.services.get(invoke_def.src)
            if not service_callable:
                raise ImplementationMissingError(
                    f"Service '{invoke_def.src}' is not implemented."
                )
            task = asyncio.create_task(
                self._invoke_service(
                    invoke_def.id,
                    service_callable,
                    state.invoke.on_done,
                    state.invoke.on_error,
                )
            )
            self.task_manager.add(task)

    async def _after_timer(self, delay_sec: float, event: AfterEvent):
        """Coroutine that waits for a delay and then sends an event."""
        await asyncio.sleep(delay_sec)
        logger.info(f"🕒 'after' timer fired: {event.type}")
        await self.send(event)

    async def _invoke_service(
        self, service_id: str, service: callable, on_done, on_error
    ):
        """Coroutine that runs a service and sends a done/error event."""
        logger.info(f"🚀 Invoking service: {service_id}")
        try:
            result = await service(self.context, Event(f"invoke.{service_id}"))
            event = DoneEvent(
                type=f"done.invoke.{service_id}", data=result, src=service_id
            )
            await self.send(event)
        except Exception as e:
            logger.error(f"💥 Service '{service_id}' failed: {e}")
            event = DoneEvent(
                type=f"error.platform.{service_id}", data=e, src=service_id
            )
            await self.send(event)

    def _cancel_state_tasks(self, state: StateNode):
        """(Placeholder) A full implementation would cancel specific tasks."""
        # A more robust TaskManager would map tasks to state IDs for precise cancellation.
        # For now, we rely on the global stop() for cleanup.
        pass

    async def _execute_actions(
        self,
        actions: List[ActionDefinition],
        event: Union[Event, AfterEvent, DoneEvent],
    ):
        """Executes a list of actions."""
        for action_def in actions:
            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                logger.warning(
                    f"🤔 Action '{action_def.type}' is not implemented. Skipping."
                )
                continue

            logger.debug(f"🎬 Executing action: {action_def.type}")
            if asyncio.iscoroutinefunction(action_callable):
                await action_callable(self.context, event)
            else:
                action_callable(self.context, event)

    def _is_guard_satisfied(
        self,
        guard_name: Optional[str],
        event: Union[Event, AfterEvent, DoneEvent],
    ) -> bool:
        """Checks if a guard condition is met."""
        if not guard_name:
            return True

        guard_callable = self.machine.logic.guards.get(guard_name)
        if not guard_callable:
            raise ImplementationMissingError(
                f"Guard '{guard_name}' is not implemented."
            )

        result = guard_callable(self.context, event)
        logger.info(
            f"🛡️ Evaluating guard '{guard_name}': {'✅' if result else '❌'}"
        )
        return result

    def _find_transition_domain(
        self, transition: TransitionDefinition
    ) -> Optional[StateNode]:
        """Find the least common compound ancestor of the source and target states."""
        target_state = resolve_target_state(
            transition.target_str, transition.source
        )
        source_ancestors = self._get_ancestors(transition.source)
        target_ancestors = self._get_ancestors(target_state)

        common_ancestors = source_ancestors.intersection(target_ancestors)
        if not common_ancestors:
            return None

        return max(common_ancestors, key=lambda s: len(s.id))

    def _get_ancestors(self, node: StateNode) -> Set[StateNode]:
        """Get a set of all ancestors of a node, including itself."""
        ancestors = set()
        current = node
        while current:
            ancestors.add(current)
            current = current.parent
        return ancestors

    @staticmethod
    def _is_descendant(node: StateNode, ancestor: StateNode) -> bool:
        """Check if a node is a descendant of another node."""
        return node.id.startswith(ancestor.id + ".") or node == ancestor

    @staticmethod
    def _get_path_to_state(
        node: StateNode, stop_at: Optional[StateNode] = None
    ) -> List[StateNode]:
        """Get the list of states from an ancestor down to a node."""
        path = []
        current = node
        while current and current != stop_at:
            path.append(current)
            current = current.parent
        return list(reversed(path))
