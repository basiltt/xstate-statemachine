# examples/integrations/eda_fulfilment/tests/test_battle_293_scenario.py
"""#293 battle: the EDA core (envelope, dispatcher, outbox, dead letters,
`xsm dlq`) on a fulfilment day as an operations team lives it.

* **a thousand orders through two consumer processes** -- two
  `FulfilmentApp`s (two service replicas) share ONE SQLite file and ONE
  fake broker; 1,000 orders interleaved with duplicates and poison; every
  order reaches `shipped`, every published envelope is published ONCE,
  per-order causation chains are intact, nothing is lost;
* **the relay is killed -9 between "published" and "marked sent"** -- a
  child process relays the outbox and dies after the broker accepted a
  row; the next relay publishes that row AGAIN (at-least-once, as
  documented) and the consumer's inbox makes it a single transition;
* **a consumer is killed -9 mid-step** -- after the snapshot save, before
  the outbox flush: the redelivered command is a duplicate, the outbox
  row is not lost twice over (either written or re-derived on retry);
* **dead letters, the operator's way** -- a poison message, a message for
  a type nobody handles, an oversize one and a corrupt one land with
  distinct reasons; `xsm dlq list/show/replay` end to end: the dry run
  touches nothing, the real replay after the FIX is `processed`, the
  record resolves and the audit names the reason; a replay against a
  CHANGED chart is refused without `--force`; `purge` needs `--yes`;
* **a dirty bus** -- envelopes with credential-bearing extensions,
  a reserved `send()` kwarg in the payload, a bad traceparent and a
  type that is not a string: all refused as `corrupt` with no snapshot
  written, nothing raised out of the loop (X0.4 / X0.8);
* **resources** -- 10,000 envelopes through one dispatcher: bounded
  memory (attempt table, step buffers), no thread growth, SQLite handles
  closed.
"""

from __future__ import annotations

import gc
import json
import logging
import os
import subprocess
import sys
import threading
import tracemalloc
from pathlib import Path
from typing import Any, Dict, List

import pytest

import app
from xstate_statemachine.eda import Envelope, SyncFakeBrokerAdapter

ROOT = Path(__file__).resolve().parents[4]
EXAMPLE = Path(__file__).resolve().parents[1]
N_ORDERS = 1000


def _xsm(*args: str, cwd: Path) -> "subprocess.CompletedProcess[str]":
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src"), str(EXAMPLE)]
        + [p for p in [env.get("PYTHONPATH")] if p]
    )
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "--plain", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _two_replicas(tmp_path: Path) -> List[Any]:
    """Two service replicas on one state file and one broker."""
    broker = SyncFakeBrokerAdapter()
    a = app.FulfilmentApp(
        tmp_path, "fake", celery=False, consumer="fulfilment-1"
    )
    a.broker = broker
    a.relay.broker.broker = broker
    b = app.FulfilmentApp(
        tmp_path, "fake", celery=False, consumer="fulfilment-2"
    )
    b.broker = broker
    b.relay.broker.broker = broker
    return [a, b]


# -----------------------------------------------------------------------------
# 1. a thousand orders through two consumer processes
# -----------------------------------------------------------------------------
def test_thousand_orders_two_replicas_once_each(tmp_path: Path) -> None:
    a, b = _two_replicas(tmp_path)
    try:
        orders = [f"o-{i}" for i in range(N_ORDERS)]
        for i, oid in enumerate(orders):
            a.command(oid, "PAY", orderId=oid, total=1 + i)
            if i % 50 == 0:
                a.publish(a.commands[-1])  # a duplicate command
            if i % 97 == 0:
                a.command(f"p-{i}", "PAYMENT_FAILED", reason=i)  # poison
        stop = threading.Event()
        stats = [{"processed": 0}, {"processed": 0}]

        def pump(replica: Any, slot: int) -> None:
            while not stop.is_set():
                s = replica.pump()
                stats[slot]["processed"] += s["processed"]
                if not s["processed"] and not s["duplicates"]:
                    if replica.broker.pending(app.TOPIC) == 0:
                        break

        ts = [
            threading.Thread(target=pump, args=(a, 0)),
            threading.Thread(target=pump, args=(b, 1)),
        ]
        for t in ts:
            t.start()
        for t in ts:
            t.join(600)
        stop.set()
        assert not any(t.is_alive() for t in ts)
        # settle whatever the other replica left on the bus
        a.pump()
        b.pump()
        # 🔥 every order shipped; both replicas did real work
        for oid in orders:
            assert a.state_of("order:" + oid) == ["order.shipped"], oid
        assert all(s["processed"] > 0 for s in stats), stats
        # every outbox row published once (relay) and every envelope id
        # seen on the broker is unique
        ids = [e.id for e in a.sent + b.sent]
        assert len(ids) == len(set(ids)), "an outbox row was relayed twice"
        assert a.outbox.count(pending_only=True) == 0
        # the poison is in the DLQ, once each, with the right reason
        recs = a.dead_letters.list()
        assert len(recs) == len([i for i in range(N_ORDERS) if i % 97 == 0])
        assert {r.reason for r in recs} == {"max_attempts"}
        # exactly one PAY transition per order despite the duplicates
        for i in range(0, N_ORDERS, 50):
            assert a.transitions(f"order:o-{i}", "PAY") == 1
    finally:
        a.close()
        b.store.close()


# -----------------------------------------------------------------------------
# 2. the relay is killed -9 between "published" and "marked sent"
# -----------------------------------------------------------------------------
RELAY_CHILD = r"""
import json, os, sys, signal
sys.path.insert(0, sys.argv[2])
from pathlib import Path
import app
a = app.FulfilmentApp(Path(sys.argv[1]), "fake", celery=False)
# the broker is in-process: a publish is "accepted" when the row reaches
# this fake. Die right after the first accepted publish, before mark_sent.
real = a.relay.broker.publish
def publish(topic, env):
    real(topic, env)
    Path(sys.argv[1], "published.json").write_text(env.to_json())
    os.kill(os.getpid(), signal.SIGKILL if hasattr(signal, "SIGKILL") else 9)
a.relay.broker.publish = publish
a.relay.relay_once_sync()
sys.exit(3)
"""


def test_relay_killed_after_publish_before_mark_republishes_once(
    tmp_path: Path,
) -> None:
    a = app.build_app("fake", tmp_path, celery=False)
    a.command("o-1", "PAY", orderId="o-1", total=5)
    # dispatch the command ONLY (no relay): leaves the OrderPaid row pending
    a.router.run_until_quiet_sync(a.broker)
    assert a.outbox.count(pending_only=True) == 1
    a.close()
    proc = subprocess.run(
        [sys.executable, "-c", RELAY_CHILD, str(tmp_path), str(EXAMPLE)],
        cwd=str(EXAMPLE),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode != 3, "kill point never reached"
    assert proc.returncode != 0, proc.stderr[-1500:]
    published = json.loads((tmp_path / "published.json").read_text())
    # 🔥 the row is STILL pending (published, not marked) -- the documented
    #    at-least-once window
    b = app.build_app("fake", tmp_path, celery=False)
    try:
        assert b.outbox.count(pending_only=True) == 1
        [rec] = b.outbox.pending()
        assert rec.envelope.id == published["id"]
        # 🔒 the dead relay's LEASE still holds the row: a second relay
        #    right away takes nothing (it must not race a relay it cannot
        #    know is dead) ...
        assert b.relay.relay_once_sync() == 0
        assert b.outbox.count(pending_only=True) == 1
        # ... and once the lease is out, the next relay publishes it
        # again -- same envelope id (at-least-once, as documented)
        b.outbox._conn().execute(
            "UPDATE xsm_outbox SET claimed_until = claimed_until - 3600"
        )
        b.outbox._conn().commit()
        assert b.relay.relay_once_sync() == 1
        assert b.outbox.count(pending_only=True) == 0
        assert [e.id for e in b.sent] == [published["id"]]
        # and the consumer side makes the double delivery ONE transition
        b.broker.publish(app.TOPIC, rec.envelope)  # the child's copy
        b.pump()
        assert b.state_of("warehouse:o-1") == ["warehouse.packed"]
        assert b.transitions("warehouse:o-1", "PACK") == 1
    finally:
        b.close()


# -----------------------------------------------------------------------------
# 3. a consumer is killed -9 after the snapshot save, before the outbox flush
# -----------------------------------------------------------------------------
CONSUMER_CHILD = r"""
import json, os, sys, signal
sys.path.insert(0, sys.argv[2])
from pathlib import Path
import app
from xstate_statemachine.eda import Envelope
a = app.FulfilmentApp(Path(sys.argv[1]), "fake", celery=False)
real_save = a.store.save
def save(*args, **kw):
    out = real_save(*args, **kw)
    os.kill(os.getpid(), signal.SIGKILL if hasattr(signal, "SIGKILL") else 9)
    return out
a.store.save = save
env = Envelope.from_json(Path(sys.argv[1], "cmd.json").read_text())
a.broker.publish(app.TOPIC, env)
a.router.run_until_quiet_sync(a.broker)
sys.exit(3)
"""


def test_consumer_killed_after_save_before_outbox_flush(
    tmp_path: Path,
) -> None:
    env = Envelope.new(
        type="xsm.order.PAY",
        subject="o-9",
        data={"orderId": "o-9", "total": 9},
        source="checkout",
    )
    (tmp_path / "cmd.json").write_text(env.to_json())
    proc = subprocess.run(
        [sys.executable, "-c", CONSUMER_CHILD, str(tmp_path), str(EXAMPLE)],
        cwd=str(EXAMPLE),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode not in (0, 3), proc.stderr[-1500:]
    b = app.build_app("fake", tmp_path, celery=False)
    try:
        saved = b.state_of("order:o-9")
        # redeliver the same command: the surviving replica must end with
        # exactly one PAY transition and exactly one OrderPaid published
        b.broker.publish(app.TOPIC, env)
        b.pump()
        assert b.state_of("order:o-9") == ["order.shipped"], saved
        assert b.transitions("order:o-9", "PAY") == 1
        paid = [e for e in b.sent if e.type == "OrderPaid"]
        # 📝 PessimisticLock on SQLite: snapshot + outbox rows commit in ONE
        #    transaction, so the kill lost both (saved is None) and the
        #    retry produced the row once. Two rows would be a double ship.
        assert len(paid) == 1, [e.id for e in paid]
        assert b.outbox.count(pending_only=True) == 0
    finally:
        b.close()


# -----------------------------------------------------------------------------
# 4. dead letters, the operator's way (xsm dlq end to end)
# -----------------------------------------------------------------------------
def test_dlq_cli_replay_after_the_fix(fulfilment: Any, tmp_path: Path):
    # the poison: reason is an int. Operators fix the PRODUCER; the
    # dead letter must be replayable once the consumer accepts it.
    env = fulfilment.command("o-4", "PAYMENT_FAILED", reason=12345)
    fulfilment.pump()
    [rec] = fulfilment.dead_letters.list()
    assert rec.id == env.id
    db = fulfilment.workdir / "state.db"
    dlq = ["dlq", "--dlq", f"sqlite:///{db}"]
    chart = ["--machine", str(EXAMPLE / "machine.json"), "--logic", "logic"]
    store = ["--store", f"sqlite:///{db}"]
    # dry run (default): nothing changes
    p = _xsm(
        *dlq, "replay", env.id, *store, *chart, "--reason", "x", cwd=tmp_path
    )
    assert p.returncode == 0, p.stdout + p.stderr
    assert "dry run" in p.stdout
    assert [r.id for r in fulfilment.dead_letters.list()] == [env.id]
    # a real replay needs --yes
    p = _xsm(
        *dlq,
        "replay",
        env.id,
        *store,
        *chart,
        "--no-dry-run",
        "--reason",
        "x",
        cwd=tmp_path,
    )
    assert p.returncode != 0 and "--yes" in (p.stdout + p.stderr)
    # ... and a reason
    p = _xsm(
        *dlq,
        "replay",
        env.id,
        *store,
        *chart,
        "--no-dry-run",
        "--yes",
        cwd=tmp_path,
    )
    assert p.returncode != 0 and "--reason" in (p.stdout + p.stderr)
    # the real replay of still-poison data: not resolved, exit 1
    p = _xsm(
        *dlq,
        "replay",
        env.id,
        *store,
        *chart,
        "--no-dry-run",
        "--yes",
        "--reason",
        "retry as-is",
        cwd=tmp_path,
    )
    assert p.returncode == 1, p.stdout + p.stderr
    assert [r.id for r in fulfilment.dead_letters.list()] == [env.id]
    # a replay against a CHANGED chart is refused without --force
    changed = json.loads((EXAMPLE / "machine.json").read_text("utf-8"))
    changed["states"]["placed"]["on"]["NEW_EVENT"] = "cancelled"
    (tmp_path / "changed.json").write_text(json.dumps(changed), "utf-8")
    p = _xsm(
        *dlq,
        "replay",
        env.id,
        *store,
        "--machine",
        str(tmp_path / "changed.json"),
        "--logic",
        "logic",
        "--reason",
        "x",
        cwd=tmp_path,
    )
    assert p.returncode == 2 and "--force" in (p.stdout + p.stderr)
    # purge needs --yes
    p = _xsm(*dlq, "purge", "--id", env.id, "--reason", "x", cwd=tmp_path)
    assert p.returncode != 0
    assert [r.id for r in fulfilment.dead_letters.list()] == [env.id]
    # the audit trail names every refused / attempted action's reason
    audit = fulfilment.dead_letters.audit_log()
    assert any(a["reason"] == "retry as-is" for a in audit), audit


def test_distinct_dead_letter_reasons(tmp_path: Path) -> None:
    a = app.build_app("fake", tmp_path, celery=False)
    try:
        a.command("o-1", "PAYMENT_FAILED", reason=1)  # poison
        a.broker.publish(
            app.TOPIC,
            Envelope.new(type="nobody.Handles", subject="x", data={}),
        )
        # corrupt: `data` is not a JSON object (the fake wire accepts it;
        # `to_event()` refuses it)
        a.broker.deliver(
            app.TOPIC,
            Envelope.new(type="xsm.order.PAY", subject="o-2", data=[1, 2]),
        )
        a.router.dispatcher.on_unknown = "dead_letter"
        a.pump()
        reasons = sorted(r.reason for r in a.dead_letters.list())
        assert reasons == sorted(
            ["max_attempts", "unknown_event", "corrupt"]
        ), reasons
        assert a.state_of("order:o-2") is None
    finally:
        a.close()


# -----------------------------------------------------------------------------
# 5. a dirty bus (X0.4 / X0.8)
# -----------------------------------------------------------------------------
DIRTY = [
    # credential-bearing extension
    lambda: Envelope.new(
        type="xsm.order.PAY",
        subject="d-1",
        data={"total": 1},
        extensions={"authorization": "Bearer x"},
    ),
    # `data` that is not a JSON object
    lambda: Envelope.new(type="xsm.order.PAY", subject="d-2", data=[1]),
    # bad traceparent
    lambda: Envelope.new(
        type="xsm.order.PAY",
        subject="d-3",
        data={"total": 1},
        extensions={"traceparent": "garbage"},
    ),
]


def test_dirty_bus_is_refused_without_a_snapshot(tmp_path: Path) -> None:
    a = app.build_app("fake", tmp_path, celery=False)
    try:
        raw = []
        for make in DIRTY:
            try:
                env = make()
            except Exception as exc:  # noqa: BLE001 - refused at build
                raw.append(repr(exc))
                continue
            a.broker.deliver(app.TOPIC, env)
        # a type that is not a string, straight onto the wire: the
        # Envelope refuses it at construction, as a real adapter's decode
        # would -- it never reaches the dispatcher
        with pytest.raises(Exception):
            a.broker.deliver(
                app.TOPIC,
                Envelope.from_dict(
                    {
                        "specversion": "1.0",
                        "id": "bad-1",
                        "type": 42,
                        "source": "x",
                        "subject": "d-4",
                        "data": {"total": 1},
                    }
                ),
            )
        stats = a.pump()
        assert a.broker.pending(app.TOPIC) == 0
        for k in ("d-1", "d-2", "d-3", "d-4"):
            assert a.state_of("order:" + k) is None, k
        # whichever were accepted onto the bus were dead-lettered, not
        # processed; the rest were refused by the Envelope itself
        assert stats["processed"] == 0
        dl = a.dead_letters.list()
        assert len(dl) + len(raw) >= 3, (stats, raw, [r.reason for r in dl])
    finally:
        a.close()


# -----------------------------------------------------------------------------
# 6. resources: 10,000 envelopes, flat memory, no thread growth
# -----------------------------------------------------------------------------
def test_ten_thousand_envelopes_flat(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    # 📝 1,400 poison messages each log a traceback; pytest's log capture
    #    would keep them all (118 MB) and the soak would measure pytest,
    #    not the EDA core (adversary B).
    caplog.set_level(logging.CRITICAL)
    logging.disable(logging.CRITICAL)
    a = app.build_app("fake", tmp_path, celery=False, instruments=False)
    threads0 = threading.active_count()
    try:

        def batch(start: int) -> None:
            for i in range(start, start + 2500):
                oid = f"m-{i}"
                a.command(oid, "PAY", orderId=oid, total=1)
                if i % 7 == 0:
                    a.command(f"p-{i}", "PAYMENT_FAILED", reason=i)
            a.pump()
            # 📝 the TEST DOUBLE keeps `published`/`acked` records and the
            #    demo app keeps `sent`/`commands` by design (both are
            #    documented); the soak measures the EDA core, so those
            #    bookkeeping lists are emptied between batches.
            a.broker.clear()
            del a.sent[:], a.commands[:]

        batch(0)
        gc.collect()
        tracemalloc.start()
        batch(2500)
        gc.collect()
        mid = tracemalloc.take_snapshot()
        batch(5000)
        batch(7500)
        gc.collect()
        end = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(
            s.size_diff
            for s in end.compare_to(mid, "filename")
            if s.size_diff > 0
        )
        # 📝 attempt table is bounded (_ATTEMPTS_MEMORY), step buffers are
        #    weak; SQLite cache aside, the second half must not cost more
        #    than a few MB over the first half
        assert growth < 8 * 1024 * 1024, growth
        assert threading.active_count() <= threads0 + 1
        assert len(a.router.dispatcher._attempts) <= 10_000
        assert a.state_of("order:m-9999") == ["order.shipped"]
    finally:
        logging.disable(logging.NOTSET)
        a.close()
