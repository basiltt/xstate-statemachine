# tests/eda/test_battle_293_a.py
"""#293 battle, adversary A: concurrency, crash consistency and resource
bounds of the EDA core (dispatcher, outbox relay leases, dead letters,
envelope decoding)."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import threading
import time
import tracemalloc
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine.eda import (
    Envelope,
    EnvelopeCorruptError,
    FakeBrokerAdapter,
    InboundDispatcher,
    MemoryOutboxStore,
    OutboxRelay,
    SQLiteDeadLetterStore,
    SQLiteOutboxStore,
    SyncFakeBrokerAdapter,
)
from src.xstate_statemachine.patterns.dead_letter import DeadLetter
from src.xstate_statemachine.persistence import (
    MemoryStore,
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
)

from .test_dispatcher import _add, _counter


def _seen(store: Any, key: str) -> List[int]:
    return list(json.loads(store.load(key).snapshot)["context"]["seen"])


_REQ = '{"id":"x","type":"t","source":"s","specversion":"1.0"'


# -----------------------------------------------------------------------------
# ✉️ Envelope decoding never escapes as a non-envelope error
# -----------------------------------------------------------------------------
class TestEnvelopeRecursion(unittest.TestCase):
    def test_deeply_nested_json_is_corrupt_not_recursion(self) -> None:
        # 🔥 Under the 1 MiB cap but deeper than the C parser allows.
        for text in (
            "[" * 200_000 + "]" * 200_000,
            _REQ + ',"data":' + "[" * 200_000 + "]" * 200_000 + "}",
        ):
            with self.assertRaises(EnvelopeCorruptError):
                Envelope.from_json(text)

    def test_unencodable_data_is_corrupt_on_to_json(self) -> None:
        deep: List[Any] = []
        cur = deep
        for _ in range(100_000):
            nxt: List[Any] = []
            cur.append(nxt)
            cur = nxt
        cyclic: Dict[str, Any] = {}
        cyclic["me"] = cyclic
        for data in ({"d": deep}, cyclic):
            env = Envelope.new(type="t", data=data)
            with self.assertRaises(EnvelopeCorruptError):
                env.to_json()

    def test_max_bytes_is_inclusive(self) -> None:
        env = Envelope.new(type="t", data={"a": "é" * 10})
        n = len(env.to_json().encode("utf-8"))
        Envelope.from_json(env.to_json(max_bytes=n), max_bytes=n)
        with self.assertRaises(EnvelopeCorruptError):
            env.to_json(max_bytes=n - 1)
        with self.assertRaises(EnvelopeCorruptError):
            Envelope.from_json(env.to_json(), max_bytes=n - 1)

    def test_garbage_shapes(self) -> None:
        bad = [
            b"\xff\xfe",
            "null",
            "[]",
            _REQ + ',"time":5}',
            _REQ + ',"extensions":{}}',
            _REQ.replace('"1.0"', "1") + "}",
            _REQ + ',"xsmattempt":-1}',
            _REQ + ',"xsmattempt":true}',
            _REQ + ',"Bad-Name":1}',
            _REQ + ',"traceparent":"00-zz"}',
            _REQ + ',"subject":["x"]}',
            '{"id":"x","type":"t","source":"s"}',
            12,
            None,
        ]
        for raw in bad:
            with self.subTest(raw=str(raw)[:40]):
                with self.assertRaises(EnvelopeCorruptError):
                    Envelope.from_json(raw)  # type: ignore[arg-type]

    def test_new_id_strictly_increasing_across_threads(self) -> None:
        from src.xstate_statemachine.eda import new_id

        out: List[List[str]] = [[] for _ in range(8)]

        def mint(bucket: List[str]) -> None:
            for _ in range(2000):
                bucket.append(new_id())

        ts = [threading.Thread(target=mint, args=(b,)) for b in out]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        every = [i for b in out for i in b]
        self.assertEqual(len(set(every)), len(every))
        for b in out:  # 📝 per thread: monotonic
            self.assertEqual(b, sorted(b))


# -----------------------------------------------------------------------------
# 📥 Dispatcher: user hooks that raise are poison too (X0.8)
# -----------------------------------------------------------------------------
class TestHooksThatRaise(unittest.TestCase):
    def _drain(self, d: InboundDispatcher, b: Any, rounds: int) -> List[str]:
        seen: List[str] = []
        for _ in range(rounds):
            seen += [o for _, o in d.run_once_sync(b, "t").outcomes]
        return seen

    def test_machine_for_type_raising_is_dead_lettered(self) -> None:
        def registry(_: str) -> Any:
            raise RuntimeError("registry down")

        d = InboundDispatcher(MemoryStore(), registry, max_attempts=3)
        b = SyncFakeBrokerAdapter()
        b.deliver("t", _add("s", 1))
        seen = self._drain(d, b, 6)
        self.assertEqual(
            seen, ["retry", "retry", "dead_lettered:max_attempts"]
        )
        self.assertEqual(b.pending("t"), 0)
        self.assertEqual(len(d.dead_letters), 1)

    def test_key_for_raising_mid_batch_spares_other_subjects(self) -> None:
        def key_for(env: Envelope, machine: Any) -> str:
            if env.subject == "bad":
                raise ValueError("no key")
            return str(env.subject)

        store = MemoryStore()
        d = InboundDispatcher(
            store,
            {"xsm.counter.ADD": _counter()},
            key_for=key_for,
            max_attempts=2,
        )
        b = SyncFakeBrokerAdapter()
        for n in range(3):
            b.deliver("t", _add("good", n))
            b.deliver("t", _add("bad", n))
        self._drain(d, b, 6)
        self.assertEqual(b.pending("t"), 0)
        snap = store.load("good")
        self.assertIsNotNone(snap)
        self.assertEqual(len(d.dead_letters), 3)

    def test_dead_letter_store_down_keeps_the_message(self) -> None:
        def registry(_: str) -> Any:
            raise RuntimeError("registry down")

        def broken_dlq(rec: Any) -> None:
            raise OSError("disk full")

        d = InboundDispatcher(
            MemoryStore(), registry, max_attempts=1, dead_letters=broken_dlq
        )
        b = SyncFakeBrokerAdapter()
        b.deliver("t", _add("s", 1))
        self.assertEqual(self._drain(d, b, 3), ["retry"] * 3)
        self.assertEqual(b.pending("t"), 1)  # ⚠️ never acked unrecorded


# -----------------------------------------------------------------------------
# 🔀 Dispatcher under concurrency: order per subject, no loss, no dup
# -----------------------------------------------------------------------------
def _poisoned(env: Any) -> None:
    if env.payload.get("poison"):
        raise RuntimeError("poison")


class TestAsyncDispatcherConcurrency(unittest.TestCase):
    def _run(self, lock: Any) -> None:
        d_ = tempfile.mkdtemp()
        store = SQLiteStore(os.path.join(d_, "s.db"))
        try:
            self._scenario(store, lock)
        finally:
            store.close()

    def _scenario(self, store: Any, lock: Any) -> None:
        d = InboundDispatcher(
            store,
            {"xsm.counter.ADD": _counter(_poisoned)},
            lock=lock,
            inbox=SQLiteInbox(store),
            max_in_flight=8,
            max_attempts=2,
        )
        broker = FakeBrokerAdapter()
        subjects = [f"s{i}" for i in range(12)]
        for n in range(15):
            for s in subjects:
                env = _add(s, n)
                broker._inject("t", env)
                if n % 4 == 0:
                    broker._inject("t", env)  # 📝 interleaved duplicate
        for s in subjects[:3]:
            broker._inject("t", _add_poison(s))

        async def go() -> None:
            for _ in range(40):
                await d.run_once(broker, "t")
                if not broker.pending("t"):
                    return

        asyncio.run(go())
        self.assertEqual(broker.pending("t"), 0)
        for s in subjects:
            seen = _seen(store, s)
            self.assertEqual(seen, list(range(15)), s)

    def test_optimistic(self) -> None:
        self._run(None)

    def test_pessimistic(self) -> None:
        self._run(PessimisticLock())


def _add_poison(subject: str) -> Envelope:
    return Envelope.new(
        type="xsm.counter.ADD", subject=subject, data={"n": -1, "poison": 1}
    )


class TestSyncDispatcherThreads(unittest.TestCase):
    def test_one_dispatcher_many_threads(self) -> None:
        store = MemoryStore()
        d = InboundDispatcher(store, {"xsm.counter.ADD": _counter()})
        brokers = [SyncFakeBrokerAdapter() for _ in range(6)]
        for k, b in enumerate(brokers):
            for n in range(50):
                b.deliver("t", _add(f"k{k}", n))

        def work(b: Any) -> None:
            while b.pending("t"):
                d.run_once_sync(b, "t")

        ts = [threading.Thread(target=work, args=(b,)) for b in brokers]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        for k in range(6):
            self.assertEqual(_seen(store, f"k{k}"), list(range(50)))

    def test_attempt_table_under_concurrent_bump_forget(self) -> None:
        d = InboundDispatcher(MemoryStore(), {})
        envs = [_add("s", n) for n in range(200)]

        def churn() -> None:
            for _ in range(20):
                for e in envs:
                    d._bump(e)
                    d._forget(e)

        ts = [threading.Thread(target=churn) for _ in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len(d._attempts), 0)


# -----------------------------------------------------------------------------
# 📤 Relay leases
# -----------------------------------------------------------------------------
class _SlowBroker:
    def __init__(self, delay: float = 0.0) -> None:
        self.delay = delay
        self.seen: List[str] = []
        self._lock = threading.Lock()

    def publish(self, topic: str, env: Envelope) -> None:
        time.sleep(self.delay)
        with self._lock:
            self.seen.append(env.id)


class TestRelayLeases(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.store = SQLiteStore(os.path.join(self.dir, "o.db"))
        self.outbox = SQLiteOutboxStore(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def test_four_relays_four_threads_publish_each_row_once(self) -> None:
        for n in range(400):
            self.outbox.add("t", Envelope.new(type="x", data={"n": n}))
        broker = _SlowBroker()

        def drain() -> None:
            relay = OutboxRelay(self.outbox, broker, batch=7)
            while relay.relay_once_sync():
                pass

        ts = [threading.Thread(target=drain) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        self.assertEqual(len(broker.seen), 400)
        self.assertEqual(len(set(broker.seen)), 400)
        self.assertEqual(self.outbox.count(pending_only=True), 0)

    def test_lease_expiry_takeover_loses_nothing(self) -> None:
        for n in range(5):
            self.outbox.add("t", Envelope.new(type="x", data={"n": n}))
        slow, fast = _SlowBroker(0.05), _SlowBroker()
        a = OutboxRelay(self.outbox, slow, owner="a", lease_s=0.05)
        b = OutboxRelay(self.outbox, fast, owner="b", lease_s=30)
        t = threading.Thread(target=a.relay_once_sync)
        t.start()
        time.sleep(0.12)  # 📝 a's lease expired mid-batch
        b.relay_once_sync()
        t.join(10)
        # ✅ at-least-once: every row out, none pending, B's lease freed
        self.assertEqual(len(set(slow.seen) | set(fast.seen)), 5)
        self.assertEqual(self.outbox.count(pending_only=True), 0)

    def test_async_broker_raising_half_way_releases_the_rest(self) -> None:
        for n in range(6):
            self.outbox.add("t", Envelope.new(type="x", data={"n": n}))

        class Half:
            def __init__(self) -> None:
                self.n = 0

            async def publish(self, topic: str, env: Envelope) -> None:
                self.n += 1
                if self.n == 4:
                    raise ConnectionError("broker gone")

        relay = OutboxRelay(self.outbox, Half(), owner="a")
        with self.assertRaises(ConnectionError):
            asyncio.run(relay.relay_once())
        self.assertEqual(self.outbox.count(pending_only=True), 3)
        other = OutboxRelay(self.outbox, _SlowBroker(), owner="b")
        self.assertEqual(other.relay_once_sync(), 3)  # 💡 not lease-blocked

    def test_memory_outbox_under_threads(self) -> None:
        ob = MemoryOutboxStore()
        broker = _SlowBroker()

        def produce() -> None:
            for n in range(200):
                ob.add("t", Envelope.new(type="x", data={"n": n}))

        def drain(stop: threading.Event) -> None:
            relay = OutboxRelay(ob, broker, batch=5)
            while not stop.is_set() or len(ob):
                relay.relay_once_sync()

        stop = threading.Event()
        ps = [threading.Thread(target=produce) for _ in range(3)]
        cs = [threading.Thread(target=drain, args=(stop,)) for _ in range(3)]
        for t in ps + cs:
            t.start()
        for t in ps:
            t.join()
        stop.set()
        for t in cs:
            t.join(30)
        self.assertEqual(len(broker.seen), 600)
        self.assertEqual(len(set(broker.seen)), 600)


# -----------------------------------------------------------------------------
# ☠️ Dead letters
# -----------------------------------------------------------------------------
def _dl(i: int, **kw: Any) -> DeadLetter:
    base: Dict[str, Any] = dict(
        machine_id="m",
        state_id="",
        event={"type": "E", "payload": {"password": "hunter2", "n": i}},
        attempts=1,
        errors=[],
        snapshot={"context": {"api_token": "abc"}},
        taken_at=time.time(),
        id=f"r{i}",
        reason="max_attempts",
    )
    base.update(kw)
    return DeadLetter(**base)


class TestDeadLetters(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.store = SQLiteStore(os.path.join(self.dir, "d.db"))
        self.dlq = SQLiteDeadLetterStore(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def test_threads_put_and_purge_concurrently(self) -> None:
        def put(k: int) -> None:
            for i in range(100):
                self.dlq.put(_dl(k * 1000 + i))

        def purge() -> None:
            for _ in range(20):
                self.dlq.purge_older_than(0.0)  # 📝 nothing that old

        ts = [threading.Thread(target=put, args=(k,)) for k in range(4)]
        ts.append(threading.Thread(target=purge))
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        self.assertEqual(len(self.dlq), 400)

    def test_secrets_are_redacted_on_disk(self) -> None:
        self.dlq.put(_dl(1, envelope={"data": {"token": "t0k"}, "id": "r1"}))
        raw = (
            self.store._conn()
            .execute("SELECT record FROM xsm_dead_letters")
            .fetchone()[0]
        )
        for secret in ("hunter2", "abc", "t0k"):
            self.assertNotIn(secret, raw)

    def test_dispatcher_dead_letter_redacts_payload(self) -> None:
        d = InboundDispatcher(MemoryStore(), {}, dead_letters=self.dlq)
        env = Envelope.new(
            type="nope", subject="s", data={"password": "hunter2"}
        )
        d.handle(env)
        raw = (
            self.store._conn()
            .execute("SELECT record FROM xsm_dead_letters")
            .fetchone()[0]
        )
        self.assertNotIn("hunter2", raw)


# -----------------------------------------------------------------------------
# 💧 Leaks on the hot path
# -----------------------------------------------------------------------------
class TestLeaks(unittest.TestCase):
    def test_handle_hot_path_does_not_grow(self) -> None:
        store = MemoryStore()
        d = InboundDispatcher(store, {"xsm.counter.ADD": _counter()})
        subjects = [f"s{i % 50}" for i in range(4000)]

        def burst(lo: int, hi: int) -> None:
            for i in range(lo, hi):
                d.handle(Envelope.new(type="nope", subject=subjects[i]))

        burst(0, 1000)  # 📝 warm-up
        tracemalloc.start()
        burst(1000, 2500)
        mid = tracemalloc.get_traced_memory()[0]
        burst(2500, 4000)
        end = tracemalloc.get_traced_memory()[0]
        tracemalloc.stop()
        # ⚠️ MemoryDeadLetterStore grows by design; compare per-batch
        #    growth, which must stay roughly linear, not explode.
        self.assertLess(end - mid, (mid + 1) * 2)
        self.assertEqual(len(d._attempts), 0)


class TestOutboxPluginBounds(unittest.TestCase):
    def test_conflict_leaves_no_row_and_no_buffer(self) -> None:
        from src.xstate_statemachine.eda import OutboxPlugin
        from src.xstate_statemachine.persistence import persisted

        from .test_outbox import _machine

        st = MemoryStore()
        ob = MemoryOutboxStore()
        pl = OutboxPlugin(ob)
        with persisted(st, "o", _machine(), plugins=[pl]):
            pass
        with self.assertRaises(Exception):
            with persisted(st, "o", _machine(), plugins=[pl]) as i:
                i.send("PAY")
                with persisted(st, "o", _machine()) as j:  # 🔥 wins
                    j.send("NOTE")
        self.assertEqual(len(ob), 0)
        self.assertEqual(pl._buffers, {})

    def test_plugin_hot_path_holds_nothing(self) -> None:
        from src.xstate_statemachine.eda import OutboxPlugin
        from src.xstate_statemachine.persistence import persisted

        from .test_outbox import _machine

        st = MemoryStore()
        pl = OutboxPlugin(MemoryOutboxStore())
        for k in range(2000):
            with persisted(st, f"o{k % 20}", _machine(), plugins=[pl]) as i:
                i.send("TOUCH")
        self.assertEqual((len(pl._buffers), len(pl._step)), (0, 0))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
