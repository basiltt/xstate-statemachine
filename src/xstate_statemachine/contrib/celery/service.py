# src/xstate_statemachine/contrib/celery/service.py
# -----------------------------------------------------------------------------
# 📞 celery_service -- a Celery task as an `invoke` src (#292)
# -----------------------------------------------------------------------------
# 🏛️ Two lifetimes, one bridge:
#
#    * LIVE (a long-running interpreter): the service dispatches the task
#      and returns a `RunningLogic` handle; a daemon watcher polls the
#      result backend. The watcher never touches the machine itself: it
#      MINTS the engine completion (`_engine_done` / `_engine_error`) and
#      hands it to ``send_threadsafe``. A per-interpreter `_LiveGuard`
#      plugin then decides ON THE ENGINE THREAD (``on_before_send``)
#      whether that completion still belongs to the live invocation (same
#      `RunningLogic` handle -- ids are static per state, so exit +
#      re-entry is a new handle), retires the handle and the durable
#      ``_xsm_celery`` record, or short-circuits it. Check and act happen
#      in one place, on one thread (review M4). A settled task is never
#      revoked (M6). ``timeout_s`` -> `onError` with `TimeoutError`.
#    * DURABLE (create -> act -> persist -> discard): the task id is
#      recorded in the context under ``_xsm_celery`` (so it is in the
#      snapshot). `poll_results` is THE durable path: it reads that record
#      and the result backend. The ``task_success`` / ``task_failure``
#      signal handlers (`connect_signals`) are a low-latency shortcut; a
#      completion that arrives BEFORE the caller saved the record (the
#      worker was faster than the ``persisted()`` block) is parked in a
#      `MemoryPendingResults` table and retried by `poll_results`, never
#      dropped (review H1).
#    * EAGER (``task_always_eager`` / a result already ready): the result
#      is returned inline, exactly like a plain service.
#
# 🔐 Every entry point refuses an app that could deserialise pickle / YAML
#    (`assert_json_serializer`, review H3).
# -----------------------------------------------------------------------------
"""`celery_service`, `deliver_result`, `poll_results`, `connect_signals`."""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...actor_logic import RunningLogic, _invocation_of
from ...events import (
    DoneEvent,
    ErrorEvent,
    Event,
    Receipt,
    _engine_done,
    _engine_error,
)
from ...plugins import PluginBase
from .worker import assert_json_serializer

__all__ = [
    "CONTEXT_KEY",
    "HEADER_INVOCATION",
    "HEADER_KEY",
    "CeleryInvocation",
    "MemoryPendingResults",
    "PendingResult",
    "celery_service",
    "connect_signals",
    "deliver_result",
    "poll_results",
]

logger = logging.getLogger(__name__)

#: Context key holding ``{invocation_id: {"task_id", "deadline"}}``.
CONTEXT_KEY = "_xsm_celery"
HEADER_KEY = "xsm_store_key"
HEADER_INVOCATION = "xsm_invocation_id"
POLL_S = 0.05
#: How long a parked early completion is retried before it is given up.
PENDING_TTL_S = 3600.0
#: Most parked completions one process holds (#292 battle B): the headers
#: are broker input, so a flood of forged ``xsm_store_key`` values must
#: not grow worker memory without bound. The oldest entry is evicted.
PENDING_MAX_ITEMS = 10_000


@dataclass(frozen=True)
class CeleryInvocation:
    """What `poll_results` found for one pending invocation.

    Attributes:
        key: The store key of the persisted instance.
        invocation_id: The ``invoke`` id recorded under ``_xsm_celery``.
        task_id: The Celery task id the instance is waiting for.
        deadline: Wall-clock ``timeout_s`` deadline, or ``None``.
    """

    key: str
    invocation_id: str
    task_id: str
    deadline: Optional[float]


def _default_args(ctx: Any, event: Any) -> Tuple[tuple, dict]:
    return (), {}


# -----------------------------------------------------------------------------
# 🎭 live delivery
# -----------------------------------------------------------------------------
@dataclass
class _Live:
    """One dispatched task of a live interpreter."""

    invocation: Any
    result: Any
    handle: Any = None
    stop: threading.Event = field(default_factory=threading.Event)
    settled: bool = False


class _LiveGuard(PluginBase[Any]):
    """Admits a watcher's completion only for its own live invocation.

    Runs on the ENGINE thread (``on_before_send`` of a
    ``send_threadsafe``), so the identity check, the handle retirement and
    the ``_xsm_celery`` pop cannot race a state exit / re-entry.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._outbox: Dict[int, _Live] = {}

    def post(self, interp: Any, live: _Live, event: Any) -> None:
        with self._lock:
            self._outbox[id(event)] = live
        interp.send_threadsafe(event)

    def on_before_send(self, interpreter: Any, event: Any) -> Any:
        if not isinstance(event, (DoneEvent, ErrorEvent)):
            return None
        with self._lock:
            live = self._outbox.pop(id(event), None)
        if live is None:
            return None  # not ours
        inv_id = live.invocation.id
        current = interpreter._running_logic.get(inv_id)
        if current is not live.handle or interpreter.status != "running":
            logger.info("stale celery completion for %r discarded", inv_id)
            for plugin in interpreter._plugins:
                plugin.on_event_dropped(interpreter, event, "stale_invocation")
            return Receipt(frozenset(interpreter.current_state_ids), False)
        live.settled = True  # M6: a finished task is never revoked
        interpreter._running_logic.pop(inv_id, None)
        live.handle.cleanup()
        pending = interpreter.context.get(CONTEXT_KEY)
        if isinstance(pending, dict):
            rec = pending.get(inv_id)
            if isinstance(rec, dict) and rec.get("task_id") == live.result.id:
                pending.pop(inv_id, None)
        return None  # admit: drives onDone / onError


def _guard_of(interp: Any) -> _LiveGuard:
    for p in interp._plugins:
        inner = getattr(p, "wrapped", p)
        if isinstance(inner, _LiveGuard):
            return inner
    guard = _LiveGuard()
    interp.use(guard)
    return guard


def celery_service(
    task: Any,
    *,
    args_from: Callable[[Any, Any], Tuple[Any, Any]] = _default_args,
    timeout_s: Optional[float] = None,
    queue: Optional[str] = None,
    poll_s: float = POLL_S,
    watch: bool = True,
) -> Callable[..., Any]:
    """An ``invoke`` service that runs *task* on a Celery worker.

    Args:
        task: A Celery task (``@app.task``). Its app must be JSON-only
            (`assert_json_serializer`).
        args_from: ``(ctx, event) -> (args, kwargs)`` for ``apply_async``.
        timeout_s: `onError` with `TimeoutError` after this many seconds
            (live watcher and `poll_results`); ``None`` waits forever.
        queue: Celery queue to route to.
        poll_s: Result-backend polling interval of the live watcher.
        watch: Start the live watcher (``False`` = durable delivery only).

    Returns:
        A service callable for `MachineLogic(services=...)`.

    Raises:
        InvalidConfigError: the task's app accepts pickle / YAML.
    """
    app = getattr(task, "app", None)
    if app is not None and hasattr(app, "conf"):
        assert_json_serializer(app)

    def _service(interp: Any, ctx: Any, event: Any) -> Any:
        invocation = _invocation_of(interp, event)
        args, kwargs = args_from(ctx, event)
        headers = {HEADER_INVOCATION: invocation.id}
        key = getattr(interp, "store_key", None)
        if key:
            headers[HEADER_KEY] = key
        opts: Dict[str, Any] = {"headers": headers}
        if queue is not None:
            opts["queue"] = queue
        result = task.apply_async(tuple(args), dict(kwargs), **opts)
        if _is_ready(result):
            # ⚡ eager / already finished: behave like a plain service.
            return _value(result)
        deadline = None if timeout_s is None else interp.wall_now() + timeout_s
        ctx.setdefault(CONTEXT_KEY, {})[invocation.id] = {
            "task_id": result.id,
            "deadline": deadline,
        }
        live = _Live(invocation, result)
        handle = RunningLogic(interp, invocation, None, completes=True)
        live.handle = handle

        def cleanup() -> None:
            live.stop.set()
            if not live.settled and interp.status == "running":
                _revoke(result)  # state EXIT of an unfinished task

        handle._cleanup = cleanup
        if watch:
            guard = _guard_of(interp)
            threading.Thread(
                target=_watch,
                args=(interp, guard, live, timeout_s, poll_s),
                name=f"xsm-celery-{invocation.id}",
                daemon=True,
            ).start()
        return handle

    _service.__name__ = f"celery_{getattr(task, 'name', 'task')}"
    return _service


def _is_ready(result: Any) -> bool:
    try:
        return bool(result.ready())
    except Exception:  # noqa: BLE001 - backend unavailable: not ready
        return False


def _value(result: Any) -> Any:
    """The task's return value, or raise its exception (-> onError)."""
    return result.get(propagate=True, disable_sync_subtasks=False)


def _revoke(result: Any) -> None:
    try:
        result.revoke(terminate=False)
    except Exception:  # noqa: BLE001 - best effort by contract
        logger.debug("revoke of %s failed", getattr(result, "id", "?"))


def _watch(
    interp: Any,
    guard: _LiveGuard,
    live: _Live,
    timeout_s: Optional[float],
    poll_s: float,
) -> None:
    """Poll the backend; POST the completion -- never apply it here."""
    inv_id = live.invocation.id
    started = time.monotonic()
    while not live.stop.is_set():
        if _is_ready(live.result):
            try:
                value = _value(live.result)  # may block on the backend
            except Exception as exc:  # noqa: BLE001 - the task failed
                event: Any = _engine_error(
                    type=f"error.platform.{inv_id}", error=exc, src=inv_id
                )
            else:
                event = _engine_done(
                    type=f"done.invoke.{inv_id}", data=value, src=inv_id
                )
            _post(interp, guard, live, event)
            return
        if timeout_s is not None and time.monotonic() - started > timeout_s:
            if live.stop.is_set():
                return
            _revoke(live.result)
            err = TimeoutError(
                f"celery task {live.result.id} did not finish in {timeout_s}s"
            )
            _post(
                interp,
                guard,
                live,
                _engine_error(
                    type=f"error.platform.{inv_id}", error=err, src=inv_id
                ),
            )
            return
        live.stop.wait(poll_s)


def _post(interp: Any, guard: _LiveGuard, live: _Live, event: Any) -> None:
    if live.stop.is_set() or interp.status != "running":
        return
    try:
        guard.post(interp, live, event)
    except RuntimeError:  # the interpreter's loop is gone
        logger.debug("celery completion for a stopped interpreter dropped")


# -----------------------------------------------------------------------------
# 📬 durable delivery
# -----------------------------------------------------------------------------
@dataclass
class PendingResult:
    """A completion that arrived before its ``_xsm_celery`` record."""

    key: str
    invocation_id: str
    task_id: str
    result: Any = None
    error: Optional[BaseException] = None
    parked_at: float = field(default_factory=time.time)


class MemoryPendingResults:
    """Per-process table of early completions (review H1).

    `connect_signals` parks a completion here when the persisted instance
    does not record the task yet; `poll_results(pending=...)` retries it.
    Entries older than ``ttl_s`` are given up (logged). For completions
    that must survive a worker restart rely on `poll_results` reading the
    result backend -- that is the durable path.
    """

    def __init__(
        self,
        ttl_s: float = PENDING_TTL_S,
        max_items: int = PENDING_MAX_ITEMS,
    ) -> None:
        self.ttl_s = float(ttl_s)
        self.max_items = int(max_items)
        self._lock = threading.Lock()
        self._items: Dict[str, PendingResult] = {}

    def add(self, item: PendingResult) -> None:
        """Park *item*; evicts (and logs) the oldest entry when full."""
        with self._lock:
            self._items.pop(item.task_id, None)
            self._items[item.task_id] = item
            while len(self._items) > self.max_items:
                old = next(iter(self._items))
                self._items.pop(old)
                logger.warning(
                    "🔥 parked celery completion %s evicted (table full, "
                    "max_items=%d); poll_results reads it from the "
                    "result backend",
                    old,
                    self.max_items,
                )

    def take_all(self) -> List[PendingResult]:
        """Remove and return every parked completion."""
        with self._lock:
            items, self._items = list(self._items.values()), {}
        return items

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


def _machine(machine_for_key: Any, key: str) -> Any:
    return (
        machine_for_key(key) if callable(machine_for_key) else machine_for_key
    )


def _active_invocation(interp: Any, invocation_id: str) -> Any:
    for state in interp._active_state_nodes:
        for inv in getattr(state, "invoke", ()):
            if inv.id == invocation_id:
                return inv
    return None


def _dropped(interp: Any, invocation_id: str, why: str) -> None:
    logger.warning(
        "🔥 stale celery completion for %r on %r ignored: %s",
        invocation_id,
        getattr(interp, "store_key", None),
        why,
    )
    event = Event(type=f"done.invoke.{invocation_id}", payload={})
    for plugin in getattr(interp, "_plugins", ()):
        plugin.on_event_dropped(interp, event, "stale_invocation")


def _recorded_task(store: Any, key: str, invocation_id: str) -> Any:
    """``task_id`` the stored snapshot records for *invocation_id*;
    ``None`` = no record (yet); raises nothing."""
    rec = store.load(key)
    if rec is None:
        return None
    try:
        ctx = json.loads(rec.snapshot).get("context") or {}
        item = (ctx.get(CONTEXT_KEY) or {}).get(invocation_id)
    except (ValueError, AttributeError):
        return None
    return item.get("task_id") if isinstance(item, dict) else None


def deliver_result(
    store: Any,
    machine_for_key: Any,
    key: str,
    invocation_id: str,
    task_id: str,
    *,
    result: Any = None,
    error: Optional[BaseException] = None,
    lock: Optional[Any] = None,
    plugins: Any = (),
    pending: Optional[MemoryPendingResults] = None,
) -> bool:
    """Complete *invocation_id* on the persisted instance *key*.

    Header values are TRUSTED only after this check: the instance exists,
    the invocation is still active, and it records *task_id*.

    * No record for the invocation yet (the worker beat the caller's
      save): parked in *pending* (if given) for `poll_results` to retry;
      nothing is written. Returns ``False``.
    * A record naming ANOTHER task, or an inactive invocation: stale --
      ignored, logged, ``on_event_dropped(..., "stale_invocation")``.

    Returns ``True`` when the completion was applied and saved.
    """
    from ...persistence import persisted_retry

    recorded = _recorded_task(store, key, invocation_id)
    if recorded is None:
        if pending is not None:
            pending.add(
                PendingResult(key, invocation_id, task_id, result, error)
            )
            logger.info(
                "celery completion for %r on %r arrived before its "
                "record; parked for poll_results",
                invocation_id,
                key,
            )
        else:
            logger.warning(
                "🔥 celery completion for %r on %r has no record and no "
                "pending table; poll_results will deliver it from the "
                "result backend",
                invocation_id,
                key,
            )
        return False
    machine = _machine(machine_for_key, key)

    def act(interp: Any) -> bool:
        pend = interp.context.get(CONTEXT_KEY) or {}
        rec = pend.get(invocation_id)
        inv = _active_invocation(interp, invocation_id)
        if inv is None or not rec or rec.get("task_id") != task_id:
            _dropped(interp, invocation_id, "not the active invocation")
            if rec and rec.get("task_id") == task_id:
                pend.pop(invocation_id, None)  # finished after exit
            return False
        pend.pop(invocation_id, None)
        if error is not None:
            interp._fail_logic(inv, error)
        else:
            interp._complete_logic(inv, result)
        interp.tick()
        return True

    return bool(
        persisted_retry(
            store,
            key,
            machine,
            act,
            lock=lock,
            plugins=plugins,
            create_if_missing=False,
        )
    )


def pending_invocations(store: Any, *, prefix: str = "") -> List[Any]:
    """Every ``_xsm_celery`` record in *store* (reads snapshots only)."""
    out: List[CeleryInvocation] = []
    for key in store.list_keys(prefix=prefix):
        rec = store.load(key)
        if rec is None:
            continue
        try:
            ctx = json.loads(rec.snapshot).get("context") or {}
        except (ValueError, AttributeError):
            continue
        for inv_id, item in (ctx.get(CONTEXT_KEY) or {}).items():
            if isinstance(item, dict) and item.get("task_id"):
                out.append(
                    CeleryInvocation(
                        key, inv_id, str(item["task_id"]), item.get("deadline")
                    )
                )
    return out


def _retry_parked(
    store: Any,
    machine_for_key: Any,
    pending: MemoryPendingResults,
    clock: Callable[[], float],
    kw: Dict[str, Any],
) -> int:
    applied = 0
    for item in pending.take_all():
        if clock() - item.parked_at > pending.ttl_s:
            logger.warning(
                "🔥 giving up parked celery completion %s for %r",
                item.task_id,
                item.key,
            )
            continue
        if _recorded_task(store, item.key, item.invocation_id) is None:
            pending.add(item)  # still no record: keep it
            continue
        if deliver_result(
            store,
            machine_for_key,
            item.key,
            item.invocation_id,
            item.task_id,
            result=item.result,
            error=item.error,
            **kw,
        ):
            applied += 1
    return applied


def poll_results(
    store: Any,
    machine_for_key: Any,
    *,
    app: Any,
    prefix: str = "",
    now: Optional[Callable[[], float]] = None,
    lock: Optional[Any] = None,
    plugins: Any = (),
    pending: Optional[MemoryPendingResults] = None,
) -> int:
    """THE durable delivery path: schedule it with Beat.

    Retries completions *pending* parked (the worker finished before the
    record was saved), then reads every ``_xsm_celery`` record against the
    result backend: delivers finished tasks, fails (and revokes)
    invocations past their ``timeout_s`` deadline. Returns how many
    completions were applied.
    """
    from celery.result import AsyncResult

    assert_json_serializer(app)
    clock = now or time.time
    kw: Dict[str, Any] = {"lock": lock, "plugins": plugins}
    applied = 0
    if pending is not None:
        applied += _retry_parked(store, machine_for_key, pending, clock, kw)
    for p in pending_invocations(store, prefix=prefix):
        res = AsyncResult(p.task_id, app=app)
        outcome: Dict[str, Any] = {}
        if _is_ready(res):
            try:
                outcome["result"] = _value(res)
            except Exception as exc:  # noqa: BLE001 - the task failed
                outcome["error"] = exc
        elif p.deadline is not None and clock() > p.deadline:
            _revoke(res)
            outcome["error"] = TimeoutError(
                f"celery task {p.task_id} timed out"
            )
        else:
            continue
        if deliver_result(
            store,
            machine_for_key,
            p.key,
            p.invocation_id,
            p.task_id,
            **kw,
            **outcome,
        ):
            applied += 1
    return applied


def _header(request: Any, name: str) -> Any:
    value = getattr(request, name, None)
    if value is None:
        headers = getattr(request, "headers", None) or {}
        value = headers.get(name)
    return value


def connect_signals(
    store: Any,
    machine_for_key: Any,
    *,
    app: Any,
    lock: Optional[Any] = None,
    plugins: Any = (),
    pending: Optional[MemoryPendingResults] = None,
) -> Callable[[], None]:
    """Install ``task_success`` / ``task_failure`` handlers (worker side)
    that deliver completions of `celery_service` tasks -- a low-latency
    shortcut for `poll_results`. Completions that arrive before their
    record are parked in *pending* (pass the same table to
    `poll_results`). Returns a ``disconnect()`` callable. Eager tasks are
    ignored (they completed inline).

    Raises:
        InvalidConfigError: *app* accepts pickle / YAML.
    """
    from celery.signals import task_failure, task_success

    assert_json_serializer(app)

    def _deliver(sender: Any, **kw: Any) -> None:
        request = getattr(sender, "request", None)
        if request is None or getattr(request, "is_eager", False):
            return
        key = _header(request, HEADER_KEY)
        inv = _header(request, HEADER_INVOCATION)
        if not key or not inv:
            return  # not a celery_service task, or a non-persisted one
        try:
            deliver_result(
                store,
                machine_for_key,
                str(key),
                str(inv),
                str(request.id),
                result=kw.get("result"),
                error=kw.get("exception"),
                lock=lock,
                plugins=plugins,
                pending=pending,
            )
        except Exception:  # noqa: BLE001 - never break the worker
            logger.exception("🔥 delivering celery result for %r failed", key)

    def on_success(sender: Any = None, result: Any = None, **kw: Any) -> None:
        _deliver(sender, result=result)

    def on_failure(
        sender: Any = None, exception: Any = None, **kw: Any
    ) -> None:
        _deliver(sender, exception=exception)

    task_success.connect(on_success, weak=False)
    task_failure.connect(on_failure, weak=False)

    def disconnect() -> None:
        task_success.disconnect(on_success)
        task_failure.disconnect(on_failure)

    return disconnect
