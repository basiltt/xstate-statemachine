# src/xstate_statemachine/actor_logic.py
# -----------------------------------------------------------------------------
# 🎭 Actor logic helpers -- XState v5 `fromPromise` / `fromCallback` /
#    `fromObservable` parity for Python (#267)
# -----------------------------------------------------------------------------
# 🏛️ A Python service today is "just a callable": fine for a one-shot
#    coroutine, awkward for CALLBACK-STYLE SDKs (a websocket client,
#    paho-mqtt, a GUI toolkit) that push many events into the machine over
#    time, and for STREAMS (an async iterator of LLM chunks, a Kafka
#    consumer). These helpers are the bridge every integration in phases
#    C-F uses to feed external events in, so they live in the zero-dep
#    core.
#
#    Mechanism: a helper returns an ordinary service callable. When the
#    engine runs it, the callable returns a `RunningLogic` handle instead
#    of a result. The engine recognises the handle and:
#      * does NOT publish `done.invoke` (the logic completes -- or not --
#        on its own terms and says so through the handle);
#      * calls `handle.cleanup()` exactly once when the invoking state
#        exits, the interpreter stops, or the logic errors;
#      * routes `sendTo(<invocation id>, ...)` to `handle.receive(event)`.
#
# 🧵 Threading rules, pinned: `send_back` is safe from ANY thread or loop.
#    On the async engine it goes through `Interpreter.send_threadsafe`
#    (`call_soon_threadsafe`); on the sync engine through
#    `SyncInterpreter.send_threadsafe` (#305), whose mailbox the owning
#    thread drains on its next `send()` / `tick()` -- the same rule as
#    sync timers. Never the plain queue (review amendment).
# -----------------------------------------------------------------------------
"""`from_coroutine`, `from_callable`, `from_callback`, `from_async_iterator`,
`from_iterator`, `from_interpreter`."""

from __future__ import annotations

import asyncio
import inspect
import threading
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    List,
    Optional,
    TypeVar,
)

from .events import StreamEvent
from .logger import logger

__all__ = [
    "RunningLogic",
    "drain_pending_cleanups",
    "SendBack",
    "from_async_iterator",
    "from_callable",
    "from_callback",
    "from_coroutine",
    "from_interpreter",
    "from_iterator",
]

T = TypeVar("T")
SendBack = Callable[..., None]
Receive = Callable[[Callable[[Any], None]], None]
Cleanup = Callable[[], Any]


# -----------------------------------------------------------------------------
# 🧩 The handle the engine recognises
# -----------------------------------------------------------------------------
class RunningLogic:
    """What a long-lived actor-logic service returns to the engine.

    Attributes:
        cleanup: Called exactly once when the invoking state exits, the
            interpreter stops, or the logic fails. Idempotent by
            construction (`_done` latch).
        completes: ``False`` for callback logic (never `onDone` on its
            own); ``True`` for streams, whose completion the logic itself
            publishes via `complete()` / `fail()`.
    """

    __slots__ = (
        "_cleanup",
        "_receivers",
        "_done",
        "_lock",
        "completes",
        "_interp",
        "_invocation",
    )

    def __init__(
        self,
        interp: Any,
        invocation: Any,
        cleanup: Optional[Cleanup],
        *,
        completes: bool,
    ) -> None:
        self._interp = interp
        self._invocation = invocation
        self._cleanup = cleanup
        self._receivers: List[Callable[[Any], None]] = []
        self._done = False
        self._lock = threading.Lock()
        self.completes = completes

    # -- parent -> logic ----------------------------------------------------------
    def subscribe(self, handler: Callable[[Any], None]) -> None:
        with self._lock:
            self._receivers.append(handler)

    def receive(self, event: Any) -> bool:
        """Deliver an event the parent `sendTo`'d this invocation. Returns
        whether any handler was registered."""
        with self._lock:
            handlers = list(self._receivers)
        for h in handlers:
            try:
                h(event)
            except Exception:  # noqa: BLE001 -- user handler
                logger.exception(
                    "🎭 receive() handler for '%s' raised; ignoring.",
                    getattr(self._invocation, "id", "?"),
                )
        return bool(handlers)

    # -- lifecycle ------------------------------------------------------------------
    @property
    def finished(self) -> bool:
        return self._done

    def cleanup(self) -> None:
        """Run the cleanup once; later calls are no-ops."""
        with self._lock:
            if self._done:
                return
            self._done = True
            fn, self._cleanup = self._cleanup, None
        if fn is None:
            return
        try:
            result = fn()
            if inspect.isawaitable(result):
                _schedule_awaitable(result)
        except Exception:  # noqa: BLE001 -- user cleanup
            logger.exception(
                "🎭 cleanup for '%s' raised; ignoring.",
                getattr(self._invocation, "id", "?"),
            )


#: Tasks for `async def` cleanups still running; `Interpreter._teardown`
#: awaits them so `stop()` returns only after every cleanup finished.
_PENDING_CLEANUPS: "set[asyncio.Task[Any]]" = set()


def _schedule_awaitable(aw: Awaitable[Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No loop on this thread: run it to completion in a private one.
        asyncio.run(_await(aw))
        return
    task = loop.create_task(_await(aw))
    _PENDING_CLEANUPS.add(task)
    task.add_done_callback(_PENDING_CLEANUPS.discard)


#: How long `stop()` waits for `async def` cleanups before giving up on
#: them (they are cancelled and logged, never awaited forever).
DEFAULT_CLEANUP_TIMEOUT = 30.0


async def drain_pending_cleanups(
    timeout: Optional[float] = DEFAULT_CLEANUP_TIMEOUT,
) -> None:
    """Await every scheduled `async def` cleanup (engine teardown hook).

    Args:
        timeout: Seconds to wait for the cleanups of the current loop.
            A cleanup still running afterwards is cancelled and logged
            (``None`` waits without bound).
    """
    # 📝 #267 battle: the registry is module-global and every
    #    `asyncio.run` makes a new loop; a task left by a closed / foreign
    #    loop made `gather` raise ValueError ("different loop"). Drain only
    #    THIS loop's tasks; forget the ones whose loop is closed.
    loop = asyncio.get_running_loop()
    for t in list(_PENDING_CLEANUPS):
        if t.get_loop() is not loop and t.get_loop().is_closed():
            _PENDING_CLEANUPS.discard(t)
    pending = [
        t
        for t in list(_PENDING_CLEANUPS)
        if not t.done() and t.get_loop() is loop
    ]
    if not pending:
        return
    # 📝 #267 battle (B): a cleanup that never returns (a socket close
    #    waiting on a dead peer) used to hang `stop()` forever. Bound it.
    _done, still = await asyncio.wait(pending, timeout=timeout)
    for t in still:
        t.cancel()
        _PENDING_CLEANUPS.discard(t)
    if still:
        logger.warning(
            "🎭 %d async cleanup(s) still running after %ss; cancelled.",
            len(still),
            timeout,
        )


async def _await(aw: Awaitable[Any]) -> None:
    await aw


#: Keyword names `send()` / `send_threadsafe()` treat as controls on at
#: least one engine; `send_back` refuses them as payload (#267 battle).
_RESERVED_SEND_KWARGS = frozenset({"internal", "wait", "priority"})


def _send_back_for(
    interp: Any, handle: Optional[RunningLogic] = None
) -> SendBack:
    """A thread-safe `send_back(event_or_type, **payload)` for *interp*.

    Dropped (debug log, never an exception in the producer) once *handle*
    was cleaned up or the interpreter is no longer running. A malformed
    event still raises `InvalidEventError` on the calling thread.
    """

    def send_back(event_or_type: Any, **payload: Any) -> None:
        # 📝 #267 battle (B): `send_back("X", internal=True)` would reach
        #    the async engine's `send_threadsafe(internal=...)` as a
        #    CONTROL argument, not payload -- and silently differ per
        #    engine. Payload keys that collide with send() controls are a
        #    caller error on both engines.
        reserved = _RESERVED_SEND_KWARGS.intersection(payload)
        if reserved:
            raise TypeError(
                "send_back(): payload key(s) %s are reserved; send a dict "
                "event {'type': ..., ...} to carry them" % sorted(reserved)
            )
        # 📝 #267 battle: a producer of an EXITED invocation kept feeding
        #    the machine -- its events landed in whatever state came next
        #    (SCXML 6.4.2: events from a cancelled invocation are ignored).
        if handle is not None and handle.finished:
            logger.debug("🎭 send_back after cleanup dropped")
            return
        if interp.status != "running":
            return
        try:
            interp.send_threadsafe(event_or_type, **payload)
        except RuntimeError:
            # 📝 #267 battle: status->send TOCTOU on the async engine (it
            #    stopped, or its loop was closed, between the check and the
            #    call). Not the producer's problem: drop, loudly enough.
            loop = getattr(interp, "_loop", None)
            closed = loop is not None and loop.is_closed()
            if interp.status == "running" and not closed:
                raise
            logger.warning(
                "🎭 send_back to '%s' dropped: interpreter is gone.",
                getattr(interp, "id", "?"),
            )

    return send_back


# -----------------------------------------------------------------------------
# 🎬 one-shot helpers (parity names)
# -----------------------------------------------------------------------------
def from_coroutine(
    fn: Callable[..., Awaitable[T]],
) -> Callable[..., Awaitable[T]]:
    """An ``async def (interp, ctx, event)`` service -- today's async
    service, under XState's ``fromPromise`` name. Async engine only."""
    if not inspect.iscoroutinefunction(fn):
        raise TypeError("from_coroutine() needs an `async def`")
    return fn


def from_callable(fn: Callable[..., T]) -> Callable[..., T]:
    """A plain ``def (interp, ctx, event)`` service; its return value is
    ``event.data`` on `onDone`. Works on both engines (inline)."""
    if inspect.iscoroutinefunction(fn):
        raise TypeError(
            "from_callable() needs a plain `def`; use from_coroutine"
        )
    return fn


# -----------------------------------------------------------------------------
# 📞 from_callback
# -----------------------------------------------------------------------------
def from_callback(
    setup: Callable[..., Optional[Cleanup]],
) -> Callable[..., RunningLogic]:
    """Callback-style actor logic (XState ``fromCallback``).

    ``setup(send_back, receive, ctx, event)`` runs once when the invoking
    state is entered. ``send_back(type, **payload)`` (or an `Event`)
    delivers events to the parent machine -- thread-safe, from any thread
    or loop. ``receive(handler)`` subscribes to events the parent
    ``sendTo``s this invocation's id. Return a cleanup callable (or
    ``None``); it is called exactly once when the state exits, the
    interpreter stops, or *setup* raised. The logic never completes on its
    own, so there is no ``onDone``; an exception inside *setup* is
    ``onError``.

    ::

        def mqtt(send_back, receive, ctx, event):
            client.on_message = lambda msg: send_back("MESSAGE", topic=msg.topic)
            receive(lambda ev: client.publish(ev.payload["topic"], ev.payload["body"]))
            client.connect()
            return client.disconnect
    """

    def _service(interp: Any, ctx: Any, event: Any) -> RunningLogic:
        handle = RunningLogic(
            interp, _invocation_of(interp, event), None, completes=False
        )
        cleanup = setup(
            _send_back_for(interp, handle), handle.subscribe, ctx, event
        )
        if cleanup is not None and not callable(cleanup):
            raise TypeError(
                "from_callback setup must return a cleanup callable or None"
            )
        handle._cleanup = cleanup
        return handle

    _service.__name__ = f"callback_{getattr(setup, '__name__', 'logic')}"
    _service.__xsm_actor_logic__ = "callback"  # type: ignore[attr-defined]
    return _service


# -----------------------------------------------------------------------------
# 🌊 from_async_iterator / from_iterator
# -----------------------------------------------------------------------------
def from_async_iterator(
    factory: Callable[..., AsyncIterator[Any]], *, event_type: str = "STREAM"
) -> Callable[..., Awaitable[Any]]:
    """Stream actor logic (XState ``fromObservable``), async engine.

    ``factory(interp, ctx, event)`` returns an async iterator (an
    ``async def`` generator). Each yielded item is sent to the parent as
    ``StreamEvent(event_type, {"data": item})`` -- ``event.data`` is the
    item (``event.payload["data"]`` too).
    Exhaustion is ``onDone`` with ``data`` = the last item; an exception is
    ``onError``; exiting the state cancels the task and ``aclose()``s the
    generator (a ``finally`` in it runs).
    """

    async def _service(interp: Any, ctx: Any, event: Any) -> Any:
        agen = factory(interp, ctx, event)
        if inspect.isawaitable(agen):  # a coroutine returning an iterator
            agen = await agen
        last: Any = None
        aclose = getattr(agen, "aclose", None)
        try:
            async for item in agen:
                last = item
                # 📝 `wait=True`: the completion this service publishes on
                #    return rides the PRIORITY lane and would overtake items
                #    still in the inbox -- `onDone` before the last STREAM
                #    was applied. Waiting for each item's receipt keeps
                #    stream order and completion order the same.
                if interp.status != "running":
                    break
                await interp.send(
                    StreamEvent(event_type, {"data": item}), wait=True
                )
            return last
        finally:
            if callable(aclose):
                try:
                    await aclose()
                except Exception:  # noqa: BLE001 -- generator finalizer
                    logger.debug("🌊 aclose() raised; ignoring", exc_info=True)

    _service.__name__ = f"stream_{getattr(factory, '__name__', 'logic')}"
    _service.__xsm_actor_logic__ = "async_iterator"  # type: ignore[attr-defined]
    return _service


#: How long `from_iterator`'s cleanup waits for its worker to notice stop.
_ITERATOR_STOP_GRACE_S = 0.1


def from_iterator(
    factory: Callable[..., Iterator[Any]], *, event_type: str = "STREAM"
) -> Callable[..., RunningLogic]:
    """Stream actor logic for the SYNC engine: ``factory(interp, ctx,
    event)`` returns an iterator that is consumed on a daemon thread. Each
    item is `send_threadsafe`'d to the parent as ``StreamEvent(event_type,
    {"data": item})`` and lands on the owner's next ``send()`` / ``tick()``;
    exhaustion delivers ``onDone`` (``data`` = last item), an exception
    ``onError``. Exiting the state stops the thread at the next item and
    ``close()``s the generator.

    On the async engine prefer `from_async_iterator`; this helper works
    there too (the thread pushes through `send_threadsafe`).
    """

    def _service(interp: Any, ctx: Any, event: Any) -> RunningLogic:
        invocation = _invocation_of(interp, event)
        stop = threading.Event()
        gen = factory(interp, ctx, event)
        close = getattr(gen, "close", None)
        handle = RunningLogic(interp, invocation, None, completes=True)
        send_back = _send_back_for(interp, handle)

        def run() -> None:
            last: Any = None
            try:
                for item in gen:
                    if stop.is_set():
                        return
                    last = item
                    send_back(StreamEvent(event_type, {"data": item}))
                if not stop.is_set():
                    interp._complete_logic(invocation, last)
            except Exception as exc:  # noqa: BLE001 -- user iterator
                if not stop.is_set():
                    interp._fail_logic(invocation, exc)
            finally:
                if callable(close):
                    try:
                        close()
                    except Exception:  # noqa: BLE001
                        pass

        thread = threading.Thread(
            target=run, name=f"xsm-stream-{invocation.id}", daemon=True
        )

        def cleanup() -> None:
            stop.set()
            # 📝 #267 battle: `stop` is seen only BETWEEN items; an iterator
            #    blocked inside `next()` (a socket read) kept the thread
            #    alive while cleanup claimed success. Contract: the iterator
            #    must return / raise promptly. Short grace, then say so.
            if thread is threading.current_thread() or not thread.is_alive():
                return
            thread.join(_ITERATOR_STOP_GRACE_S)
            if thread.is_alive():
                logger.warning(
                    "🌊 from_iterator '%s' is blocked inside next(); its "
                    "thread lingers until the iterator returns.",
                    invocation.id,
                )

        handle._cleanup = cleanup
        thread.start()
        return handle

    _service.__name__ = f"stream_{getattr(factory, '__name__', 'logic')}"
    _service.__xsm_actor_logic__ = "iterator"  # type: ignore[attr-defined]
    return _service


# -----------------------------------------------------------------------------
# 🎭 from_interpreter
# -----------------------------------------------------------------------------
def from_interpreter(child: Any) -> Any:
    """Use an EXISTING interpreter's machine as a child actor (XState
    ``fromActor`` parity). A `MachineNode` is already a valid ``invoke``
    ``src``; this helper reads it off an interpreter so an application
    that built the child up front can hand it over: the engine starts a
    fresh actor of that machine under the invocation id (child actors are
    per-invocation; the passed instance itself is not adopted -- an
    interpreter is bound to its own loop / thread)."""
    machine = getattr(child, "machine", None)
    if machine is None:
        raise TypeError("from_interpreter() needs an interpreter instance")
    return machine


def _invocation_of(interp: Any, event: Any) -> Any:
    """The `InvokeDefinition` the engine is running (`invoke.<id>` event)."""
    inv_id = str(getattr(event, "type", ""))[len("invoke.") :]
    for state in list(interp._active_state_nodes):
        for inv in getattr(state, "invoke", ()):
            if inv.id == inv_id:
                return inv
    for state in getattr(interp, "_states_to_invoke", ()):
        for inv in getattr(state, "invoke", ()):
            if inv.id == inv_id:
                return inv

    class _Anon:  # pragma: no cover - defensive
        id = inv_id
        src = None

    return _Anon()
