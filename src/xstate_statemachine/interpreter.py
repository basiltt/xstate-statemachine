# src/xstate_statemachine/interpreter.py

# -----------------------------------------------------------------------------
# 🚀 Asynchronous Interpreter
# -----------------------------------------------------------------------------
# This module contains the `Interpreter` class, the core asynchronous state
# machine engine. It inherits from `BaseInterpreter` and adds all the
# necessary `asyncio`-based functionality for event handling, background tasks
# (`after`, `invoke`), and actor management.
# -----------------------------------------------------------------------------

import asyncio
import uuid
import logging
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Union,
    overload,
    Callable,
    Awaitable,
)

from .base_interpreter import BaseInterpreter
from .events import AfterEvent, DoneEvent, Event
from .exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
)
from .models import (
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TEvent,
)
from .task_manager import TaskManager

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🚀 Interpreter Class Definition
# -----------------------------------------------------------------------------


class Interpreter(BaseInterpreter[TContext, TEvent]):
    """
    Brings a state machine definition to life by interpreting its behavior
    asynchronously.

    The `Interpreter` class is the core runtime engine. It manages the machine's
    current state, processes events from an async queue, executes actions and
    side effects, and orchestrates the full state transition lifecycle, including
    asynchronous operations like services, delays, and spawned child actors.

    Attributes:
        task_manager (TaskManager): Manages all background asyncio tasks.
        _event_queue (asyncio.Queue): An internal queue for incoming events.
        _event_loop_task (Optional[asyncio.Task]): The task running the main event loop.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]):
        """
        Initializes a new asynchronous Interpreter instance.

        Args:
            machine (MachineNode[TContext, TEvent]): The machine definition
                (`MachineNode` instance) that this interpreter will run.
        """
        super().__init__(machine, interpreter_class=Interpreter)
        logger.info("🚀 Initializing Asynchronous Interpreter...")

        # 🚀 Concurrency & Task Management
        self.task_manager: TaskManager = TaskManager()
        self._event_queue: asyncio.Queue[
            Union[Event, AfterEvent, DoneEvent]
        ] = asyncio.Queue()
        self._event_loop_task: Optional[asyncio.Task] = None

        logger.info("Asynchronous Interpreter '%s' initialized.", self.id)

    # -------------------------------------------------------------------------
    # Public API (Async Implementation)
    # -------------------------------------------------------------------------

    async def start(self) -> "Interpreter":
        """
        Starts the interpreter and its main event loop.

        This method initializes the machine by transitioning it to its initial
        state and begins processing events. It now includes exception handling
        to gracefully stop the interpreter if startup fails.

        Returns:
            Interpreter: The interpreter instance, allowing for method chaining.
        """
        if self.status != "uninitialized":
            logger.info(
                "🏁 Interpreter '%s' already running or stopped. Skipping start.",
                self.id,
            )
            return self

        logger.info("🏁 Starting interpreter '%s'...", self.id)
        self.status = "running"
        self._event_loop_task = asyncio.create_task(self._run_event_loop())

        try:
            for plugin in self._plugins:
                plugin.on_interpreter_start(self)

            await self._enter_states([self.machine])
            logger.info(
                "✅ Interpreter '%s' started. Current states: %s",
                self.id,
                self.current_state_ids,
            )
        except Exception:
            logger.error(
                "💥 Interpreter '%s' failed to start.", self.id, exc_info=True
            )
            self.status = "stopped"
            # The event loop task might not have stopped yet, ensure it's cancelled.
            if self._event_loop_task and not self._event_loop_task.done():
                self._event_loop_task.cancel()
            raise
        return self

    async def stop(self) -> None:
        """
        Stops the interpreter, cleaning up all tasks and spawned actors.
        """
        if self.status != "running":
            logger.info(
                "🛑 Interpreter '%s' is not running. Skipping stop.", self.id
            )
            return

        logger.info("🛑 Gracefully stopping interpreter '%s'...", self.id)
        self.status = "stopped"

        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        for actor in self._actors.values():
            await actor.stop()
        self._actors.clear()

        await self.task_manager.cancel_all()

        if self._event_loop_task:
            self._event_loop_task.cancel()
            await asyncio.gather(self._event_loop_task, return_exceptions=True)
            self._event_loop_task = None

        logger.info("✅ Interpreter '%s' stopped successfully.", self.id)

    @overload
    async def send(  # noqa
        self, event_type: str, **payload: Any
    ) -> None: ...  # noqa: E704

    @overload
    async def send(  # noqa
        self, event: Union[Dict[str, Any], Event]
    ) -> None: ...  # noqa: E704

    async def send(
        self, event_or_type: Union[str, Dict[str, Any], Event], **payload: Any
    ) -> None:
        """
        Sends an event to the machine's internal event queue for processing.
        """
        event_obj: Event
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

        await self._event_queue.put(event_obj)

    # -------------------------------------------------------------------------
    # Internal Event Loop & Execution
    # -------------------------------------------------------------------------

    async def _run_event_loop(self) -> None:
        """The main asynchronous event loop for the interpreter."""
        logger.debug("Event loop started for interpreter '%s'.", self.id)
        try:
            while self.status == "running":
                event = await self._event_queue.get()
                logger.debug("🔥 Event '%s' dequeued.", event.type)

                for plugin in self._plugins:
                    plugin.on_event_received(self, event)

                await self._process_event(event)

                # After processing an event, immediately process any event-less ("transient") transitions
                while True:
                    transient_event = Event(type="")
                    transition = self._find_optimal_transition(transient_event)
                    if transition and transition.event == "":
                        logger.info("⚡ Processing transient transition...")
                        await self._process_event(transient_event)
                    else:
                        break  # No more transient transitions, state is stable

                self._event_queue.task_done()
        except asyncio.CancelledError:
            logger.debug("🛑 Event loop for '%s' cancelled; exiting.", self.id)
        except Exception as exc:
            logger.critical(
                "💥 Fatal error in event loop for '%s': %s",
                self.id,
                exc,
                exc_info=True,
            )
            # Set status to stopped and then re-raise the exception.
            # This ensures the interpreter is in a correct final state.
            self.status = "stopped"
            raise
        finally:
            logger.debug("⚓ Event loop for '%s' exited.", self.id)

    async def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """
        Asynchronously executes a list of actions.

        This implementation checks if actions are coroutine functions and awaits
        them accordingly. It also handles the special "spawn_" action.

        Args:
            actions (List[ActionDefinition]): The actions to execute.
            event (Event): The event that triggered these actions.
        """
        if not actions:
            return

        for action_def in actions:
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            if action_def.type.startswith("spawn_"):
                await self._spawn_actor(action_def, event)
                continue

            action_callable = self.machine.logic.actions.get(action_def.type)
            # ✅ FIX: Raise an error if the action is not implemented.
            if not action_callable:
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' is not implemented."
                )

            if asyncio.iscoroutinefunction(action_callable):
                await action_callable(self, self.context, event, action_def)
            else:
                action_callable(self, self.context, event, action_def)

    # -------------------------------------------------------------------------
    # Actor, Service, and Timer Implementations (Async)
    # -------------------------------------------------------------------------

    async def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> None:
        """Handles the logic for spawning a child actor."""
        logger.info("👶 Spawning actor for action: '%s'", action_def.type)
        actor_machine_key = action_def.type.replace("spawn_", "")
        actor_machine = self.machine.logic.services.get(actor_machine_key)

        if not isinstance(actor_machine, MachineNode):
            raise ActorSpawningError(
                f"Cannot spawn '{actor_machine_key}'. "
                "Source in `services` is not a valid MachineNode."
            )

        actor_id = f"{self.id}:{actor_machine_key}:{uuid.uuid4()}"
        # Ensure child actor is also an async Interpreter
        actor_interpreter = Interpreter(actor_machine)
        actor_interpreter.parent = self
        actor_interpreter.id = actor_id
        await actor_interpreter.start()

        self._actors[actor_id] = actor_interpreter
        self.context.setdefault("actors", {})[actor_id] = actor_interpreter
        logger.info("✅ Actor '%s' spawned successfully.", actor_id)

    async def _cancel_state_tasks(self, state: StateNode) -> None:
        """
        Asynchronously cancels all background tasks associated with a specific state.

        This implementation manually handles the cancellation process to ensure
        that tasks are properly cancelled and awaited.
        """
        owner_id = state.id
        if owner_id in self.task_manager._tasks_by_owner:
            tasks_to_cancel = list(self.task_manager._tasks_by_owner[owner_id])
            logger.debug(
                "Cancelling %d tasks for owner '%s'",
                len(tasks_to_cancel),
                owner_id,
            )
            for task in tasks_to_cancel:
                task.cancel()

            # Wait for all tasks to acknowledge cancellation. This is the crucial step
            # to ensure the ".cancelled()" status is updated before tests check it.
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

            # Manually clean up the task manager for this owner
            del self.task_manager._tasks_by_owner[owner_id]

    async def _after_timer_task(
        self, delay_sec: float, event: AfterEvent
    ) -> None:
        """Coroutine that waits and then sends a delayed event."""
        try:
            await asyncio.sleep(delay_sec)
            logger.info("🕒 'after' timer fired for event '%s'.", event.type)
            await self.send(event)
        except asyncio.CancelledError:
            logger.debug(
                "🚫 'after' timer for event '%s' was cancelled.", event.type
            )

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Creates a task for a delayed `AfterEvent`."""
        task = asyncio.create_task(self._after_timer_task(delay_sec, event))
        self.task_manager.add(owner_id, task)

    async def _invoke_service_task(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Awaitable[Any]],
    ) -> None:
        """
        Runs an invoked service coroutine and emits the appropriate done/error
        events.  If the task gets cancelled while awaiting the service, we
        re-raise the `CancelledError` so the surrounding `asyncio.Task` keeps
        its “cancelled” status (needed by the test suite).
        """
        logger.info(
            "📞 Invoking service '%s' (ID: '%s')…",
            invocation.src,
            invocation.id,
        )
        try:
            invoke_event = Event(
                f"invoke.{invocation.id}", {"input": invocation.input or {}}
            )
            result = await service(self, self.context, invoke_event)

            # Service completed successfully → emit done event.
            await self.send(
                DoneEvent(
                    f"done.invoke.{invocation.id}",
                    data=result,
                    src=invocation.id,
                )
            )
            logger.info(
                "✅ Service '%s' (ID: '%s') completed.",
                invocation.src,
                invocation.id,
            )

        except asyncio.CancelledError:
            # Preserve cancellation so `task.cancelled()` returns True.
            logger.debug(
                "🚫 Service '%s' (ID: '%s') cancelled.",
                invocation.src,
                invocation.id,
            )
            raise

        except Exception as e:
            logger.error(
                "💥 Service '%s' (ID: '%s') failed: %s",
                invocation.src,
                invocation.id,
                e,
                exc_info=True,
            )
            await self.send(
                DoneEvent(
                    f"error.platform.{invocation.id}",
                    data=e,
                    src=invocation.id,
                )
            )

    def _invoke_service(
        self, invocation: InvokeDefinition, service: Callable, owner_id: str
    ) -> None:
        """Creates a task to run an invoked service."""

        async def _invoke_wrapper():
            # Yield control to the event loop to ensure the task is registered
            # in the TaskManager before the service is awaited. This resolves
            # a race condition in tests for long-running services.
            await asyncio.sleep(0)
            await self._invoke_service_task(invocation, service)

        task = asyncio.create_task(_invoke_wrapper())
        self.task_manager.add(owner_id, task)
