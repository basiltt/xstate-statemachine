# tests/contrib/redis/test_redis_streams.py
"""#294: `RedisStreamsBroker` / `SyncRedisStreamsBroker` -- the shared
`AsyncBrokerContract` against fakeredis (Lua) or a live ``XSM_REDIS_URL``,
plus Streams specifics: consumer groups + XACK, PEL reclaim after
``min_idle_ms`` with the delivery count carried as the attempt, sharding
by subject, per-subject order under 1,000 envelopes / 10 subjects through
`InboundDispatcher`, ``maxlen``, no URL in ``repr``."""

from __future__ import annotations

import asyncio
import os
import time
import unittest
import uuid
from typing import Any

import pytest

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.eda import (
    BrokerAdapter,
    Envelope,
    InboundDispatcher,
    SyncBrokerAdapter,
)
from src.xstate_statemachine.persistence import MemoryStore

from ...eda.contract import AsyncBrokerContract
from ..conftest import requires_extra
from .conftest import _client

pytestmark = requires_extra("redis")


def _env(subject: str, n: int) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


class _Fresh:
    def setUp(self) -> None:
        self.client = _client()
        self.prefix = f"t-{uuid.uuid4().hex[:8]}"

    def tearDown(self) -> None:
        for k in self.client.scan_iter(match=f"{self.prefix}:*"):
            self.client.delete(k)

    def sync(self, **kw: Any) -> Any:
        from src.xstate_statemachine.contrib.brokers.redis_streams import (
            SyncRedisStreamsBroker,
        )

        return SyncRedisStreamsBroker(self.client, prefix=self.prefix, **kw)

    def make_broker(self) -> Any:
        from src.xstate_statemachine.contrib.brokers.redis_streams import (
            RedisStreamsBroker,
        )

        return RedisStreamsBroker(self.client, prefix=self.prefix)


class TestRedisStreamsContract(_Fresh, AsyncBrokerContract, unittest.TestCase):
    pass


class TestRedisStreamsSharded(_Fresh, AsyncBrokerContract, unittest.TestCase):
    def make_broker(self) -> Any:
        from src.xstate_statemachine.contrib.brokers.redis_streams import (
            RedisStreamsBroker,
        )

        return RedisStreamsBroker(self.client, prefix=self.prefix, shards=4)


class TestRedisStreamsSpecific(_Fresh, unittest.TestCase):
    def test_protocols_and_repr(self) -> None:
        b = self.sync()
        self.assertIsInstance(b, SyncBrokerAdapter)
        self.assertIsInstance(self.make_broker(), BrokerAdapter)
        self.assertNotIn("redis://", repr(b))
        self.assertIn(self.prefix, repr(self.make_broker()))

    def test_prefix_is_mandatory(self) -> None:
        from src.xstate_statemachine.contrib.brokers.redis_streams import (
            SyncRedisStreamsBroker,
        )
        from src.xstate_statemachine.exceptions import InvalidConfigError

        with self.assertRaises(InvalidConfigError):
            SyncRedisStreamsBroker(self.client, prefix="")
        with self.assertRaises(ValueError):
            SyncRedisStreamsBroker(prefix="p")  # no client, no url
        with self.assertRaises(ValueError):
            SyncRedisStreamsBroker(self.client, prefix="p", shards=0)

    def test_ack_is_xack_and_stream_key_uses_prefix(self) -> None:
        b = self.sync()
        b.publish("orders", _env("o-1", 1))
        stream = f"{self.prefix}:stream:orders"
        self.assertEqual(self.client.xlen(stream), 1)
        (d,) = list(b.subscribe("orders", timeout=0))
        self.assertEqual(self.client.xpending(stream, "xsm")["pending"], 1)
        b.ack(d)
        self.assertEqual(self.client.xpending(stream, "xsm")["pending"], 0)

    def test_dead_consumer_entries_are_reclaimed_with_attempts(self) -> None:
        dead = self.sync(consumer="dead")
        dead.publish("orders", _env("o-1", 1))
        list(dead.subscribe("orders", timeout=0))  # read, never acked
        alive = self.sync(consumer="alive", min_idle_ms=0)
        (d,) = list(alive.subscribe("orders", timeout=0))
        self.assertEqual(d.envelope.data["n"], 1)
        self.assertGreaterEqual(d.envelope.attempt, 1)
        alive.ack(d)
        self.assertEqual(list(alive.subscribe("orders", timeout=0)), [])

    def test_reclaim_never_bumps_our_own_held_entries(self) -> None:
        """M3: two live consumers; the second one's reclaim must not
        claim (and so re-count) entries the first still holds, nor its
        own; a dead consumer's entries are claimed with one XCLAIM."""
        a = self.sync(consumer="a", min_idle_ms=0)
        b = self.sync(consumer="b", min_idle_ms=0)
        for n in range(3):
            a.publish("t", _env("k", n))
        held_by_b = list(b.subscribe("t", timeout=0))  # b holds all 3
        stream = f"{self.prefix}:stream:t"
        before = {
            r["message_id"]: r["times_delivered"]
            for r in self.client.xpending_range(stream, "xsm", "-", "+", 10)
        }
        list(b.subscribe("t", timeout=0))  # b polls again: skips its own
        after = {
            r["message_id"]: (r["consumer"], r["times_delivered"])
            for r in self.client.xpending_range(stream, "xsm", "-", "+", 10)
        }
        for mid, n in before.items():
            self.assertEqual(after[mid], (b"b", n))
        # a is alive and idle: b's entries ARE eligible for a (b "died")
        got = list(a.subscribe("t", timeout=0))
        self.assertEqual([d.envelope.attempt for d in got], [1, 1, 1])
        self.assertEqual(len(held_by_b), 3)

    def test_not_reclaimed_before_min_idle(self) -> None:
        dead = self.sync(consumer="dead")
        dead.publish("orders", _env("o-1", 1))
        list(dead.subscribe("orders", timeout=0))
        alive = self.sync(consumer="alive", min_idle_ms=60_000)
        self.assertEqual(list(alive.subscribe("orders", timeout=0)), [])

    def test_shard_is_stable_per_subject(self) -> None:
        b = self.sync(shards=4)
        t = b.transport
        self.assertEqual(t.shard_of("o-1"), t.shard_of("o-1"))
        self.assertEqual(len(t.streams("x")), 4)
        self.assertTrue(t.stream("x", 3).endswith(":stream:x:3"))

    def test_maxlen_trims(self) -> None:
        b = self.sync(maxlen=5)
        for n in range(50):
            b.publish("t", _env("k", n))
        self.assertLess(self.client.xlen(f"{self.prefix}:stream:t"), 50)

    def test_group_created_once_even_if_it_exists(self) -> None:
        self.client.xgroup_create(
            f"{self.prefix}:stream:t", "xsm", id="0", mkstream=True
        )
        self.assertEqual(list(self.sync().subscribe("t", timeout=0)), [])

    def test_blocking_read_waits(self) -> None:
        if not os.environ.get("XSM_REDIS_URL"):
            self.skipTest("fakeredis BLOCK semantics are not a real server's")
        b = self.sync()
        t0 = time.monotonic()
        self.assertEqual(list(b.subscribe("t", timeout=0.2)), [])
        self.assertGreaterEqual(time.monotonic() - t0, 0.15)

    def test_thousand_envelopes_ten_subjects_through_dispatcher(self) -> None:
        cfg = {
            "id": "m",
            "initial": "on",
            "context": {"seen": []},
            "states": {"on": {"on": {"E": {"actions": "rec"}}}},
        }

        def rec(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ctx["seen"] = ctx["seen"] + [e.payload["n"]]

        machine = create_machine(cfg, logic=MachineLogic(actions={"rec": rec}))
        store = MemoryStore()
        broker = self.make_broker()
        disp = InboundDispatcher(store, {"xsm.m.E": machine})

        async def go() -> None:
            for n in range(1000):
                await broker.publish("t", _env(f"s{n % 10}", n))
            while True:
                res = await disp.run_once(broker, "t", timeout=0.05)
                if not (res.processed or res.retried):
                    break

        asyncio.run(go())
        for s in range(10):
            import json

            rec_ = store.load(f"s{s}")
            assert rec_ is not None
            seen = json.loads(rec_.snapshot)["context"]["seen"]
            self.assertEqual(seen, list(range(s, 1000, 10)))


@pytest.mark.skipif(
    not os.environ.get("XSM_REDIS_URL"), reason="live Redis: XSM_REDIS_URL"
)
def test_live_url_constructor() -> None:
    from src.xstate_statemachine.contrib.brokers.redis_streams import (
        SyncRedisStreamsBroker,
    )

    p = f"t-{uuid.uuid4().hex[:8]}"
    b = SyncRedisStreamsBroker(url=os.environ["XSM_REDIS_URL"], prefix=p)
    b.publish("t", _env("k", 1))
    (d,) = list(b.subscribe("t", timeout=0.1))
    b.ack(d)
    for k in b.transport.client.scan_iter(match=f"{p}:*"):
        b.transport.client.delete(k)
    b.close()
