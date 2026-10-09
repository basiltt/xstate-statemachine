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
# 🔐 Review H3: messages AND results are JSON only.
#    `assert_json_serializer` refuses an app whose task or result
#    serializer is not ``json``, or whose ``accept_content`` /
#    ``result_accept_content`` admits pickle or YAML by name OR by MIME
#    type (``application/x-python-serialize``, ``application/x-yaml``).
#    `result.get()` deserialises with the result settings, so they matter
#    as much as the task ones. Every entry point calls it.
# -----------------------------------------------------------------------------
"""`statechart_task` and `assert_json_serializer`."""

from __future__ import annotations

import functools
from typing import Any, Callable, Iterable, Optional

from ...exceptions import (
    ConflictError,
    InvalidConfigError,
    LockTimeoutError,
)

__all__ = [
    "register_task",
    "UNSAFE_CONTENT",
    "assert_json_serializer",
    "statechart_task",
]

#: Serializer names / MIME types that execute or construct arbitrary
#: objects on deserialisation.
UNSAFE_CONTENT = (
    "pickle",
    "application/x-python-serialize",
    "yaml",
    "application/x-yaml",
    "application/yaml",
    "text/yaml",
)


def _unsafe(values: Optional[Iterable[Any]]) -> list:
    return [
        str(v)
        for v in (values or ())
        if any(bad in str(v).lower() for bad in UNSAFE_CONTENT)
    ]


def register_task(app: Any, fn: Any, **options: Any) -> Any:
    """``app.task(shared=False, **options)(fn)``, refusing a taken name.

    🔥 #292 battle: Celery tasks are ``shared=True`` by default -- a task
    registered on app A is RE-CREATED on every app built later, with A's
    closure (its store, its machine, its outbox). The example's second
    `FulfilmentApp` ran the FIRST app's Beat scan against the first
    app's database and reported "0 woken" for its own. These tasks are
    bound to one store, so they are registered ``shared=False``; and
    because ``app.task`` silently returns an existing task of the same
    name, a genuine same-app duplicate is refused -- pass ``name=`` to
    register more than one on an app.

    Raises:
        InvalidConfigError: the name is already a task on *app*.
    """
    name = options.get("name") or app.gen_task_name(fn.__name__, fn.__module__)
    # 📝 `app.tasks` (not the private `_tasks`): it finalises the app,
    #    so pending shared registrations from OTHER apps are visible too
    # 🔥 #292-a battle: on an ``autofinalize=False`` app (the pattern for
    #    apps configured after import) `app.tasks` raises "Contract breach:
    #    app not finalized" -- every helper failed to register. Read the
    #    registry without finalising there.
    finalized = getattr(app, "finalized", True) or getattr(
        app, "autofinalize", True
    )
    registry = app.tasks if finalized else app._tasks
    if name in registry:
        raise InvalidConfigError(
            f"a Celery task named {name!r} is already registered on this "
            f"app; pass a distinct name= (the existing task would "
            f"otherwise be returned with ITS store / machine / outbox)"
        )
    options.setdefault("shared", False)
    return app.task(**options)(fn)


def assert_json_serializer(app: Any) -> None:
    """Raise `InvalidConfigError` unless *app* speaks JSON only.

    Checks ``task_serializer``, ``result_serializer``, ``accept_content``
    and ``result_accept_content`` (``None`` there means "same as
    ``accept_content``").
    """
    conf = app.conf
    for name in ("task_serializer", "result_serializer"):
        value = getattr(conf, name, "json")
        if value != "json":
            raise InvalidConfigError(
                f"statechart tasks need {name}='json', got {value!r} "
                "(pickle / YAML execute broker input)"
            )
    for name in ("accept_content", "result_accept_content"):
        bad = _unsafe(getattr(conf, name, None))
        if bad:
            raise InvalidConfigError(
                f"statechart tasks refuse an app whose {name} allows "
                f"{', '.join(bad)}"
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

    ⚠️ A `ConflictError` retry RE-RUNS ``fn`` from the start on a freshly
    loaded instance -- including any side effect it performed outside the
    machine (an HTTP call, an email). Keep side effects in machine
    actions/services or make them idempotent.

    Retries back off exponentially from 1 s (Celery rounds
    ``retry_backoff`` up to a whole second) to ``retry_backoff_max``
    (2 s), with full jitter; override either through *task_options*.

    Args:
        app: The Celery app (JSON-only, see `assert_json_serializer`).
        store: A `StateStore` every worker can reach.
        machine_for_key: A `MachineNode`, or ``(key) -> MachineNode``.
        lock: A `LockStrategy`; default optimistic. A `ConflictError` or
            a `LockTimeoutError` retries the task.
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
            # 🔥 #292-a battle: a `PessimisticLock` that could not be
            #    taken in time is as transient as a lost optimistic race
            #    (`LockTimeoutError` is documented "Retryable"); it used to
            #    FAIL the task on the first contended lock.
            "autoretry_for": (ConflictError, LockTimeoutError),
            # 📝 Celery computes `int(max(1.0, retry_backoff))` -- a
            #    sub-second value is silently 1 s; say so honestly.
            "retry_backoff": 1,
            "retry_backoff_max": 2,
            "retry_jitter": True,
            "max_retries": max_retries,
            "serializer": "json",
        }
        options.update(task_options)
        if name is not None:
            options["name"] = name
        return register_task(app, run, **options)

    return decorate
