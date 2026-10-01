"""Choreography: three orders reach ``shipped`` through events alone."""

import json

ORDERS = ("o-1", "o-2", "o-3")


def _place_all(app_):
    for n, oid in enumerate(ORDERS, start=1):
        app_.command(oid, "PAY", orderId=oid, total=10 * n)
    return app_.pump()


def test_three_orders_reach_shipped(fulfilment):
    _place_all(fulfilment)
    for oid in ORDERS:
        assert fulfilment.state_of(f"order:{oid}") == ["order.shipped"]
        assert fulfilment.state_of(f"warehouse:{oid}") == ["warehouse.packed"]
        rec = fulfilment.store.load(f"order:{oid}")
        ctx = json.loads(rec.snapshot)["context"]
        assert ctx["trackingId"] == f"TRK-{oid}"


def test_every_outbox_row_was_published_once(fulfilment):
    _place_all(fulfilment)
    published = [
        e for e in fulfilment.broker.published if e.source != "checkout"
    ]
    assert fulfilment.outbox.count() == len(published) == 9
    assert fulfilment.outbox.count(pending_only=True) == 0
    assert len({e.id for e in published}) == len(published)
    assert sorted({e.type for e in published}) == [
        "OrderPacked",
        "OrderPaid",
        "OrderShipped",
    ]


def test_per_subject_order_is_preserved(fulfilment):
    _place_all(fulfilment)
    for oid in ORDERS:
        seq = [
            e.type
            for e in fulfilment.broker.published
            if e.subject == oid and e.source != "checkout"
        ]
        assert seq == ["OrderPaid", "OrderPacked", "OrderShipped"], seq


def test_causation_chain(fulfilment):
    _place_all(fulfilment)
    for cmd in fulfilment.commands:
        out = {
            e.type: e
            for e in fulfilment.broker.published
            if e.subject == cmd.subject
        }
        paid, packed = out["OrderPaid"], out["OrderPacked"]
        assert paid.causationid == cmd.id
        assert packed.causationid == paid.id
        assert out["OrderShipped"].causationid == packed.id
        # 📝 one conversation, one correlation id.
        assert {paid.correlationid, packed.correlationid} == {cmd.id}


def test_published_data_is_the_declared_fields_only(fulfilment):
    fulfilment.command("o-9", "PAY", orderId="o-9", total=7, card="4111")
    fulfilment.pump()
    paid = next(
        e for e in fulfilment.broker.published if e.type == "OrderPaid"
    )
    assert paid.data == {"orderId": "o-9", "total": 7}


def test_audit_log_records_each_transition(fulfilment):
    _place_all(fulfilment)
    events = [r.event_type for r in fulfilment.log.read("order:o-1")]
    assert events[:2] == ["PAY", "PACKED"]
    assert fulfilment.transitions("order:o-1") == 3


def test_guard_blocks_a_zero_total(fulfilment):
    fulfilment.command("o-0", "PAY", orderId="o-0", total=0)
    fulfilment.pump()
    assert fulfilment.state_of("order:o-0") == ["order.placed"]
    assert fulfilment.outbox.count() == 0


def test_packing_late_escalation_publishes(tmp_path):
    """The ``after`` on ``paid`` fires through the persisted deadline."""
    import app
    from xstate_statemachine.clock import SimulatedClock
    from xstate_statemachine.persistence import DueTimerScanner

    a = app.build_app("fake", tmp_path, celery=False)
    try:
        a.router.dispatcher.clock = SimulatedClock(wall_start=1_000.0)
        a.command("o-5", "PAY", orderId="o-5", total=5)
        a.relay.relay_once_sync()
        a.router.run_until_quiet_sync(a.broker)  # order paid; no PACK yet
        # ⚠️ the warehouse got OrderPaid only if relayed; it was not.
        assert a.state_of("order:o-5") == ["order.paid"]
        scanner = DueTimerScanner(
            a.store,
            a.machine_for_key,
            plugins=a.plugins,
            now=lambda: 1_000.0 + 61,
        )
        assert scanner.run_once() == 1
        assert a.state_of("order:o-5") == ["order.packingLate"]
        a.pump()
        types = [e.type for e in a.broker.published]
        assert "PackingLate" in types
        # the late order still completes when the warehouse catches up.
        assert a.state_of("order:o-5") == ["order.shipped"]
    finally:
        a.close()
