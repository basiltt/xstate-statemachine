# src/xstate_statemachine/contrib/celery/service.py
# -----------------------------------------------------------------------------
# 📞 celery_service -- a Celery task as an `invoke` src (#292)
# -----------------------------------------------------------------------------
# 🏛️ Two lifetimes, one bridge:
#
#    * LIVE (a long-running interpreter): the service dispatches the task
#      and returns a `RunningLogic` handle; a daemon watcher polls the
#      result backend and completes the invocation through the engine's
#      own `_complete_logic` / `_fail_logic` (engine-minted events -- the
#      only way `onDone` fires; a user `send("done.invoke.x")` is refused
#      by the engine). ``timeout_s`` -> `onError` with `TimeoutError`.
#      Exiting the state ``revoke()``s the task (best effort,
#      ``terminate=False``); a mere ``stop()`` (end of a `persisted()`
#      block) only stops the watcher.
#    * DURABLE (create -> act -> persist -> discard): the task id is
#      recorded in the context under ``_xsm_celery`` (so it is in the
#      snapshot) and sent in the task headers. The completion arrives
#      later via `deliver_result` -- from the ``task_success`` /
#      ``task_failure`` signal handlers (`connect_signals`) or from
#      `poll_results` -- which re-opens the instance and completes the
#      invocation ONLY if it is still active AND records this task id.
#      Anything else is a stale completion: ignored, logged, reported to
#      ``on_event_dropped`` (reason ``"stale_invocation"``).
#    * EAGER (``task_always_eager`` / a result already ready): the result
#      is returned inline, exactly like a plain service.
# -----------------------------------------------------------------------------
"""`celery_service`, `deliver_result`, `poll_results`, `connect_signals`."""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from ...actor_logic import RunningLogic, _invocation_of
from ...events import Event

__all__ = [
    "CONTEXT_KEY",
    "HEADER_INVOCATION",
    "HEADER_KEY",
    "HEADER_STATE_SEQ",
    "CeleryInvocation",
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
HEADER_STATE_SEQ = "xsm_state_seq"
POLL_S = 0.05


@dataclass(frozen=True)
class CeleryInvocation:
    """What `poll_results` found for one pending invocation."""

    key: str
    invocation_id: str
    task_id: str
    deadline: Optional[float]


def _default_args(ctx: Any, event: Any) -> Tuple[tuple, dict]:
    return (), {}


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
        task: A Celery task (``@app.task``).
        args_from: ``(ctx, event) -> (args, kwargs)`` for ``apply_async``.
        timeout_s: `onError` with `TimeoutError` after this many seconds
            (live watcher and `poll_results`); ``None`` waits forever.
        queue: Celery queue to route to.
        poll_s: Result-backend polling interval of the live watcher.
        watch: Start the live watcher (``False`` = durable delivery only).

    Returns:
        A service callable for `MachineLogic(services=...)`.
    """

    def _service(interp: Any, ctx: Any, event: Any) -> Any:
        invocation = _invocation_of(interp, event)
        args, kwargs = args_from(ctx, event)
        headers = {
            HEADER_INVOCATION: invocation.id,
            HEADER_STATE_SEQ: int(getattr(interp, "_entry_seq", 0)),
        }
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
        handle = RunningLogic(interp, invocation, None, completes=True)
        stop = threading.Event()

        def cleanup() -> None:
            stop.set()
            if interp.status == "running":  # state EXIT, not stop()
                _revoke(result)

        handle._cleanup = cleanup
        if watch:
            threading.Thread(
                target=_watch,
                args=(
                    interp,
                    invocation,
                    handle,
                    result,
                    timeout_s,
                    poll_s,
                    stop,
                ),
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


def _still_mine(interp: Any, invocation: Any, handle: Any) -> bool:
    """This watcher's invocation is still the live one. Invocation ids
    are static per state, so after exit + re-entry a NEW handle sits
    under the same id -- an old watcher must never complete it."""
    return (
        interp.status == "running"
        and interp._running_logic.get(invocation.id) is handle
    )


def _settle_live(
    interp: Any, invocation: Any, handle: Any, result: Any, fn: Any
) -> None:
    """Deliver once, and only for this handle. The live completion also
    retires the durable ``_xsm_celery`` record so a signal handler or
    `poll_results` cannot apply the same completion a second time."""
    if not _still_mine(interp, invocation, handle):
        return
    pending = interp.context.get(CONTEXT_KEY)
    if isinstance(pending, dict):
        rec = pending.get(invocation.id)
        if isinstance(rec, dict) and rec.get("task_id") == result.id:
            pending.pop(invocation.id, None)
    fn()


def _watch(
    interp: Any,
    invocation: Any,
    handle: Any,
    result: Any,
    timeout_s: Optional[float],
    poll_s: float,
    stop: threading.Event,
) -> None:
    started = time.monotonic()
    while not stop.is_set():
        if _is_ready(result):
            try:
                value = _value(result)  # may block on the backend
            except Exception as exc:  # noqa: BLE001 - the task failed
                err = exc
                _settle_live(
                    interp,
                    invocation,
                    handle,
                    result,
                    lambda: interp._fail_logic(invocation, err),
                )
            else:
                _settle_live(
                    interp,
                    invocation,
                    handle,
                    result,
                    lambda: interp._complete_logic(invocation, value),
                )
            return
        if timeout_s is not None and time.monotonic() - started > timeout_s:
            if stop.is_set() or not _still_mine(interp, invocation, handle):
                return
            _revoke(result)
            timeout_err = TimeoutError(
                f"celery task {result.id} did not finish in {timeout_s}s"
            )
            _settle_live(
                interp,
                invocation,
                handle,
                result,
                lambda: interp._fail_logic(invocation, timeout_err),
            )
            return
        stop.wait(poll_s)


# -----------------------------------------------------------------------------
# 📬 durable delivery
# -----------------------------------------------------------------------------
def _machine(machine_for_key: Any, key: str) -> Any:
    return (
        machine_for_key(key)
        if callable(machine_for_key)
        else (machine_for_key)
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
) -> bool:
    """Complete *invocation_id* on the persisted instance *key*.

    Header values are TRUSTED only after this check: the instance exists,
    the invocation is still active, and it records *task_id*. Returns
    ``True`` when the completion was applied and saved.
    """
    from ...persistence import persisted_retry

    machine = _machine(machine_for_key, key)

    def act(interp: Any) -> bool:
        pending = interp.context.get(CONTEXT_KEY) or {}
        rec = pending.get(invocation_id)
        inv = _active_invocation(interp, invocation_id)
        if inv is None or not rec or rec.get("task_id") != task_id:
            _dropped(interp, invocation_id, "not the active invocation")
            if rec and rec.get("task_id") == task_id:
                pending.pop(invocation_id, None)  # finished after exit
            return False
        pending.pop(invocation_id, None)
        if error is not None:
            interp._fail_logic(inv, error)
        else:
            interp._complete_logic(inv, result)
        interp.tick()
        return True

    if store.load(key) is None:
        logger.warning("🔥 celery completion for unknown key %r", key)
        return False
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


def poll_results(
    store: Any,
    machine_for_key: Any,
    *,
    app: Any,
    prefix: str = "",
    now: Optional[Callable[[], float]] = None,
    lock: Optional[Any] = None,
    plugins: Any = (),
) -> int:
    """Result-backend fallback for durable delivery (no signals needed,
    e.g. the worker is another process). Delivers every finished task,
    fails (and revokes) every invocation past its ``timeout_s`` deadline.
    Returns how many completions were applied."""
    from celery.result import AsyncResult

    clock = now or time.time
    applied = 0
    for p in pending_invocations(store, prefix=prefix):
        res = AsyncResult(p.task_id, app=app)
        kw: Dict[str, Any] = {}
        if _is_ready(res):
            try:
                kw["result"] = _value(res)
            except Exception as exc:  # noqa: BLE001 - the task failed
                kw["error"] = exc
        elif p.deadline is not None and clock() > p.deadline:
            _revoke(res)
            kw["error"] = TimeoutError(f"celery task {p.task_id} timed out")
        else:
            continue
        if deliver_result(
            store,
            machine_for_key,
            p.key,
            p.invocation_id,
            p.task_id,
            lock=lock,
            plugins=plugins,
            **kw,
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
    lock: Optional[Any] = None,
    plugins: Any = (),
) -> Callable[[], None]:
    """Install ``task_success`` / ``task_failure`` handlers (worker side)
    that deliver completions of `celery_service` tasks. Returns a
    ``disconnect()`` callable. Eager tasks are ignored (they completed
    inline)."""
    from celery.signals import task_failure, task_success

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
