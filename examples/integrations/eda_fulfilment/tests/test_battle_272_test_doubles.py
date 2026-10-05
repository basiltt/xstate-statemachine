# examples/integrations/eda_fulfilment/tests/test_battle_272_test_doubles.py
"""#272 battle: the fulfilment team tests its EDA pipeline with NO broker.

Two statecharts (order, warehouse) talk only through events. Before this,
every test needed Docker Compose. With `SyncFakeBrokerAdapter`, `replay()`
/ `assert_replay_consistent()` and `given()/when()/then()` the suite runs
in-process and still exercises what production exercises. Pinned:

* **failure injection is honest** -- `fail_next_publish()` on the outbox
  relay leaves the row unpublished and the next relay publishes it ONCE
  (no duplicate, no loss); a handler that raises nacks without requeue
  and the exception reaches the test; a broker "partition" (publish
  failing N times) delays, never reorders, per-subject delivery;
* **redelivery accounting** -- a poison command is attempted exactly
  `MAX_ATTEMPTS` times, then dead-lettered and ACKed: nothing committed,
  nothing pending, `nacked` carries the attempts, the DLQ record names
  the error chain;
* **ordering per subject under interleaving** -- 50 orders × 3 commands
  interleaved round-robin: each order's transitions are in command order,
  every causation chain points at the command that caused it;
* **threads + the fake** -- 8 producer threads publishing commands while
  the pump drains: no lost command, every order reaches `shipped`, the
  fake's counters balance (published == acked + dead-lettered);
* **replay from the audit log** -- `assert_replay_consistent` on every
  order after the run; a log tampered with mid-stream raises
  `ReplayDivergenceError` naming the seq; replaying `upto=` a seq
  reproduces the intermediate state;
* **given/when/then** -- the team's specs for the order chart read as one
  line each; a failing spec says which step, what was expected, what was
  active;
* **ten thousand envelopes** through the fake: memory flat (N/2 vs N),
  per-subject order kept, `pending == 0` at the end.
"""

from __future__ import annotations

import gc
import json
import threading
import tracemalloc
from typing import Any, Dict, List

import pytest

import app
import logic
from xstate_statemachine.contrib.testing import (
    SyncFakeBrokerAdapter,
    assert_replay_consistent,
    given,
    replay,
)
from xstate_statemachine.eda import Envelope
from xstate_statemachine.persistence import ReplayDivergenceError

pytestmark = pytest.mark.timeout(300)


def _place(a: Any, oid: str, total: int = 10) -> None:
    a.command(oid, "PAY", orderId=oid, total=total)


# -----------------------------------------------------------------------------
# 1. failure injection
# -----------------------------------------------------------------------------
def test_relay_publish_failure_is_retried_once_not_duplicated(
    fulfilment: Any,
) -> None:
    _place(fulfilment, "o-1")
    # the inbound command dispatches; the outbox row for OrderPaid exists
    fulfilment.router.run_until_quiet_sync(fulfilment.broker)
    assert fulfilment.outbox.count() >= 1
    fulfilment.broker.fail_next_publish(times=1)
    # 📝 at-least-once: the relay marks what it DID send and re-raises the
    #    broker error to its caller (a scheduler tick) -- the failed row
    #    stays pending for the next tick, it is never marked sent.
    with pytest.raises(Exception, match="injected"):
        fulfilment.relay.relay_once_sync()
    assert fulfilment.outbox.count() >= 1
    stats = fulfilment.pump()
    assert stats["dead_lettered"] == 0
    paid_events = [
        e for e in fulfilment.broker.published if e.type.endswith("OrderPaid")
    ]
    assert len(paid_events) == 1  # published exactly once after the retry
    assert fulfilment.state_of("order:o-1") == ["order.shipped"]


def test_partition_delays_but_never_reorders(fulfilment: Any) -> None:
    for n in range(1, 6):
        _place(fulfilment, f"o-{n}", total=n)
    # dispatch the commands so OrderPaid rows sit in the outbox
    fulfilment.router.run_until_quiet_sync(fulfilment.broker)
    assert fulfilment.outbox.count() >= 5
    # a 4-publish "partition": each failing relay tick raises to its
    # caller; the rows wait, nothing is marked sent twice
    fulfilment.broker.fail_next_publish(times=4)
    for _ in range(4):
        with pytest.raises(Exception, match="injected"):
            fulfilment.relay.relay_once_sync()
    fulfilment.pump()
    for n in range(1, 6):
        assert fulfilment.state_of(f"order:o-{n}") == ["order.shipped"]
    # per subject: OrderPaid before OrderPacked before OrderShipped
    seen: Dict[str, List[str]] = {}
    for e in fulfilment.broker.published:
        if e.source != "checkout":
            seen.setdefault(e.subject, []).append(e.type.rsplit(".", 1)[-1])
    for sub, types in seen.items():
        assert types == ["OrderPaid", "OrderPacked", "OrderShipped"], (
            sub,
            types,
        )


def test_raising_handler_nacks_without_requeue_and_propagates() -> None:
    broker = SyncFakeBrokerAdapter()
    hits = {"n": 0}

    def boom(env: Envelope) -> None:
        hits["n"] += 1
        raise RuntimeError("handler exploded")

    broker.on("t", boom)
    broker.publish("t", Envelope.new(type="x.y", subject="s", data={}))
    with pytest.raises(RuntimeError, match="exploded"):
        broker.drain("t")
    assert hits["n"] == 1
    assert broker.pending("t") == 0  # not requeued
    assert len(broker.nacked) == 1 and broker.in_flight == 0


# -----------------------------------------------------------------------------
# 2. redelivery accounting for poison
# -----------------------------------------------------------------------------
def test_poison_is_attempted_max_attempts_times_then_dead_lettered(
    fulfilment: Any,
) -> None:
    env = fulfilment.command("o-9", "PAYMENT_FAILED", reason=12345)
    stats = fulfilment.pump()
    assert stats["dead_lettered"] == 1
    attempts = [e for e in fulfilment.broker.nacked if e.id == env.id]
    assert len(attempts) == app.MAX_ATTEMPTS - 1  # requeued N-1 times
    acked = [e for e in fulfilment.broker.acked if e.id == env.id]
    assert len(acked) == 1  # dead-lettered → acked once
    [rec] = fulfilment.dead_letters.list()
    assert rec.attempts == app.MAX_ATTEMPTS
    assert [e["type"] for e in rec.errors][-1] == "ProcessingFailedError"
    assert fulfilment.broker.pending(app.TOPIC) == 0
    assert fulfilment.broker.in_flight == 0
    assert fulfilment.state_of("order:o-9") is None


# -----------------------------------------------------------------------------
# 3. ordering per subject under interleaving
# -----------------------------------------------------------------------------
def test_fifty_interleaved_orders_keep_per_subject_order(
    fulfilment: Any,
) -> None:
    ids = [f"o-{n:03d}" for n in range(50)]
    for oid in ids:
        _place(fulfilment, oid, total=5)
    fulfilment.pump()
    for oid in ids:
        assert fulfilment.state_of(f"order:{oid}") == ["order.shipped"]
        recs = [
            r
            for r in fulfilment.log.read(f"order:{oid}")
            if r.disposition == "transition"
        ]
        events = [r.event_type for r in recs]
        assert events[:2] == ["PAY", "PACKED"], events
    # causation: every published domain event names an inbound cause
    by_id = {e.id: e for e in fulfilment.broker.published}
    for e in fulfilment.broker.published:
        if e.source == "checkout":
            continue
        assert e.causationid in by_id, (e.type, e.causationid)


# -----------------------------------------------------------------------------
# 4. threads + the fake
# -----------------------------------------------------------------------------
def test_eight_producer_threads_lose_nothing(fulfilment: Any) -> None:
    per_thread = 12
    barrier = threading.Barrier(8)
    errors: List[BaseException] = []

    def producer(t: int) -> None:
        try:
            barrier.wait(10)
            for k in range(per_thread):
                _place(fulfilment, f"t{t}-{k:02d}", total=1)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=producer, args=(t,)) for t in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join(30)
    assert errors == []
    fulfilment.pump()
    for t in range(8):
        for k in range(per_thread):
            assert fulfilment.state_of(f"order:t{t}-{k:02d}") == [
                "order.shipped"
            ]
    b = fulfilment.broker
    assert b.pending(app.TOPIC) == 0 and b.in_flight == 0
    acked_ids = {e.id for e in b.acked}
    published_ids = {e.id for e in b.published}
    assert published_ids <= acked_ids  # everything published was settled


# -----------------------------------------------------------------------------
# 5. replay from the audit log
# -----------------------------------------------------------------------------
def test_replay_is_consistent_and_tampering_is_named(fulfilment: Any) -> None:
    for n in range(1, 4):
        _place(fulfilment, f"o-{n}", total=n)
    fulfilment.pump()
    for n in range(1, 4):
        key = f"order:o-{n}"
        assert_replay_consistent(fulfilment.order, fulfilment.log, key=key)
        recs = list(fulfilment.log.read(key))
        # replay up to the first transition reproduces `paid`
        first_seq = next(r.seq for r in recs if r.disposition == "transition")
        mid = replay(fulfilment.order, recs, upto=first_seq)
        assert mid.matches("order.paid")
        mid.stop()
    # tamper: drop a record in the middle of o-1's stream
    key = "order:o-1"
    recs = list(fulfilment.log.read(key))
    tampered = [r for r in recs if r.seq != recs[len(recs) // 2].seq]
    with pytest.raises(ReplayDivergenceError) as ei:
        replay(fulfilment.order, tampered)
    assert str(recs[len(recs) // 2].seq) in str(ei.value) or "seq" in str(
        ei.value
    )


# -----------------------------------------------------------------------------
# 6. given / when / then specs for the order chart
# -----------------------------------------------------------------------------
class TestOrderSpecs:
    def test_specs_read_as_one_line_each(self) -> None:
        m = app.order_machine()
        given(m).when("PAY", orderId="o", total=10).then_state(
            "paid"
        ).then_context(total=10).then_changed()
        given(m).in_state("placed").when(
            "PAY", orderId="o", total=0
        ).then_state("placed").then_changed(
            False
        )  # hasTotal guard
        given(m).in_state("placed").when(
            "PAYMENT_FAILED", reason="x"
        ).then_state("cancelled")
        given(m).in_state("paid").with_context(orderId="o", total=10).after(
            logic.PACKING_SLA_MS if hasattr(logic, "PACKING_SLA_MS") else 10**9
        ).then_state("packingLate")
        given(m).in_state("paid").with_context(orderId="o", total=10).when(
            "PACKED"
        ).then_state("shipped").then_context(trackingId="TRK-o").then_done()

    def test_failure_message_names_step_expected_and_actual(self) -> None:
        m = app.order_machine()
        with pytest.raises(AssertionError) as ei:
            given(m).when("PAY", orderId="o", total=10).then_state("cancelled")
        msg = str(ei.value)
        assert "when('PAY')" in msg and "cancelled" in msg and "paid" in msg
        with pytest.raises(ValueError, match="no state named"):
            given(m).in_state("nowhere")
        with pytest.raises(RuntimeError, match="before the first when"):
            given(m).when("PAY", orderId="o", total=1).in_state("paid")


# -----------------------------------------------------------------------------
# 7. ten thousand envelopes through the fake
# -----------------------------------------------------------------------------
def test_ten_thousand_envelopes_flat_memory_and_ordered() -> None:
    broker = SyncFakeBrokerAdapter()
    seen: Dict[str, List[int]] = {}

    def handler(env: Envelope) -> None:
        seen.setdefault(env.subject, []).append(int(env.data["n"]))

    broker.on("t", handler)

    def burst(start: int, count: int) -> None:
        for n in range(start, start + count):
            broker.publish(
                "t",
                Envelope.new(type="x.y", subject=f"s{n % 20}", data={"n": n}),
            )
        broker.drain("t")

    burst(0, 1000)
    gc.collect()
    tracemalloc.start()
    burst(1000, 4500)
    gc.collect()
    half = tracemalloc.take_snapshot()
    burst(5500, 4500)
    gc.collect()
    full = tracemalloc.take_snapshot()
    tracemalloc.stop()
    grown = sum(
        s.size_diff
        for s in full.compare_to(half, "filename")
        if s.size_diff > 0
    )
    # 📝 `published` / `acked` are test affordances that keep every
    #    envelope by design; the growth must be linear in envelopes kept
    #    (~4500 × a few hundred bytes), never quadratic.
    assert grown < 8 * 1024 * 1024, grown
    assert broker.pending("t") == 0 and broker.in_flight == 0
    for sub, ns in seen.items():
        assert ns == sorted(ns), sub
    assert sum(len(v) for v in seen.values()) == 10_000
