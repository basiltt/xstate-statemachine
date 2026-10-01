"""Poison messages, redelivery and oversize envelopes (X0.4 / X0.8)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import app
from xstate_statemachine.eda import Envelope

ROOT = Path(__file__).resolve().parents[4]


def _xsm(*args, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src")] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "--plain", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _poison(fulfilment):
    env = fulfilment.command("o-4", "PAYMENT_FAILED", reason=12345)
    stats = fulfilment.pump()
    return env, stats


def test_poison_lands_in_the_dlq_after_max_attempts(fulfilment):
    env, stats = _poison(fulfilment)
    assert stats["dead_lettered"] == 1
    [rec] = fulfilment.dead_letters.list()
    assert rec.id == env.id
    assert rec.reason == "max_attempts"
    assert rec.attempts == app.MAX_ATTEMPTS
    assert rec.errors[0]["type"] == "ProcessingFailedError"
    # 📝 nothing committed: no snapshot, no outbox row, broker drained.
    assert fulfilment.state_of("order:o-4") is None
    assert fulfilment.outbox.count() == 0
    assert fulfilment.broker.pending(app.TOPIC) == 0


def test_xsm_dlq_list_shows_the_poison(fulfilment, tmp_path):
    env, _ = _poison(fulfilment)
    db = fulfilment.workdir / "state.db"
    proc = _xsm(
        "dlq", "--dlq", f"sqlite:///{db}", "list", "--json", cwd=tmp_path
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rows = json.loads(proc.stdout)["dead_letters"]
    assert [r["id"] for r in rows] == [env.id]
    assert rows[0]["reason"] == "max_attempts"
    assert rows[0]["attempts"] == app.MAX_ATTEMPTS
    # 🔍 an operator inspects one record before any replay.
    proc = _xsm(
        "dlq", "--dlq", f"sqlite:///{db}", "show", env.id, cwd=tmp_path
    )
    assert proc.returncode == 0 and env.id in proc.stdout


def test_duplicate_envelope_is_a_single_transition(fulfilment):
    cmd = fulfilment.command("o-1", "PAY", orderId="o-1", total=10)
    fulfilment.pump()
    before = fulfilment.transitions("order:o-1", "PAY")
    fulfilment.publish(cmd)  # the broker redelivers the same id
    stats = fulfilment.pump()
    assert stats["duplicates"] == 1 and stats["processed"] == 0
    assert fulfilment.transitions("order:o-1", "PAY") == before == 1
    assert [
        e.type for e in fulfilment.broker.published if e.type == "OrderPaid"
    ] == ["OrderPaid"]


def test_unknown_types_are_ignored_on_a_shared_bus(fulfilment):
    fulfilment.publish(Envelope.new(type="billing.InvoiceSent", subject="x"))
    stats = fulfilment.pump()
    assert stats["dead_lettered"] == 0
    assert fulfilment.dead_letters.list() == []


def test_oversize_envelope_is_dead_lettered_as_corrupt(tmp_path):
    """X0.4: the real adapters cap inbound bytes BEFORE parsing; the body
    is never stored in the dead-letter record (it may be hostile)."""
    import pytest

    pytest.importorskip("fakeredis")
    import fakeredis

    client = fakeredis.FakeRedis()
    a = app.build_app(
        "redis-streams", tmp_path, celery=False, redis_client=client
    )
    try:
        secret = "S3CRET-" + "x" * (app.MAX_ENVELOPE_BYTES + 10)
        big = Envelope.new(
            type="xsm.order.PAY", subject="o-big", data={"blob": secret}
        )
        # 📝 A hostile producer bypasses our publish-side cap.
        stream = a.broker.transport.stream(app.TOPIC)
        client.xadd(stream, {"ce": big.to_json(max_bytes=10**7)})
        stats = a.pump()
        assert stats["processed"] == 0
        [rec] = a.dead_letters.list()
        assert rec.reason == "corrupt"
        assert "S3CRET" not in json.dumps(rec.to_dict())
        assert a.state_of("order:o-big") is None
    finally:
        a.close()
