"""The Celery bridge in eager mode: invoke, statechart task, Beat, relay."""

import pytest

pytest.importorskip("celery")

import app  # noqa: E402
import celery_app  # noqa: E402
from xstate_statemachine import PluginBase  # noqa: E402
from xstate_statemachine.clock import SimulatedClock  # noqa: E402
from xstate_statemachine.contrib.celery import (  # noqa: E402
    assert_json_serializer,
    deliver_result,
    statechart_task,
)
from xstate_statemachine.exceptions import InvalidConfigError  # noqa: E402
from xstate_statemachine.persistence import persisted  # noqa: E402


class Dropped(PluginBase):
    def __init__(self):
        self.reasons = []

    def on_event_dropped(self, interpreter, event, reason):
        self.reasons.append((event.type, reason))


def test_eager_celery_service_completes_the_invoke(fulfilment):
    assert fulfilment.celery.conf.task_always_eager
    fulfilment.command("o-1", "PAY", orderId="o-1", total=10)
    fulfilment.pump()
    assert fulfilment.state_of("order:o-1") == ["order.shipped"]
    shipped = [
        e for e in fulfilment.broker.published if e.type == "OrderShipped"
    ]
    assert shipped[0].data == {"orderId": "o-1", "trackingId": "TRK-o-1"}


def test_forged_task_id_is_ignored_then_the_real_one_lands(tmp_path):
    """Durable delivery: a completion is trusted only when the persisted
    instance records that task id for the ACTIVE invocation."""
    capp = celery_app.make_celery(eager=False, name="durable")
    machine = app.order_machine(celery_app.ship_service(capp, watch=False))
    store = app.SQLiteStore(tmp_path / "s.db")
    try:
        with persisted(store, "order:o-7", machine) as order:
            order.send("PAY", orderId="o-7", total=5)
            order.send("PACKED")
            assert order.current_state_ids == {"order.packed"}
            [(inv_id, rec)] = order.context["_xsm_celery"].items()
        dropped = Dropped()
        assert not deliver_result(
            store,
            machine,
            "order:o-7",
            inv_id,
            "forged-task-id",
            result={"trackingId": "EVIL"},
            plugins=[dropped],
        )
        assert dropped.reasons == [
            (f"done.invoke.{inv_id}", "stale_invocation")
        ]
        assert deliver_result(
            store,
            machine,
            "order:o-7",
            inv_id,
            rec["task_id"],
            result={"trackingId": "TRK-o-7"},
        )
        with persisted(store, "order:o-7", machine) as order:
            assert order.current_state_ids == {"order.shipped"}
            assert order.context["trackingId"] == "TRK-o-7"
    finally:
        store.close()


def test_statechart_task_drives_an_order(tmp_path):
    capp = celery_app.make_celery()
    machine = app.order_machine(celery_app.ship_service(capp))
    store = app.SQLiteStore(tmp_path / "s.db")
    try:
        task = celery_app.handle_order_event_task(capp, store, machine)
        res = task.delay("order:o-2", "PAY", {"orderId": "o-2", "total": 3})
        assert res.get() == ["order.paid"]
        assert task.delay("order:o-2", "PACKED", {}).get() == ["order.shipped"]
    finally:
        store.close()


def test_pickle_config_is_refused(tmp_path):
    capp = celery_app.make_celery(name="unsafe")
    capp.conf.accept_content = ["json", "pickle"]
    with pytest.raises(InvalidConfigError):
        assert_json_serializer(capp)
    with pytest.raises(InvalidConfigError):
        statechart_task(capp, None, None)
    capp.conf.accept_content = ["json"]
    capp.conf.task_serializer = "pickle"
    with pytest.raises(InvalidConfigError):
        celery_app.ship_service(capp)


def test_beat_scan_fires_the_escalation_exactly_once(tmp_path):
    a = app.build_app("fake", tmp_path)
    try:
        a.router.dispatcher.clock = SimulatedClock(wall_start=1_000.0)
        a.command("o-3", "PAY", orderId="o-3", total=5)
        a.router.run_until_quiet_sync(a.broker)  # paid; OrderPaid unrelayed
        assert a.state_of("order:o-3") == ["order.paid"]
        now = [1_000.0 + 30]
        sched = celery_app.timer_scheduler(
            a.celery,
            a.store,
            a.machine_for_key,
            plugins=a.plugins,
            now=lambda: now[0],
        )
        assert sched.task.delay().result == 0  # not due yet
        now[0] = 1_000.0 + 61
        assert sched.task.delay().result == 1
        assert sched.task.delay().result == 0  # already fired
        assert a.state_of("order:o-3") == ["order.packingLate"]
        relay = celery_app.relay_task(a.celery, a.outbox, a.broker)
        assert relay.delay().result == 2  # OrderPaid + PackingLate
        assert [e.type for e in a.broker.published][-2:] == [
            "OrderPaid",
            "PackingLate",
        ]
    finally:
        a.close()
