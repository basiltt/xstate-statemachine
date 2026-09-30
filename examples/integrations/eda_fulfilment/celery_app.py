"""The Celery bridge: shipping as a Celery task, a statechart task, the
Beat timer scan and the outbox relay task.

Every app here is JSON-only (`assert_json_serializer`); the demo runs in
``task_always_eager`` mode against the in-memory transport, so no worker
or broker process is needed.
"""

from typing import Any

from celery import Celery

from xstate_statemachine.contrib.celery import (
    DurableTimerScheduler,
    assert_json_serializer,
    celery_service,
    outbox_relay_task,
    statechart_task,
)

import logic


def make_celery(*, eager: bool = True, name: str = "fulfilment") -> Celery:
    app = Celery(name, broker="memory://", backend="cache+memory://")
    app.conf.update(
        task_always_eager=eager,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        result_accept_content=["json"],
    )
    assert_json_serializer(app)
    return app


def ship_order_task(app: Celery) -> Any:
    """Register (once per app) the carrier call as a Celery task."""
    name = "fulfilment.ship_order"
    if name in app.tasks:
        return app.tasks[name]

    @app.task(name=name, serializer="json")
    def ship_order(order_id: str) -> dict:
        return {"trackingId": logic.tracking_for(order_id)}

    return ship_order


def ship_service(app: Celery, *, watch: bool = True) -> Any:
    """The ``shipOrder`` invoke ``src``: dispatch `ship_order` to Celery."""
    return celery_service(
        ship_order_task(app),
        args_from=lambda ctx, e: ((ctx.get("orderId"),), {}),
        watch=watch,
    )


def handle_order_event_task(
    app: Celery, store: Any, machine: Any, **kw: Any
) -> Any:
    """``handle_order_event.delay(key, type, payload)`` -- load, send,
    persist; a `ConflictError` is retried by Celery."""

    @statechart_task(
        app, store, machine, name="fulfilment.handle_order_event", **kw
    )
    def handle_order_event(order: Any, type: str, payload: dict) -> list:
        order.send(type, **(payload or {}))
        return sorted(order.current_state_ids)

    return handle_order_event


def timer_scheduler(
    app: Celery, store: Any, machine_for_key: Any, **kw: Any
) -> DurableTimerScheduler:
    """The Beat scan that fires persisted ``after`` deadlines (run EXACTLY
    one Beat process)."""
    return DurableTimerScheduler(app, store, machine_for_key, **kw)


def relay_task(app: Celery, outbox: Any, broker: Any) -> Any:
    return outbox_relay_task(app, outbox, broker, name="fulfilment.relay")
