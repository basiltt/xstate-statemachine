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
import inspect
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
from .exceptions import (
    ActorSpawningError,
    ImplementationMissingError,
    InvalidConfigError,
)
from .actions import (
    ESCALATE,
    FORWARD_TO,
    RAISE,
    SEND_PARENT,
    SEND_TO,
    SPAWN_CHILD,
    STOP_CHILD,
    is_builtin,
    resolve_builtin,
)
from .models import (
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TContext,
    TEvent,
    spawn_service_key,
)
from .task_manager import TaskManager

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# ⏱️ How often `_spawn_and_manage_actor` checks whether an invoked child
#    machine has reached a final state. Small enough that `onDone` feels
#    immediate, large enough not to busy-wait a core.
_ACTOR_POLL_INTERVAL = 0.005


# -----------------------------------------------------------------------------
# 🚀 Interpreter Class Definition
# -----------------------------------------------------------------------------


class Interpreter(BaseInterpreter[TContext, TEvent]):
    """Brings a state machine to life by interpreting it asynchronously.

    The `Interpreter` is the core runtime engine for the state machine. It
    manages the machine's current state, processes events from an async queue,
    executes actions and side effects, and orchestrates the full state
    transition lifecycle. This includes handling complex asynchronous operations
    like invoked services, timed delays (`after`), and spawned child actors
    (which are themselves `Interpreter` instances).

    It uses a dedicated `TaskManager` to cleanly manage the lifecycle of all
    background `asyncio.Task` objects, ensuring they are properly cancelled
    when states are exited.

    Attributes:
        task_manager (TaskManager): An instance of `TaskManager` that tracks and
            manages all background `asyncio.Task` objects created by this
            interpreter for services and timers.
    """

    def __init__(
        self,
        machine: MachineNode[TContext, TEvent],
        input: Optional[Any] = None,
    ) -> None:
        """Initializes a new asynchronous Interpreter instance.

        Args:
            machine (MachineNode[TContext, TEvent]): The `MachineNode` instance
                that this interpreter will execute.
        """
        # 🏛️ Initialize the base class, passing our own class type so that
        # `from_snapshot` can create the correct `Interpreter` instance.
        super().__init__(machine, interpreter_class=Interpreter, input=input)
        logger.info(
            "🚀 Initializing Asynchronous Interpreter for '%s'...", self.id
        )

        # 🗃️ Concurrency & Task Management
        self.task_manager: TaskManager = TaskManager()
        self._event_queue: asyncio.Queue[
            Union[Event, AfterEvent, DoneEvent]
        ] = asyncio.Queue()
        self._event_loop_task: Optional[asyncio.Task[None]] = None
        #: Length of the current self-raised event chain. Incremented when an
        #: action enqueues onto our own queue *during* processing, reset when
        #: a macrostep completes without having done so. Bounds a runaway
        #: `raise` without ever throttling external `send()` traffic.
        self._raise_depth: int = 0
        #: True while `_run_event_loop` is inside `_process_event...`.
        self._processing: bool = False

        logger.info("✅ Asynchronous Interpreter '%s' initialized.", self.id)

    # -------------------------------------------------------------------------
    # ⏯️ Public Control API (Start, Stop, Send)
    # -------------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        """Indicates whether this interpreter can actually process events.

        🏛️ Architecture decision: the async interpreter needs a liveness check
        stronger than `status == "running"`. `from_snapshot()` restores the
        persisted status directly, producing an instance that reports
        `"running"` while `_event_loop_task` is `None` — nothing is draining
        the queue, so every `send()` would be silently enqueued and never
        handled. Requiring a live loop task means `is_running` never claims a
        machine is processing when it cannot.

        Returns:
            bool: `True` only when the status is `"running"` *and* the event
            loop task exists and has not finished.
        """
        return (
            self.status == "running"
            and self._event_loop_task is not None
            and not self._event_loop_task.done()
        )

    async def start(self) -> "Interpreter[TContext, TEvent]":
        """Starts the interpreter and its main event-processing loop.

        This method initializes the machine by transitioning it to its initial
        state and begins the main event loop to process events from the queue.
        It is idempotent; calling `start` on an already running or stopped
        interpreter has no effect and will simply return.

        Returns:
            Interpreter[TContext, TEvent]: The interpreter instance (`self`),
            allowing for convenient method chaining (e.g., `await
            Interpreter(m).start()`).

        Raises:
            Exception: Propagates any exception that occurs during the initial
                state entry, ensuring a clean failure state if the machine
                cannot start correctly.
        """
        # ♻️ Resume a snapshot-restored interpreter.
        #
        # 🏛️ Architecture decision: `from_snapshot` restores the persisted
        # status verbatim, so a restored actor reads `"running"` with no
        # `_event_loop_task`. The idempotency check below then refused to
        # start it, leaving a machine that looked alive, queued every event
        # and processed none. Detecting that shape and attaching a loop makes
        # `start()` the documented way to resume a restored actor.
        if (
            self.status in ("running", "done", "error")
            and self._event_loop_task is None
        ):
            logger.info("♻️ Resuming restored interpreter '%s'...", self.id)
            if self.status == "running":
                self._event_loop_task = asyncio.create_task(
                    self._run_event_loop()
                )
            # 👶 Resume restored child actors too, so a whole hierarchy comes
            #    back alive rather than just its root.
            for actor in list(self._actors.values()):
                resumed = actor.start()
                if inspect.isawaitable(resumed):
                    await resumed
            return self

        # 🛡️ Idempotency check: Don't start if already running or stopped.
        #
        # 🛑 A STOPPED interpreter cannot be revived. Returning `self` made
        #    restart appear to succeed — state ids still read as live while
        #    `status` stayed "stopped" and every `send()` was silently
        #    dropped. Fail loudly instead of returning a corpse.
        if self.status == "stopped":
            raise InvalidConfigError(
                f"Interpreter '{self.id}' has been stopped and cannot be "
                f"restarted. Create a new interpreter, or restore one with "
                f"`Interpreter.from_snapshot(...)`."
            )
        if self.status != "uninitialized":
            logger.warning(
                "⚠️ Interpreter '%s' already running. Skipping start.",
                self.id,
            )
            return self

        logger.info("🏁 Starting interpreter '%s'...", self.id)
        self.status = "running"
        # 🌀 Launch the main event loop as a background task.
        self._event_loop_task = asyncio.create_task(self._run_event_loop())

        try:
            # 🔔 Notify plugins that the interpreter is starting.
            for plugin in self._plugins:
                plugin.on_interpreter_start(self)

            # 🚀 Enter the initial state(s) of the machine.
            # We use a synthetic init event to allow any entry actions on the
            # root state to execute.
            init_event = Event(type="___xstate_statemachine_init___")
            await self._enter_states([self.machine], init_event)

            # ⚡ Settle eventless ("always") transitions before returning.
            #
            # 🏛️ Architecture decision: `SyncInterpreter.start()` already does
            # this, so without it the two engines disagreed on the very first
            # observable state — a machine whose initial state declares
            # `always` sat in that state under the async engine until some
            # unrelated event happened to nudge it. `start()` must return a
            # settled configuration in BOTH engines.
            await self._settle_transient_transitions()

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
            # Ensure the event loop task is cancelled if it was created.
            if self._event_loop_task and not self._event_loop_task.done():
                self._event_loop_task.cancel()
            raise  # Re-raise the original exception to the caller.

        return self

    async def stop(self) -> None:
        """Stops the interpreter, cleaning up all tasks and spawned actors.

        This method gracefully shuts down the event loop, cancels all running
        background tasks (timers, services), and recursively stops any child
        actors that were spawned by this interpreter. It is idempotent.
        """
        # 🛡️ Idempotency check.
        #
        # 🏛️ `done` and `error` are terminal but NOT torn down: reaching a
        # top-level final state must still release child actors and tasks.
        if self.status in ("uninitialized", "stopped"):
            logger.warning(
                "⚠️ Interpreter '%s' is not running. Skipping stop.", self.id
            )
            return

        logger.info("🛑 Gracefully stopping interpreter '%s'...", self.id)
        self.status = "stopped"

        # 🔔 Notify plugins of the impending shutdown.
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        # 🛑 Stop all child actors recursively.
        #
        # 🧵 Iterate over a SNAPSHOT. Stopping a child yields to the event
        #    loop, which lets that child's own managing task run its `finally`
        #    and pop itself from `self._actors` — mutating the dict mid-loop
        #    and raising "dictionary changed size during iteration".
        for actor in list(self._actors.values()):
            await actor.stop()
        self._actors.clear()

        # ❌ Cancel all background tasks (timers, services) owned by this interpreter.
        await self.task_manager.cancel_all()

        # 🔌 Terminate the main event processing loop.
        if self._event_loop_task:
            self._event_loop_task.cancel()
            # Wait for the loop to acknowledge the cancellation to prevent leaks.
            try:
                await self._event_loop_task
            except asyncio.CancelledError:
                logger.debug(
                    "Event loop task for '%s' acknowledged cancellation.",
                    self.id,
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
        """Sends an event to the machine's internal queue for processing.

        This is the primary method for interacting with a running state machine.
        It provides a flexible API, accepting either a string type with keyword
        arguments for the payload, a dictionary, or a pre-constructed `Event`
        object. This is a non-blocking operation that returns immediately after
        placing the event in the queue.

        Args:
            event_or_type: The event to send. Can be an event type string,
                a dictionary (e.g., `{"type": "MY_EVENT", "value": 42}`),
                or an `Event`, `DoneEvent`, or `AfterEvent` object.
            **payload: Keyword arguments that become the event's payload if
                `event_or_type` is a string.
        """
        # 🚪 Refuse events once the machine is no longer processing. Nothing
        #    drains the queue after `stop()`, so every `send()` accumulated
        #    forever — a slow memory leak in any long-lived process that keeps
        #    a reference to a finished machine. Dropping with a warning also
        #    surfaces the mistake instead of hiding it.
        if self.status in ("stopped", "done"):
            logger.warning(
                "⚠️ Interpreter '%s' is %s; dropping event. Nothing drains "
                "the queue after shutdown, so queuing here would leak.",
                self.id,
                self.status,
            )
            return

        # 📦 Use the centralized helper from the base class to normalize the input.
        event_obj = self._prepare_event(event_or_type, **payload)

        # 📥 Place the standardized event object into the async queue.
        await self._event_queue.put(event_obj)

    async def send_events(
        self, events: List[Union[Dict[str, Any], Event, str]]
    ) -> None:
        """Sends a list of events to the machine's internal queue for processing.

        This method places all events in the queue without waiting for them to be
        processed, allowing for high-throughput, non-blocking event submission.

        Args:
            events: A list of events to send. Each event can be a string,
                a dictionary, or an `Event` object.
        """
        if self.status in ("stopped", "done"):
            logger.warning(
                "⚠️ Interpreter '%s' is %s; dropping %d event(s).",
                self.id,
                self.status,
                len(events),
            )
            return

        for event in events:
            event_obj = self._prepare_event(event)
            await self._event_queue.put(event_obj)

    # -------------------------------------------------------------------------
    # ⚙️ Internal Event Loop & Execution Logic
    # -------------------------------------------------------------------------

    async def _run_event_loop(self) -> None:
        """The main asynchronous event-processing loop for the interpreter."""
        logger.debug("🔄 Event loop started for interpreter '%s'.", self.id)
        # 🛟 Bound a SELF-FEEDING chain. The `raise` built-in enqueues onto
        #    this same queue and `Queue.put()` on an unbounded queue never
        #    suspends, so an action raising its own trigger event spins here
        #    forever WITHOUT yielding — starving the entire asyncio loop (a
        #    heartbeat scheduled every 50 ms was measured running zero times
        #    in four seconds).
        #
        # 🏛️ Architecture decision: measure the RAISE CHAIN, not queue depth.
        #    An earlier version incremented whenever the queue was non-empty
        #    after processing, which cannot tell a runaway `raise` from a
        #    merely busy producer — 5,000 legitimate concurrent `send()` calls
        #    lost 3,999 of them. `_raise_depth` counts only events this loop
        #    enqueued *while processing another event*, so external traffic of
        #    any volume is never throttled.
        limit = getattr(self.machine, "max_iterations", 1000)
        try:
            while self.status == "running":
                # 📬 Wait indefinitely for the next event from the queue.
                event = await self._event_queue.get()

                if self._raise_depth > limit:
                    logger.error(
                        "🛑 Exceeded %d chained self-raised events on '%s'. "
                        "This means an action raises the event that triggers "
                        "it. Breaking the chain; externally queued events are "
                        "unaffected.",
                        limit,
                        self.id,
                    )
                    self._raise_depth = 0
                    self._event_queue.task_done()
                    continue

                logger.debug(
                    "🔥 Event '%s' dequeued for processing in '%s'.",
                    event.type,
                    self.id,
                )

                # 🔌 Notify plugins that an event is about to be processed.
                for plugin in self._plugins:
                    plugin.on_event_received(self, event)

                # 🧠 Process the event using the core algorithm from BaseInterpreter.
                # This single step will handle the event and any subsequent
                # "always" transitions until the machine is in a stable state.
                #
                # 🛡️ Architecture decision: a failure while processing ONE
                #    event must not terminate the run loop. Previously any
                #    escaping error — an unresolvable target, a missing action,
                #    a raising guard — killed the loop and flipped `status` to
                #    "stopped". Because `send()` is fire-and-forget, the caller
                #    was never told: the machine went silently dead and dropped
                #    every subsequent event. `SyncInterpreter` raises to the
                #    caller and keeps running, so the two engines disagreed on
                #    a basic error path, and the async one failed in the more
                #    dangerous direction.
                #
                #    The transition itself is already atomic (see
                #    `_execute_transition`), so the configuration is intact
                #    here; we log and carry on with the next event.
                try:
                    self._processing = True
                    depth_before = self._raise_depth
                    await self._process_event_and_transient_transitions(event)
                    # ✅ A macrostep that raised nothing ends the chain.
                    if self._raise_depth == depth_before:
                        self._raise_depth = 0
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error(
                        "💥 Error processing event '%s' on '%s'; the "
                        "interpreter remains running. %s",
                        event.type,
                        self.id,
                        exc,
                        exc_info=True,
                    )
                finally:
                    self._processing = False

                self._event_queue.task_done()

        except asyncio.CancelledError:
            # This is an expected, clean shutdown triggered by `stop()`.
            #
            # 🏛️ Architecture decision: deliberately do NOT touch `status`
            # here, and do not use a `finally` clause to force it to
            # "stopped". Cancellation is not always initiated by `stop()` —
            # an enclosing TaskGroup, a supervisor, or a timeout around the
            # owning task can cancel `_event_loop_task` directly. If this path
            # set `status = "stopped"`, a subsequent `stop()` would hit its own
            # idempotency guard, return early, and skip actor teardown and
            # `task_manager.cancel_all()` — leaking invoked services and child
            # actors that keep running forever. `stop()` owns the status
            # transition for every orderly shutdown.
            logger.debug("🛑 Event loop for '%s' was cancelled.", self.id)
            raise
        except BaseException as exc:
            # This indicates a critical, unexpected failure in the machine's logic.
            #
            # 🏛️ Architecture decision: this catches `BaseException`, not
            # `Exception`. A `BaseException` subclass escaping the loop would
            # otherwise terminate it *without* updating `status`, leaving the
            # interpreter permanently reporting `status == "running"` and
            # nothing draining the queue — every subsequent `send()` silently
            # dropped. The exception is always re-raised, so this only
            # corrects the bookkeeping. `CancelledError` is handled above and
            # never reaches here.
            logger.critical(
                "💥 Fatal error in event loop for '%s': %s",
                self.id,
                exc,
                exc_info=True,
            )
            # Ensure the interpreter is fully stopped on catastrophic failure.
            self.status = "stopped"
            raise
        finally:
            logger.debug("⚓ Event loop for '%s' has exited.", self.id)

    async def _process_event_and_transient_transitions(
        self, event: Union[Event, AfterEvent, DoneEvent]
    ) -> None:
        """Processes a single event and any resulting event-less transitions.

        This method ensures that after an event is processed, the machine
        immediately checks for and takes any available "always" transitions
        until it settles into a stable state. This entire sequence is treated
        as a single, atomic "step".

        Args:
            event: The external event to process first.
        """
        # 1️⃣ Process the initial event that was dequeued.
        await self._process_event(event)

        # 2️⃣ Immediately settle any event-less ("always") transitions.
        await self._settle_transient_transitions()

    async def _settle_transient_transitions(self) -> None:
        """Runs eventless ("always") transitions until the state is stable.

        Extracted so `start()` can settle the initial configuration too — the
        sync engine already did this, so leaving it inline made the two
        engines disagree on the very first observable state.
        """
        # 🛟 Bound the microstep loop. A pair of `always` transitions that
        #    target each other spins forever; XState added the same guard in
        #    v5.31.0. `max_iterations` is configurable on the machine.
        iterations = 0
        limit = getattr(self.machine, "max_iterations", 1000)
        while True:
            iterations += 1
            if iterations > limit:
                logger.error(
                    "🔁 Exceeded %d microsteps while settling transient "
                    "transitions in '%s'. Aborting to avoid an infinite "
                    "loop; check for mutually-targeting 'always' transitions.",
                    limit,
                    self.id,
                )
                break
            transient_event = Event(type="")
            # 🧠 Use the memoised selection path so a transient transition on
            #    a shared ancestor evaluates its guard ONCE, not once per
            #    active leaf. The legacy single-winner scan re-evaluated it
            #    per region, multiplying any guard side effects.
            selected = self._select_transitions(transient_event)
            if selected and any(t.event == "" for t in selected):
                logger.info(
                    "⚡ Processing transient (event-less) transition in '%s'.",
                    self.id,
                )
                await self._process_event(transient_event)
            else:
                break  # No more transient transitions; state is stable.

    async def _execute_actions(
        self, actions: List[ActionDefinition], event: Event
    ) -> None:
        """Asynchronously executes a list of action definitions.

        This implementation respects the asynchronous nature of actions,
        `await`ing them if they are coroutine functions. It also handles the
        special "spawn" action for creating child actors.

        Args:
            actions (List[ActionDefinition]): The list of `ActionDefinition`
                objects to execute.
            event (Event): The event that triggered these actions.

        Raises:
            ImplementationMissingError: If a named action is not defined in the
                machine's logic dictionary.
        """
        if not actions:
            return

        for action_def in actions:
            # 🔔 Notify plugins before executing each action.
            for plugin in self._plugins:
                plugin.on_action_execute(self, action_def)

            # 👶 Handle actor spawning as a special, built-in action type.
            if action_def.type.startswith("spawn_") and not is_builtin(
                action_def.type
            ):
                await self._spawn_actor(action_def, event)
                continue

            # 🔎 Find the implementation for the named action.
            action_callable = self.machine.logic.actions.get(action_def.type)

            # 🎬 Built-in action creators. Resolved only when the user has NOT
            #    supplied an action of the same name, so a machine that
            #    legitimately defines its own `log` or `assign` keeps working.
            if action_callable is None:
                canonical = resolve_builtin(action_def.type)
                if canonical is not None:
                    # 🛡️ Built-ins resolve user-supplied params/callables, so
                    #    they can raise for exactly the same reasons a user
                    #    action can. Containing them here keeps the documented
                    #    contract - and stops an escaping error from killing
                    #    the fire-and-forget run loop.
                    try:
                        await self._execute_builtin_action(
                            canonical, action_def, event
                        )
                    except asyncio.CancelledError:
                        raise
                    except Exception:
                        logger.exception(
                            "🔥 Built-in action '%s' raised while handling "
                            "'%s'; skipping remaining actions.",
                            action_def.type,
                            event.type,
                        )
                        return
                    continue

            if not action_callable:
                raise ImplementationMissingError(
                    f"Action '{action_def.type}' is not implemented."
                )

            # 🏃‍♂️ Execute the action, awaiting if it's an async function.
            #
            # 🏛️ Architecture decision: exceptions from user-supplied actions
            # are contained here. `send()` is fire-and-forget, so an escaping
            # exception would tear down `_run_event_loop` while callers still
            # observed `status == "running"` — a silently dead machine. Per
            # the documented contract the error is logged, the remaining
            # actions are skipped, and the run loop survives. Configuration
            # errors (missing action) are raised above and remain fatal.
            try:
                if inspect.iscoroutinefunction(action_callable):
                    await action_callable(
                        self, self.context, event, action_def
                    )
                else:
                    action_callable(self, self.context, event, action_def)
            except asyncio.CancelledError:
                # 🛑 Cooperative cancellation must always propagate.
                raise
            except Exception:
                logger.exception(
                    "🔥 Action '%s' raised while handling event '%s'; "
                    "skipping remaining actions in this list.",
                    action_def.type,
                    event.type,
                )
                return

    # -------------------------------------------------------------------------
    # 🤖 Asynchronous Task Implementations (Actors, Timers, Services)
    # -------------------------------------------------------------------------

    async def _execute_builtin_action(
        self,
        canonical: str,
        action_def: ActionDefinition,
        event: Event,
    ) -> None:
        """Executes a built-in action creator asynchronously.

        Pure-state effects (`assign`, `log`, `emit`, `pure`, `choose`,
        `enqueueActions`, `cancel`) are handled by the shared base
        implementation. Delivery effects (`raise`, `sendTo`, `sendParent`,
        `forwardTo`, `escalate`, `stopChild`, `spawnChild`) need the event
        loop and are handled here.

        Args:
            canonical (str): The canonical built-in action name.
            action_def (ActionDefinition): The action being executed.
            event (Event): The triggering event.
        """
        # 🧮 Shared semantics first; may yield nested actions to run.
        followups = self._collect_builtin_followups(
            canonical, action_def, event
        )
        if followups:
            self._action_depth += 1
            try:
                await self._execute_actions(
                    [ActionDefinition(f) for f in followups], event
                )
            finally:
                self._action_depth -= 1

        params = self._resolve_params(action_def.params, event) or {}

        if canonical == RAISE:
            target_event = self._resolve_event_spec(params.get("event"), event)
            delay = self._resolve_delay(params.get("delay"), event)
            await self._deliver(self, target_event, delay, params.get("id"))

        elif canonical == SEND_TO:
            actor = self._resolve_actor_target(params.get("to"), event)
            if actor is None:
                logger.warning(
                    "⚠️ sendTo could not resolve target %r; event dropped.",
                    params.get("to"),
                )
                return
            target_event = self._resolve_event_spec(params.get("event"), event)
            delay = self._resolve_delay(params.get("delay"), event)
            await self._deliver(actor, target_event, delay, params.get("id"))

        elif canonical == SEND_PARENT:
            if self.parent is None:
                logger.warning("⚠️ sendParent called with no parent actor.")
                return
            target_event = self._resolve_event_spec(params.get("event"), event)
            delay = self._resolve_delay(params.get("delay"), event)
            await self._deliver(
                self.parent, target_event, delay, params.get("id")
            )

        elif canonical == FORWARD_TO:
            actor = self._resolve_actor_target(params.get("to"), event)
            if actor is None:
                logger.warning(
                    "⚠️ forwardTo could not resolve target %r.",
                    params.get("to"),
                )
                return
            await self._deliver(actor, event, None, None)

        elif canonical == ESCALATE:
            error_payload = params.get("error")
            escalate_event = Event(
                type=f"xstate.error.actor.{self.id}",
                payload={"error": error_payload},
            )
            if self.parent is not None:
                await self._deliver(self.parent, escalate_event, None, None)
            else:
                logger.error(
                    "🔥 escalate() with no parent actor: %r", error_payload
                )

        elif canonical == STOP_CHILD:
            await self._stop_child_actor(params.get("id"), event)

        elif canonical == SPAWN_CHILD:
            await self._spawn_child_action(params, event)

    async def _deliver(
        self,
        actor: "BaseInterpreter[Any, Any]",
        target_event: Event,
        delay: Optional[float],
        send_id: Optional[str],
    ) -> None:
        """Sends an event to an actor, honouring an optional delay.

        Args:
            actor (BaseInterpreter): The recipient.
            target_event (Event): The event to deliver.
            delay (Optional[float]): Delay in milliseconds, or `None`.
            send_id (Optional[str]): Id allowing later cancellation.
        """
        if not delay:
            # 🔁 A zero-delay delivery to OURSELVES during processing is the
            #    self-feeding shape that can spin the loop. Count it so
            #    `_run_event_loop` can break the chain; external `send()`
            #    calls never pass through here.
            if actor is self and self._processing:
                self._raise_depth += 1
            await self._send_to_actor(actor, target_event)
            return

        key = str(send_id) if send_id else None

        async def _delayed() -> None:
            """Waits out the delay, then delivers."""
            try:
                await asyncio.sleep(delay / 1000.0)
                await self._send_to_actor(actor, target_event)
            except asyncio.CancelledError:  # pragma: no cover - shutdown
                raise
            finally:
                # 🧹 Only clear the registry if it still points at THIS task.
                #    A later send reusing the same id replaces the entry, and
                #    popping unconditionally would drop the live registration
                #    and leave the newer send uncancellable.
                if (
                    key is not None
                    and self._scheduled_sends.get(key) is _cancel
                ):
                    self._scheduled_sends.pop(key, None)

        task = asyncio.create_task(_delayed())
        self.task_manager.add(self.id, task)

        def _cancel() -> None:
            """Cancels this specific delayed send."""
            task.cancel()

        if key is not None:
            # 🔁 Reusing a send id supersedes the earlier send. Without this
            #    the first task is orphaned: the registry entry is
            #    overwritten, so `cancel(id)` can no longer reach it and it
            #    fires anyway. Mirrors the sync engine.
            previous = self._scheduled_sends.get(key)
            if previous is not None:
                previous()
            self._scheduled_sends[key] = _cancel

    @staticmethod
    async def _send_to_actor(
        actor: "BaseInterpreter[Any, Any]", target_event: Event
    ) -> None:
        """Dispatches an event to an actor of either execution mode.

        📝 A parent may spawn a `SyncInterpreter` child (blocking actors), so
        the recipient's `send` is not guaranteed to be a coroutine.

        Args:
            actor (BaseInterpreter): The recipient.
            target_event (Event): The event to deliver.
        """
        result = actor.send(target_event)
        if inspect.isawaitable(result):
            await result

    async def _stop_child_actor(self, spec: Any, event: Event) -> None:
        """Stops a spawned child actor by id.

        Args:
            spec (Any): The child's id, or a callable resolving one.
            event (Event): The triggering event.
        """
        actor = self._resolve_actor_target(spec, event)
        if actor is None:
            logger.warning("⚠️ stopChild could not resolve %r.", spec)
            return
        for actor_id, candidate in list(self._actors.items()):
            if candidate is actor:
                del self._actors[actor_id]
                self._actor_sources.pop(actor_id, None)
                break
        # 🌐 Also drop it from the actor-system registry, otherwise a stopped
        #    actor stays addressable by systemId and silently swallows events.
        registry = self._system_registry()
        for system_id, candidate in list(registry.items()):
            if candidate is actor:
                del registry[system_id]
        result = actor.stop()
        if inspect.isawaitable(result):
            await result

    async def _spawn_child_action(
        self, params: Dict[str, Any], event: Event
    ) -> None:
        """Spawns an actor declaratively via the `spawnChild` action.

        Args:
            params (Dict[str, Any]): Params carrying `src`, `id`, `systemId`
                and `input`.
            event (Event): The triggering event.
        """
        src = params.get("src")
        if not isinstance(src, str):
            logger.warning("⚠️ spawnChild requires a string 'src'.")
            return
        synthetic = ActionDefinition(
            {
                "type": f"spawn_{src}",
                "params": {
                    "id": params.get("id"),
                    "systemId": params.get("systemId"),
                    "input": params.get("input"),
                },
            }
        )
        await self._spawn_actor(synthetic, event)

    async def _spawn_actor(
        self, action_def: ActionDefinition, event: Event
    ) -> None:
        """Handles the logic for spawning a child state machine actor.

        This method resolves the actor's `MachineNode` from the machine's
        logic, creates a new `Interpreter` instance for it, and starts it as
        a child process managed by the current interpreter.

        Args:
            action_def (ActionDefinition): The `spawn_` action definition.
            event (Event): The event that triggered the spawn action.

        Raises:
            ActorSpawningError: If the source for the actor in the machine's
                `services` logic is not a valid `MachineNode` or an async
                factory function that returns one.
        """
        logger.info("👶 Spawning actor for action: '%s'", action_def.type)
        actor_machine_key = spawn_service_key(action_def.type)

        actor_source = self.machine.logic.services.get(actor_machine_key)
        actor_machine: Optional[MachineNode] = None

        # 🏭 The actor source can be a direct machine node or a factory function.
        if isinstance(actor_source, MachineNode):
            actor_machine = actor_source
        elif callable(actor_source):
            # Execute the factory to get the machine definition.
            result = actor_source(self, self.context, event)
            if asyncio.iscoroutine(result):
                result = await result  # Await if the factory is async.
            if isinstance(result, MachineNode):
                actor_machine = result

        if not actor_machine:
            raise ActorSpawningError(
                f"Cannot spawn '{actor_machine_key}'. Source in `services` "
                "is not a valid MachineNode or a function that returns one."
            )

        # 🧬 Create, configure, and start the new child interpreter.
        spawn_params = action_def.params or {}
        explicit_id = spawn_params.get("id")
        actor_id = (
            f"{self.id}:{explicit_id}"
            if explicit_id
            else f"{self.id}:{actor_machine_key}:{uuid.uuid4()}"
        )
        child_interpreter = Interpreter(actor_machine)
        child_interpreter.parent = self
        child_interpreter.id = actor_id
        # 📥 Seed the child's context with any declared input.
        child_input = spawn_params.get("input")
        if child_input is not None:
            child_interpreter.context.setdefault("input", child_input)
        # 🌐 Register under a systemId so siblings can address it.
        self._register_in_system(
            spawn_params.get("systemId"), child_interpreter
        )
        await child_interpreter.start()

        self._actors[actor_id] = child_interpreter
        self._actor_sources[actor_id] = actor_machine_key
        logger.info(
            "✅ Actor '%s' (child of '%s') spawned and started successfully.",
            actor_id,
            self.id,
        )

    async def _cancel_state_tasks(self, state: StateNode) -> None:
        """Cancels all background tasks associated with an exited state.

        When a state is exited, this method ensures that any running timers
        or invoked services belonging to that state are properly cancelled.
        This prevents orphaned tasks, memory leaks, and race conditions.

        Args:
            state (StateNode): The `StateNode` being exited.
        """
        # Encapsulation: Delegate cancellation to the dedicated TaskManager.
        await self.task_manager.cancel_by_owner(state.id)

    async def _after_timer_task(
        self, delay_sec: float, event: AfterEvent
    ) -> None:
        """Coroutine that waits for a delay and then sends an `AfterEvent`.

        This is the actual task body for a timed transition (`after`).

        Args:
            delay_sec (float): The delay in seconds to wait.
            event (AfterEvent): The `AfterEvent` to send after the delay.
        """
        try:
            await asyncio.sleep(delay_sec)
            logger.info(
                "🕒 'after' timer fired for event '%s' in '%s'.",
                event.type,
                self.id,
            )
            await self.send(event)
        except asyncio.CancelledError:
            # This is expected when a state is exited before the timer fires.
            logger.debug(
                "🚫 'after' timer for event '%s' in '%s' was cancelled.",
                event.type,
                self.id,
            )
            raise  # Re-raise to ensure the task is properly cleaned up.

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Creates and registers a background task for a delayed `AfterEvent`.

        Args:
            delay_sec (float): The delay in seconds.
            event (AfterEvent): The event to be sent after the delay.
            owner_id (str): The ID of the state that owns this timer, used for
                cancellation upon state exit.
        """
        task = asyncio.create_task(self._after_timer_task(delay_sec, event))
        # Register the task with its owner for lifecycle management.
        self.task_manager.add(owner_id, task)

    async def _invoke_service_task(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Awaitable[Any]],
    ) -> None:
        """Wrapper coroutine that runs an invoked service and handles its result.

        This coroutine manages the full lifecycle of a service invocation: it
        runs the service, captures its successful result or any exceptions, and
        sends the appropriate `DoneEvent` (`done.invoke.*` or `error.platform.*`)
        back to the machine's event queue.

        Args:
            invocation (InvokeDefinition): The metadata for the service invocation.
            service (Callable[..., Awaitable[Any]]): The actual async callable
                service implementation from the machine's logic.
        """
        logger.info(
            "📞 Invoking service '%s' (ID: '%s')...",
            invocation.src,
            invocation.id,
        )
        for plugin in self._plugins:
            plugin.on_service_start(self, invocation)

        try:
            # Create a synthetic event to pass to the service if it needs context.
            invoke_event = Event(
                type=f"invoke.{invocation.id}",
                payload={"input": invocation.input or {}},
            )
            # 🏃‍♂️ Await the actual service coroutine.
            # 🔀 Accept both plain and coroutine services.
            #
            # 🏛️ Architecture decision: a synchronous `src` used to be
            # `await`ed unconditionally, which raised TypeError inside the
            # service task and left the machine sitting in the invoking state
            # forever — silently, since the task exception was never
            # retrieved. `SyncInterpreter` accepted the same service happily,
            # so the two engines disagreed on identical config.
            produced = service(self, self.context, invoke_event)
            result = (
                await produced if inspect.isawaitable(produced) else produced
            )

            # ✅ Service completed, send a 'done' event with the result data.
            done_event = DoneEvent(
                type=f"done.invoke.{invocation.id}",
                data=result,
                src=invocation.id,
            )
            await self.send(done_event)
            logger.info(
                "✅ Service '%s' (ID: '%s') completed successfully.",
                invocation.src,
                invocation.id,
            )
            for plugin in self._plugins:
                plugin.on_service_done(self, invocation, result)

        except asyncio.CancelledError:
            # 🚫 Service was cancelled (due to state exit). This is a clean path.
            logger.debug(
                "🚫 Service '%s' (ID: '%s') was cancelled.",
                invocation.src,
                invocation.id,
            )
            raise  # Re-raise to ensure the task is marked as cancelled.

        except Exception as e:
            # 💥 Service raised an unhandled exception.
            logger.error(
                "💥 Service '%s' (ID: '%s') failed: %s",
                invocation.src,
                invocation.id,
                e,
                exc_info=True,
            )
            # Send an 'error' event so the machine can transition to a failure state.
            error_event = DoneEvent(
                type=f"error.platform.{invocation.id}",
                data=e,
                src=invocation.id,
            )
            # 🚨 If nothing handles the error event, the failure is
            #    unhandled and must be observable rather than merely logged.
            handled = self._has_error_handler(invocation)
            await self.send(error_event)
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)
            if not handled:
                self._fail(e)

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
        owner_id: str,
    ) -> None:
        """Creates and registers a background task to run an invoked service or actor.

        This method acts as a dispatcher.
        - If the service is a `MachineNode`, it's spawned as a child actor.
        - If the service is a `Callable`, it's run as a standard async task.

        Args:
            invocation: The invoke definition from the state config.
            service: The service implementation or MachineNode from logic.
            owner_id: The ID of the state that owns this invocation.
        """
        # 🎭 Case 1: The service is a MachineNode, so we spawn it as an actor.
        if isinstance(service, MachineNode):
            # Create a task to manage the actor's lifecycle and handle onDone/onError.
            task = asyncio.create_task(
                self._spawn_and_manage_actor(invocation, service)
            )
            self.task_manager.add(owner_id, task)
            return

        # 📞 Case 2: The service is a standard callable.
        async def _invoke_wrapper() -> None:
            # This sleep(0) is a critical best practice to prevent a race
            # condition, ensuring the task is registered before the service
            # code runs.
            await asyncio.sleep(0)
            await self._invoke_service_task(invocation, service)

        task = asyncio.create_task(_invoke_wrapper())
        # Register the task with its owner for lifecycle management.
        self.task_manager.add(owner_id, task)

    async def _spawn_and_manage_actor(
        self, invocation: InvokeDefinition, actor_machine: MachineNode
    ) -> None:
        """Spawns, starts, and manages an actor, sending events on completion.

        This coroutine wraps the entire lifecycle of a child actor that was
        created via `invoke`. It waits for the child to finish and then sends
        the appropriate `onDone` or `onError` event to the parent.

        Args:
            invocation: The invoke definition containing the actor's config.
            actor_machine: The MachineNode definition for the actor.
        """
        child_interpreter = None
        try:
            # 🧬 Create, configure, and start the new child interpreter.
            actor_id = f"{self.id}:{invocation.src}:{uuid.uuid4()}"
            child_interpreter = Interpreter(actor_machine)
            child_interpreter.parent = self
            child_interpreter.id = actor_id
            self._actors[actor_id] = child_interpreter

            for plugin in self._plugins:
                plugin.on_service_start(self, invocation)
            logger.info(
                "🚀 Actor '%s' (ID: %s) invoked by '%s'...",
                invocation.src,
                actor_id,
                self.id,
            )
            # 🚀 Start the child. NOTE: `start()` returns as soon as the
            #    child's INITIAL state is entered — it does NOT block until the
            #    machine finishes. Treating it as "run to completion" fired
            #    `onDone` immediately with the child's initial context, so a
            #    parent transitioned onward while the child was still working.
            await child_interpreter.start()

            # ⏳ Now actually wait for the child to finish. `status` flips to
            #    "done" on completion, or "error" if the machine failed;
            #    polling the child's own lifecycle is what makes `onDone` mean
            #    what XState says it means.
            while child_interpreter.status == "running":
                await asyncio.sleep(_ACTOR_POLL_INTERVAL)

            # 💥 A child that FAILED must satisfy `onError`, not `onDone`.
            #    Treating any non-running status as success reported a crashed
            #    child as a clean completion, so a parent modelling failure
            #    with `onError` silently took the happy path.
            if child_interpreter.status == "error":
                failure = getattr(
                    child_interpreter,
                    "error",
                    None,
                ) or RuntimeError(
                    f"Invoked machine '{invocation.src}' failed."
                )
                logger.warning(
                    "💥 Invoked machine '%s' ended in error; firing onError.",
                    invocation.src,
                )
                error_event = DoneEvent(
                    type=f"error.platform.{invocation.id}",
                    data=failure,
                    src=invocation.id,
                )
                await self.send(error_event)
                for plugin in self._plugins:
                    plugin.on_service_error(self, invocation, failure)
                return

            # ✅ Child finished cleanly (reached a top-level final state).
            done_event = DoneEvent(
                type=f"done.invoke.{invocation.id}",
                data=child_interpreter.context,  # Return child's final context
                src=invocation.id,
            )
            await self.send(done_event)
            for plugin in self._plugins:
                plugin.on_service_done(self, invocation, done_event.data)

        except asyncio.CancelledError:
            # 🚫 Parent state was exited, cleanly cancel the actor.
            logger.debug(
                "🚫 Actor '%s' (ID: %s) was cancelled.",
                invocation.src,
                invocation.id,
            )
            if child_interpreter:
                await child_interpreter.stop()
            raise

        except Exception as e:
            # 💥 Child actor failed with an unhandled exception.
            logger.error(
                "💥 Actor '%s' (ID: '%s') failed: %s",
                invocation.src,
                invocation.id,
                e,
                exc_info=True,
            )
            error_event = DoneEvent(
                type=f"error.platform.{invocation.id}",
                data=e,
                src=invocation.id,
            )
            await self.send(error_event)
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)
        finally:
            # 🧹 ALWAYS tear the child down. Deleting the registry entry
            #    without stopping the interpreter orphaned it: its run loop and every
            #    `after` timer survived the parent's own `stop()` forever,
            #    because `stop()` iterates `self._actors` and the entry was
            #    already gone. Measured at +2 permanently live asyncio tasks
            #    per invocation — an unbounded leak for any server that
            #    invokes a child machine per request.
            if child_interpreter is not None:
                self._actors.pop(child_interpreter.id, None)
                if child_interpreter.status == "running":
                    await child_interpreter.stop()
