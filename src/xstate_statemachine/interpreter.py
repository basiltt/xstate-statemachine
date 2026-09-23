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
import concurrent.futures
import copy
import dataclasses
import inspect
import logging
import threading
import time
import uuid
import warnings
from collections import deque
from typing import (
    Literal,
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
    overload,
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

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .base_interpreter import AnyEvent, BaseInterpreter
from .exceptions import RunawayChainError, StateNotFoundError
import contextvars

#: 🧭 #105 / #225: "is a `send()` self-generated?" is decided by TASK
#: IDENTITY -- the sending task is one that is, right now, running one of
#: this interpreter's user actions (`Interpreter._action_tasks`). A
#: `send()` from any other task (a concurrent external producer, a helper
#: an action spawned) is user traffic even while the run loop is busy.
#: `_processing` alone could not tell those apart (#105: an external
#: producer during a slow step was charged to `maxIterations` and
#: dropped), and a ContextVar could not either (#225: `ensure_future` /
#: `create_task` COPY the context, so a helper spawned from an action
#: inherited "I am the action" for its whole life; its later `send()` was
#: routed to the internal queue, which is drained only inside a
#: macrostep, and with the loop idle the event sat there for ever).
#:
#: The ContextVar below is kept for ONE path: `send_threadsafe(
#: internal=None)` from a FOREIGN THREAD (#150). There is no asyncio task
#: on that thread, so "the thread was started with
#: `contextvars.copy_context().run(...)` from inside an action" is both
#: the only signal available and the documented opt-in. It is never
#: consulted on the loop thread.
_ACTIVE_ACTION_OWNER: (
    "contextvars.ContextVar[Optional[BaseInterpreter[Any]]]"
) = contextvars.ContextVar("xsm_active_action_owner", default=None)
from .clock import Clock, SimulatedClock
from .events import (
    AfterEvent,
    DoneEvent,
    ErrorEvent,
    Event,
    Receipt,
    _engine_after,
    _engine_done,
    _engine_error,
    is_system_event,
    system_event,
)
from .exceptions import (
    ActorSpawningError,
    ReentrantWaitError,
    ImplementationMissingError,
    InterpreterStoppedError,
    InvalidConfigError,
    QueueOverflowError,
    WrongThreadError,
)
from .models import (
    TransitionDefinition,
    DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS,
    SPAWN_BLOCKING_PREFIX,
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    OverflowPolicy,
    StateNode,
    TContext,
    spawn_service_key,
)
from .task_manager import TaskManager

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🚀 Interpreter Class Definition
# -----------------------------------------------------------------------------


class _PreStartQueue:
    """Stand-in for `Interpreter._event_queue` until `start()` binds a loop.

    🏛️ Architecture decision: events may be sent BEFORE `start()` and must
    be processed once it runs -- that is documented, tested behaviour. But
    on Python 3.9 `asyncio.Queue()` binds to the current loop at
    construction and raises when there is none, so the real queue cannot
    exist until `start()`. This buffer speaks just enough of the `Queue`
    API for the pre-start window (`put_nowait`, `put`, `qsize`, `empty`);
    `_bind_loop()` drains it into the real queue in order.
    """

    def __init__(self) -> None:
        self._items: List[AnyEvent] = []

    def put_nowait(self, item: AnyEvent) -> None:
        self._items.append(item)

    async def put(self, item: AnyEvent) -> None:
        self._items.append(item)

    def qsize(self) -> int:
        return len(self._items)

    def empty(self) -> bool:
        return not self._items

    def drain(self) -> List[AnyEvent]:
        items, self._items = self._items, []
        return items

    def peek(self) -> List[AnyEvent]:
        return list(self._items)


def _is_plain_sync_callable(fn: Any) -> bool:
    """``True`` for a callable that will return its result synchronously.

    🏛️ #116: `inspect.iscoroutinefunction` is the wrong test on its own --
    it says False for an `AsyncMock` (before 3.12), a `functools.partial`
    of a coroutine function, or any callable object whose `__call__` is a
    coroutine function -- and treating those as plain would run them
    inline and drop their awaitable. Look through the common wrappers and
    require a genuine synchronous function.
    """
    target = fn
    # unwrap functools.partial / bound methods / mock wrappers
    for _ in range(4):
        inner = (
            getattr(target, "func", None)
            or getattr(target, "__func__", None)
            or getattr(target, "__wrapped__", None)
        )
        if inner is None or inner is target:
            break
        target = inner
    if inspect.iscoroutinefunction(target) or inspect.isasyncgenfunction(
        target
    ):
        return False
    # `AsyncMock` / awaitable-returning mock objects
    if getattr(type(fn), "__module__", "").startswith("unittest.mock"):
        return False
    call = getattr(type(fn), "__call__", None)
    if call is not None and inspect.iscoroutinefunction(call):
        return False
    return (
        inspect.isfunction(target)
        or inspect.isbuiltin(target)
        or (callable(fn) and not inspect.isclass(fn))
    )


def _completed() -> "asyncio.Future[None]":
    """An already-resolved awaitable -- what `send()` hands back.

    🏛️ `send()` performs its work eagerly (see its docstring), so the object
    it returns has nothing left to do. It exists so the call is still
    ``await``-able and so `asyncio.gather(interp.send(...), ...)` continues
    to type-check and run. A resolved `Future` is used rather than a
    coroutine because an un-awaited coroutine triggers a `RuntimeWarning`
    at GC time -- the very noise #37 set out to remove -- while a resolved
    `Future` that nobody awaits is silent and correct.
    """
    fut: "asyncio.Future[None]" = asyncio.get_running_loop().create_future()
    fut.set_result(None)
    return fut


#: 🧵 #173: workers in the executor an `Interpreter` creates for plain-`def`
#: services when none is supplied. Override per instance with
#: ``Interpreter(..., service_pool_size=N)``.
DEFAULT_SERVICE_POOL_SIZE: int = 4

#: ⏳ #181: seconds `Interpreter.start()` waits for the initial configuration's
#: invoked child actors to finish their bring-up before returning with a
#: WARNING. A child's bring-up runs its entry actions -- user code -- so the
#: wait is bounded by default. Override per call: ``start(children_timeout=)``.
DEFAULT_CHILDREN_TIMEOUT: float = 2.0


class Interpreter(BaseInterpreter[TContext]):
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

    📏 Every `Interpreter` in a process shares ONE event loop on ONE thread.
    Concurrency between machines is interleaving, not parallelism, so
    throughput is a per-process budget divided among all live interpreters
    (~30k trivial events/s on a laptop; ~22 ev/s each at 1,000 machines),
    and `after` timers fire late under load. Blocking work inside an action
    stalls every machine. Measured tables and a sizing rule:
    https://basiltt.github.io/xstate-statemachine/guide/production-characteristics/

    Attributes:
        task_manager (TaskManager): An instance of `TaskManager` that tracks and
            manages all background `asyncio.Task` objects created by this
            interpreter for services and timers.
    """

    #: ⚡ How many consecutive INBOX events the run loop processes before it
    #: yields to the asyncio loop (#48 fairness for `call_later` timers and
    #: other tasks). 1 = the 0.8.0 behaviour (yield every event). Higher
    #: trades timer-lateness bound (N * per-event cost) for throughput.
    _INBOX_YIELD_EVERY: int = 16

    # ⚡ See BaseInterpreter.__slots__.
    __slots__ = (
        "_event_loop_task",
        "_inbox_streak",
        "_inline_service_futures",
        "_actor_bringups",
        "_invoked_children",
        "_loop",
        "_loop_thread_name",
        "_max_queue_size",
        "_overflow_policy",
        "_owns_service_executor",
        "_service_pool_size",
        "_priority_queue",
        "_processing",
        "_raise_depth",
        "_chain_tripped",
        "_action_tasks",
        "dropped_receipts",
        "_settle_iterations",
        "_settle_tripped",
        "_chain_owed_tasks",
        "_chain_owed_sends",
        "_armed_this_step",
        "_seed_pending",
        "_seed_internal",
        "_descent_done",
        "_receipts",
        "_replay_pending",
        "_service_executor",
        "_threadsafe_self_sends_in_flight",
        "_wakeup",
        "task_manager",
    )

    def __init__(
        self,
        machine: MachineNode[TContext],
        input: Optional[Any] = None,
        clock: Optional[Clock] = None,
        max_queue_size: Optional[int] = None,
        overflow_policy: "OverflowPolicy" = OverflowPolicy.RAISE,
        strict: Optional[bool] = None,
        service_executor: Optional[concurrent.futures.Executor] = None,
        service_pool_size: int = DEFAULT_SERVICE_POOL_SIZE,
    ) -> None:
        """Initializes a new asynchronous Interpreter instance.

        Args:
            machine: The machine to run.
            input: Creation input for a `context` factory.
            clock: Source of time (#49).
            max_queue_size: Bound on the inbox (#38). ``None`` (default)
                keeps today's unbounded queue. When set, `overflow_policy`
                decides what a full inbox does to `send()`.
            overflow_policy: ``RAISE`` (default) / ``BLOCK`` /
                ``DROP_NEWEST``; see `OverflowPolicy`. Ignored when no
                bound is set. The priority lane is never bounded: an urgent
                decision must get through a full inbox.
            service_executor: Where a PLAIN (non-coroutine) ``invoke``
                service runs (#149). ``None`` (default) lazily creates a
                small `ThreadPoolExecutor` owned by this interpreter and
                shut down with it. Pass a shared / bounded pool, or a
                `ProcessPoolExecutor` for CPU-bound work. The entering
                macrostep still awaits the result before it completes, so
                a plain service's ``done.invoke`` lands ahead of any event
                already waiting in the inbox exactly as on the sync engine
                (#116) -- but the event loop is free for the duration.
            service_pool_size: Worker count of the executor this
                interpreter creates when ``service_executor`` is ``None``
                (#173). Default ``DEFAULT_SERVICE_POOL_SIZE`` (= 4). The
                (N+1)-th concurrently-running plain service waits for a
                worker, and because the entering macrostep awaits its
                result, that wait also blocks the macrostep: size the
                pool to the number of plain services a single
                configuration can have in flight. Ignored when an
                executor is supplied.

        Args:
            machine (MachineNode[TContext]): The `MachineNode` instance
                that this interpreter will execute.
        """
        # 🏛️ Initialize the base class, passing our own class type so that
        # `from_snapshot` can create the correct `Interpreter` instance.
        super().__init__(
            machine,
            interpreter_class=Interpreter,
            input=input,
            clock=clock,
            strict=strict,
        )
        #: ⚡ #48: a fired timer is delivered here, NOT via the inbox, so it
        #: cannot queue behind 2,000 external events. Checked first by the
        #: run loop. `_timer_handles` maps owner state id -> live handles so
        #: exiting a state cancels its timers on any Clock.
        #: 🚦 #192: each item is ``(event, self_generated)``. Provenance
        #: travels WITH the event so the charge site (`_deliver_priority`)
        #: and the shed site (the run loop's chain-budget cut) read one
        #: flag; an external `send(priority=True)` can never be shed by a
        #: trip it did not cause, whatever position it holds in the FIFO.
        self._priority_queue: "deque[Tuple[AnyEvent, bool]]" = deque()
        #: 🔁 #36: the INTERNAL queue -- events this machine raised for
        #: itself mid-macrostep. Drained to completion before the next
        #: external event is taken, per SCXML. Distinct from the priority
        #: lane (timers) and the inbox (the outside world).
        self._internal_queue: "deque[AnyEvent]" = deque()
        self._timer_handles: Dict[str, List[Any]] = {}
        #: Wakes the run loop when a priority event arrives while it is
        #: blocked on the (empty) inbox.
        self._wakeup: Optional[asyncio.Event] = None
        #: ⚡ Inbox events taken since the run loop last yielded to the event
        #: loop; see `_next_event`.
        self._inbox_streak: int = 0
        #: 📏 #38: inbox bound and overflow policy.
        if max_queue_size is not None and max_queue_size < 1:
            raise InvalidConfigError("max_queue_size must be >= 1 or None")
        self._max_queue_size: Optional[int] = max_queue_size
        self._overflow_policy: OverflowPolicy = OverflowPolicy(overflow_policy)
        #: 🧵 #149: executor for plain-`def` services; `None` until first
        #: use (a machine with only coroutine services never creates one).
        self._service_executor: Optional[concurrent.futures.Executor] = (
            service_executor
        )
        self._owns_service_executor: bool = service_executor is None
        if service_pool_size < 1:
            raise ValueError("service_pool_size must be >= 1")
        self._service_pool_size: int = service_pool_size
        #: 🧵 #149: plain-service results the CURRENT macrostep must await
        #: before it completes (see `_process_event_and_transient_transitions`).
        self._inline_service_futures: List["asyncio.Future[Any]"] = []
        #: 👶 #171: invoked-child bring-up tasks the current step awaits.
        self._actor_bringups: List["asyncio.Task[Any]"] = []
        #: 🧾 #39: receipts awaiting the macrostep of a specific event,
        #: keyed by the event object's identity (events are NamedTuples and
        #: may compare equal; identity is what distinguishes two sends of
        #: "TICK"). Resolved by the run loop; failed by `_teardown`.
        self._receipts: Dict[int, "asyncio.Future[Receipt]"] = {}
        logger.info(
            "🚀 Initializing Asynchronous Interpreter for '%s'...", self.id
        )

        # 🗃️ Concurrency & Task Management
        self.task_manager: TaskManager = TaskManager()
        #: 🎭 #43: invoked child actors by owning state id. They have no
        #: manager task, so state exit stops them through this map.
        self._invoked_children: Dict[str, List["Interpreter[Any]"]] = {}
        #: The asyncio loop that owns this interpreter, bound at start().
        #: Lets send() detect a foreign-thread call instead of silently
        #: discarding the coroutine (#37).
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread_name: str = ""
        # 📬 Created lazily in `_bind_loop()`, not here.
        #
        # 🏛️ Architecture decision: on Python 3.9 `asyncio.Queue()` binds to
        #    the CURRENT event loop at construction and raises when there is
        #    none, so an `Interpreter` could only ever be built inside a
        #    running loop. Deferring the queue to `start()` lets the object be
        #    constructed anywhere (module level, a sync test, a factory) and
        #    guarantees the queue belongs to the loop that actually drives it.
        #    3.10+ removed the binding, so this is behaviour-neutral there.
        self._event_queue: "asyncio.Queue[AnyEvent]"
        self._event_queue = _PreStartQueue()  # type: ignore[assignment]
        self._event_loop_task: Optional[asyncio.Task[None]] = None
        #: Length of the current self-raised event chain. Incremented when an
        #: action enqueues onto our own queue *during* processing, reset when
        #: a macrostep completes without having done so. Bounds a runaway
        #: `raise` without ever throttling external `send()` traffic.
        self._raise_depth: int = 0
        #: 🔁 #166: per-macrostep `always`-settle budget (mirrors the sync
        #: engine's `_settle_iterations` / `_settle_tripped`, #103 / #151).
        self._settle_iterations: int = 0
        self._settle_tripped: bool = False
        #: 🔗 #179 / #200: the coroutine-service TASKS a step armed whose
        #: completion has not landed yet. Each is a debt keyed to its own
        #: task and settled by that task's done-callback on EVERY terminal
        #: outcome -- normal return, `Exception`, `CancelledError`, or any
        #: other `BaseException` (`KeyboardInterrupt`, `SystemExit`) -- so
        #: the ledger cannot leak and one invocation's completion can never
        #: settle another's debt. While non-empty the step that armed them
        #: has not finished generating; see the chain-end test in the run
        #: loop. Plain-`def` services are awaited in-step and never owe.
        self._chain_owed_tasks: "Set[asyncio.Task[Any]]" = set()
        #: ⏲️ #206: delayed self-`send`s a step of the current chain armed
        #: that have not fired yet, keyed by their clock handle. The same
        #: debt as a coroutine service (#179): the step that armed one has
        #: not finished generating, so the chain stays open, and the firing
        #: is charged as engine-generated work (see `_deliver`). Settled on
        #: fire OR cancel (state exited, `cancel(id)`, superseded id), so it
        #: cannot leak.
        self._chain_owed_sends: "Set[Any]" = set()
        #: 🔗 #179 / #200: how many coroutine-service tasks the CURRENT
        #: step armed. Read by the chain-end test: a step that armed work
        #: whose completion has not landed has not finished generating.
        #: A count of *arming*, not a size delta of the ledger -- the step
        #: that consumes completion N also lets N's done-callback pop it
        #: while arming N+1, so the ledger size is unchanged (1 -> 1) and a
        #: delta-based test wrongly ended the chain (the exact point at
        #: which the callback runs also differs between Python versions).
        self._armed_this_step: int = 0
        #: 🌱 #201: `True` between `start()` returning and the loop's first
        #: turn when the initial configuration invoked a plain-`def` service
        #: whose completion is still in flight; that completion is the seed
        #: of the machine's first chain (sync parity, #77), not a link.
        self._seed_pending: bool = False
        #: 🌱 #215: how many internal-queue items the initial descent left
        #: behind; each is processed with SEED standing (the sync drain's
        #: `seed_internal`, #77), so the chain count starts at their first
        #: descendant and both engines cut an entry-raise cycle at the same
        #: lap.
        self._seed_internal: int = 0
        #: 🚦 #215: set by `start()` once the initial descent has settled.
        #: The run loop is spawned BEFORE the descent (so the machine is
        #: live during it) but must not consume the descent's own raises
        #: while it is still running -- an `async def` entry action yields,
        #: and the loop took the queued `raise` mid-descent, interleaving
        #: two macrosteps. The sync engine's re-entrancy guard forbids the
        #: same interleaving.
        self._descent_done: Optional["asyncio.Event"] = None
        #: 🛟 #168: set when the chain budget trips; spares exactly one
        #: pending engine completion at the trip, then cuts every further
        #: self-generated event until an external event ends the chain.
        self._chain_tripped: bool = False
        #: 🧭 #105 / #225: the asyncio tasks currently running one of THIS
        #: interpreter's user actions, with a nesting depth each. The single
        #: source of truth for "is this `send()` self-generated?" and for
        #: the #219 in-step-await guard. Keyed by task identity, not by an
        #: inherited context: a task an action spawns runs concurrently with
        #: it (or outlives it) and is NOT the action.
        self._action_tasks: Dict["asyncio.Task[Any]", int] = {}
        #: 🔢 #244: how many `send(wait=True)` receipts issued from inside
        #: an action were dropped without ever being awaited or handed out.
        #: The #232 RuntimeWarning fires from a finaliser, which CPython
        #: routes to `sys.unraisablehook` -- invisible to `-W error` and to
        #: `pytest.warns`. This counter (and `on_receipt_dropped`) is the
        #: deterministic, gateable signal: assert it is 0 after a step.
        self.dropped_receipts: int = 0
        #: 🔗 #150: self-issued `send_threadsafe` deliveries accepted on a
        #: worker thread but not yet landed on the loop. A macrostep that
        #: "raised nothing" must not end the chain while one is in flight.
        self._threadsafe_self_sends_in_flight: int = 0
        #: 📨 #125: set when a step changed the configuration while events
        #: were deferred; the run loop replays them as separate macrosteps.
        self._replay_pending: bool = False
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

    async def start(
        self, *, children_timeout: Optional[float] = DEFAULT_CHILDREN_TIMEOUT
    ) -> "Interpreter[TContext]":
        """Starts the interpreter and its main event-processing loop.

        This method initializes the machine by transitioning it to its initial
        state and begins the main event loop to process events from the queue.
        It is idempotent; calling `start` on an already running or stopped
        interpreter has no effect and will simply return.

        Args:
            children_timeout: Upper bound, in seconds, on how long
                ``start()`` waits for the initial configuration's invoked
                child actors to finish their own bring-up (#171 / #181).
                A child's bring-up runs its entry actions, which are
                arbitrary user code; without a bound a slow ``async def``
                entry action held ``await start()`` for its whole
                duration while ``status`` already read ``"running"``.
                Default ``DEFAULT_CHILDREN_TIMEOUT`` (2 s); ``None`` waits
                without bound. The allowance is PER CHILD (#194): N
                children each awaiting D seconds settle in ~D. On timeout
                a WARNING is logged and ``start()`` returns with the
                interpreter running and the child still starting; the
                child is already registered and addressable, and finishes
                its bring-up on its own. What the bound CANNOT do is
                pre-empt a plain-``def`` entry action that never yields:
                such an action holds the event-loop thread until it
                returns (the cooperative-concurrency rule that applies to
                every action in the process), so ``start()`` returns when
                it does -- and the WARNING still reports the overrun.

        Returns:
            Interpreter[TContext]: The interpreter instance (`self`),
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
            self._notify_interpreter_start()  # #240: balanced with stop()
            if self.status == "running":
                self._bind_loop()
                self._event_loop_task = self._spawn_run_loop()
                # ⏲️ #213: re-arm delayed self-sends with their remaining
                #    delay -- unconditional, unlike `after` timers (#128):
                #    the snapshot recorded exactly how long was left.
                self._rearm_restored_self_sends()
                # 🔁 #44: opt-in re-drive of invokes the snapshot left parked.
                if self._restart_services_on_start:
                    self._restart_services_on_start = False
                    self._restart_dormant_invocations()
                # ⏱️ #128: opt-in re-arm of `after` timers, from zero.
                if self._restart_timers_on_start:
                    self._restart_timers_on_start = False
                    armed = self._rearm_dormant_timers()
                    if armed:
                        logger.info(
                            "⏱️ Re-armed %d dormant 'after' timer state(s) "
                            "on restored interpreter '%s'.",
                            armed,
                            self.id,
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
        self._bind_loop()
        self._descent_done = asyncio.Event()  # #215: loop waits on this
        self._event_loop_task = self._spawn_run_loop()

        try:
            # 🛡️ #182 / #199: the initial descent IS a macrostep -- entry
            #    actions run, context is written -- and the mid-step
            #    snapshot refusal (#102/#169) keys on `_processing`.
            #    Raised BEFORE `on_interpreter_start` fires (#199): that
            #    hook runs with `status="running"` and an EMPTY
            #    configuration, so a snapshot taken from it was the exact
            #    torn shape #182 closed for entry actions. Cleared in the
            #    `finally` below so a failing entry action never leaves it
            #    stuck.
            self._processing = True

            # 🔔 Notify plugins that the interpreter is starting.
            self._notify_interpreter_start()

            # 🚀 Enter the initial state(s) of the machine.
            # We use a synthetic init event to allow any entry actions on the
            # root state to execute.
            init_event = system_event("___xstate_statemachine_init___")
            pre_states = set(self._active_state_nodes)
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
            # 👶 #171: `start()` means "the machine is up": the children
            #    its initial configuration invoked are registered and
            #    addressable, as after `SyncInterpreter.start()`. That was
            #    left to the FIRST event's macrostep, so `await start();
            #    send("POKE")` lost the poke to `unresolved_target` on the
            #    async engine only. A plain-`def` service's RESULT is not
            #    awaited here: #149 requires `start()` to return while it
            #    runs; its `done.invoke` lands through the priority lane.
            await self._await_actor_bringups(timeout=children_timeout)
            # ✅ Settled: the initial macrostep is complete and observable.
            self._processing = False
            # 🔗 Raises AND completions the INITIAL descent queued were
            #    counted while the flag was up, but they are the seed of the
            #    machine's first chain, not its self-generated tail: the
            #    sync drain gives events already queued when it opens "user
            #    standing" so the count starts at their FIRST descendant
            #    (#77). Match it exactly -- including a plain-`def`
            #    service's `done.invoke` already sitting in the priority
            #    lane (#201) -- or the async engine cuts a chain that starts
            #    from the initial state one link early (22 vs 23 laps).
            self._raise_depth = 0
            self._priority_queue = deque(
                (ev, False) for ev, _ in self._priority_queue
            )
            # 🔁 #215: the descent's own `always` settle work belongs to the
            #    descent. On the sync engine the drain that `start()` opens
            #    resets the settle budget before it processes the raises the
            #    descent queued; give the first chain the same clean budget.
            self._settle_iterations = 0
            self._settle_tripped = False
            # 🌱 A `raise` the descent queued is likewise the seed (#77):
            #    the internal queue's items get the standing of events
            #    "already queued when the drain opens".
            self._seed_internal = len(self._internal_queue)
            # A service the initial configuration invoked -- plain `def`
            # (still running, #149) or `async def` (its own task) -- has
            # not completed yet; its completion lands on a later loop turn
            # and is likewise the seed, not a link. The run loop gives the
            # first such completion seed standing once (`_seed_pending`).
            self._seed_pending = bool(
                self._inline_service_futures or self._chain_owed_tasks
            )

            # 🔌 #124: the sync engine reports entering the initial
            #    configuration as an `on_transition` record for the init
            #    event; a hook-based audit trace from the two engines had one
            #    record fewer here and misaligned at index 0. Emit the same
            #    record with the same shape.
            init_transition = TransitionDefinition(
                event="___xstate_statemachine_init___",
                config={},
                source=self.machine,
            )
            for plugin in self._plugins:
                plugin.on_transition(
                    self,
                    pre_states,
                    set(self._active_state_nodes),
                    init_transition,
                )
            self._descent_done.set()  # #215: the loop may now consume

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
        finally:
            self._processing = False  # #182: never left stuck by a raise
            if self._descent_done is not None:
                self._descent_done.set()  # never leave the loop parked

        return self

    async def stop(
        self, *, drain: bool = False, timeout: Optional[float] = None
    ) -> None:
        """Stops the interpreter, cleaning up all tasks and spawned actors.

        This method gracefully shuts down the event loop, cancels all running
        background tasks (timers, services), and recursively stops any child
        actors that were spawned by this interpreter. It is idempotent.

        Args:
            drain: When `True`, process every event already accepted by
                `send()` before tearing down, so nothing the caller was
                told "yes" to is discarded (#47). Default `False` keeps
                0.7.x semantics, but a non-empty inbox is now logged.
            timeout: Upper bound in seconds for the drain; `None` waits
                until the inbox is empty.
        """
        # 🛡️ Idempotency check.
        if self.status in ("uninitialized", "stopped"):
            logger.warning(
                "⚠️ Interpreter '%s' is not running. Skipping stop.", self.id
            )
            return
        # 🏁 #57: a terminal machine has already reaped itself (or has a
        #    teardown task in flight). `stop()` is then a quiet no-op that
        #    leaves `status` as "done"/"error" so `output`/`error` stay
        #    meaningful.
        if self.status in ("done", "error"):
            await self._teardown()
            return

        if drain and self.status == "running":
            await self._drain_inbox(timeout)
            # 🏁 A drained event may have completed the machine (review F5).
            #    That is a `done`, not a `stopped`: keep the terminal status
            #    and let the reaping path (already scheduled) finish.
            if self.status in ("done", "error"):
                await self._teardown()
                return
        pending = self._event_queue.qsize()
        if pending:
            logger.warning(
                "📬 Interpreter '%s' stopping with %d pending event(s) that "
                "will NOT be processed. Use stop(drain=True) to finish them, "
                "or read `pending_events` / `get_snapshot()` to persist them.",
                self.id,
                pending,
            )
        # 🔔 #129: every other loss site fires `on_event_dropped`; `stop()`
        #    was the exception. Each accepted-but-unprocessed event (inbox,
        #    priority lane, internal queue) is reported with reason
        #    "stopped", and any receipt attached to it is failed so no
        #    awaiter hangs. Producers parked in `_enqueue_blocking` observe
        #    the status flip on their next spin and fail their own receipt.
        for ev in self._snapshot_pending_events():
            for plugin in self._plugins:
                plugin.on_event_dropped(self, ev, "stopped")
            self._fail_receipt(ev, "dropped: interpreter stopped")

        logger.info("🛑 Gracefully stopping interpreter '%s'...", self.id)
        self.status = "stopped"

        # 🔔 Notify plugins of the impending shutdown.
        for plugin in self._plugins:
            plugin.on_interpreter_stop(self)

        # 🧹 Children, tasks, registry entry, run loop -- one shared path.
        await self._teardown()
        logger.info("✅ Interpreter '%s' stopped successfully.", self.id)

    # 🧷 Overloads: `wait=True` -> Awaitable[Receipt]; otherwise
    #    Awaitable[None]. Both keyword flags are spelled out so a checker
    #    rejects `wait="yes"` / `priority="high"` instead of swallowing
    #    them into `**payload`, and so `r = await send(..., wait=True)`
    #    is a Receipt (it typed as None before, making `r.error` an error).
    @overload
    def send(  # noqa: E704
        self,
        event_type: str,
        /,
        *,
        wait: Literal[True],
        priority: bool = ...,
        **payload: Any,
    ) -> Awaitable[Receipt]: ...

    @overload
    def send(  # noqa: E704
        self,
        event_type: str,
        /,
        *,
        wait: Literal[False] = ...,
        priority: bool = ...,
        **payload: Any,
    ) -> Awaitable[None]: ...

    @overload
    def send(  # noqa: E704
        self,
        event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent],
        /,
        *,
        wait: Literal[True],
        priority: bool = ...,
        **payload: Any,
    ) -> Awaitable[Receipt]: ...

    @overload
    def send(  # noqa: E704
        self,
        event: Union[Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent],
        /,
        *,
        wait: Literal[False] = ...,
        priority: bool = ...,
        **payload: Any,
    ) -> Awaitable[None]: ...

    @overload
    def send(  # noqa: E704
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: bool = ...,
        priority: bool = ...,
        **payload: Any,
    ) -> Awaitable[Optional[Receipt]]: ...

    def send(  # type: ignore[override, misc]
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: bool = False,
        priority: bool = False,
        **payload: Any,
    ) -> "Awaitable[Optional[Receipt]]":
        """Sends an event to the machine's internal queue for processing.

        This is the primary method for interacting with a running state machine.
        It provides a flexible API, accepting either a string type with keyword
        arguments for the payload, a dictionary, or a pre-constructed `Event`
        object. Await the result: ``await interp.send("GO")``.

        🏛️ Architecture decision (#37): this is a *regular* method that
        returns an awaitable, not an ``async def``. An ``async def`` body
        runs only when awaited -- so a call from a foreign thread (which
        cannot await it) executed NOTHING: not the status guard, not the
        queue put. The coroutine was discarded and every event silently
        lost, with only a GC-timed RuntimeWarning the library did not own.

        ALL of the work -- thread check, normalisation, status guard and
        the queue put -- therefore happens eagerly, before anything is
        awaited. The queue is unbounded so ``put_nowait`` never blocks, and
        the returned awaitable exists purely so ``await interp.send(...)``
        keeps working unchanged. Consequences: a wrong-thread call raises
        AT THE CALL SITE, and a fire-and-forget ``interp.send("GO")`` from
        inside the loop is delivered rather than silently dropped.

        Event shapes and what is validated (#113 / #161): a ``str`` is the
        type; a ``dict`` must carry a non-empty ``str`` ``"type"`` and every
        other key must be a ``str`` (those become the payload; their VALUES
        are not inspected -- payload semantics are domain-specific and belong
        to ``event_schemas``); an `Event` / `DoneEvent` / `AfterEvent` /
        `ErrorEvent` is passed through. Anything else raises
        `InvalidEventError` (also a `TypeError`), and `on_invalid_event`
        fires first (#159).

        Args:
            event_or_type: The event to send. Can be an event type string,
                a dictionary (e.g., `{"type": "MY_EVENT", "value": 42}`),
                or an `Event`, `DoneEvent`, or `AfterEvent` object.
            **payload: Keyword arguments that become the event's payload if
                `event_or_type` is a string.

            wait: (#39) When ``True``, the returned awaitable resolves to a
                :class:`Receipt` only AFTER the macrostep caused by this
                event has run to completion -- state, whether anything
                changed, and any error. Default ``False`` resolves
                immediately to ``None``, exactly as before.
            priority: (#39) When ``True``, the event goes to the head of
                processing, ahead of every already-queued external event
                (FIFO among priority events) and exempt from
                ``max_queue_size``. Use for decisions that must not wait
                behind routine traffic; it REORDERS events relative to
                non-priority sends.

        Raises:
            WrongThreadError: Called from a thread other than the one whose
                event loop owns this interpreter. Use
                :meth:`send_threadsafe` from other threads.
            QueueOverflowError: The inbox is bounded, full, and the policy
                is ``RAISE`` (#38).
        """
        self._assert_owning_thread("send")
        # 📦 Normalise eagerly so a malformed event also fails at the call site.
        event_obj = self._prepare_event_reporting(event_or_type, **payload)
        self._warn_reserved_payload_keys(event_obj)
        self._check_strict(event_obj)  # #51: at the call site, pre-queue
        if wait and event_obj is event_or_type:
            # 🧾 #75: the caller handed us its own object; give the queued
            #    envelope a distinct identity so a reused instance cannot
            #    collide in the receipt map.
            event_obj = self._detach(event_obj)
        receipt = self._make_receipt(event_obj) if wait else None
        if receipt is not None and self._issued_from_own_action():
            # 🔒 #219: an action that AWAITS a receipt on its own interpreter
            #    deadlocks by construction -- the receipt resolves when the
            #    run loop processes the event, and the loop cannot advance
            #    until this action returns (mid-run; and from `start()` too
            #    since the #215 descent gate). Handing the receipt out is
            #    fine (`asyncio.ensure_future(i.send(..., wait=True))` and
            #    awaiting it LATER is a supported shape, #27); awaiting it
            #    inside the step is the hang. Wrap it so the in-step await
            #    raises `ReentrantWaitError` instead of parking for ever.
            receipt = self._guard_reentrant_await(receipt, event_obj.type)
        if priority:
            # 🚦 #192: the priority lane asks the SAME provenance question
            #    the inbox lane asks (#90): a `send(priority=True)` issued
            #    from one of this interpreter's own actions is self-
            #    generated work, charged to `maxIterations` and shed with
            #    the chain; one from outside is external and never is.
            if not self._refuse_if_not_running(event_obj):
                self._deliver_priority(
                    event_obj,
                    engine_completion=self._issued_from_own_action(),
                )
        elif self._overflow_policy is OverflowPolicy.BLOCK and (
            self._max_queue_size is not None
        ):
            # 🔒 #38 (0.8.0 audit): a BLOCK send issued FROM AN ACTION runs
            #    on the run-loop task itself. The run loop is the only
            #    thing that ever drains the inbox, so suspending it in
            #    `_enqueue_blocking` until the inbox has room is a
            #    self-deadlock: `status` stays "running" while nothing
            #    advances. A self-send during a macrostep is, semantically,
            #    an internal event (#36) -- route it there. The internal
            #    queue is unbounded by design and drained before the next
            #    external event, so ordering matches SCXML `raise`.
            if (
                self._issued_from_own_action()
                and not self._refuse_if_not_running(event_obj)
            ):
                self._raise_depth += 1
                self._internal_queue.append(event_obj)
                return receipt if receipt is not None else _completed()
            # ⏸️ BLOCK must genuinely await ONLY when the inbox is full.
            #    #104: returning the un-started coroutine unconditionally
            #    meant a fire-and-forget `interp.send("GO")` under BLOCK
            #    never ran its put -- the event vanished with no hook and no
            #    log, even on an EMPTY inbox. Enqueue eagerly when there is
            #    room, exactly like the other two policies; fall back to the
            #    awaiting path only when we would actually have to wait.
            if self._refuse_if_not_running(event_obj):
                # Refused: the receipt (if any) was failed by the refusal.
                return receipt if receipt is not None else _completed()
            if not self._inbox_is_full():
                self._put_inbox(event_obj)
                return receipt if receipt is not None else _completed()
            return self._enqueue_blocking(event_obj, receipt)
        else:
            # 🏛️ #90: a `send()` issued FROM AN ACTION on this interpreter is
            #    self-generated work, exactly like `raise`. It used to bypass
            #    the chain budget entirely (only BLOCK-policy self-sends were
            #    routed internally), so `async def act(i,...): await
            #    i.send(...)` spun unbounded while the sync engine stopped at
            #    the limit. Route it to the internal queue and count it.
            if (
                self._issued_from_own_action()
                and not self._refuse_if_not_running(event_obj)
            ):
                self._raise_depth += 1
                self._internal_queue.append(event_obj)
                return receipt if receipt is not None else _completed()
            self._enqueue(event_obj)
        return receipt if receipt is not None else _completed()

    @overload
    def send_priority(  # noqa: E704
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: Literal[True] = ...,
        **payload: Any,
    ) -> Awaitable[Receipt]: ...

    @overload
    def send_priority(  # noqa: E704
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: Literal[False],
        **payload: Any,
    ) -> Awaitable[None]: ...

    def send_priority(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        /,
        *,
        wait: bool = True,
        **payload: Any,
    ) -> "Awaitable[Optional[Receipt]]":
        """``send(..., priority=True, wait=True)`` -- ask an urgent question.

        The discoverable spelling of the two `send()` options that together
        give a bounded-latency decision under any backlog (#39)::

            receipt = await interp.send_priority("CHECK", order_id=oid)
            if "risk.halted" in receipt.state_ids:
                ...

        `wait` defaults to ``True`` here because a priority send is almost
        always a question that needs its answer; pass ``wait=False`` for a
        fire-and-forget event that merely jumps the queue.
        """
        # 🧭 `send` is overloaded on the event's TYPE; mypy resolves this
        #    forwarding call against the first (str) overload. Runtime
        #    dispatch is by value, so the cast only silences the checker.
        if wait:
            return self.send(
                cast(str, event_or_type), wait=True, priority=True, **payload
            )
        return self.send(
            cast(str, event_or_type), wait=False, priority=True, **payload
        )

    # -------------------------------------------------------------------------
    # 🧾 Receipts (#39) and inbox bound (#38)
    # -------------------------------------------------------------------------
    @staticmethod
    def _detach(event_obj: Any) -> Any:
        """Return an equal-but-distinct copy of *event_obj* (#75).

        Receipts are keyed on the identity of the QUEUED envelope. If the
        caller passes one pre-built `Event` instance to two concurrent
        ``send(ev, wait=True)`` calls, keying on the caller's object makes
        the second receipt overwrite the first, which then hangs forever.
        Copying at the boundary means caller-side reuse is irrelevant by
        construction: every queued envelope has its own identity for as
        long as it is in flight, because the receipt map holds it.
        """
        if isinstance(event_obj, Event):
            # 🏷️ #111: `dataclasses.replace` re-runs `__init__`, which cannot
            #    carry the `init=False` provenance slot -- so an engine event
            #    sent with `wait=True` silently became user traffic and
            #    failed an `onUnhandled: "error"` machine. Copy the marker.
            fresh = dataclasses.replace(event_obj)
            object.__setattr__(fresh, "_provenance", event_obj._provenance)
            return fresh
        replace = getattr(event_obj, "_replace", None)  # NamedTuple events
        return replace() if callable(replace) else copy.copy(event_obj)

    def _guard_reentrant_await(
        self, receipt: "asyncio.Future[Receipt]", event_type: str
    ) -> "asyncio.Future[Receipt]":
        """#219: a receipt issued from inside one of THIS interpreter's
        actions, made safe to hand out but fatal to await in-step.

        The returned future resolves exactly as the original does. If it is
        awaited by the task that is running the issuing action, before the
        run loop has processed the event, it raises `ReentrantWaitError`
        at once instead of hanging. Awaiting it from any other task, or
        after the action returned, behaves normally.

        🧭 #225: the predicate is TASK IDENTITY. Only an await performed
        BY the task that is running one of our actions cannot make
        progress, so the guard asks `_issued_from_own_action()` again at
        await time. Both documented hand-out shapes -- a worker that
        outlives its action, and `ensure_future(i.send(..., wait=True))`
        whether or not the action awaits again afterwards -- run on a
        different task and are admitted. (A ContextVar could not do this:
        `ensure_future` copies the context, so the spawned task looked
        like the action for its whole life.)
        """
        loop = asyncio.get_running_loop()
        guarded: "asyncio.Future[Receipt]" = loop.create_future()

        def _forward(src: "asyncio.Future[Receipt]") -> None:
            if guarded.done():
                return
            if src.cancelled():
                guarded.cancel()
            elif src.exception() is not None:
                guarded.set_exception(src.exception())  # type: ignore[arg-type]
            else:
                guarded.set_result(src.result())

        receipt.add_done_callback(_forward)
        machine_id = self.id

        class _PendingReceipt:
            """The awaitable `send(wait=True)` hands an action (#219).

            🔔 #232: like a coroutine, it warns if it is finalised without
            ever being awaited or otherwise used. A plain `def` action has
            no `await`; one that wrote ``r = i.send("B", wait=True)``
            expecting a `Receipt` got this object back and nothing ever
            told it so -- the call was silently useless. Any use counts
            (`await`, `asyncio.ensure_future(...)`, `.add_done_callback`,
            `.result()`), so the documented hand-out shapes stay quiet;
            only an object dropped on the floor is reported.
            """

            __slots__ = ("_used",)

            def __init__(inner) -> None:  # noqa: N805
                inner._used = False

            def __await__(inner) -> Any:  # noqa: N805
                inner._used = True
                # 🔒 #225: refuse only if THIS task is running our action.
                if not receipt.done() and self._issued_from_own_action():
                    raise ReentrantWaitError(machine_id, event_type)
                return guarded.__await__()

            def __getattr__(inner, name: str) -> Any:  # noqa: N805
                object.__setattr__(inner, "_used", True)
                return getattr(guarded, name)

            def __del__(inner) -> None:  # noqa: N805
                if inner._used:
                    return
                # 🔢 #244: count and notify BEFORE warning, so the signal
                #    exists even where the warning is unobservable.
                self.dropped_receipts += 1
                for plugin in self._plugins:
                    plugin.on_receipt_dropped(self, event_type)
                warnings.warn(
                    f"send('{event_type}', wait=True) on '{machine_id}' "
                    f"was called from inside an action and its receipt was "
                    f"never awaited (#232). A plain `def` action cannot "
                    f"await, so it received this awaitable, not a Receipt. "
                    f"Send without wait=True, or hand the awaitable out "
                    f"(asyncio.ensure_future(...)) to be awaited elsewhere.",
                    RuntimeWarning,
                    stacklevel=2,
                )

        return _PendingReceipt()  # type: ignore[return-value]

    def _make_receipt(self, event_obj: Any) -> "asyncio.Future[Receipt]":
        loop = asyncio.get_running_loop()
        fut: "asyncio.Future[Receipt]" = loop.create_future()
        self._receipts[id(event_obj)] = fut
        return fut

    def _resolve_receipt(
        self,
        event_obj: Any,
        changed: bool,
        error: Optional[BaseException],
        deferred: bool = False,
        denied: bool = False,
    ) -> None:
        fut = self._receipts.pop(id(event_obj), None)
        if fut is not None and not fut.done():
            fut.set_result(
                Receipt(
                    frozenset(self.current_state_ids),
                    changed,
                    error,
                    deferred,
                    denied,
                )
            )

    def _fail_receipt(self, event_obj: Any, message: str) -> None:
        fut = self._receipts.pop(id(event_obj), None)
        if fut is not None and not fut.done():
            fut.set_result(
                Receipt(
                    frozenset(self.current_state_ids),
                    False,
                    InterpreterStoppedError(message),
                )
            )

    def _on_internal_events_withdrawn(self, events: List[Any]) -> None:
        """#27 rollback withdrew self-queued events: keep the books straight.

        * Each was counted into `_raise_depth` when queued; un-count it, or
          rollbacks would accumulate into a false runaway trip that drops
          an unrelated external event.
        * A `BLOCK`-policy `send(..., wait=True)` issued from an action is
          routed to the internal queue too. Its receipt must resolve, not
          hang: report the rollback the same way a receipt on the failing
          event itself does.
        """
        self._raise_depth = max(0, self._raise_depth - len(events))
        for ev in events:
            fut = self._receipts.pop(id(ev), None)
            if fut is not None and not fut.done():
                fut.set_result(
                    Receipt(
                        frozenset(self.current_state_ids),
                        False,
                        self._last_action_error
                        or RuntimeError("withdrawn by transition rollback"),
                    )
                )

    def _fail_all_receipts(self) -> None:
        """`_teardown`: nobody awaiting a receipt may hang on shutdown."""
        for key in list(self._receipts):
            fut = self._receipts.pop(key)
            if not fut.done():
                fut.set_result(
                    Receipt(
                        frozenset(self.current_state_ids),
                        False,
                        InterpreterStoppedError(
                            f"Interpreter '{self.id}' stopped before the "
                            f"event was processed."
                        ),
                    )
                )

    def _refuse_if_not_running(self, event_obj: Any) -> bool:
        """Drop + report an event sent to a stopped/done/errored machine.

        Returns ``True`` if the event was refused.
        """
        if self.status not in ("stopped", "done", "error"):
            return False
        logger.warning(
            "⚠️ Interpreter '%s' is %s; dropping event '%s'. Nothing drains "
            "the queue after shutdown, so queuing here would leak.",
            self.id,
            self.status,
            event_obj.type,
        )
        for plugin in self._plugins:
            plugin.on_event_dropped(self, event_obj, "not_running")
        self._fail_receipt(
            event_obj,
            f"Interpreter '{self.id}' is {self.status}; event "
            f"'{event_obj.type}' was dropped.",
        )
        return True

    def _inbox_is_full(self) -> bool:
        return (
            self._max_queue_size is not None
            and self._event_queue.qsize() >= self._max_queue_size
        )

    async def _enqueue_blocking(
        self, event_obj: Any, receipt: "Optional[asyncio.Future[Receipt]]"
    ) -> Optional[Receipt]:
        """`OverflowPolicy.BLOCK`: suspend the producer until there is room."""
        if self._refuse_if_not_running(event_obj):
            return await receipt if receipt is not None else None
        while self._inbox_is_full():
            if self.status != "running":
                # 🔔 #129: a producer parked on a full inbox when the machine
                #    stopped never delivered its event -- that is a drop and
                #    fires the hook like every other one. Its receipt (if
                #    any) is failed; a fire-and-forget caller gets the hook.
                for plugin in self._plugins:
                    plugin.on_event_dropped(self, event_obj, "stopped")
                self._fail_receipt(
                    event_obj, "stopped while blocked on a full inbox"
                )
                return await receipt if receipt is not None else None
            await asyncio.sleep(0)
        self._put_inbox(event_obj)
        return await receipt if receipt is not None else None

    def _enqueue(self, event_obj: AnyEvent) -> None:
        """Put *event_obj* on the queue, or drop it if the machine is over.

        Synchronous on purpose: see :meth:`send`. Must run on the owning
        loop's thread (``asyncio.Queue`` is not thread-safe); callers on
        other threads go through :meth:`send_threadsafe`.
        """
        # 🚪 Refuse events once the machine is no longer processing. Nothing
        #    drains the queue after `stop()`, so every `send()` accumulated
        #    forever — a slow memory leak in any long-lived process that keeps
        #    a reference to a finished machine. Dropping with a warning also
        #    surfaces the mistake instead of hiding it.
        if self._refuse_if_not_running(event_obj):
            return
        # 📏 #38: bounded inbox. RAISE and DROP_NEWEST are decided here,
        #    synchronously; BLOCK is handled by `_enqueue_blocking`.
        if self._inbox_is_full():
            depth = self._event_queue.qsize()
            if self._overflow_policy is OverflowPolicy.DROP_NEWEST:
                logger.warning(
                    "📉 Interpreter '%s' inbox full (%d/%d); event '%s' "
                    "dropped (OverflowPolicy.DROP_NEWEST).",
                    self.id,
                    depth,
                    self._max_queue_size,
                    event_obj.type,
                )
                for plugin in self._plugins:
                    plugin.on_event_dropped(self, event_obj, "queue_full")
                self._fail_receipt(event_obj, "dropped: inbox full")
                return
            self._fail_receipt(event_obj, "refused: inbox full")
            raise QueueOverflowError(self.id, depth, self._max_queue_size or 0)
        # 📥 Place the standardized event object into the async queue.
        self._put_inbox(event_obj)

    def _enqueue_from_thread(self, event_obj: AnyEvent) -> None:
        """`_enqueue` for a cross-thread send (#157): a refusal is OBSERVABLE.

        On the loop thread a `RAISE` refusal reaches the caller as an
        exception -- the exception *is* the signal. From `send_threadsafe`
        it lands on a `concurrent.futures.Future` the documented
        fire-and-forget pattern never reads, so under load a producer could
        shed the majority of its sends with no warning, no hook and no
        unretrieved-exception traceback: correct load shedding with a
        hidden shed rate. The future still carries the error for callers
        who do read it; this adds a WARNING and `on_event_dropped(reason=
        "queue_full")` so the shed is measurable either way.
        """
        try:
            self._enqueue(event_obj)
        except QueueOverflowError:
            logger.warning(
                "📉 Interpreter '%s' inbox full (%d/%d); cross-thread event "
                "'%s' refused (OverflowPolicy.RAISE). The error is on the "
                "future send_threadsafe() returned.",
                self.id,
                self._event_queue.qsize(),
                self._max_queue_size,
                event_obj.type,
            )
            for plugin in self._plugins:
                plugin.on_event_dropped(self, event_obj, "queue_full")
            raise

    def send_threadsafe(
        self,
        event_or_type: Union[
            str, Dict[str, Any], Event, DoneEvent, AfterEvent, ErrorEvent
        ],
        internal: Optional[bool] = None,
        **payload: Any,
    ) -> "concurrent.futures.Future[None]":
        """Send an event from ANY thread.

        Routes the enqueue through the interpreter's owning event loop via
        ``run_coroutine_threadsafe``, because ``asyncio.Queue`` is not
        thread-safe. Returns a ``concurrent.futures.Future`` the caller may
        ``.result()`` on to block until the event is queued (not processed).

        Raises:
            RuntimeError: The interpreter has not been started, or the loop
                that owned it has since been closed.
            UnknownEventError: `strict` and the type is undeclared (#78).
                Raised on the calling thread, before anything is queued.
            InvalidEventPayloadError: a registered `event_schemas` validator
                rejected the payload (#78). Same guardrail as `send()`.
            QueueOverflowError: the inbox is bounded, full, and the policy
                is ``RAISE`` -- raised **on the calling thread** (#157), so
                a fire-and-forget producer sees backpressure at the call
                site rather than on a future it never reads. Evaluated
                against the inbox depth visible from the caller's thread;
                a concurrent producer may still be refused on the loop, in
                which case the returned future carries the error.

        Args:
            internal: Charge this send to the machine's ``maxIterations``
                chain budget as a self-send (#150). ``None`` (default)
                decides by context: a call made from inside one of this
                interpreter's own actions, or from a thread/executor that
                inherited that action's ``contextvars`` context, is
                internal. A plain ``threading.Thread`` does NOT inherit
                the context (before 3.14, and on 3.14 unless
                ``thread_inherit_context`` is on) -- an action that hands
                its own re-trigger to one must pass ``internal=True``, or
                start the thread with ``contextvars.copy_context().run``.
                ``False`` forces external accounting.
        """
        if self._loop is None:
            raise RuntimeError(
                f"Interpreter '{self.id}' has not been started; there is no "
                f"event loop to hand the event to."
            )
        if self._loop.is_closed():
            raise RuntimeError(
                f"Interpreter '{self.id}' was bound to an event loop that "
                f"has been closed; it can no longer accept events."
            )
        event_obj = self._prepare_event_reporting(event_or_type, **payload)
        # 🛡️ #78: the SAME guardrail as `send()`, on the calling thread. It
        #    reads only immutable machine data, so it is safe off-loop, and
        #    raising here -- not inside the returned future -- is what a
        #    foreign-thread caller can actually act on. Without this the
        #    recommended cross-thread path was the one without validation.
        self._check_strict(event_obj)
        # 🔗 #150: decide "self-send or external" on the CALLING thread,
        #    where the action's context (if inherited) is visible, and carry
        #    the answer to the loop. Deciding on the loop always read the
        #    loop task's own context and classified every threadsafe send
        #    as external.
        self_issued = (
            self._issued_from_own_action() if internal is None else internal
        )
        # 🚦 #157: backpressure at the CALL SITE. `qsize()` is a plain read
        #    that is safe from any thread; if the inbox is already full and
        #    the policy is RAISE, refuse here rather than on a future the
        #    documented fire-and-forget pattern never inspects. Self-issued
        #    sends go to the internal queue, which is never bounded.
        if (
            not self_issued
            and self._overflow_policy is OverflowPolicy.RAISE
            and self._inbox_is_full()
        ):
            raise QueueOverflowError(
                self.id, self._event_queue.qsize(), self._max_queue_size or 0
            )

        if self_issued:
            # Counted at ISSUE time, on this thread: the loop may finish
            # the issuing action's macrostep before `_deliver` runs, and
            # must not conclude the chain has ended.
            self._threadsafe_self_sends_in_flight += 1

        async def _deliver() -> None:
            if self_issued:
                if not self._refuse_if_not_running(event_obj):
                    self._raise_depth += 1
                    self._internal_queue.append(event_obj)
                    if self._wakeup is not None:
                        self._wakeup.set()
                return
            self._enqueue_from_thread(event_obj)

        fut = asyncio.run_coroutine_threadsafe(_deliver(), self._loop)
        if self_issued:
            # 🧮 #172: balance the increment on EVERY terminal outcome --
            #    delivered, refused, cancelled, loop stopped before the
            #    coroutine ran. Decrementing inside `_deliver` leaked one
            #    per send that never ran, and the leaked count gated the
            #    `_raise_depth` reset for the rest of the machine's life.
            fut.add_done_callback(self._threadsafe_self_send_settled)
        return fut

    def _arm_restored_self_send(
        self, event: Any, delay_ms: float, send_id: Optional[str]
    ) -> None:
        """#213: schedule a restored delayed self-send on this loop.

        Runs the same `_deliver` a live `raise(delay=)` uses. `_processing`
        is raised for the call so the send keeps its self-generated standing
        (#206): it was armed by one of this machine's own actions before
        the snapshot, and restoring does not change who produced it.
        """
        was = self._processing
        self._processing = True
        try:
            # `_deliver`'s delayed branch arms the clock synchronously (no
            # await before `_set_timeout`), so driving the coroutine one
            # step here arms it NOW, under the raised flag -- a task would
            # run after the flag is lowered and lose the standing.
            coro = self._deliver(self, event, delay_ms, send_id)
            try:
                coro.send(None)
            except StopIteration:
                pass
            else:  # pragma: no cover -- the delayed branch never awaits
                self._loop_create_task(coro)
        finally:
            self._processing = was

    def _threadsafe_self_send_settled(self, _fut: Any) -> None:
        """#172: one self-issued `send_threadsafe` reached a terminal state."""
        self._threadsafe_self_sends_in_flight -= 1

    def _bind_loop(self) -> None:
        """Record the loop (and thread) that owns this interpreter.

        Also materialises the event queue on first bind -- see the note in
        `__init__`. A re-bind (resuming a restored interpreter) keeps the
        existing queue so already-queued events are not lost.
        """
        self._loop = asyncio.get_running_loop()
        self._loop_thread_name = threading.current_thread().name
        if self._wakeup is None:
            self._wakeup = asyncio.Event()
        # 🧪 A SimulatedClock must let THIS interpreter settle after firing
        #    timers, or `await clock.increment()` returns before the machine
        #    has processed the AfterEvent it just queued.
        if isinstance(self.clock, SimulatedClock):
            self.clock._attach(self._settle_for_clock)
        if isinstance(self._event_queue, _PreStartQueue):
            pending = self._event_queue.drain()
            self._event_queue = asyncio.Queue()
            for item in pending:  # 📬 preserve pre-start send() order
                self._event_queue.put_nowait(item)

    # -------------------------------------------------------------------------
    # 🏁 Completion signal (#43) and reaping (#57)
    # -------------------------------------------------------------------------
    def wait_done(self) -> "asyncio.Future[str]":
        """A future that resolves to the terminal status ("done" / "error").

        🏛️ Architecture decision (#43): a parent used to learn its child had
        finished by polling `child.status` every 5 ms in a dedicated task.
        Every idle child therefore cost TWO tasks and 200 wake-ups a second,
        and `onDone` had a 5 ms floor. This future is resolved from
        `_on_terminal` the instant `status` flips, so the parent awaits it.
        Returns an already-resolved future if the machine is terminal now
        (the "child finished during start()" race must keep working).
        """
        loop = asyncio.get_running_loop()
        fut: "asyncio.Future[str]" = loop.create_future()
        if self.status in ("done", "error"):
            fut.set_result(self.status)
            return fut

        def _resolve(status: str) -> None:
            if not fut.done():
                fut.set_result(status)

        self._terminal_listeners.append(_resolve)
        return fut

    def _forget_actor(self, actor_id: str) -> None:
        """Drop a finished spawned child from the actor maps."""
        self._actors.pop(actor_id, None)
        self._actor_sources.pop(actor_id, None)

    def _schedule_teardown(self) -> None:
        # 🧵 `_complete()` is called from inside `_enter_states`, mid-
        #    transition; tearing down children synchronously there would
        #    stop them while the parent's own step is still unwinding.
        #    Defer by one loop turn.
        if self._loop is None or self._loop.is_closed():
            return
        self._loop.create_task(self._teardown())

    async def _teardown(self) -> None:
        """Release everything except `status` / `output` / `error` / `context`.

        Shared by `stop()` and by reaching a terminal status (#57).
        """
        self._detach_clock()  # #115
        # 🧵 #149: release the plain-service pool we created (never one the
        #    caller handed in). `wait=False`: a still-running service is
        #    user code we cannot interrupt; its result is discarded because
        #    the machine is gone.
        if self._owns_service_executor and self._service_executor is not None:
            self._service_executor.shutdown(wait=False)
            self._service_executor = None
        for actor in list(self._actors.values()):
            _stopped = actor.stop()
            if _stopped is not None:
                await _stopped
        self._actors.clear()
        await self.task_manager.cancel_all()
        for handles in self._timer_handles.values():
            for handle in handles:
                self.clock.clear_timeout(handle)
        self._timer_handles.clear()
        self._priority_queue.clear()
        self._internal_queue.clear()  # mid-macrostep state; never persisted
        self._fail_all_receipts()
        self._unregister_from_system()
        if self._event_loop_task and self.status != "running":
            self._event_loop_task.cancel()
            try:
                await self._event_loop_task
            except asyncio.CancelledError:
                pass
            self._event_loop_task = None
            # 📬 Ack anything still queued so a concurrent
            #    `_event_queue.join()` (stop(drain=True), review F5) can
            #    complete instead of waiting forever for a dead consumer.
            q = self._event_queue
            if not isinstance(q, _PreStartQueue):
                while not q.empty():
                    q.get_nowait()
                    q.task_done()

    # -------------------------------------------------------------------------
    # 📬 Inbox (#47)
    # -------------------------------------------------------------------------
    def _snapshot_pending_events(
        self,
    ) -> List[AnyEvent]:
        q = self._event_queue
        if isinstance(q, _PreStartQueue):
            inbox = q.peek()
        else:
            # 🔍 `asyncio.Queue` keeps its items in a deque named `_queue`.
            #    This is CPython-internal but stable since 3.4 and read-only
            #    here; a public alternative would mean re-implementing the
            #    queue.
            inbox = list(getattr(q, "_queue", ()))
        # 📬 #107: a FIRED `after` timer waits in the priority lane, ahead of
        #    the inbox. It is accepted-but-unprocessed work exactly like an
        #    inbox event, and omitting it lost the deadline across a
        #    snapshot with no trace. Priority first, preserving delivery
        #    order on restore.
        return [ev for ev, _ in self._priority_queue] + inbox

    def _enqueue_restored(
        self, event: AnyEvent, *, priority: bool = False
    ) -> None:
        # 🛣️ #214: an item persisted from the priority lane (a fired timer,
        #    an engine completion) goes back into the lane, ahead of the
        #    inbox, with engine standing -- not demoted to inbox traffic.
        if priority:
            self._priority_queue.append((event, is_system_event(event)))
            if self._wakeup is not None:
                self._wakeup.set()
            return
        self._put_inbox(event)

    def _persist_pending_events(self) -> List[Dict[str, Any]]:
        """#214: priority-lane items are tagged so they restore as a lane."""
        out = [
            self._persist_event_reporting(ev, lane="priority")
            for ev, _ in self._priority_queue
        ]
        out.extend(
            self._persist_event_reporting(ev)
            for ev in self._snapshot_pending_events()[
                len(self._priority_queue) :
            ]
        )
        return out

    def _put_inbox(self, event: AnyEvent) -> None:
        """Enqueue on the inbox AND wake a run loop parked on an empty one.

        Every inbox write must go through here: `_next_event` blocks on
        `_wakeup`, not on `Queue.get()`, so a bare `put_nowait` would be
        invisible to an idle loop until the next unrelated event.
        """
        self._event_queue.put_nowait(event)
        if self._wakeup is not None:
            self._wakeup.set()

    async def drain_pending(self) -> List[AnyEvent]:
        """Remove and return every accepted-but-unprocessed event.

        The events are NOT processed. Intended for shutdown paths that must
        persist accepted work durably before the process exits.

        🛣️ #239: the async engine has TWO lanes -- the priority lane
        (fired `after` timers, engine completions, `send_priority()`) and
        the inbox. This used to read the inbox only, so the lane's events
        were omitted from the result AND left queued, where `stop()`'s
        teardown cleared them: the documented "drain, persist, stop" recipe
        silently lost every deadline that had fired just before shutdown.
        Both lanes are drained now, priority first -- the same order
        `pending_events` reports and a restore replays. A receipt attached
        to a drained event is failed with `InterpreterStoppedError` so a
        waiter learns the event will not be processed rather than hanging.
        """
        drained: List[AnyEvent] = [ev for ev, _ in self._priority_queue]
        self._priority_queue.clear()
        q = self._event_queue
        if isinstance(q, _PreStartQueue):
            drained.extend(q.drain())
        else:
            while not q.empty():
                drained.append(q.get_nowait())
                q.task_done()
        # 🧾 A `send(wait=True)` on a drained event can never resolve
        #    through the run loop; say so instead of leaving it pending.
        for ev in drained:
            self._fail_receipt(ev, "drained: removed by drain_pending()")
        return drained

    async def _drain_inbox(self, timeout: Optional[float]) -> None:
        """Let the run loop process the inbox to empty (bounded by timeout).

        🏛️ Review F5: if a drained event drives the machine to a terminal
        status, `_on_terminal` schedules teardown, which cancels the run
        loop while events remain queued -- and nothing ever calls
        `task_done()` for them, so `join()` never returns. `_teardown`
        therefore acks whatever is left before cancelling the loop, and
        this wait is additionally bounded by the machine no longer running.
        """
        # 📬 Restored-but-unstarted: the buffer is a `_PreStartQueue` with
        #    nothing draining it (review F6); there is nothing to wait for.
        if isinstance(self._event_queue, _PreStartQueue):
            return
        join = asyncio.ensure_future(self._event_queue.join())
        try:
            await asyncio.wait_for(join, timeout)
        except asyncio.TimeoutError:
            logger.warning(
                "⏱️ stop(drain=True) on '%s' timed out after %.3fs with %d "
                "event(s) still pending.",
                self.id,
                timeout,
                self._event_queue.qsize(),
            )

    def _assert_owning_thread(self, method: str) -> None:
        """Raise if called from a thread that does not own our loop."""
        if self._loop is None:
            return  # not started yet; start() will bind
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is self._loop:
            return
        # 🪦 A closed loop is not "another thread": the interpreter simply
        #    outlived its `asyncio.run()`. Say that, rather than emitting a
        #    WrongThreadError that names the same thread on both sides.
        if self._loop.is_closed():
            raise RuntimeError(
                f"Interpreter '{self.id}' was bound to an event loop that "
                f"has been closed; {method}() can no longer be used. Create "
                f"a new interpreter (or restore one with from_snapshot) "
                f"inside the new event loop."
            )
        # 📝 #37: the check runs at the CALL SITE, before any coroutine is
        #    created, so it cannot tell a bare `interp.send()` (whose events
        #    WERE silently lost in 0.7.x) from
        #    `run_coroutine_threadsafe(interp.send(...), loop)` (which was
        #    the correct 0.7.x idiom). Name both, and do not claim the
        #    caller's code was always broken.
        raise WrongThreadError(
            f"Interpreter '{self.id}' is bound to the event loop on thread "
            f"'{self._loop_thread_name}'; {method}() was called from thread "
            f"'{threading.current_thread().name}'. {method}() must run on "
            f"the interpreter's own loop thread. From another thread use "
            f"send_threadsafe(). Note that "
            f"asyncio.run_coroutine_threadsafe(interp.{method}(...), loop) "
            f"is also rejected since 0.8.0, because this check runs before "
            f"the coroutine is scheduled; replace it with send_threadsafe()."
        )

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
        if self.status in ("stopped", "done", "error"):
            logger.warning(
                "⚠️ Interpreter '%s' is %s; dropping %d event(s).",
                self.id,
                self.status,
                len(events),
            )
            return

        for event in events:
            self._enqueue(self._prepare_event(event))

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
            if self._descent_done is not None:
                # 🚦 #215: let `start()` finish the initial descent before
                #    taking anything it queued (see `_descent_done`).
                await self._descent_done.wait()
            while self.status == "running":
                # 🧵 #171 / #116: a plain service the INITIAL configuration
                #    invoked is still running when `start()` returns (#149
                #    forbids blocking there). Its completion must still land
                #    ahead of the first inbox event, as every later step's
                #    does -- so await it here, before the inbox is read. The
                #    loop stays live: this is an await, not a block.
                if self._inline_service_futures:
                    await self._await_inline_services()
                # ⚡ #48: due timers first. They were delivered by the clock
                #    straight into the priority lane; an external backlog of
                #    any depth cannot delay them past this point.
                event, from_inbox, self_generated = await self._next_event()
                if self._seed_pending and is_system_event(event):
                    # 🌱 #201: the FIRST completion the initial descent
                    #    produced (either service kind) has the SEED's user
                    #    standing -- the sync drain's rule (#77), where that
                    #    completion is already queued when the drain opens:
                    #    its first descendant is generated event #1. Both
                    #    engines then cut a cycle that starts from the
                    #    initial state at the same lap (23 at
                    #    maxIterations=20, not 22). A user event arriving
                    #    first does not consume the standing -- on the sync
                    #    engine it never could, because the completion had
                    #    already landed inside `start()`. The same standing
                    #    applies to the SETTLE budget (#209): on the sync
                    #    engine the seed's descendants are settled inside
                    #    the drain that `start()` opened, whose budget was
                    #    reset at the drain's start -- so the initial
                    #    descent's own settle work is not charged against
                    #    the chain the seed begins.
                    self._seed_pending = False
                    self._raise_depth = 0
                    self._settle_iterations = 0
                    self._settle_tripped = False

                # 🏛️ #120: an engine completion (`done.invoke`,
                #    `error.platform`, a due `after`) is finished work and
                #    cannot self-feed; dropping it strands the machine in
                #    the invoking state. The sync engine spares these by
                #    construction; mirror that here. It still counts toward
                #    the depth (below) so a rollback->re-arm cycle stays
                #    bounded.
                # 🛟 #168: `not is_system_event(event)` exempted EVERY
                #    completion, so an invoke cycle (`ver -> arm -> ver`) ran
                #    unbounded and silent here while the sync engine tripped.
                #    Mirror the sync rule: the FIRST completion that arrives
                #    at the trip is spared (finished work must land, #120),
                #    every later self-generated event -- completion or not --
                #    is cut until an external event resets the chain.
                # 🚦 #192: the axe falls ONLY on self-generated work. An
                #    external event -- inbox, or a caller's priority send --
                #    that happens to be at the head of a lane when an
                #    unrelated chain trips is not the chain and is processed.
                over = self._raise_depth > limit and self_generated
                if over and is_system_event(event) and not self._chain_tripped:
                    self._chain_tripped = True
                    logger.warning(
                        "🛟 Chain budget reached on '%s' while an engine "
                        "completion ('%s') was pending; delivering it, then "
                        "cutting the self-generated tail.",
                        self.id,
                        event.type,
                    )
                elif over:
                    logger.error(
                        "🛑 Exceeded %d chained self-raised events on '%s'. "
                        "This means an action raises the event that triggers "
                        "it. Breaking the chain; externally queued events are "
                        "unaffected.",
                        limit,
                        self.id,
                    )
                    # 🔗 Sticky within the chain (#88): the runaway keeps
                    #    regenerating until an external event resets the
                    #    depth below; do not hand it a fresh budget per drop.
                    self._chain_tripped = True
                    # 🔔 #77 criterion 6: observable, not just logged.
                    for plugin in self._plugins:
                        plugin.on_event_dropped(self, event, "chain_budget")
                    self.last_transition_ok = False
                    # 🧷 #207: a discarded completion for a still-active
                    #    invoking state leaves the machine parked with
                    #    nothing running. Name it, on the error and via the
                    #    hook, so "cut and stranded" is distinguishable from
                    #    "settled".
                    stranded = self._stranded_by_cut([event])
                    err = RunawayChainError(
                        self.id, limit, 1, [iid for _, iid in stranded]
                    )
                    self._last_action_error = err
                    self._note_chain_trip(err, event)  # #222 sticky
                    self._report_stranded(stranded, err)
                    # 🧾 The dropped event may carry a receipt; never hang it.
                    self._fail_receipt(
                        event,
                        f"dropped: '{event.type}' exceeded the {limit}-event "
                        f"self-raised chain budget on '{self.id}'",
                    )
                    if from_inbox:
                        self._event_queue.task_done()
                    # 🏁 A drop that leaves NO self-generated work pending
                    #    ends the chain -- the sync drain would have
                    #    returned here. Without this the trip stayed sticky
                    #    across idle time, and a service that finished
                    #    50 ms later (#120) was cut as if it were the
                    #    runaway. A cycle made of completions (#167/#168)
                    #    stays bounded: the dropped completion is the only
                    #    thing that could have re-armed it.
                    if (
                        not self._internal_queue
                        and not self._priority_queue
                        and not self._threadsafe_self_sends_in_flight
                    ):
                        self._raise_depth = 0
                        self._chain_tripped = False
                        self._chain_trip_open = False  # #222
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
                # 🧾 #39: what a receipt reports is decided by comparing
                #    the configuration + context before and after, and by
                #    the action-failure signal the policy machinery records.
                config_before = frozenset(self._active_state_nodes)
                # ⚡ A machine with no actions anywhere cannot mutate
                #    context, so `changed` reduces to the configuration
                #    compare and the per-receipt deepcopy is skipped.
                context_before = (
                    copy.deepcopy(self.context)
                    if id(event) in self._receipts
                    and not self.machine.context_is_immutable
                    else None
                )
                step_error: Optional[BaseException] = None
                self.last_transition_ok = True
                self._deferred_this_step.clear()  # #106: per-step scope
                self._guard_denied_this_step = False  # #153: per-step scope
                if self._seed_internal and self_generated:
                    # 🌱 #215: a `raise` the initial descent queued is the
                    #    seed, not a link -- the count starts at its first
                    #    descendant, as on the sync engine (#77).
                    self._seed_internal -= 1
                    self._raise_depth = 0
                if not self_generated and not is_system_event(event):
                    # 🔁 #166 / #151 / #179 / #215: an EXTERNAL user event
                    #    starts a fresh settle budget; anything the machine
                    #    produced itself -- an engine completion OR a
                    #    self-`raise`d plain event -- continues the running
                    #    one. That is the sync drain's rule (`is_generated`
                    #    keeps the budget): #215 found the async engine
                    #    resetting on a raised `GO`, so an `always` +
                    #    `raise` cycle got a fresh settle allowance every
                    #    lap and ran ~2x the sync engine's laps before the
                    #    chain budget caught it.
                    self._settle_iterations = 0
                    self._settle_tripped = False
                try:
                    self._processing = True
                    depth_before = self._raise_depth
                    self._armed_this_step = 0  # #179 / #200
                    await self._process_event_and_transient_transitions(event)
                    # ✅ A macrostep that raised nothing ends the chain --
                    #    provided no self-generated work is still queued.
                    #    #150: an action that hands its re-trigger to a
                    #    worker thread returns before that send lands, so
                    #    "raised nothing during the step" was true on every
                    #    lap and the chain never accumulated. The internal
                    #    queue being non-empty means the chain is alive.
                    # 🔗 #179: a step that ARMED engine work whose
                    #    completion has not landed yet (an `async def`
                    #    service, a child actor) has not finished
                    #    generating: its completion is the next link. Only
                    #    THIS step's arming counts -- work outstanding from
                    #    an earlier, unrelated step (a long poll running
                    #    beside independent user traffic) must not keep a
                    #    chain open, or legitimate one-deep raises would
                    #    accumulate into a false trip.
                    if (
                        self._raise_depth == depth_before
                        and not self._armed_this_step
                        and not self._internal_queue
                        and not self._priority_queue
                        and not self._threadsafe_self_sends_in_flight
                    ):
                        self._raise_depth = 0
                        self._chain_tripped = False
                        self._chain_trip_open = False  # #222
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    step_error = exc
                    # 🏛️ #31 (runtime parity): the sync engine RAISES an
                    #    unresolvable target / missing implementation to its
                    #    caller. This engine cannot raise into a
                    #    fire-and-forget `send()`, so the same failure is
                    #    published where a caller CAN see it without
                    #    `wait=True`: `last_transition_ok` / `last_error`,
                    #    plus the `on_transition_failed` hook -- the same
                    #    surface a failed action list uses. Logging alone
                    #    left the two engines disagreeing on an error path.
                    self.last_transition_ok = False
                    self._last_action_error = exc
                    # (#134: `on_resolve_error` fires from the shared
                    #  `_execute_transition`, on both engines.)
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
                if id(event) in self._receipts:
                    if step_error is None and not self.last_transition_ok:
                        step_error = self._last_action_error
                    # 🛡️ #208: a receipt is resolved only here, AFTER the
                    #    in-flight flag is down, so it can never coincide
                    #    with a mid-step snapshot refusal. Belt and braces:
                    #    a running machine whose step ended over an EMPTY
                    #    configuration is a torn result, never a success --
                    #    the receipt says so instead of `ok`.
                    if (
                        step_error is None
                        and self.status == "running"
                        and not self._configuration_is_legal()
                    ):
                        step_error = self._last_action_error or RuntimeError(
                            f"'{event.type}' left machine '{self.id}' with "
                            f"no legal configuration (#208)"
                        )
                        self.last_transition_ok = False
                    changed = frozenset(
                        self._active_state_nodes
                    ) != config_before or (
                        context_before is not None
                        and self.context != context_before
                    )
                    deferred = any(
                        ev is event for ev in self._deferred_this_step
                    )
                    self._resolve_receipt(
                        event,
                        changed,
                        step_error,
                        deferred,
                        denied=(not changed and self._guard_denied_this_step),
                    )
                # 📨 #125: replay deferred events as their OWN macrosteps,
                #    after this event's receipt has been resolved, so the
                #    receipt describes THIS event's transition and not the
                #    consequences of replaying an older one.
                if self._replay_pending:
                    self._replay_pending = False
                    # `_deliver_priority` APPENDS, so feed in original order
                    # (LC-18: replay must preserve arrival order).
                    for ev in self._take_deferred_for_replay():
                        # A replayed event keeps its original (external)
                        # standing: it was a caller's event held for later.
                        self._deliver_priority(ev)

                if from_inbox:
                    self._event_queue.task_done()

        except asyncio.CancelledError:
            # 🏛️ #114: cancellation reaching here is EITHER an orderly
            #    `stop()` (status already "stopped"/"done"/"error") OR
            #    something killed the loop task from outside while the
            #    machine believed it was running. In the second case the
            #    machine is dead but every probe says healthy and every
            #    pending receipt hangs forever. Plugin-hook CancelledError is
            #    contained upstream (`_SafePlugin`), so what remains here is
            #    a genuine external cancel: publish it.
            if self.status == "running":
                self._die(
                    RuntimeError(
                        f"Interpreter '{self.id}' run loop was cancelled "
                        f"while running; the machine is no longer processing "
                        f"events."
                    )
                )
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
        self, event: AnyEvent
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
        # ⚡ Only needed to decide whether deferred events earned a replay;
        #    skip both frozensets when nothing is deferred.
        before = (
            frozenset(self._active_state_nodes)
            if self._deferred_events
            else None
        )
        await self._process_event(event)
        await self._await_inline_services()  # #149

        # 2️⃣ Immediately settle any event-less ("always") transitions.
        await self._settle_transient_transitions()
        await self._await_inline_services()  # a settle may enter an invoke

        # 3️⃣ Replay deferred events now that the configuration changed.
        #
        # 🏛️ Architecture decision: replayed HERE, inside the same run-loop
        #    iteration, rather than re-queued. That is what puts them ahead
        #    of live traffic in original order (LC-18) without touching the
        #    asyncio.Queue. Anything still unhandled in the new state is
        #    re-deferred by `_handle_unhandled_event`, not re-dropped.
        #    Bounded by the same microstep limit as `always` loops.
        # 🏛️ #125: replay is NOT folded into this event's macrostep any more.
        #    Doing so made the triggering event's `Receipt` describe the
        #    replayed event's transition (ARM's receipt said `c`, the state
        #    LATE's replay reached). The run loop replays each held event as
        #    its own macrostep -- ahead of live traffic via the priority
        #    lane, in original order -- right after this receipt resolves.
        if (
            before is not None
            and self._deferred_events
            and before != frozenset(self._active_state_nodes)
        ):
            self._replay_pending = True

    async def _settle_transient_transitions(self) -> None:
        """Runs eventless ("always") transitions until the state is stable.

        Extracted so `start()` can settle the initial configuration too — the
        sync engine already did this, so leaving it inline made the two
        engines disagree on the very first observable state.
        """
        # 🛟 Bound the microstep loop. A pair of `always` transitions that
        #    target each other spins forever; XState added the same guard in
        #    v5.31.0. `max_iterations` is configurable on the machine.
        if not self.machine.has_always_transitions:
            # ⚡ nothing to settle; see MachineNode.has_always_transitions.
            self._arm_pending_invokes()  # #204: still the macrostep's end
            return
        limit = getattr(self.machine, "max_iterations", 1000)
        while True:
            # 🛟 #166: the budget is per MACROSTEP on the instance, not a
            #    local counter per call. A local counter restarted at 0 on
            #    every completion-driven re-entry (an `always` into an
            #    invoking child whose service finishes inside the settle
            #    re-delivers `done.invoke`, which re-settles...), so the
            #    async loop spun for ever while the sync engine -- whose
            #    counter lives on the instance (#103 / #151) -- tripped in
            #    milliseconds. Reset by the run loop when an EXTERNAL event
            #    begins its macrostep; a trip is observable (#112).
            self._settle_iterations += 1
            if self._settle_iterations > limit:
                if not self._settle_tripped:
                    logger.error(
                        "🔁 Exceeded %d microsteps while settling transient "
                        "transitions in '%s'. Aborting to avoid an infinite "
                        "loop; check for mutually-targeting 'always' "
                        "transitions or an 'always' into an invoking state.",
                        limit,
                        self.id,
                    )
                first_trip = not self._settle_tripped
                self._settle_tripped = True
                self.last_transition_ok = False
                self._last_action_error = RunawayChainError(self.id, limit, 0)
                if first_trip:  # #222 sticky, once per settle storm
                    self._chain_trip_open = False
                    self._note_chain_trip(self._last_action_error, Event(""))
                self._repair_configuration()
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
        # 📞 #204 (SCXML 6.1): the macrostep is stable -- arm the invokes of
        #    the states it entered and did not exit. Also reached when the
        #    settle budget trips: the states still active are the machine's
        #    real configuration and must invoke.
        self._arm_pending_invokes()

    # -------------------------------------------------------------------------
    # 🤖 Asynchronous Task Implementations (Actors, Timers, Services)
    # -------------------------------------------------------------------------

    async def _run_user_action(
        self,
        impl: Callable[..., Any],
        action_def: ActionDefinition,
        event: Any,
    ) -> None:
        """Leaf: call one action, awaiting it if it is a coroutine function.

        Records the running TASK in `_action_tasks` for the duration
        (#105 / #225), so a `send()` issued on `self` from this task is
        recognised as a self-send by identity of the running task -- not
        by the loop being busy, and not by an inherited context a spawned
        helper would carry for its whole life. A depth per task, not a
        flag, because actions nest (an action that awaits something which
        runs another action on the same task); a flag would be cleared
        early by the inner `finally`.
        """
        task = asyncio.current_task()
        if task is not None:
            self._action_tasks[task] = self._action_tasks.get(task, 0) + 1
        # 🧵 #150: for a thread the action starts with a COPIED context.
        token = _ACTIVE_ACTION_OWNER.set(self)
        try:
            if inspect.iscoroutinefunction(impl):
                await impl(self, self.context, event, action_def)
            else:
                impl(self, self.context, event, action_def)
        finally:
            _ACTIVE_ACTION_OWNER.reset(token)
            if task is not None:
                depth = self._action_tasks[task] - 1
                if depth:
                    self._action_tasks[task] = depth
                else:
                    del self._action_tasks[task]

    def _spawn_run_loop(self) -> "asyncio.Task[None]":
        """Create the run-loop task with death publication attached to the TASK.

        🏛️ #148: #114 published an external cancel from the
        ``except CancelledError`` inside `_run_event_loop`. That handler
        only exists once the coroutine body has started; a task cancelled
        between `start()` returning and its first scheduling turn never
        enters the body, so nothing published and the machine was a
        zombie (`status="running"`, `is_running=False`, receipts hung).
        A done-callback fires for EVERY way a task ends -- cancelled
        before first step, cancelled mid-way, or a non-cancel exception
        that escaped the loop -- so it is the one place that cannot be
        skipped. `_die` is idempotent on status, so the in-body handler
        (still there for the common case) and this callback never
        double-publish.
        """
        task = asyncio.create_task(self._run_event_loop())

        def _on_loop_done(t: "asyncio.Task[None]") -> None:
            if self.status != "running":
                return  # orderly stop / done / error: nothing to publish
            if t.cancelled():
                self._die(
                    RuntimeError(
                        f"Interpreter '{self.id}' run loop was cancelled "
                        f"while running; the machine is no longer "
                        f"processing events."
                    )
                )
                return
            exc = t.exception()
            if exc is not None:
                self._die(exc)

        task.add_done_callback(_on_loop_done)
        return task

    def _die(self, error: BaseException) -> None:
        """The run loop is gone without an orderly `stop()` (#114).

        Flip `status` so `is_running` / `_refuse_if_not_running` tell the
        truth, record the cause on `error`, fail every pending receipt so
        no awaiter hangs, and fire `on_error` -- the same surface a fatal
        `actionErrorPolicy="fail"` uses.
        """
        if self.status != "running":
            # 🔁 Idempotent: the task done-callback (#148) and the in-body
            #    CancelledError handler (#114) may both arrive.
            return
        self.status = "error"
        self.error = error
        for key in list(self._receipts):
            fut = self._receipts.pop(key, None)
            if fut is not None and not fut.done():
                fut.set_exception(error)
        for plugin in self._plugins:
            plugin.on_error(self, error)

    def _issued_from_own_action(self) -> bool:
        """``True`` when the caller is one of THIS interpreter's user
        actions (#105) -- the only case a `send()` is self-generated.

        On the loop thread the answer is TASK IDENTITY (#225): the current
        task is one recorded in `_action_tasks`. A task an action spawned
        is not the action, however much context it inherited. On a
        FOREIGN thread there is no task; the documented opt-in (#150) is a
        context copied from the action (`contextvars.copy_context().run`),
        so the ContextVar decides there -- and only there.
        """
        try:
            task = asyncio.current_task()
        except RuntimeError:
            # 🧵 No running loop on this thread: `send_threadsafe` path.
            return _ACTIVE_ACTION_OWNER.get() is self
        return task is not None and task in self._action_tasks

    async def _dispatch_internal(self, event: Any) -> None:
        self._enqueue(event)

    async def _stop_actor_leaf(self, actor: Any) -> None:
        result = actor.stop()
        if inspect.isawaitable(result):
            await result

    async def _deliver(
        self,
        actor: "BaseInterpreter[Any]",
        target_event: AnyEvent,
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
                # 🔁 #36: a `raise` to OURSELVES during a macrostep is an
                #    INTERNAL event. It goes to the internal queue, drained
                #    before any external event, so the machine finishes its
                #    own step before it observes the outside world again.
                self._raise_depth += 1
                self._internal_queue.append(target_event)
                return
            await self._send_to_actor(actor, target_event)
            return

        key = str(send_id) if send_id else None
        # ⏲️ #206: a DELAYED send to ourselves, issued from our own action,
        #    is self-generated work exactly like a zero-delay `raise` -- the
        #    delay changes WHEN it lands, not WHO produced it. Charging it at
        #    delivery as external (#192's provenance tag) made a
        #    `raise(delay=1)` ping-pong un-sheddable and un-charged: a cycle
        #    `maxIterations` could not bound. It is a debt of the arming
        #    step (like a coroutine service, #179) and its firing is charged
        #    as engine-generated (like a completion).
        self_armed = actor is self and self._processing
        handle_box: List[Any] = []

        def _settle_debt() -> None:
            if handle_box:
                self._chain_owed_sends.discard(handle_box[0])
                self._armed_self_sends.pop(handle_box[0], None)  # #213
                self._release_timer_handle(self.id, handle_box[0])  # #218

        def _fire() -> None:
            """Deliver once the clock says the delay has elapsed (#49)."""
            # 🧹 Only clear the registry if it still points at THIS send.
            #    A later send reusing the same id replaces the entry, and
            #    popping unconditionally would drop the live registration
            #    and leave the newer send uncancellable.
            if key is not None and self._scheduled_sends.get(key) is _cancel:
                self._scheduled_sends.pop(key, None)
            _settle_debt()
            if self.status != "running":
                return
            if actor is self:
                # ⏲️ #212: a delayed self-send that fires is a CLOCK event
                #    with exactly the standing of an `after` firing: engine-
                #    generated (charged +1 like any completion, shed-able if
                #    it lands on an already-tripped chain), but the delay
                #    itself ended the arming step's chain -- see the arming
                #    branch above. So a self-paced heartbeat of any period
                #    runs for ever, and so does a 1 ms `raise(delay=)` ping-
                #    pong, exactly as an `after: 1` ping-pong does: both are
                #    periodic processes driven by the clock, not chains the
                #    machine feeds itself within a step.
                self._deliver_priority(
                    target_event, engine_completion=self_armed
                )
            else:
                asyncio.ensure_future(self._send_to_actor(actor, target_event))

        handle = self._set_timeout(_fire, delay / 1000.0, owner=self.id)
        handle_box.append(handle)
        self._timer_handles.setdefault(self.id, []).append(handle)
        if self_armed:
            # 🔗 #206 -> #212: a delayed self-send is a TIMER, and gets the
            #    `after` rule. Its firing is charged as engine work (see
            #    `_fire`), but ARMING it does not keep the step's chain
            #    open: a step that armed a deadline has finished generating
            #    -- the clock, not the machine, produces the next event. An
            #    `after` that re-arms itself every lap is a periodic process,
            #    not a runaway; a `raise(delay=)` heartbeat is the same shape
            #    spelled differently. #206 counted the arming as
            #    `_armed_this_step`, so the chain-end test was false on every
            #    lap and a 250 ms heartbeat died at `maxIterations` beats;
            #    the time-blind charge could not tell a 1 ms ping-pong from a
            #    poller -- and neither is a chain: `maxIterations` bounds
            #    work the machine feeds itself WITHIN a step (zero-delay
            #    `raise`, `send` to self, completions re-arming invokes),
            #    which is what `after: 1` ping-pongs have always been exempt
            #    from too. The handle is still recorded so a snapshot sees
            #    the debt (#213) and cancellation is clean.
            self._chain_owed_sends.add(handle)
        if actor is self:
            # ⏲️ #213: visible to the snapshot until it fires or is cancelled.
            self._armed_self_sends[handle] = (
                target_event,
                self.clock.now() + delay / 1000.0,
                key,
            )

        def _cancel() -> None:
            """Cancels this specific delayed send."""
            self.clock.clear_timeout(handle)
            _settle_debt()
            self._armed_self_sends.pop(handle, None)

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
        actor: "BaseInterpreter[Any]", target_event: AnyEvent
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
        # 📥 Input goes in at CONSTRUCTION so a child `context` factory
        #    receives `{input}` (#42); `_build_initial_context` also seeds
        #    declared keys and exposes `context["input"]`.
        # 🕰️ A child shares the parent's `clock` (#49) -- one timeline for
        #    a whole actor tree -- and its constructor-level `strict` (#51):
        #    a parent that opted into strict mode must not get a child that
        #    silently swallows typos because it fell back to `machine.strict`.
        child_interpreter = Interpreter(
            actor_machine,
            input=spawn_params.get("input"),
            clock=self.clock,
            strict=self.strict,
        )
        child_interpreter.parent = self
        child_interpreter.id = actor_id
        # 🌐 Register under a systemId so siblings can address it.
        self._register_in_system(
            spawn_params.get("systemId"), child_interpreter
        )
        self._actors[actor_id] = child_interpreter
        self._actor_sources[actor_id] = actor_machine_key

        # 🧹 #57 review F3: a spawned child that finishes on its own must
        #    leave the parent's map, or a supervisor that spawns per request
        #    grows without bound. (Invoked children are popped by their
        #    manager task; spawned ones had no owner watching.)
        def _on_child_terminal(_status: str, aid: str = actor_id) -> None:
            self._forget_actor(aid)

        child_interpreter._terminal_listeners.append(_on_child_terminal)
        await child_interpreter.start()

        # ⏸️ #41: `spawn_blocking_<key>` -- the child runs to completion
        #    BEFORE the parent's next action, exactly as on the sync engine.
        #    Before 0.8.0 the async engine discarded the marker, so the same
        #    action string meant two different things on the two engines.
        #    Bounded by `spawnBlockingTimeout` (ms, machine config) so a
        #    child with no final state cannot hang the parent forever.
        if action_def.type.startswith(SPAWN_BLOCKING_PREFIX):
            timeout_ms = self.machine.spawn_blocking_timeout_ms
            if timeout_ms is None:
                # 🛡️ An unbounded wait INSIDE a transition wedges the parent
                #    forever if the child never reaches a final state, and
                #    the machine still reports "running" (review F2). A
                #    bounded default keeps the guarantee for children that
                #    do finish and makes the failure mode a WARNING, not a
                #    hang. Set `spawnBlockingTimeout` explicitly to tune.
                timeout_ms = DEFAULT_SPAWN_BLOCKING_TIMEOUT_MS
            try:
                await asyncio.wait_for(
                    child_interpreter.wait_done(), timeout_ms / 1000.0
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "⏱️ Blocking spawn of '%s' did not finish within %s ms; "
                    "continuing without it.",
                    actor_id,
                    timeout_ms,
                )
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
        # 🎭 #43: invoked children have no manager task to cancel; stop
        #    them directly. Copy: `stop()` -> `_on_terminal` -> listener
        #    would otherwise mutate the list we iterate. A child stopped
        #    this way is "cancelled", not "done": its listener must NOT
        #    fire `onDone` into a state we just left, so detach first.
        for child in list(self._invoked_children.pop(state.id, [])):
            child._terminal_listeners = [
                fn
                for fn in child._terminal_listeners
                if getattr(fn, "__name__", "") != "_on_child_terminal"
            ]
            self._actors.pop(child.id, None)
            self._actor_sources.pop(child.id, None)
            if child.status == "running":
                await child.stop()
        # ⏱️ And the clock-scheduled timers this state owns (#49).
        for handle in self._timer_handles.pop(state.id, []):
            self.clock.clear_timeout(handle)

    async def _next_event(
        self,
    ) -> Tuple[AnyEvent, bool, bool]:
        """Return ``(event, from_inbox, self_generated)``.

        Priority lane first, then inbox. ``self_generated`` (#192) is the
        provenance recorded when the event was queued: ``True`` for the
        internal queue (a `raise` / self-send) and for priority items the
        engine or one of this machine's own actions produced; ``False`` for
        the inbox and for a caller's `send(priority=True)`. The run loop's
        chain-budget cut sheds ONLY self-generated items.

        `from_inbox` tells the caller whether it owes the inbox a
        `task_done()` -- priority events never passed through `get()`, and
        acking them would corrupt the join counter.

        🏛️ Architecture decision: this deliberately does NOT race a
        `Queue.get()` future against the wake-up event. An earlier version
        did, and a cancelled `get()` that had already dequeued an item lost
        that item (148 of 3,000 events under load), while the loser future
        of every race leaked a task. Instead: take from the lane, else
        `get_nowait()` from the inbox, and only when BOTH are empty block
        on the wake-up event -- which `put()` and `_deliver_priority` both
        set. One await, no futures, nothing to cancel.
        """
        assert self._wakeup is not None
        while True:
            # 🔁 #36: finish our own macrostep first (SCXML internal queue).
            if self._internal_queue:
                return self._internal_queue.popleft(), False, True
            if self._priority_queue:
                event, self_generated = self._priority_queue.popleft()
                return event, False, self_generated
            try:
                event = self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            else:
                # ⚡ #48: taking from the inbox without ever awaiting would
                #    drain a 2,000-event backlog in ONE loop turn, and a
                #    `call_later` timer that came due meanwhile could not
                #    run until the inbox was empty -- the starvation this
                #    lane exists to end. Yield so due timers get their turn
                #    and land in the lane, which is checked first on the
                #    next iteration.
                #
                # ⚡ Amortised: a yield per inbox event made two loop turns
                #    of every event's cost (~45% of `send(wait=True)`
                #    throughput). Yield every `_INBOX_YIELD_EVERY` inbox
                #    events instead; the starvation bound becomes N events
                #    (microseconds) instead of one, still far below any
                #    timer's resolution. Priority/internal lanes are checked
                #    before each inbox take regardless.
                self._inbox_streak += 1
                if self._inbox_streak >= self._INBOX_YIELD_EVERY:
                    self._inbox_streak = 0
                    await asyncio.sleep(0)
                return event, True, False
            # 🔒 Clear THEN re-check both sources, so an event that arrived
            #    between the checks above and this clear is not slept
            #    through (lost wake-up).
            self._wakeup.clear()
            self._inbox_streak = 0  # ⚡ reaching the park point ends a streak
            if self._priority_queue or not self._event_queue.empty():
                # 🏁 Something landed between the emptiness checks and the
                #    clear. Yield before taking it: this path can be
                #    re-entered continuously by a producer racing the loop,
                #    and without a yield nothing else on the event loop
                #    (timers, the producer's own continuation) could run.
                await asyncio.sleep(0)
                continue
            await self._wakeup.wait()

    def _deliver_priority(
        self, event: AnyEvent, *, engine_completion: bool = False
    ) -> None:
        """Place *event* at the head of processing and wake the run loop.

        Args:
            event: The event to deliver ahead of the inbox.
            engine_completion: ``True`` when the ENGINE produced *event*
                as the result of work the machine itself started -- a
                service's ``done.invoke`` / ``error.platform``, a child
                actor's completion, a due ``after`` timer. ``False`` for a
                caller's ``send(..., priority=True)`` and for deferred
                events being replayed.

        🏛️ Chain-budget accounting is decided by PROVENANCE, never by
        timing (#180). An earlier version charged whatever arrived while
        ``_processing`` was true; an external producer whose send happened
        to land mid-macrostep was then treated as a self-feeding chain and
        shed as ``chain_budget`` -- the exact failure #105 had fixed on the
        inbox lane, resurfacing on this one. The public priority lane is
        external traffic and is never charged, whatever the loop is doing.

        🛟 #166 / #167 / #168 / #179: an engine completion the machine
        produced WHILE processing (a service that finished inside the
        entering macrostep, a rollback that re-armed an invoke, an
        ``always`` that re-entered an invoking child, an ``async def``
        service whose completion lands inside a step) is self-generated
        work and IS charged, exactly as the sync engine charges it -- for
        every service kind, on this single lane (#179). A completion that
        lands on an idle loop (no step open) is free: that is external time
        passing, not the machine feeding itself, and the next step's
        "raised nothing" check ends any chain it might have belonged to.
        """
        # 🚦 #192: the flag is stored on the ITEM (see `_priority_queue`)
        #    so the run loop's shed decision uses the same provenance the
        #    charge did, instead of the event's position in the FIFO.
        self_generated = engine_completion
        if engine_completion:
            # 🔗 #179: EVERY engine completion is charged, as on the sync
            #    engine, where a completion is by construction generated
            #    by the drain that armed it. Whether the chain it belongs
            #    to is over is decided after the step that consumes it:
            #    "raised nothing, armed nothing, owes nothing" ends the
            #    chain and clears the count -- so N independent one-deep
            #    completions never accumulate, while `a -> done -> b ->
            #    done -> a` does, for `def` and `async def` alike.
            # (#200: the debt is settled by the OWING task's done-callback,
            #  not here -- a completion must never pay another task's debt.)
            self._raise_depth += 1
        self._priority_queue.append((event, self_generated))
        if self._wakeup is not None:
            self._wakeup.set()

    async def _settle_for_clock(self) -> None:
        """`SimulatedClock` hook: process everything queued by fired timers."""
        for _ in range(1000):
            if not self._priority_queue and self._event_queue.empty():
                if not self._processing:
                    return
            await asyncio.sleep(0)
        # Something is looping; leave it to the runaway guard.

    def _invocation_is_live(
        self, state: StateNode, invocation: InvokeDefinition
    ) -> bool:
        # A service invoke runs as a task owned by the state; a machine
        # invoke as a child actor addressed `<self.id>:<invoke id>` (or a
        # uuid-suffixed anonymous id recorded in `_actor_sources`).
        if any(
            not t.done()
            for t in self.task_manager.get_tasks_by_owner(state.id)
        ):
            return True
        # 🎭 #43: an invoked child is live while it is running.
        if any(
            c.status == "running"
            for c in self._invoked_children.get(state.id, [])
        ):
            return True
        if f"{self.id}:{invocation.id}" in self._actors:
            return True
        return any(
            src == invocation.src for src in self._actor_sources.values()
        )

    def _after_timer(
        self, delay_sec: float, event: AfterEvent, owner_id: str
    ) -> None:
        """Schedule a delayed `AfterEvent` on the interpreter's clock (#49).

        🏛️ #48: the callback does NOT go through `send()`. It stamps
        `fired_at` and drops the event into the PRIORITY lane, so a due
        timer is processed before any external backlog. On a `RealClock`
        inside a loop this is `loop.call_later`; on a `SimulatedClock` it
        fires from `increment()`.

        Args:
            delay_sec (float): The delay in seconds.
            event (AfterEvent): The event to deliver after the delay.
            owner_id (str): The owning state; exiting it cancels the timer.
        """

        def _fire() -> None:
            if self.status != "running":
                return
            # 🏷️ #235: the engine stamps `fired_at` by re-minting, so the
            #    fired event keeps engine provenance (`_replace` now
            #    returns the public class by design).
            fired = _engine_after(
                event.type, event.scheduled_for, self.clock.now()
            )
            logger.info(
                "🕒 'after' timer fired for event '%s' in '%s' (+%.1f ms).",
                fired.type,
                self.id,
                fired.lateness_ms,
            )
            self._deliver_priority(fired, engine_completion=True)

        handle = self._set_timeout(_fire, delay_sec, owner=owner_id)
        self._timer_handles.setdefault(owner_id, []).append(handle)

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
                # 📥 #42: callable `input` is resolved here too, so a
                #    service `src` and a machine `src` see the same value.
                payload={
                    "input": invocation.resolve_input(self.context, None) or {}
                },
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

            # ✅ Service completed: publish its 'done' event.
            #
            # 🛟 #179: through the PRIORITY lane, marked as an engine
            #    completion, NOT `send()`. `send()` put it on the public
            #    inbox, where (a) it was never charged to the chain budget
            #    and (b) it arrived `from_inbox` and reset the settle
            #    budget every lap -- so `maxIterations` was inert for any
            #    machine whose services were `async def`, the style the
            #    docs recommend, while the identical `def` service tripped.
            #    One lane for every service kind; one accounting rule.
            done_event = _engine_done(
                type=f"done.invoke.{invocation.id}",
                data=result,
                src=invocation.id,
            )
            self._publish_completion(done_event)
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
            error_event = _engine_error(
                type=f"error.platform.{invocation.id}",
                error=e,
                src=invocation.id,
            )
            # 🚨 If nothing handles the error event, the failure is
            #    unhandled and must be observable rather than merely logged.
            handled = self._has_error_handler(invocation)
            self._publish_completion(error_event)  # #179: charged lane
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)
            if not handled:
                self._fail(e)

    def _invoke_service(
        self,
        invocation: InvokeDefinition,
        service: Union[Callable[..., Any], "MachineNode[Any]"],
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
        #
        # 🏛️ #43: NO manager task. The child's own run-loop task is the only
        #    task an invoked child costs. Completion is pushed: the child's
        #    terminal listener (fired the instant `status` flips) sends
        #    `onDone` / `onError` to the parent. Bring-up itself is a short
        #    coroutine that must run to completion before this state's
        #    entry finishes, and a failure inside it (bad `input` resolver,
        #    child `start()` raising) is a child failure -> `onError`.
        if isinstance(service, MachineNode):
            task = asyncio.create_task(
                self._start_invoked_actor(invocation, service, owner_id)
            )
            # The bring-up task is transient (microseconds) and is tracked
            # only so an exit racing the start cancels it cleanly.
            self.task_manager.add(owner_id, task)
            # (Not `_owe_completion`: a child's terminal may legitimately
            #  never come -- a long-lived child is stopped by exit -- so
            #  it cannot be a debt. Its terminal IS charged when it lands.)
            # 👶 #171: the ENTERING macrostep (and `start()`) awaits the
            #    bring-up, so the child is addressable -- `sendTo("kid")`
            #    resolves, `_actors` lists it -- by the time the step that
            #    entered the invoking state is observable, as on the sync
            #    engine. Kept apart from plain-service futures: `start()`
            #    must await registration (microseconds) but NOT a plain
            #    service's result (#149 -- the loop stays live).
            self._actor_bringups.append(task)
            return

        # 📞 Case 2: The service is a standard callable.
        #
        # 🏛️ #116: a PLAIN (non-coroutine) callable runs INLINE, exactly as
        #    the sync engine runs it -- inside the macrostep that enters the
        #    invoking state, with its `done.invoke` delivered ahead of any
        #    event already waiting in the inbox. Wrapping it in a task
        #    deferred the call until after the run loop yielded, so an
        #    external event queued behind the entry (CANCEL) was processed
        #    BEFORE the completion, and the identical (GO, CANCEL) script
        #    diverged between engines. Coroutine services still run as
        #    tasks: they genuinely await, and that is the async engine's
        #    whole reason to exist.
        if _is_plain_sync_callable(service):
            self._invoke_plain_service_inline(invocation, service, owner_id)
            return

        async def _invoke_wrapper() -> None:
            # This sleep(0) is a critical best practice to prevent a race
            # condition, ensuring the task is registered before the service
            # code runs.
            await asyncio.sleep(0)
            await self._invoke_service_task(invocation, service)

        task = asyncio.create_task(_invoke_wrapper())
        # Register the task with its owner for lifecycle management.
        self.task_manager.add(owner_id, task)
        self._owe_completion(task)

    def _report_service_failure(
        self, invocation: InvokeDefinition, exc: Exception
    ) -> None:
        """Deliver `error.platform.<id>` for a failed service and, with no
        `onError` declared, fail the parent (shared by the inline and
        late-awaitable paths of #116)."""
        logger.error(
            "💥 Service '%s' (ID: '%s') failed: %s",
            invocation.src,
            invocation.id,
            exc,
            exc_info=True,
        )
        error_event = _engine_error(
            type=f"error.platform.{invocation.id}",
            error=exc,
            src=invocation.id,
        )
        handled = self._has_error_handler(invocation)
        self._publish_completion(error_event)
        for plugin in self._plugins:
            plugin.on_service_error(self, invocation, exc)
        if not handled:
            self._fail(exc)

    @property
    def _chain_owed(self) -> int:
        """Number of coroutine-service completions the open chain is still
        owed (#179 / #200). Read-only diagnostic view of `_chain_owed_tasks`.
        """
        return len(self._chain_owed_tasks)

    def _owe_completion(self, task: "asyncio.Task[Any]") -> None:
        """#179 / #200: the current step armed a coroutine service whose
        completion will land on a later loop turn. Record the TASK as a
        debt so the step's "raised nothing, armed nothing" chain-end test
        knows the chain is not over.

        The debt is settled by *task*'s own done-callback, which asyncio
        fires for every way a task can end -- normal return, `Exception`,
        `CancelledError`, `KeyboardInterrupt` / `SystemExit` / any other
        `BaseException`. Keying the debt to the task (rather than a bare
        count decremented by whichever completion arrives next) means a
        completion belonging to one invocation can never settle a debt
        opened by another, and nothing that ends a task can leak a debt.
        Child actors are deliberately NOT counted: a long-lived child is
        stopped by an exit and never produces a terminal, so its bring-up
        cannot be a debt.
        """
        if not self._processing:
            return
        self._chain_owed_tasks.add(task)
        self._armed_this_step += 1
        task.add_done_callback(self._chain_owed_tasks.discard)

    def _publish_completion(self, event: AnyEvent) -> None:
        """Publish an ENGINE completion (`done.invoke`, `error.platform`).

        🏛️ #179: the ONE place every service kind's completion goes
        through -- plain `def` (inline, via the executor), `async def`
        (its own task), a plain `def` that returned an awaitable, and an
        invoked child actor's terminal event. Routing them all here is
        what makes the chain budget a property of the machine rather than
        of how a service happens to be spelled. Refused (not queued) once
        the machine is no longer running, like every other delivery.
        """
        if self._refuse_if_not_running(event):
            return
        self._deliver_priority(event, engine_completion=True)

    def _get_service_executor(self) -> concurrent.futures.Executor:
        """The executor plain services run on; created on first use (#149)."""
        if self._service_executor is None:
            # 🧵 Small and explicit: the number of concurrently-running
            #    plain services is a property of the machine, not the host.
            #    #173: the size is public (`service_pool_size=`) because a
            #    fifth concurrent service otherwise waited in a wave, and
            #    each wave blocked a macrostep -- slower than serial.
            self._service_executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self._service_pool_size,
                thread_name_prefix=f"xsm-svc-{self.id}",
            )
            self._owns_service_executor = True
        return self._service_executor

    async def _await_inline_services(self) -> None:
        """Block the CURRENT macrostep (not the loop) on plain services (#149).

        Each future was created by `_invoke_plain_service_inline` when the
        step entered an invoking state. Awaiting here -- before the step
        completes and before `_next_event` looks at the inbox -- is what
        keeps #116's guarantee: the `done.invoke` is in the priority lane
        before any external event queued behind the entry is considered.
        A service that itself enters another invoking state (via its
        completion) is picked up by the loop's next iteration.
        """
        await self._await_actor_bringups()
        while self._inline_service_futures:
            pending, self._inline_service_futures = (
                self._inline_service_futures,
                [],
            )
            await asyncio.gather(*pending, return_exceptions=True)
            await self._await_actor_bringups()

    async def _await_actor_bringups(
        self, *, timeout: Optional[float] = None
    ) -> None:
        """#171: block the current step until invoked children are registered.

        A bring-up cancelled by an exit racing the start is a normal
        outcome here, not an error to surface.

        Args:
            timeout: #181 -- bound the wait. A bring-up awaits the child's
                ``start()``, i.e. its entry actions, which are arbitrary
                user code; unbounded, a slow child held the caller for
                its whole duration. On timeout the bring-ups keep running
                (they are the children's own tasks), a WARNING names them,
                and the caller proceeds; the children register when they
                finish.
        """
        started_at = time.monotonic()
        overran = 0
        while self._actor_bringups:
            pending, self._actor_bringups = self._actor_bringups, []
            if timeout is None:
                await asyncio.gather(*pending, return_exceptions=True)
                continue
            # 👶 #194: the bound is PER CHILD, not aggregate. The bring-up
            #    tasks run concurrently on the loop, so N children whose
            #    entry actions each `await` for D seconds settle in ~D, not
            #    N x D, and each one is given the same allowance.
            done, not_done = await asyncio.wait(pending, timeout=timeout)
            overran += len(not_done)
            if not_done:
                # 🏁 They are the children's OWN tasks and finish on
                #    their own; each registers its child on completion.
                #    Do NOT re-queue them for the next step to await --
                #    that made the first event after a timed-out start()
                #    block for the rest of the slow bring-up, turning a
                #    bounded start() into an unbounded first send.
                break
        if timeout is None:
            return
        elapsed = time.monotonic() - started_at
        # 🔔 #194: the WARNING fires whenever the allowance was EXCEEDED,
        #    including the case `asyncio.wait` could not observe -- a
        #    plain-`def` entry action that never yields holds the loop
        #    thread, so the wait's timer cannot fire until it returns, by
        #    which time the task is already done. A bound cannot pre-empt
        #    non-yielding code on a single thread (see the docs); it can
        #    and now does report that it was overrun.
        if overran or elapsed > timeout:
            logger.warning(
                "⏳ Interpreter '%s': invoked child bring-up exceeded the "
                "%.3fs children_timeout (%.3fs elapsed, %d still starting). "
                "start() continues with the machine running. A plain-`def` "
                "entry action that blocks cannot be pre-empted on the event "
                "loop thread -- make it `async def`, or offload the blocking "
                "call (#181 / #194).",
                self.id,
                timeout,
                elapsed,
                overran,
            )

    def _invoke_plain_service_inline(
        self,
        invocation: InvokeDefinition,
        service: Callable[..., Any],
        owner_id: str,
    ) -> None:
        """Run a non-coroutine service off the loop; the step awaits it.

        🏛️ #116 made a plain callable complete INSIDE the macrostep that
        enters the invoking state, so `done.invoke` lands ahead of any
        event already in the inbox -- the same point the sync engine
        completes it. #149: doing that by calling the function on the loop
        thread stalled every timer, actor and inbound send for the
        service's full duration. The call now runs on
        `_get_service_executor()`; the macrostep awaits the result
        (`_await_inline_services`) so the ORDERING is unchanged while the
        loop keeps turning. Failure is reported on the loop thread through
        the same `_report_service_failure` path. If the callable returns an
        awaitable after all (a plain `def` returning a coroutine), it is
        awaited as a task instead.
        """
        for plugin in self._plugins:
            plugin.on_service_start(self, invocation)
        try:
            invoke_event = Event(
                type=f"invoke.{invocation.id}",
                payload={
                    "input": invocation.resolve_input(self.context, None) or {}
                },
            )
        except Exception as exc:  # noqa: BLE001 -- user code (input factory)
            self._report_service_failure(invocation, exc)
            return

        loop = asyncio.get_running_loop()
        owner = self.machine.get_state_by_id(owner_id)

        async def _settle() -> None:
            # 🧵 #193: the executor handoff happens HERE, inside the task
            #    the engine holds, not eagerly at entry. A transition that
            #    arms this invoke and is then rolled back (a later entry
            #    action raised under `actionErrorPolicy: "rollback"`) or
            #    rolled forward (an `always` leaves the state before it
            #    stabilises) cancels this task via `_cancel_state_tasks`
            #    BEFORE it runs -- so the callable is never submitted, as
            #    a coroutine service's task is never started. Eager
            #    submission left a `def` service running for a state the
            #    machine had already left, with no handle to unwind.
            await asyncio.sleep(0)
            if owner is not None and owner not in self._active_state_nodes:
                return  # armed by a step that was undone; never submit
            try:
                handoff = loop.run_in_executor(
                    self._get_service_executor(),
                    service,
                    self,
                    self.context,
                    invoke_event,
                )
            except RuntimeError as exc:  # executor already shut down
                self._report_service_failure(invocation, exc)
                return
            try:
                produced = await handoff
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 -- user code
                self._report_service_failure(invocation, exc)
                return
            # 🚫 SCXML 6.4.2 (#193): once the invoking state has been
            #    exited, events from that invocation MUST be ignored. The
            #    entering macrostep awaits this result, so ordinarily the
            #    owner is still active here (#116 parity with the sync
            #    engine, where a plain service completes inside the step);
            #    this guards the exit-during-await shapes only.
            if owner is not None and owner not in self._active_state_nodes:
                logger.debug(
                    "🚫 Plain service '%s' finished after its state '%s' "
                    "was exited; result ignored (SCXML 6.4.2).",
                    invocation.id,
                    owner_id,
                )
                return
            self._finish_plain_service(invocation, owner_id, produced)

        fut = asyncio.ensure_future(_settle())
        self._inline_service_futures.append(fut)
        self.task_manager.add(owner_id, fut)

    def _finish_plain_service(
        self, invocation: InvokeDefinition, owner_id: str, produced: Any
    ) -> None:
        """Deliver a plain service's result (#116 / #149 tail)."""
        if inspect.isawaitable(produced):
            # A `def` that returned an awaitable after all: await it in a
            # task, with the same success / failure handling as the
            # coroutine path (`_invoke_service_task`).
            async def _finish() -> None:
                try:
                    result = await produced
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # noqa: BLE001 -- user code
                    self._report_service_failure(invocation, exc)
                    return
                self._publish_completion(  # #179: charged lane
                    _engine_done(
                        type=f"done.invoke.{invocation.id}",
                        data=result,
                        src=invocation.id,
                    )
                )
                for plugin in self._plugins:
                    plugin.on_service_done(self, invocation, result)

            self.task_manager.add(owner_id, asyncio.create_task(_finish()))
            return
        done_event = _engine_done(
            type=f"done.invoke.{invocation.id}",
            data=produced,
            src=invocation.id,
        )
        self._publish_completion(done_event)
        logger.info(
            "✅ Service '%s' (ID: '%s') completed (plain service).",
            invocation.src,
            invocation.id,
        )
        for plugin in self._plugins:
            plugin.on_service_done(self, invocation, produced)

    async def _start_invoked_actor(
        self,
        invocation: InvokeDefinition,
        actor_machine: MachineNode,
        owner_id: str,
    ) -> None:
        """Create and start an invoked child; wire completion as a PUSH.

        🏛️ #43: the previous design awaited `child.wait_done()` inside a
        dedicated manager task, so every idle invoked child cost two
        asyncio tasks (its run loop + the waiter). The waiter did nothing
        but sleep on a future and then call `send()`. That is exactly what
        a terminal listener does with no task at all, so the listener now
        owns completion delivery and this coroutine returns as soon as the
        child is running. N idle children cost N tasks and zero wake-ups.

        Cancellation: exiting the owning state used to cancel the manager
        task, whose `except CancelledError` stopped the child. With no task
        to cancel, the child is registered in `_invoked_children[owner_id]`
        and `_cancel_state_tasks` stops it directly. The "child finished
        during start()" race is handled because `wait_done()` semantics are
        preserved: a child already terminal when the listener is attached
        fires it immediately.

        Args:
            invocation: The invoke definition containing the actor's config.
            actor_machine: The MachineNode definition for the actor.
            owner_id: The id of the state that owns this invocation.
        """
        child_interpreter: Optional["Interpreter[Any]"] = None
        try:
            # 🏛️ #40: mint the address from the DECLARED `id` when there is
            #    one, so `sendTo("kid")` reaches the child invoked as
            #    `{"src": ..., "id": "kid"}`. Anonymous invokes keep the uuid
            #    suffix so two of them in one state stay distinct.
            actor_id = (
                f"{self.id}:{invocation.id}"
                if invocation.id_is_explicit
                else f"{self.id}:{invocation.src}:{uuid.uuid4()}"
            )
            # 📥 #42: resolve `input` against the PARENT's live context. A
            #    raising resolver is a child failure -> `onError`.
            child_input = invocation.resolve_input(self.context, None)
            # 🕰️ Same inheritance as `_spawn_actor`: clock (#49) + strict (#51).
            child_interpreter = Interpreter(
                actor_machine,
                input=child_input,
                clock=self.clock,
                strict=self.strict,
            )
            child_interpreter.parent = self
            child_interpreter.id = actor_id
            child_interpreter._invoked_as = invocation.id  # #156
            self._actors[actor_id] = child_interpreter
            self._actor_sources[actor_id] = invocation.src or ""
            self._invoked_children.setdefault(owner_id, []).append(
                child_interpreter
            )
            self._register_in_system(invocation.system_id, child_interpreter)

            for plugin in self._plugins:
                plugin.on_service_start(self, invocation)
            logger.info(
                "🚀 Actor '%s' (ID: %s) invoked by '%s'...",
                invocation.src,
                actor_id,
                self.id,
            )

            # 🔔 Completion is PUSHED. Attach BEFORE `start()` so a child
            #    whose initial state is final (terminal during start) is
            #    still observed exactly once -- `_on_terminal` fires the
            #    listener synchronously as `status` flips.
            child = child_interpreter
            fired = False

            def _on_child_terminal(status: str) -> None:
                nonlocal fired
                if fired:
                    return
                fired = True
                # Deliver from a fresh task: `_on_terminal` runs inside the
                # child's transition, and the parent's `send()` is async.
                self._loop_create_task(
                    self._deliver_invoked_completion(
                        invocation, child, owner_id, status
                    )
                )

            child_interpreter._terminal_listeners.append(_on_child_terminal)

            # 🚀 `start()` returns once the child's INITIAL state is entered;
            #    it does not run the child to completion.
            await child_interpreter.start()

        except asyncio.CancelledError:
            # 🚫 Owning state exited while we were still bringing the child
            #    up; stop it so nothing is orphaned.
            if child_interpreter is not None:
                await self._retire_invoked_child(
                    owner_id, child_interpreter, stop=True
                )
            raise
        except Exception as e:  # noqa: BLE001 -- user code (input/start)
            logger.error(
                "💥 Actor '%s' (ID: '%s') failed to start: %s",
                invocation.src,
                invocation.id,
                e,
                exc_info=True,
            )
            if child_interpreter is not None:
                await self._retire_invoked_child(
                    owner_id, child_interpreter, stop=True
                )
            self._publish_completion(  # #179: charged lane
                _engine_error(
                    type=f"error.platform.{invocation.id}",
                    error=e,
                    src=invocation.id,
                )
            )
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, e)

    async def _deliver_invoked_completion(
        self,
        invocation: InvokeDefinition,
        child: "Interpreter[Any]",
        owner_id: str,
        status: str,
    ) -> None:
        """Send `onDone` / `onError` for a finished invoked child (#43).

        Runs as a short task spawned by the child's terminal listener.
        Retires the child from the parent's maps first so a parent that
        transitions on `onDone` never sees a stale registry entry.
        """
        # 🧹 The child already tore itself down (#57); just forget it. Do
        #    NOT `stop()` it -- that would clear the `output` / `error` the
        #    parent is about to read.
        await self._retire_invoked_child(owner_id, child, stop=False)
        # 💥 A child that ended in `error`, OR one that STOPPED because its
        #    own `actionErrorPolicy: "fail"` halted it (#145: status is
        #    "stopped" with `error` set), both failed from the parent's
        #    point of view: neither reached a final state and both know why.
        child_error = getattr(child, "error", None)
        if status == "error" or (status == "stopped" and child_error):
            failure = child_error or RuntimeError(
                f"Invoked machine '{invocation.src}' failed."
            )
            logger.warning(
                "💥 Invoked machine '%s' ended in error; firing onError.",
                invocation.src,
            )
            # 🏛️ #99: with no `onError` declared the failure must not park
            #    the parent at `status="running"` forever -- indistinguishable
            #    from a healthy machine waiting on a slow child. Mirror the
            #    callable-service path (and the sync engine): fail the parent.
            handled = self._has_error_handler(invocation)
            self._publish_completion(  # #179: charged lane
                _engine_error(
                    type=f"error.platform.{invocation.id}",
                    error=failure,
                    src=invocation.id,
                )
            )
            for plugin in self._plugins:
                plugin.on_service_error(self, invocation, failure)
            if not handled:
                self._fail(failure)
            return
        # ✅ Reached a top-level final state. `onDone` carries the child's
        #    OUTPUT (#109) -- the value its final state declared -- not its
        #    private context. XState: "the output of a done actor is the
        #    output of its final state". Falls back to the context only for
        #    a child that declares no output, preserving 0.8.0 behaviour for
        #    machines that never used `output`.
        done_event = _engine_done(
            type=f"done.invoke.{invocation.id}",
            data=child.output if child.output is not None else child.context,
            src=invocation.id,
        )
        self._publish_completion(done_event)  # #179: charged lane
        for plugin in self._plugins:
            plugin.on_service_done(self, invocation, done_event.data)

    async def _retire_invoked_child(
        self,
        owner_id: str,
        child: "Interpreter[Any]",
        *,
        stop: bool,
    ) -> None:
        """Drop *child* from the parent's registries; optionally stop it."""
        self._actors.pop(child.id, None)
        self._actor_sources.pop(child.id, None)
        siblings = self._invoked_children.get(owner_id)
        if siblings is not None:
            try:
                siblings.remove(child)
            except ValueError:
                pass
            if not siblings:
                self._invoked_children.pop(owner_id, None)
        if stop and child.status == "running":
            await child.stop()

    def _loop_create_task(self, coro: Any) -> "asyncio.Task[Any]":
        """Schedule *coro* on this interpreter's loop (never the caller's)."""
        loop = self._loop or asyncio.get_running_loop()
        return loop.create_task(coro)
