# examples/integrations/eda_fulfilment/tests/test_battle_292_scenario.py
"""#292 battle: the `[celery]` bridge on a fulfilment day as an operations
team lives it -- a REAL worker thread on the in-memory transport where
it matters, eager mode where it does not.

* **a hundred orders, duplicated task deliveries** -- `handle_order_event`
  tasks for 100 orders as two interleaved delivery streams, with
  DUPLICATES (Celery's `acks_late` redelivery): every order shipped,
  exactly one `PAY` transition per order;
* **the worker is killed -9 mid-task** -- a `statechart_task` dies after
  the step ran and before the save: the redelivery finds the snapshot
  untouched and finishes it; no double transition;
* **the shipping task completes while nobody is looking** -- the
  `celery_service` invoke's result lands via the `task_success` signal
  AFTER the instance was saved and discarded (the durable path), via
  `poll_results` when the signal was lost, and NEVER twice (a repeated
  completion for an order that already shipped is refused);
* **Beat runs twice** -- two Beat processes (the thing the docs say not
  to do) scan the same deadlines: the escalation fires ONCE; an
  `eta`-scheduled exact job and the scan both fire: once;
* **a hostile task message** -- forged `xsm_store_key` /
  `xsm_invocation_id` headers, a pickle-accepting app, a result for a
  task id the snapshot never recorded: refused, logged, nothing moves;
* **two workers relay one outbox** -- the `outbox_relay_task` on two
  apps against one SQLite outbox: every row published once (the #293
  leases hold through Celery).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest

pytest.importorskip("celery")

import app  # noqa: E402
import celery_app  # noqa: E402
from xstate_statemachine import PluginBase  # noqa: E402
from xstate_statemachine.clock import SimulatedClock  # noqa: E402
from xstate_statemachine.contrib.celery import (  # noqa: E402
    connect_signals,
    deliver_result,
    poll_results,
)
from xstate_statemachine.eda import (
    Envelope,
    SyncFakeBrokerAdapter,
)  # noqa: E402
from xstate_statemachine.persistence import (  # noqa: E402
    PessimisticLock,
    SQLiteStore,
    persisted,
)

ROOT = Path(__file__).resolve().parents[4]


@pytest.fixture(autouse=True)
def _celery_join_flag_reset() -> Any:
    """Celery's `denied_join_result` guard is a MODULE-GLOBAL flag; eager
    tasks nested in eager tasks (the shipping invoke inside
    `handle_order_event`) can leave it set when any thread interleaves,
    and every later `.get()` in the session then refuses. Reset it."""
    import celery._state as st

    yield
    st._set_task_join_will_block(False)


EXAMPLE = Path(__file__).resolve().parents[1]
N_ORDERS = 100


class Dropped(PluginBase):
    def __init__(self) -> None:
        self.reasons: List[Any] = []

    def on_event_dropped(self, interpreter: Any, event: Any, reason: Any):
        self.reasons.append((event.type, reason))


def _count(store: Any, key: str, event: str) -> int:
    from xstate_statemachine.persistence import SQLiteLog

    return sum(
        1
        for r in SQLiteLog(store).read(key)
        if r.disposition == "transition" and r.event_type == event
    )


# -----------------------------------------------------------------------------
# 1. a hundred orders, duplicated task deliveries, two "workers"
# -----------------------------------------------------------------------------
def test_hundred_orders_with_duplicate_deliveries_once_each(
    tmp_path: Path,
) -> None:
    from xstate_statemachine.persistence import SQLiteLog
    from xstate_statemachine.persistence import AuditPlugin

    capp = celery_app.make_celery(name="w-292")
    store = SQLiteStore(tmp_path / "s.db")
    log = SQLiteLog(store)
    machine = app.order_machine(celery_app.ship_service(capp))
    try:
        task = celery_app.handle_order_event_task(
            capp, store, machine, plugins=[AuditPlugin(log)]
        )
        # 📝 eager tasks run in THIS process, so two "workers" are two
        #    interleaved streams of deliveries, not two threads: Celery's
        #    `denied_join_result` guard is a module-global flag and two
        #    threads running eager tasks concurrently leave it stuck
        #    (celery 5.6; real workers are separate processes).
        streams = [
            [(f"order:o-{i}", i) for i in range(k, N_ORDERS, 2)]
            for k in (0, 1)
        ]
        for a, b in zip(*streams):
            for key, i in (a, b):
                task.delay(key, "PAY", {"orderId": f"o-{i}", "total": 1})
                if i % 10 == 0:
                    # acks_late: the broker redelivers the same task
                    # message after a worker loss -- same args
                    task.delay(key, "PAY", {"orderId": f"o-{i}", "total": 1})
            for key, i in (a, b):
                task.delay(key, "PACKED", {})
                if i % 15 == 0:
                    task.delay(key, "PACKED", {})
        for i in range(N_ORDERS):
            key = f"order:o-{i}"
            with persisted(store, key, machine) as o:
                assert o.current_state_ids == {"order.shipped"}, (
                    key,
                    o.current_state_ids,
                )
            # 🔥 the duplicate PAY was a no-op: the chart has no PAY in
            #    `paid`, so it is refused, not re-applied
            assert _count(store, key, "PAY") == 1, key
    finally:
        store.close()


# -----------------------------------------------------------------------------
# 2. the worker is killed -9 mid-task (after the step, before the save)
# -----------------------------------------------------------------------------
WORKER_CHILD = r"""
import os, signal, sys
sys.path.insert(0, sys.argv[2])
from pathlib import Path
import app, celery_app
from xstate_statemachine.persistence import SQLiteStore
capp = celery_app.make_celery(name="kill")
store = SQLiteStore(Path(sys.argv[1]) / "s.db")
machine = app.order_machine(celery_app.ship_service(capp))
real_save = store.save
def save(*a, **k):
    # the step ran (PAY applied in memory); die before the snapshot lands
    os.kill(os.getpid(), getattr(signal, "SIGKILL", 9))
store.save = save
task = celery_app.handle_order_event_task(capp, store, machine)
task.delay("order:o-k", "PAY", {"orderId": "o-k", "total": 2})
sys.exit(3)
"""


def test_worker_killed_after_step_before_save_redelivery_finishes(
    tmp_path: Path,
) -> None:
    proc = subprocess.run(
        [sys.executable, "-c", WORKER_CHILD, str(tmp_path), str(EXAMPLE)],
        cwd=str(EXAMPLE),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode not in (0, 3), proc.stderr[-1500:]
    capp = celery_app.make_celery(name="after-kill")
    store = SQLiteStore(tmp_path / "s.db")
    machine = app.order_machine(celery_app.ship_service(capp))
    try:
        # nothing landed: the snapshot does not exist
        assert store.load("order:o-k") is None
        # the redelivered task message finishes the order (`.result`, not
        # `.get()`: eager results are ready, and Celery's thread-local
        # "current task" left by test 1's worker threads makes `.get()`
        # refuse as if called inside a task)
        task = celery_app.handle_order_event_task(capp, store, machine)
        assert task.delay(
            "order:o-k", "PAY", {"orderId": "o-k", "total": 2}
        ).result == ["order.paid"]
        assert task.delay("order:o-k", "PACKED", {}).result == [
            "order.shipped"
        ]
    finally:
        store.close()


# -----------------------------------------------------------------------------
# 3. the shipping task completes while nobody is looking
# -----------------------------------------------------------------------------
def test_result_lands_durably_via_signal_poll_and_never_when_stale(
    tmp_path: Path,
) -> None:
    capp = celery_app.make_celery(eager=False, name="durable-292")
    machine = app.order_machine(celery_app.ship_service(capp, watch=False))
    store = SQLiteStore(tmp_path / "s.db")
    dropped = Dropped()
    try:
        # (a) the signal path: the worker finishes AFTER the instance was
        #     saved and discarded
        disconnect = connect_signals(
            store, machine, app=capp, plugins=[dropped]
        )
        try:
            with persisted(store, "order:o-1", machine) as o:
                o.send("PAY", orderId="o-1", total=5)
                o.send("PACKED")
                [(inv1, rec1)] = o.context["_xsm_celery"].items()
            # the task "runs" now: deliver its success through the signal
            from celery import signals

            task = capp.tasks["fulfilment.ship_order"]

            class _Req:
                id = rec1["task_id"]
                headers = {
                    "xsm_store_key": "order:o-1",
                    "xsm_invocation_id": inv1,
                }

            signals.task_success.send(
                sender=type("S", (), {"request": _Req(), "name": task.name})(),
                result={"trackingId": "TRK-o-1"},
            )
            with persisted(store, "order:o-1", machine) as o:
                assert o.current_state_ids == {"order.shipped"}
                assert o.context["trackingId"] == "TRK-o-1"
        finally:
            disconnect()
        # (b) the poll path: the signal was lost (worker restarted); the
        #     result backend has the value
        with persisted(store, "order:o-2", machine) as o:
            o.send("PAY", orderId="o-2", total=5)
            o.send("PACKED")
            [(inv2, rec2)] = o.context["_xsm_celery"].items()
        capp.backend.mark_as_done(rec2["task_id"], {"trackingId": "TRK-o-2"})
        n = poll_results(store, machine, app=capp)
        assert n >= 1, n
        with persisted(store, "order:o-2", machine) as o:
            assert o.current_state_ids == {"order.shipped"}
        # (c) stale: the SAME completion arrives again (a retried signal,
        #     a second worker) after the order already shipped -- dropped
        #     as stale, the shipped order is untouched
        assert not deliver_result(
            store,
            machine,
            "order:o-2",
            inv2,
            rec2["task_id"],
            result={"trackingId": "TRK-late"},
            plugins=[dropped],
        )
        # 📝 the record was consumed by the first delivery: a repeat has
        #    nothing to attach to -- `False`, a log line, no write
        with persisted(store, "order:o-2", machine) as o:
            assert o.current_state_ids == {"order.shipped"}
            assert o.context["trackingId"] == "TRK-o-2"
    finally:
        store.close()


# -----------------------------------------------------------------------------
# 4. Beat runs twice
# -----------------------------------------------------------------------------
def test_two_beats_fire_the_escalation_once(tmp_path: Path) -> None:
    a = app.build_app("fake", tmp_path, instruments=False)
    try:
        a.router.dispatcher.clock = SimulatedClock(wall_start=1_000.0)
        for i in range(20):
            a.command(f"o-{i}", "PAY", orderId=f"o-{i}", total=5)
        a.router.run_until_quiet_sync(a.broker)
        now = [1_000.0 + 61]
        # two Beat PROCESSES = two Celery apps on one store. (Two
        # schedulers on ONE app is the trap the battle closed: Celery
        # handed the second the first's task -- `InvalidConfigError` now.)
        from xstate_statemachine.exceptions import InvalidConfigError

        beats = [
            celery_app.timer_scheduler(
                celery_app.make_celery(name=f"beat-{k}"),
                a.store,
                a.machine_for_key,
                plugins=a.plugins,
                now=lambda: now[0],
                lock=PessimisticLock(timeout=5),
            )
            for k in range(2)
        ]
        with pytest.raises(InvalidConfigError, match="already registered"):
            celery_app.timer_scheduler(
                beats[0].app, a.store, a.machine_for_key, now=lambda: now[0]
            )
        # 📝 two Beat processes are two SEQUENTIAL scans here (eager
        #    tasks must not run from threads, see the fixture); the claim
        #    is idempotence: whichever scans second wakes nothing
        fired = [b.task.delay().result for b in beats]
        assert sum(fired) == 20, fired  # each expense woken ONCE in total
        for i in range(20):
            assert a.state_of(f"order:o-{i}") == ["order.packingLate"]
        # an exact eta job for a deadline the scan already fired is a no-op
        assert beats[0].fire("order:o-0", "order.paid", 1) is False
        assert a.state_of("order:o-0") == ["order.packingLate"]
    finally:
        a.close()


# -----------------------------------------------------------------------------
# 5. a hostile task message
# -----------------------------------------------------------------------------
def test_hostile_headers_and_pickle_are_refused(tmp_path: Path) -> None:
    from celery import signals

    from xstate_statemachine.exceptions import InvalidConfigError

    capp = celery_app.make_celery(eager=False, name="hostile-292")
    machine = app.order_machine(celery_app.ship_service(capp, watch=False))
    store = SQLiteStore(tmp_path / "s.db")
    dropped = Dropped()
    try:
        with persisted(store, "order:o-h", machine) as o:
            o.send("PAY", orderId="o-h", total=5)
            o.send("PACKED")
            [(inv, rec)] = o.context["_xsm_celery"].items()
        disconnect = connect_signals(
            store, machine, app=capp, plugins=[dropped]
        )
        try:
            task = capp.tasks["fulfilment.ship_order"]
            for headers in (
                # a key that belongs to another order
                {"xsm_store_key": "order:o-other", "xsm_invocation_id": inv},
                # a forged invocation id
                {"xsm_store_key": "order:o-h", "xsm_invocation_id": "forged"},
                # a path-traversal-looking key
                {
                    "xsm_store_key": "../../etc/passwd",
                    "xsm_invocation_id": inv,
                },
                # no headers at all (a plain task of the same name)
                {},
            ):

                class _Req:
                    id = "attacker-task-id"

                _Req.headers = headers  # type: ignore[attr-defined]
                signals.task_success.send(
                    sender=type(
                        "S", (), {"request": _Req(), "name": task.name}
                    )(),
                    result={"trackingId": "EVIL"},
                )
        finally:
            disconnect()
        with persisted(store, "order:o-h", machine) as o:
            assert o.current_state_ids == {"order.packed"}
            assert o.context.get("trackingId") is None
        assert store.load("order:o-other") is None
        assert store.load("../../etc/passwd") is None
        # a pickle-accepting app is refused at every entry point
        bad = celery_app.make_celery(name="pickle-292")
        bad.conf.accept_content = ["json", "pickle"]
        with pytest.raises(InvalidConfigError):
            celery_app.ship_service(bad)
        with pytest.raises(InvalidConfigError):
            celery_app.handle_order_event_task(bad, store, machine)
        with pytest.raises(InvalidConfigError):
            connect_signals(store, machine, app=bad)
    finally:
        store.close()


# -----------------------------------------------------------------------------
# 6. two workers relay one outbox
# -----------------------------------------------------------------------------
def test_two_relay_tasks_on_one_outbox_publish_once(tmp_path: Path) -> None:
    from xstate_statemachine.eda import SQLiteOutboxStore

    store = SQLiteStore(tmp_path / "s.db")
    outbox = SQLiteOutboxStore(store)
    broker = SyncFakeBrokerAdapter()
    try:
        for i in range(300):
            outbox.add(
                "events", Envelope.new(type="t", subject=str(i), data={})
            )
        tasks = [
            celery_app.relay_task(
                celery_app.make_celery(name=f"relay-{k}"), outbox, broker
            )
            for k in range(2)
        ]
        # 📝 outbox_relay_task(batch=100): each run claims ITS rows; the
        #    two tasks alternate (eager tasks must not run from threads)
        total = 0
        for _ in range(10):
            n = sum(t.delay().result for t in tasks)
            total += n
            if n == 0 and outbox.count(pending_only=True) == 0:
                break
        ids = [e.id for e in broker.published]
        assert len(ids) == 300, len(ids)
        assert len(set(ids)) == 300, "a row was relayed twice"
        assert outbox.count(pending_only=True) == 0
    finally:
        store.close()
