# tests/eda/test_outbox.py
"""#293: `OutboxPlugin` publishes ONLY chart-tagged transitions; with a
`SQLiteOutboxStore` sharing the `SQLiteStore` the row commits with the
snapshot and a forced failure after the write leaves NO row (X0.3); the
relay moves rows at-least-once; direct-broker mode; both engines."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from typing import Any

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.eda import (
    Envelope,
    FakeBrokerAdapter,
    InboundDispatcher,
    MemoryOutboxStore,
    OutboxPlugin,
    OutboxRelay,
    OutboxStore,
    SQLiteOutboxStore,
    SyncFakeBrokerAdapter,
    publish_specs,
)
from src.xstate_statemachine.persistence import (
    MemoryStore,
    PessimisticLock,
    SQLiteStore,
    persisted,
)

CFG = {
    "id": "order",
    "initial": "open",
    "context": {"total": 7, "secret_token": "s3cr3t", "note": "n"},
    "states": {
        "open": {
            "on": {
                "PAY": {
                    "target": "paid",
                    "meta": {
                        "publish": {"type": "order.paid", "data": ["total"]}
                    },
                },
                "NOTE": {"actions": []},  # not tagged: never published
                "TOUCH": {"meta": {"publish": "order.touched"}},
                "BAD": {"meta": {"publish": True}},
            }
        },
        "paid": {"tags": ["publish"], "on": {"SHIP": "shipped"}},
        "shipped": {"type": "final"},
    },
}


def _machine() -> Any:
    return create_machine(CFG)


class TestSelection(unittest.TestCase):
    def test_only_tagged_transitions_publish(self) -> None:
        sink = MemoryOutboxStore()
        i = SyncInterpreter(_machine()).use(OutboxPlugin(sink)).start()
        i.send("NOTE")
        self.assertEqual(len(sink), 0)
        i.send("TOUCH")
        i.send("BAD")
        i.send("PAY")
        types = [r.envelope.type for r in sink.pending()]
        self.assertEqual(
            types,
            [
                "order.touched",
                "xsm.order.transition.open",
                "order.paid",
                "xsm.order.transition.paid",
            ],
        )
        paid = sink.pending()[2].envelope
        self.assertEqual(paid.data, {"total": 7})  # only the listed field
        state_ev = sink.pending()[3].envelope
        self.assertEqual(state_ev.data["secret_token"], "***")  # redacted
        self.assertEqual(state_ev.machineid, "order")
        self.assertIsInstance(sink, OutboxStore)
        i.stop()

    def test_publish_specs(self) -> None:
        specs = publish_specs(_machine())
        self.assertEqual(
            sorted(s["type"] for s in specs),
            sorted(
                [
                    "order.paid",
                    "order.touched",
                    "xsm.order.transition.open",
                    "xsm.order.transition.paid",
                ]
            ),
        )

    def test_invalid_publish_meta_fails_loudly(self) -> None:
        for bad in ({"type": 3}, {"type": "x", "data": "total"}, 5):
            cfg = {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"E": {"meta": {"publish": bad}}}}},
            }
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    publish_specs(create_machine(cfg))

    def test_transition_meta_must_be_a_dict(self) -> None:
        from src.xstate_statemachine.exceptions import InvalidConfigError

        with self.assertRaises(InvalidConfigError):
            create_machine(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"on": {"E": {"meta": "x"}}}},
                }
            )

    def test_async_engine(self) -> None:
        async def go() -> Any:
            sink = MemoryOutboxStore()
            i = Interpreter(_machine()).use(OutboxPlugin(sink))
            await i.start()
            await i.send("PAY", wait=True)
            await i.stop()
            return [r.envelope.type for r in sink.pending()]

        self.assertEqual(
            asyncio.run(go()), ["order.paid", "xsm.order.transition.paid"]
        )


class TestSQLiteTransactional(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.store = SQLiteStore(os.path.join(self.dir, "o.db"))
        self.outbox = SQLiteOutboxStore(self.store)

    def tearDown(self) -> None:
        self.store.close()

    def test_row_commits_with_the_snapshot(self) -> None:
        plugin = OutboxPlugin(self.outbox, topic="orders")
        with persisted(
            self.store,
            "o-1",
            _machine(),
            lock=PessimisticLock(),
            plugins=[plugin],
        ) as i:
            i.send("PAY")
        self.assertEqual(self.outbox.count(), 2)
        self.assertIsNotNone(self.store.load("o-1"))
        [a, b] = self.outbox.pending()
        self.assertEqual((a.topic, a.envelope.type), ("orders", "order.paid"))
        self.assertLess(a.seq, b.seq)
        self.assertIs(self.outbox.shares_connection_with, self.store)

    def test_forced_failure_after_the_write_leaves_no_row(self) -> None:
        plugin = OutboxPlugin(self.outbox)
        real_add = self.outbox.add

        def add_then_fail(topic: str, env: Envelope) -> None:
            real_add(topic, env)  # the row IS written ...
            raise RuntimeError("crash after the outbox write")

        self.outbox.add = add_then_fail  # type: ignore[method-assign]
        with self.assertRaises(RuntimeError):
            with persisted(
                self.store,
                "o-1",
                _machine(),
                lock=PessimisticLock(),
                plugins=[plugin],
            ) as i:
                i.send("PAY")
        # ... and rolled back WITH the snapshot.
        self.assertEqual(self.outbox.count(), 0)
        self.assertIsNone(self.store.load("o-1"))

    def test_failure_inside_the_block_writes_nothing(self) -> None:
        plugin = OutboxPlugin(self.outbox)
        with self.assertRaises(ValueError):
            with persisted(
                self.store,
                "o-1",
                _machine(),
                lock=PessimisticLock(),
                plugins=[plugin],
            ) as i:
                i.send("PAY")
                raise ValueError("business rule")
        self.assertEqual(self.outbox.count(), 0)

    def test_relay_marks_sent_and_retries_failures(self) -> None:
        plugin = OutboxPlugin(self.outbox)
        with persisted(self.store, "o-1", _machine(), plugins=[plugin]) as i:
            i.send("PAY")
        broker = SyncFakeBrokerAdapter()
        broker.fail_next_publish()
        relay = OutboxRelay(self.outbox, broker)
        with self.assertRaises(ConnectionError):
            relay.relay_once_sync()
        self.assertEqual(self.outbox.count(pending_only=True), 2)
        self.assertEqual(relay.relay_once_sync(), 2)
        self.assertEqual(self.outbox.count(pending_only=True), 0)
        self.assertEqual(relay.relay_once_sync(), 0)
        self.assertEqual(len(broker.published), 2)
        self.assertEqual(self.outbox.purge_sent(older_than_s=-1), 2)
        self.assertEqual(self.outbox.mark_sent([]), 0)

    def test_async_relay(self) -> None:
        self.outbox.add("t", Envelope.new(type="x"))
        broker = FakeBrokerAdapter()
        self.assertEqual(
            asyncio.run(OutboxRelay(self.outbox, broker).relay_once()), 1
        )
        self.assertEqual(len(broker.published), 1)

    def test_standalone_path(self) -> None:
        ob = SQLiteOutboxStore(os.path.join(self.dir, "side.db"))
        self.assertIsNone(ob.shares_connection_with)
        ob.add("t", Envelope.new(type="x"))
        self.assertEqual(ob.count(), 1)
        ob.close()


class TestDirectBroker(unittest.TestCase):
    def test_sync_broker_after_the_step(self) -> None:
        broker = SyncFakeBrokerAdapter()
        i = SyncInterpreter(_machine()).use(OutboxPlugin(broker)).start()
        i.send("PAY")
        self.assertEqual(
            [e.type for e in broker.published_on("events")],
            ["order.paid", "xsm.order.transition.paid"],
        )
        i.stop()

    def test_async_broker_from_the_sync_engine(self) -> None:
        broker = FakeBrokerAdapter()
        i = SyncInterpreter(_machine()).use(OutboxPlugin(broker)).start()
        i.send("PAY")  # no loop: run to completion
        self.assertEqual(len(broker.published), 2)
        i.stop()

    def test_async_broker_on_the_async_engine(self) -> None:
        async def go() -> int:
            broker = FakeBrokerAdapter()
            plugin = OutboxPlugin(broker)
            i = Interpreter(_machine()).use(plugin)
            await i.start()
            await i.send("PAY", wait=True)
            await plugin.drain()
            await i.stop()
            return len(broker.published)

        self.assertEqual(asyncio.run(go()), 2)

    def test_discard_marks_drops_buffered(self) -> None:
        p = OutboxPlugin(MemoryOutboxStore())
        p.buffer_marks = True
        p._buffer().append(Envelope.new(type="x"))
        self.assertEqual(p.discard_marks(), 1)
        self.assertEqual(p.flush_marks(), 0)


class TestSessionIsolation(unittest.TestCase):
    """Review fixes: one plugin shared by concurrent persisted() blocks."""

    def test_interleaved_apersisted_blocks_keep_their_own_rows(self) -> None:
        from src.xstate_statemachine.persistence import apersisted

        sink = MemoryOutboxStore()
        plugin = OutboxPlugin(sink)

        async def block(key: str, mine: Any, other: Any, fail: bool) -> None:
            async with apersisted(
                MemoryStore(), key, _machine(), plugins=[plugin]
            ) as i:
                await i.send("PAY", wait=True)
                mine.set()
                await other.wait()  # both buffered before either exits
                if fail:
                    raise ValueError("b fails")

        async def go() -> None:
            # 📝 3.9: an asyncio.Event binds to the loop at construction.
            gate_a, gate_b = asyncio.Event(), asyncio.Event()
            a = asyncio.ensure_future(block("a", gate_a, gate_b, False))
            b = asyncio.ensure_future(block("b", gate_b, gate_a, True))
            await a
            with self.assertRaises(ValueError):
                await b

        asyncio.run(go())
        subjects = {r.envelope.subject for r in sink.pending()}
        self.assertEqual(subjects, {"a"})  # b's rows were discarded
        self.assertEqual(len(sink), 2)

    def test_buffering_is_switched_off_after_the_block(self) -> None:
        sink = MemoryOutboxStore()
        plugin = OutboxPlugin(sink)
        with persisted(MemoryStore(), "k", _machine(), plugins=[plugin]):
            pass
        self.assertFalse(plugin.buffer_marks)
        i = SyncInterpreter(_machine()).use(plugin).start()
        i.send("PAY")  # outside persisted(): written at once
        self.assertEqual(len(sink), 2)
        i.stop()

    def test_broker_publish_waits_for_the_commit(self) -> None:
        broker = SyncFakeBrokerAdapter()
        plugin = OutboxPlugin(broker)
        with self.assertRaises(RuntimeError):
            with persisted(
                MemoryStore(), "k", _machine(), plugins=[plugin]
            ) as i:
                i.send("PAY")
                raise RuntimeError("rolled back")
        self.assertEqual(broker.published, [])
        with persisted(MemoryStore(), "k", _machine(), plugins=[plugin]) as i:
            i.send("PAY")
            self.assertEqual(broker.published, [])  # not before the exit
        self.assertEqual(len(broker.published), 2)

    def test_a_store_with_a_publish_method_is_still_a_store(self) -> None:
        class Both(MemoryOutboxStore):
            def publish(self, topic: str, env: Envelope) -> None:
                raise AssertionError("must not be used")

        sink = Both()
        i = SyncInterpreter(_machine()).use(OutboxPlugin(sink)).start()
        i.send("PAY")
        self.assertEqual(len(sink), 2)
        i.stop()

    def test_a_failing_outbox_flush_does_not_skip_the_inbox_mark(
        self,
    ) -> None:
        from src.xstate_statemachine.persistence import (
            IdempotencyPlugin,
            MemoryInbox,
        )

        class Broken(MemoryOutboxStore):
            def add(self, topic: str, env: Envelope) -> None:
                raise ConnectionError("outbox down")

        inbox = MemoryInbox()
        idem = IdempotencyPlugin(inbox, principal=lambda e: "p")
        with self.assertRaises(ConnectionError):
            with persisted(
                MemoryStore(),
                "k",
                _machine(),
                plugins=[OutboxPlugin(Broken()), idem],
            ) as i:
                i.send("PAY", idempotency_key="e1")
        self.assertIsNotNone(inbox.get("p/order/k", "e1").receipt_json)


class TestCausationViaDispatcher(unittest.TestCase):
    def test_causation_and_correlation_from_the_inbound_envelope(self) -> None:
        broker = FakeBrokerAdapter()
        disp = InboundDispatcher(
            MemoryStore(),
            lambda t: _machine(),
            plugins=[OutboxPlugin(broker, topic="out")],
        )
        cmd = Envelope.new(
            type="xsm.order.PAY", subject="o-1", correlationid="c-1"
        )

        async def go() -> None:
            await broker.deliver("in", cmd)
            await disp.run_once(broker, "in")

        asyncio.run(go())
        out = broker.published_on("out")
        self.assertEqual(len(out), 2)
        for e in out:
            self.assertEqual(
                (e.causationid, e.correlationid, e.subject),
                (cmd.id, "c-1", "o-1"),
            )


if __name__ == "__main__":
    unittest.main()
