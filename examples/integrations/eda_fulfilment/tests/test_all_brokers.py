"""The same choreography on every real broker adapter.

Offline, each adapter runs over the stand-in from `brokers_local`
(fakeredis, the fake aiokafka / aio-pika / nats-py clients, moto SQS).
A test skips cleanly when its client library is not installed, so a CI
cell with only one broker extra still runs that broker's tests.

``XSM_CONTAINERS=1`` (and Docker) adds the live variant: the demo against
real Redis, Redpanda, RabbitMQ, NATS and LocalStack containers started
by the repository's testcontainers helpers.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest

import app
import brokers_local
from xstate_statemachine.eda import Envelope

#: broker -> the modules its adapter + stand-in need.
NEEDS = {
    "redis-streams": ("redis", "fakeredis"),
    "kafka": ("aiokafka",),
    "rabbitmq": ("aio_pika",),
    "nats": ("nats",),
    "sqs": ("boto3", "moto"),
}
REAL = tuple(NEEDS)
ORDERS = ("o-1", "o-2", "o-3")


def _need(name):
    for module in NEEDS[name]:
        pytest.importorskip(module)


@pytest.fixture(params=REAL)
def broker_name(request, monkeypatch):
    _need(request.param)
    # 📝 the offline suite must never pick up a developer's live broker.
    for env in app.LIVE_ENV.values():
        monkeypatch.delenv(env, raising=False)
    return request.param


@pytest.fixture
def stand_in(broker_name):
    s = brokers_local.new_stand_in(broker_name)
    yield s
    brokers_local.close_stand_in(s)


def _build(name, workdir, stand_in, consumer="fulfilment-1"):
    return app.build_app(
        name, workdir, celery=False, stand_in=stand_in, consumer=consumer
    )


def test_demo_reaches_shipped(broker_name, tmp_path):
    summary = app.run_demo(broker_name, tmp_path)
    assert summary["broker"] == broker_name
    assert all(s == ["order.shipped"] for s in summary["orders"].values())
    assert summary["transitions"] == 9
    assert summary["outbox_rows"] == summary["published"] == 9
    assert summary["dead_letters"] == 1
    # 📝 NATS JetStream drops the repeated Nats-Msg-Id at PUBLISH time,
    #    so the inbox never sees it; everywhere else the inbox answers it.
    assert summary["duplicates"] == (0 if broker_name == "nats" else 1)


def test_outbox_rows_equal_published_and_order_holds(
    broker_name, stand_in, tmp_path
):
    a = _build(broker_name, tmp_path, stand_in)
    try:
        for n, oid in enumerate(ORDERS, start=1):
            a.command(oid, "PAY", orderId=oid, total=10 * n)
        a.pump()
        for oid in ORDERS:
            assert a.state_of(f"order:{oid}") == ["order.shipped"]
            assert a.state_of(f"warehouse:{oid}") == ["warehouse.packed"]
        assert a.outbox.count() == len(a.sent) == 9
        assert a.outbox.count(pending_only=True) == 0
        assert len({e.id for e in a.sent}) == 9
        for oid in ORDERS:
            seq = [e.type for e in a.sent if e.subject == oid]
            assert seq == ["OrderPaid", "OrderPacked", "OrderShipped"], seq
    finally:
        a.close()


def test_poison_is_dead_lettered_after_max_attempts(
    broker_name, stand_in, tmp_path
):
    a = _build(broker_name, tmp_path, stand_in)
    try:
        env = a.command("o-4", "PAYMENT_FAILED", reason=12345)
        seen = _spy_attempts(a)
        stats = a.pump()
        assert stats["dead_lettered"] == 1
        [rec] = a.dead_letters.list()
        assert rec.id == env.id
        assert rec.reason == "max_attempts"
        assert rec.attempts == app.MAX_ATTEMPTS
        # the requeue path carried the count: 0, 1, 2
        assert seen == list(range(app.MAX_ATTEMPTS)), seen
        assert a.state_of("order:o-4") is None
    finally:
        a.close()


def _spy_attempts(a):
    seen = []
    real = a.router.dispatcher.handle

    def spy(env: Envelope, **kw):
        seen.append(env.attempt)
        return real(env, **kw)

    a.router.dispatcher.handle = spy
    return seen


def test_crashed_consumer_redelivers_with_attempts(
    broker_name, stand_in, tmp_path
):
    """Consumer A fetches two commands and dies before acking. Consumer B
    (same broker, same database) gets them again through the broker's
    own redelivery path and finishes both orders."""
    a = _build(broker_name, tmp_path, stand_in, consumer="A")
    a.command("o-1", "PAY", orderId="o-1", total=10)
    a.command("o-2", "PAY", orderId="o-2", total=20)
    got = list(a.broker.subscribe(app.TOPIC, timeout=0))
    assert len(got) == 2  # read, never acked: "crash"
    brokers_local.crash(broker_name, stand_in, a.broker, got)
    b = _build(broker_name, tmp_path, stand_in, consumer="B")
    try:
        seen = _spy_attempts(b)
        b.pump()
        assert len(seen) >= 2
        if broker_name == "kafka":
            # 📝 Kafka keeps no delivery count: the un-committed offsets
            #    are re-read, and the attempt is the envelope's own.
            assert seen[:2] == [0, 0], seen
        else:
            assert all(n >= 1 for n in seen[:2]), seen
        for oid in ("o-1", "o-2"):
            assert b.state_of(f"order:{oid}") == ["order.shipped"]
        assert b.dead_letters.list() == []
    finally:
        b.close()
        a.close()


# -------------------------------------------------------------------------
# 🐳 Live variant (XSM_CONTAINERS=1 + Docker)
# -------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[4]


def _live_helpers():
    pytest.importorskip("testcontainers")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tests.contrib.brokers import test_live_containers as live

    return live


def _start_live(name, live):
    """Start the repository's pinned container; return (box, env)."""
    port = live._free_port()
    C = live._Container
    if name == "redis-streams":
        box = C(live.IMAGES["redis"], {6379: port}).start(
            lambda: live._wait_port(port)
        )
        return box, {"REDIS_URL": f"redis://127.0.0.1:{port}/0"}
    if name == "kafka":
        box = C(
            live.IMAGES["redpanda"],
            {9092: port},
            command=(
                "redpanda start --mode dev-container --smp 1 "
                "--kafka-addr 0.0.0.0:9092 "
                f"--advertise-kafka-addr 127.0.0.1:{port}"
            ),
        ).start(lambda: live._wait_kafka(port))
        return box, {"XSM_KAFKA_BOOTSTRAP": f"127.0.0.1:{port}"}
    if name == "rabbitmq":
        box = C(live.IMAGES["rabbitmq"], {5672: port}).start(
            lambda: live._wait_amqp(port)
        )
        return box, {
            "XSM_RABBITMQ_URL": f"amqp://guest:guest@127.0.0.1:{port}/"
        }
    if name == "nats":
        box = C(live.IMAGES["nats"], {4222: port}, command="-js").start(
            lambda: live._wait_port(port)
        )
        return box, {"XSM_NATS_URL": f"nats://127.0.0.1:{port}"}
    box = C(
        live.IMAGES["localstack"], {4566: port}, env={"SERVICES": "sqs"}
    ).start(lambda: live._wait_port(port))
    return box, {
        "XSM_SQS_ENDPOINT": f"http://127.0.0.1:{port}",
        "AWS_ACCESS_KEY_ID": "test",
        "AWS_SECRET_ACCESS_KEY": "test",
        "AWS_DEFAULT_REGION": "us-east-1",
    }


@pytest.mark.skipif(
    not os.environ.get("XSM_CONTAINERS"),
    reason="live brokers: XSM_CONTAINERS=1 and Docker",
)
@pytest.mark.parametrize("name", REAL)
def test_demo_on_a_live_broker(name, tmp_path, monkeypatch):
    _need(name)
    live = _live_helpers()
    box, env = _start_live(name, live)
    try:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        summary = app.run_demo(name, tmp_path / uuid.uuid4().hex[:6])
        assert all(s == ["order.shipped"] for s in summary["orders"].values())
        assert summary["outbox_rows"] == summary["published"] == 9
        assert summary["dead_letters"] == 1
    finally:
        box.stop()
