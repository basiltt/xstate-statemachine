# /src/xstate_statemachine/interpreter.py
# -----------------------------------------------------------------------------
# 🚀 Asynchronous Interpreter
# -----------------------------------------------------------------------------
# This module contains the `Interpreter` class, the primary asynchronous state
# machine engine. It inherits from `BaseInterpreter` and implements all the
# necessary `asyncio`-based functionality for event handling, background tasks
# (`after`, `invoke`), and actor management.
#
# This class is the workhorse that brings a machine definition to life in an
# async environment, making it suitable for I/O-bound applications like web
# servers, IoT clients, and automation scripts.
# -----------------------------------------------------------------------------
"""
Provides the primary asynchronous interpreter for running state machines.

The `Interpreter` class manages the state machine's lifecycle in a non-blocking
fashion using Python's `asyncio` library. It processes events from a queue,
handles timed transitions, and invokes asynchronous services, making it the
recommended choice for most modern applications.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import logging
import uuid
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Union,
    overload,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .base_interpreter import BaseInterpreter
from .events import AfterEvent, DoneEvent, Event
from .exceptions import ActorSpawningError, ImplementationMissingError
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
    """Brings a state machine definition to life by interpreting it asynchronously.

    The `Interpreter` is the core runtime engine. It manages the machine's
    current state, processes events from an async queue, executes actions and
    side effects, and orchestrates the full state transition lifecycle. This
    includes handling complex asynchronous operations like invoked services,
    timed delays, and spawned child actors (other interpreters).

    Attributes:
        task_manager: An instance of `TaskManager` to manage all background
                      `asyncio.Task` objects created by this interpreter.
    """

    def __init__(self, machine: MachineNode[TContext, TEvent]) -> None:
        """Initializes a new asynchronous Interpreter instance.

        Args:
            machine: The `MachineNode` instance that this interpreter will run.
        """
        # 🏛️ Initialize the base class, passing our own class for snapshotting.
        super().__init__(machine, interpreter_class=Interpreter)
        logger.info(
            "🚀 Initializing Asynchronous Interpreter for '%s'...", self.id
        )

        # 🚀 Concurrency & Task Management
        self.task_manager: TaskManager = TaskManager()
        self._event_queue: asyncio.Queue[
            Union[Event, AfterEvent, DoneEvent]
        ] = asyncio.Queue()
        self._event_loop_task: Optional[asyncio.Task[None]] = None

        logger.info("✅ Asynchronous Interpreter '%s' initialized.", self.id)

    # -------------------------------------------------------------------------
    # ⏯️ Public Control API (Start, Stop, Send)
    # -------------------------------------------------------------------------

    async def start(self) -> "Interpreter[TContext, TEvent]":
        """Starts the interpreter and its main event-processing loop.

        This method initializes the machine by transitioning it to its initial
        state and begins processing events from the queue. It is idempotent;
        calling `start` on an already running interpreter has no effect.

        Returns:
            The interpreter instance (`self`), allowing for method chaining.

        Raises:
            Exception: Propagates any exception that occurs during the initial
            state entry, ensuring a clean failure state.
        """
        if self.status != "uninitialized":
            logger.warning(
                "⚠️ Interpreter '%s' already running or stopped. Skipping start.",
                self.id,
            )
            return self

        logger.info("🏁 Starting interpreter '%s'...", self.id)
        self.status = "running"
        self._event_loop_task = asyncio.create_task(self._run_event_loop())

        try:
            # 🔔 Notify plugins that the interpreter is starting.
            for plugin in self._plugins:
                plugin.on_interpreter_start(self)

            # 🚀 Enter the initial state of the machine.
            # We pass a synthetic init event to allow startup actions to execute.
            init_event = Event(type="___xstate_statemachine_init___")
            await self._enter_states([self.machine], init_event)

            logger.info(
                "✅ Interpreter '%s' started successfully. Current states: %s",
                self.id,
                self.current_state_ids,
            )
        except Exception:
            # 💥 If startup fails, perform a graceful shutdown.
            logger.error(
                "💥 Interpreter '%s' failed to start.", self.id, exc_info=True
            )
            self.status = "stopped"
            if self._event_loop_task and not self._event_loop_task.done():
                self._event_loop_task.cancel()
            raise  # Re-raise the original exception.

        return self

    async def stop(self) -> None:
        """Stops the interpreter, cleaning up all tasks and spawned actors.

        This method gracefully shuts down the event loop, cancels all running
        background tasks (timers, services), and recursively stops any child
        actors that were spawned by this interpreter. It is idempotent.
        """
        if self.status != "running":
            logger.warning(
                "⚠️ Interpreter '%s' is not running. Skipping stop.", self.id
            )
            return

        logger.info("🛑 Gracefully stopping interpreter '%s'...", self.id)
        self.status = "stopped"

        # 🔔 Notify plugins of the shutdown.
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        # 🛑 Stop all child actors recursively.
        for actor in self._actors.values():
            await actor.stop()
        self._actors.clear()

        # ❌ Cancel all background tasks managed by this interpreter.
        await self.task_manager.cancel_all()

        # 🔌 Terminate the main event loop.
        if self._event_loop_task:
            self._event_loop_task.cancel()
            # Wait for the loop to acknowledge cancellation.
            try:
                await self._event_loop_task
            except asyncio.CancelledError:
                logger.debug(
                    "Event loop task successfully caught cancellation."
                )
            self._event_loop_task = None

        logger.info("✅ Interpreter '%s' stopped successfully.", self.id)

    @overload
    async def send(self, event_type: str, **payload: Any) -> None: ...  # noqa

    @overload
    async def send(  # noqa
        self, event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent]
    ) -> None: ...

    async def send(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent
        ],
        **payload: Any,
    ) -> None:
        """Sends an event to the machine's internal event queue for processing.

        This method provides a flexible API to send events, accepting either
        a string type with keyword arguments for the payload, a dictionary,
        or a pre-constructed `Event` object (or its subclasses). This is an
        async operation that returns immediately after queueing the event.

        Args:
            event_or_type: The event to send. Can be an event type string,
                a dictionary (e.g., `{"type": "MY_EVENT", "value": 42}`),
                or an `Event`, `DoneEvent`, or `AfterEvent` object.
            **payload: Keyword arguments that become the event's payload if
                `event_or_type` is a string.
        """
        #  DRY: Use the centralized helper from the base class to prepare
        # the event object.
        event_obj = self._prepare_event(event_or_type, **payload)

        # 📥 Place the standardized event object into the async queue.
        await self._event_queue.put(event_obj)

    # -------------------------------------------------------------------------
    # ⚙️ Internal Event Loop & Execution
    # -------------------------------------------------------------------------

    async def _run_event_loop(self) -> None:
        """The main asynchronous event-processing loop for the interpreter."""
        logger.debug("🔄 Event loop started for interpreter '%s'.", self.id)
        try:
            while self.status == "running":
                # 📬 Wait for the next event from the queue.
                event = await self._event_queue.get()
                logger.debug(
                    "🔥 Event '%s' dequeued for processing.", event.type
                )

                # 🔌 Notify plugins that an event has been received.
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)

                # 🧠 Process the event, which may cause a state transition.
                await self._process_event(event)

                # ⚡ After processing, check for and handle any "transient"
                # (event-less) transitions until the state stabilizes.
                while True:
                    transient_event = Event(type="")
                    transition = self._find_optimal_transition(transient_event)
                    if transition and transition.event == "":
                        logger.info(
                            "⚡ Processing transient (event-less) transition..."
                        )
                        await self._process_event(transient_event)
                    else:
                        # No more transient transitions; state is stable.
                        break

                self._event_queue.task_done()

        except asyncio.CancelledError:
            logger.debug("🛑 Event loop for '%s' was cancelled.", self.id)
            # This is an expected, clean shutdown.
            raise
        except Exception as exc:
            logger.critical(
                "💥 Fatal error in event loop for '%s': %s",
                self.id,
                exc,
                exc_info=True,
            )
            # On catastrophic failure, ensure the interpreter is stopped.
            self.status = "stopped"
            raise
        finally:
            logger.debug("⚓ Event loop for '%s' has exited.", self.id)

    async def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """Asynchronously executes a list of actions.

        This implementation respects the asynchronous nature of actions,
        awaiting them if they are coroutine functions. It also handles the
        special "spawn" action for creating child actors.

        Args:
            actions: The list of `ActionDefinition` objects to execute.
            event: The event that triggered these actions.

        Raises:
            ImplementationMissingError: If a named action is not defined in the
            machine's logic.
        """
        if not actions:
            return

        for action_def in actions:
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 👶 Handle actor spawning as a special action type.
            if action_def.type.startswith("spawn_"):
                await self._spawn_actor(action_def, event)
                continue

            # 🔎 Find the implementation for the named action.
            action_callable = self.machine.logic.actions.get(action_def.type)
            if not action_callable:
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' is not implemented."
                )

            # 🏃‍♂️ Execute the action, awaiting if it's an async function.
            if asyncio.iscoroutinefunction(action_callable):
                await action_callable(self, self.context, event, action_def)
            else:
                action_callable(self, self.context, event, action_def)

    # -------------------------------------------------------------------------
    # 🤖 Actor, Service, and Timer Implementations (Async)
    # -------------------------------------------------------------------------

    async def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> None:
        """Handles the logic for spawning a child state machine actor.

        Args:
            action_def: The "spawn_" action definition from the config.
            event: The event that triggered the spawn action.

        Raises:
            ActorSpawningError: If the source for the actor in the machine's
            `services` logic is not a valid `MachineNode` or a
            function that returns one.
        """
        logger.info("👶 Spawning actor for action: '%s'", action_def.type)
        actor_machine_key = action_def.type.replace("spawn_", "")

        actor_source = self.machine.logic.services.get(actor_machine_key)
        actor_machine: Optional[MachineNode] = None

        if isinstance(actor_source, MachineNode):
            actor_machine = actor_source
        elif callable(actor_source):
            # 🏭 If the source is a callable, treat it as a factory.
            result = actor_source(self, self.context, event)
            if asyncio.iscoroutine(result):
                result = (
                    await result
                )  # Await the factory if it's an async function
            if isinstance(result, MachineNode):
                actor_machine = result

        if not actor_machine:
            raise ActorSpawningError(
                f"Cannot spawn '{actor_machine_key}'. Source in `services` "
                "is not a valid MachineNode or a function that returns one."
            )

        # 🧬 Create and start the new child interpreter.
        actor_id = f"{self.id}:{actor_machine_key}:{uuid.uuid4()}"
        child_interpreter = Interpreter(actor_machine)
        child_interpreter.parent = self
        child_interpreter.id = actor_id
        await child_interpreter.start()

        self._actors[actor_id] = child_interpreter
        logger.info(
            "✅ Actor '%s' spawned and started successfully.", actor_id
        )

    async def _cancel_state_tasks(self, state: StateNode) -> None:
        """Asynchronously cancels all background tasks associated with a state.

        When a state is exited, this method ensures that any running timers
        or invoked services belonging to that state are properly cancelled
        to prevent orphaned tasks and race conditions.

        Args:
            state: The `StateNode` being exited.
        """
        # Encapsulation: Delegate cancellation to the TaskManager.
        await self.task_manager.cancel_by_owner(state.id)

    async def _after_timer_task(
        self, delay_sec: float, event: AfterEvent
    ) -> None:
        """Coroutine that waits for a delay and then sends an `AfterEvent`.

        Args:
            delay_sec: The delay in seconds.
            event: The `AfterEvent` to send after the delay.
        """
        try:
            await asyncio.sleep(delay_sec)
            logger.info("🕒 'after' timer fired for event '%s'.", event.type)
            await self.send(event)
        except asyncio.CancelledError:
            # This is expected when a state is exited before the timer fires.
            logger.debug(
                "🚫 'after' timer for event '%s' was cancelled.", event.type
            )
            # Re-raise to ensure the task is properly cleaned up.
            raise

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Creates and registers a task for a delayed `AfterEvent`.

        Args:
            delay_sec: The delay in seconds.
            event: The event to be sent.
            owner_id: The ID of the state that owns this timer.
        """
        task = asyncio.create_task(self._after_timer_task(delay_sec, event))
        self.task_manager.add(owner_id, task)

    async def _invoke_service_task(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Awaitable[Any]],
    ) -> None:
        """Wrapper coroutine that runs an invoked service.

        It handles the full lifecycle: running the service, capturing its result
        or any exceptions, and sending the appropriate `DoneEvent` back to the
        machine.

        Args:
            invocation: The `InvokeDefinition` from the machine config.
            service: The actual async callable service implementation.
        """
        logger.info(
            "📞 Invoking service '%s' (ID: '%s')...",
            invocation.src,
            invocation.id,
        )
        # 🔔 Notify plugins that the service is starting.
        for plugin in self._plugins:
            plugin.on_service_start(self, invocation)

        try:
            # Create a synthetic event to pass to the service if needed.
            invoke_event = Event(
                type=f"invoke.{invocation.id}",
                payload={"input": invocation.input or {}},
            )
            # 🏃‍♂️ Await the actual service coroutine.
            result = await service(self, self.context, invoke_event)

            # ✅ Service completed successfully, send 'done' event.
            await self.send(
                DoneEvent(
                    type=f"done.invoke.{invocation.id}",
                    data=result,
                    src=invocation.id,
                )
            )
            logger.info(
                "✅ Service '%s' (ID: '%s') completed successfully.",
                invocation.src,
                invocation.id,
            )
            # 🔔 Notify plugins that the service completed.
            for plugin in self._plugins:
                plugin.on_service_done(self, invocation, result)

        except asyncio.CancelledError:
            # 🚫 Service was cancelled (due to state exit).
            logger.debug(
                "🚫 Service '%s' (ID: '%s') was cancelled.",
                invocation.src,
                invocation.id,
            )
            # Re-raise to ensure the task is marked as cancelled.
            raise

        except Exception as e:
            # 💥 Service raised an unhandled exception.
            logger.error(
                "💥 Service '%s' (ID: '%s') failed: %s",
                invocation.src,
                invocation.id,
                e,
                exc_info=True,
            )
            # Send 'error' event so the machine can transition to a failure state.
            await self.send(
                DoneEvent(
                    type=f"error.platform.{invocation.id}",
                    data=e,
                    src=invocation.id,
                )
            )
            # 🔔 Notify plugins that the service failed.
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
        owner_id: str,
    ) -> None:
        """Creates and registers a task to run an invoked service.

        Args:
            invocation: The invoke definition from the state.
            service: The callable service implementation.
            owner_id: The ID of the state that owns this service.
        """

        async def _invoke_wrapper() -> None:
            # 🧠 This is a subtle but important detail to prevent a race
            # condition. We yield control briefly (await sleep(0)) to ensure
            # the task is fully registered in the TaskManager *before* the
            # potentially long-running service is awaited. This prevents a
            # state from exiting and trying to cancel a task that hasn't
            # been added to the manager yet.
            await asyncio.sleep(0)
            await self._invoke_service_task(invocation, service)

        task = asyncio.create_task(_invoke_wrapper())
        self.task_manager.add(owner_id, task)
