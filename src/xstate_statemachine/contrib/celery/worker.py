# src/xstate_statemachine/contrib/celery/worker.py
# -----------------------------------------------------------------------------
# 👷 @statechart_task -- load → act → persist → discard on a worker (#292)
# -----------------------------------------------------------------------------
# 🏛️ The worker-side act-loop is `persisted()` from Phase A. Concurrency
#    between workers is optimistic: a save that lost the race raises
#    `ConflictError`, and the task is RETRIED by Celery's own
#    ``autoretry_for`` (so retries are visible in Flower / the result
#    backend, not hidden in a loop). With ``acks_late=True`` a worker crash
#    re-runs the task -- make ``fn`` idempotent (or dedup with an inbox).
#
# 🔐 Amendment: messages are JSON only. `assert_json_serializer` refuses
#    an app whose ``task_serializer`` is not ``"json"`` or that accepts
#    ``pickle`` -- a pickle-accepting worker executes whatever the broker
#    hands it.
# -----------------------------------------------------------------------------
"""`statechart_task` and `assert_json_serializer`."""

from __future__ import annotations

import functools
from typing import Any, Callable, Optional

from ...exceptions import ConflictError, InvalidConfigError

__all__ = ["assert_json_serializer", "statechart_task"]


def assert_json_serializer(app: Any) -> None:
    """Raise `InvalidConfigError` unless *app* speaks JSON only."""
    conf = app.conf
    if conf.task_serializer != "json":
        raise InvalidConfigError(
            f"statechart tasks need task_serializer='json', got "
            f"{conf.task_serializer!r} (pickle executes broker input)"
        )
    accept = conf.accept_content or ()
    if any("pickle" in str(c) for c in accept):
        raise InvalidConfigError(
            "statechart tasks refuse an app whose accept_content allows "
            "pickle"
        )


def statechart_task(
    app: Any,
    store: Any,
    machine_for_key: Any,
    *,
    lock: Optional[Any] = None,
    plugins: Any = (),
    name: Optional[str] = None,
    max_retries: int = 10,
    **task_options: Any,
) -> Callable[[Callable[..., Any]], Any]:
    """Register ``fn(interp, *args, **kwargs)`` as a Celery task that runs
    inside ``persisted(store, key, machine)``; the task's first argument
    is the instance key::

        @statechart_task(app, store, order_machine)
        def pay(order, amount):
            order.send("PAY", amount=amount)

        pay.delay("order-1", 42)

    Args:
        app: The Celery app (JSON serializer enforced).
        store: A `StateStore` every worker can reach.
        machine_for_key: A `MachineNode`, or ``(key) -> MachineNode``.
        lock: A `LockStrategy`; default optimistic (conflict -> retry).
        plugins: Attached to every instance.
        name / max_retries / task_options: Passed to ``app.task``.
    """
    assert_json_serializer(app)
    from ...persistence import persisted

    def decorate(fn: Callable[..., Any]) -> Any:
        @functools.wraps(fn)
        def run(key: str, *args: Any, **kwargs: Any) -> Any:
            machine = (
                machine_for_key(key)
                if callable(machine_for_key)
                else machine_for_key
            )
            with persisted(
                store, key, machine, lock=lock, plugins=plugins
            ) as interp:
                return fn(interp, *args, **kwargs)

        options = {
            "autoretry_for": (ConflictError,),
            "retry_backoff": 0.05,
            "retry_backoff_max": 2,
            "retry_jitter": True,
            "max_retries": max_retries,
            "serializer": "json",
        }
        options.update(task_options)
        if name is not None:
            options["name"] = name
        return app.task(**options)(run)

    return decorate
