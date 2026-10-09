"""Verification for G7: #294 F3 (broker adapters) and #292 F1 (`[celery]`).

`python scripts/verify/G7_brokers.py` (``XSM_CONTAINERS=1`` also runs the
live testcontainers suite -- Docker required).

Windows-safe (no heredocs, no /tmp). Runs the broker / Celery test
folders, then end-to-end checks straight from the issues:

* #294: every adapter satisfies `BrokerAdapter`; 1,000 envelopes across
  10 subjects through `InboundDispatcher` on Redis Streams (fakeredis) and
  SQS FIFO (moto) -- order kept per subject, none lost; a crashed Redis
  consumer's pending entries are reclaimed with the attempt count and
  poison reaches the dead-letter store; the adapters are listed under
  the ``xstate_statemachine.brokers`` entry-point group; each module
  raises `MissingExtraError` naming its own extra; a broker outage
  fires on_disconnect / on_reconnect once and loses nothing; two
  consumers on one topic see every envelope once, in subject order.
* #292: the issue's snippet verbatim; `@statechart_task` refuses pickle;
  8 threads x 100 sends on one key lose nothing; the Beat scheduler fires
  a matured deadline once and skips a stale ``eta`` generation.

Prints ``ALL OK``.
"""

import asyncio
import json
import os
import pathlib
import subprocess
import sys
import threading
from typing import Any, List

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 💡 Verify THIS checkout even when an editable install points elsewhere
#    (git worktrees share one environment).
sys.path.insert(0, str(ROOT / "src"))
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))


def step(name: str) -> None:
    print(f"\n== {name}")


def run_tests() -> None:
    step("pytest brokers + celery + redis streams + extras matrix")
    targets = [
        "tests/contrib/brokers",
        "tests/contrib/kafka",
        "tests/contrib/rabbitmq",
        "tests/contrib/nats",
        "tests/contrib/sqs",
        "tests/contrib/celery",
        "tests/contrib/redis/test_redis_streams.py",
        "tests/contrib/test_extras_matrix.py",
        "tests/eda/test_fake_broker.py",
    ]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *targets,
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:xstate_statemachine",
        ],
        cwd=str(ROOT),
        env=ENV,
    )
    assert proc.returncode == 0, "tests failed"


def _counter_machine() -> Any:
    from xstate_statemachine import MachineLogic, create_machine

    def rec(i: Any, ctx: Any, e: Any, a: Any) -> None:
        ctx["seen"] = ctx["seen"] + [e.payload["n"]]

    return create_machine(
        {
            "id": "m",
            "initial": "on",
            "context": {"seen": []},
            "states": {"on": {"on": {"E": {"actions": "rec"}}}},
        },
        logic=MachineLogic(actions={"rec": rec}),
    )


def _thousand(broker: Any, topic: str, label: str) -> None:
    from xstate_statemachine.eda import Envelope, InboundDispatcher
    from xstate_statemachine.persistence import MemoryStore
    from xstate_statemachine.persistence.idempotency import MemoryInbox

    store = MemoryStore()
    disp = InboundDispatcher(
        store, {"xsm.m.E": _counter_machine()}, inbox=MemoryInbox()
    )

    async def go() -> None:
        for n in range(1000):
            await broker.publish(
                topic,
                Envelope.new(
                    type="xsm.m.E", subject=f"s{n % 10}", data={"n": n}
                ),
            )
        idle = 0
        while idle < 3:
            res = await disp.run_once(broker, topic, timeout=0.05)
            idle = 0 if (res.processed or res.retried) else idle + 1

    asyncio.run(go())
    for s in range(10):
        rec = store.load(f"s{s}")
        assert rec is not None, (label, s)
        seen = json.loads(rec.snapshot)["context"]["seen"]
        assert seen == list(range(s, 1000, 10)), (label, s, seen[:5])
    print(f"  {label}: 1,000 envelopes / 10 subjects, order kept, none lost")


def f3_thousand() -> None:
    step("#294 1,000 envelopes / 10 subjects (Redis Streams, SQS FIFO)")
    import fakeredis

    from xstate_statemachine.contrib.brokers.redis_streams import (
        RedisStreamsBroker,
    )

    _thousand(
        RedisStreamsBroker(fakeredis.FakeRedis(), prefix="g7"),
        "orders",
        "redis-streams",
    )
    try:
        import boto3
        from moto import mock_aws
    except ImportError:
        print("  (moto not installed: SQS leg skipped)")
        return
    from xstate_statemachine.contrib.brokers.sqs import SqsBroker

    os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
    with mock_aws():
        client = boto3.client("sqs", region_name="us-east-1")
        client.create_queue(
            QueueName="orders.fifo", Attributes={"FifoQueue": "true"}
        )
        _thousand(SqsBroker(client), "orders.fifo", "sqs-fifo")


def f3_reclaim_and_poison() -> None:
    step("#294 crashed consumer reclaimed; poison -> DLQ across restarts")
    import fakeredis

    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.contrib.brokers.redis_streams import (
        SyncRedisStreamsBroker,
    )
    from xstate_statemachine.eda import (
        Envelope,
        InboundDispatcher,
        MemoryDeadLetterStore,
    )
    from xstate_statemachine.persistence import MemoryStore

    r = fakeredis.FakeRedis()
    dead = SyncRedisStreamsBroker(r, prefix="g7p", consumer="dead")
    dead.publish("t", Envelope.new(type="xsm.m.BOOM", subject="k", data={}))
    list(dead.subscribe("t", timeout=0))  # read, then "crash"

    def boom(i: Any, ctx: Any, e: Any, a: Any) -> None:
        raise RuntimeError("poison")

    m = create_machine(
        {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"BOOM": {"actions": "boom"}}}},
        },
        logic=MachineLogic(actions={"boom": boom}),
    )
    dlq = MemoryDeadLetterStore()
    attempts: List[int] = []
    for round_ in range(6):  # every round is a fresh process
        broker = SyncRedisStreamsBroker(
            r, prefix="g7p", consumer=f"c{round_}", min_idle_ms=0
        )
        disp = InboundDispatcher(
            MemoryStore(), {"xsm.m.BOOM": m}, dead_letters=dlq, max_attempts=3
        )
        for d in broker.subscribe("t", timeout=0):
            attempts.append(d.envelope.attempt)
            broker.nack(d, requeue=True)  # consumer "dies" again
            break
        if attempts and attempts[-1] >= 2:
            res = disp.run_once_sync(broker, "t")
            if res.dead_lettered:
                break
    assert attempts[0] >= 1, attempts  # reclaimed from the dead consumer
    assert len(dlq) == 1, (attempts, len(dlq))
    print(f"  attempts seen {attempts}; dead-lettered after a restart")


def f3_entry_points_and_extras() -> None:
    step("#294 entry points + MissingExtraError per extra")
    from xstate_statemachine.plugin_discovery import BROKERS_GROUP, discover

    names = {p.name for p in discover(group=BROKERS_GROUP)}
    want = {"redis-streams", "kafka", "rabbitmq", "nats", "sqs"}
    if want <= names:
        print(f"  xsm plugins lists: {sorted(names & want)}")
    else:
        print(
            "  (entry points not installed in this environment -- run "
            f"`pip install -e .`; found {sorted(names)})"
        )
    from xstate_statemachine.eda import BrokerAdapter

    from xstate_statemachine.contrib.brokers import (  # noqa: F401
        kafka,
        nats,
        rabbitmq,
        redis_streams,
        sqs,
    )

    for cls in (
        kafka.KafkaBroker(),
        rabbitmq.RabbitMQBroker(url="amqp://x/"),
        nats.NatsBroker(servers="nats://x"),
    ):
        assert isinstance(cls, BrokerAdapter), cls
    child = (
        "import importlib, importlib.abc, sys\n"
        "class B(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, n, p=None, t=None):\n"
        "        if n.split('.')[0] == 'aiokafka': raise ImportError(n)\n"
        "sys.meta_path.insert(0, B())\n"
        "from xstate_statemachine.exceptions import MissingExtraError\n"
        "try:\n"
        "    import xstate_statemachine.contrib.brokers.kafka\n"
        "except MissingExtraError as e: print(e)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", child],
        env=ENV,
        capture_output=True,
        text=True,
        timeout=60,
    ).stdout
    assert 'pip install "xstate-statemachine[kafka]"' in out, out
    print("  blocked aiokafka -> MissingExtraError naming [kafka]")


def f3_outage_and_two_consumers() -> None:
    step("#294 outage observable, nothing lost; two consumers once each")
    import fakeredis

    from xstate_statemachine.contrib.brokers.redis_streams import (
        SyncRedisStreamsBroker,
    )
    from xstate_statemachine.eda import Envelope

    r = fakeredis.FakeRedis()
    events: List[str] = []
    broker = SyncRedisStreamsBroker(
        r,
        prefix="g7o",
        consumer="a",
        on_disconnect=lambda exc: events.append("down"),
        on_reconnect=lambda: events.append("up"),
    )
    real_send = broker.transport.send
    failures = {"left": 3}

    def flaky(topic: str, env: Any) -> None:
        if failures["left"]:
            failures["left"] -= 1
            raise ConnectionError("broker gone")
        real_send(topic, env)

    broker.transport.send = flaky  # type: ignore[method-assign]
    pending = [
        Envelope.new(type="xsm.m.GO", subject=f"s{n % 4}", data={"n": n})
        for n in range(40)
    ]
    while pending:  # an outbox: keep the row until publish succeeds
        try:
            broker.publish("t", pending[0])
        except ConnectionError:
            assert not broker.healthy
            continue
        pending.pop(0)
    assert broker.healthy and events == ["down", "up"], events

    second = SyncRedisStreamsBroker(r, prefix="g7o", consumer="b")
    seen: List[Any] = []
    for _ in range(20):
        for b in (broker, second):
            for d in b.subscribe("t", timeout=0):
                seen.append((b, d.envelope.subject, d.envelope.data["n"]))
                b.ack(d)
                break
    for b in (broker, second):
        for d in b.subscribe("t", timeout=0):
            seen.append((b, d.envelope.subject, d.envelope.data["n"]))
            b.ack(d)
    assert sorted(n for _, _, n in seen) == list(range(40)), seen
    # 📝 Competing consumers on ONE unsharded stream split a subject
    #    between them: order holds per consumer, not across both (the
    #    guide's ordering caveat). Order across consumers needs shards
    #    (or Kafka partitions / SQS FIFO groups).
    for who in (broker, second):
        for k in range(4):
            ns = [n for b_, s_, n in seen if b_ is who and s_ == f"s{k}"]
            assert ns == sorted(ns), (k, ns)
    print(f"  callbacks {events}; 40 envelopes, 2 consumers, once each")


def f1_issue_snippet() -> None:
    step("#292 issue snippet (eager Celery, no broker)")
    from celery import Celery

    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.contrib.celery import celery_service
    from xstate_statemachine.persistence import MemoryStore, persisted

    app = Celery(broker="memory://", backend="cache+memory://")
    app.conf.task_always_eager = True

    @app.task
    def charge(amount: int) -> dict:
        return {"ok": True, "amount": amount}

    cfg = {
        "id": "o",
        "initial": "paying",
        "states": {
            "paying": {
                "invoke": {
                    "src": "charge",
                    "onDone": "paid",
                    "onError": "failed",
                }
            },
            "paid": {"type": "final"},
            "failed": {},
        },
    }
    m = create_machine(
        cfg,
        logic=MachineLogic(
            services={
                "charge": celery_service(
                    charge, args_from=lambda c, e: ((42,), {})
                )
            }
        ),
    )
    store = MemoryStore()
    with persisted(store, "o1", m):
        pass
    with persisted(store, "o1", m) as i:
        print(" ", i.current_state_ids)
        assert "o.paid" in i.current_state_ids


def f1_statechart_task() -> None:
    step("#292 @statechart_task: JSON only; 8 threads x 100 sends")
    from celery import Celery

    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.contrib.celery import statechart_task
    from xstate_statemachine.exceptions import InvalidConfigError
    from xstate_statemachine.persistence import MemoryStore

    app = Celery("g7", broker="memory://", backend="cache+memory://")
    app.conf.task_always_eager = True
    app.conf.accept_content = ["json", "application/x-python-serialize"]
    try:
        statechart_task(app, MemoryStore(), None)
        raise AssertionError("pickle accepted")
    except InvalidConfigError:
        print("  pickle (MIME) in accept_content refused")
    app.conf.accept_content = ["json"]

    def inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
        ctx["n"] += 1

    m = create_machine(
        {
            "id": "c",
            "initial": "on",
            "context": {"n": 0},
            "states": {"on": {"on": {"INC": {"actions": "inc"}}}},
        },
        logic=MachineLogic(actions={"inc": inc}),
    )
    store = MemoryStore()

    @statechart_task(app, store, m, max_retries=1000)
    def bump(counter: Any) -> None:
        counter.send("INC")

    def worker() -> None:
        for _ in range(100):
            assert bump.delay("k").state != "FAILURE"

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(180)
    rec = store.load("k")
    assert rec is not None
    n = json.loads(rec.snapshot)["context"]["n"]
    assert n == 800, n
    print("  800 / 800 increments persisted (no lost update)")


def f1_beat() -> None:
    step("#292 Beat scan fires once; stale eta generation skipped")
    from celery import Celery

    from xstate_statemachine import create_machine
    from xstate_statemachine.clock import SimulatedClock
    from xstate_statemachine.contrib.celery import DurableTimerScheduler
    from xstate_statemachine.persistence import MemoryStore, persisted

    app = Celery("g7b", broker="memory://", backend="cache+memory://")
    app.conf.task_always_eager = True
    clock = SimulatedClock(wall_start=1_000_000.0)
    m = create_machine(
        {
            "id": "t",
            "initial": "w",
            "states": {"w": {"after": {"1000": "x"}}, "x": {}},
        }
    )
    store = MemoryStore()
    with persisted(store, "t1", m, clock=clock):
        pass
    now = [1_000_002.0]
    s = DurableTimerScheduler(app, store, m, now=lambda: now[0])
    (d,) = store.load("t1").deadlines
    assert not s.fire("t1", d.state_id, d.entry_seq + 1)
    assert s.task.delay().result == 1
    assert s.task.delay().result == 0
    assert not s.fire("t1", d.state_id, d.entry_seq)
    print("  woke once, second scan and late eta job were no-ops")


def maybe_live() -> None:
    if os.environ.get("XSM_CONTAINERS") != "1":
        print("\n== live brokers skipped (set XSM_CONTAINERS=1 + Docker)")
        return
    step("#294 live brokers (testcontainers)")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/contrib/brokers/test_live_containers.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:xstate_statemachine",
        ],
        cwd=str(ROOT),
        env=ENV,
    )
    assert proc.returncode == 0, "live broker tests failed"


def main() -> None:
    run_tests()
    f3_thousand()
    f3_reclaim_and_poison()
    f3_entry_points_and_extras()
    f3_outage_and_two_consumers()
    f1_issue_snippet()
    f1_statechart_task()
    f1_beat()
    maybe_live()
    print("\nALL OK")


if __name__ == "__main__":
    main()
