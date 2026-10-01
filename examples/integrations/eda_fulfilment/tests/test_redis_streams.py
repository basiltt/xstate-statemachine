"""The same demo on Redis Streams (fakeredis), plus crash recovery."""

import pytest

pytest.importorskip("redis")
fakeredis = pytest.importorskip("fakeredis")

import app  # noqa: E402
from xstate_statemachine.eda import Envelope  # noqa: E402


def test_demo_on_redis_streams(tmp_path):
    summary = app.run_demo("redis-streams", tmp_path)
    assert all(s == ["order.shipped"] for s in summary["orders"].values())
    assert summary["dead_letters"] == 1
    assert summary["duplicates"] == 1
    assert summary["outbox_rows"] == summary["published"] == 9


def test_crashed_consumer_is_reclaimed_with_attempts(tmp_path):
    """Consumer A reads a batch and dies before acking. Consumer B (a new
    process sharing Redis and the database) reclaims the pending entries;
    the redelivery count travels as the envelope's attempt."""
    client = fakeredis.FakeRedis()
    a = app.build_app(
        "redis-streams",
        tmp_path,
        celery=False,
        redis_client=client,
        consumer="A",
    )
    a.command("o-1", "PAY", orderId="o-1", total=10)
    a.command("o-2", "PAY", orderId="o-2", total=20)
    got = list(a.broker.subscribe(app.TOPIC, timeout=0))
    assert len(got) == 2  # read, never acked: "crash"
    b = app.build_app(
        "redis-streams",
        tmp_path,
        celery=False,
        redis_client=client,
        consumer="B",
    )
    try:
        seen = []
        real = b.router.dispatcher.handle

        def spy(env: Envelope, **kw):
            seen.append(env.attempt)
            return real(env, **kw)

        b.router.dispatcher.handle = spy
        b.pump()
        assert seen[:2] and all(n >= 1 for n in seen[:2]), seen
        for oid in ("o-1", "o-2"):
            assert b.state_of(f"order:{oid}") == ["order.shipped"]
        assert b.dead_letters.list() == []
    finally:
        b.close()
        a.store.close()
