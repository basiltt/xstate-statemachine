# tests/eda/test_review_fixes.py
"""0.12.0 review fixes for `eda` and `inspect` (one test per finding)."""

from __future__ import annotations

import asyncio
import os
import queue
import tempfile
import threading
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.eda import (
    BrokerDeadLetterSink,
    Envelope,
    FakeBrokerAdapter,
    InboundDispatcher,
    MemoryDeadLetterStore,
    MemoryOutboxStore,
    OutboxRelay,
    ReplayRefusedError,
    SQLiteOutboxStore,
    replay_dead_letter,
)
from src.xstate_statemachine.eda.envelope import EnvelopeCorruptError
from src.xstate_statemachine.exceptions import StoreError
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryStore,
    SQLiteStore,
)

COUNTER = {
    "id": "counter",
    "initial": "on",
    "context": {"seen": []},
    "states": {"on": {"on": {"ADD": {"actions": "record"}}}},
}


def _counter() -> Any:
    def record(i: Any, c: Dict[str, Any], e: Any, a: Any) -> None:
        c["seen"] = list(c["seen"]) + [1]

    return create_machine(
        COUNTER, logic=MachineLogic(actions={"record": record})
    )


class TestEda01ReplayRefusesRedacted(unittest.TestCase):
    def test_masked_record_is_inspect_only_unless_forced(self) -> None:
        dlq = MemoryDeadLetterStore()
        d = InboundDispatcher(
            MemoryStore(),
            lambda t: None,
            max_attempts=1,
            dead_letters=dlq,
        )
        env = Envelope.new(
            type="xsm.counter.ADD",
            subject="c-1",
            data={"email": "a@b.c", "n": 1},
        )
        d.handle(env, topic="in")
        rec = dlq.list()[0]
        self.assertEqual(rec.envelope["data"]["email"], "***")
        live = InboundDispatcher(
            MemoryStore(),
            {"xsm.counter.ADD": _counter()},
            dead_letters=dlq,
            inbox=MemoryInbox(),
        )
        with self.assertRaises(ReplayRefusedError) as cm:
            replay_dead_letter(
                dlq, rec.id, live, reason="fixed", dry_run=False
            )
        self.assertIn("redacted", str(cm.exception))
        self.assertIsNone(dlq.get(rec.id).resolved_at)
        res = replay_dead_letter(
            dlq, rec.id, live, reason="fixed", dry_run=False, force=True
        )
        self.assertEqual(res.outcome, "processed")


class TestEda02SseCloseNeverBlocks(unittest.TestCase):
    def test_close_with_a_full_client_queue_returns(self) -> None:
        from src.xstate_statemachine.inspect import SseSink

        sink = SseSink(max_queue=1).start()
        q: "queue.Queue[Any]" = queue.Queue(maxsize=1)
        q.put("frame")
        with sink._lock:
            sink._clients.append(q)
        t = threading.Thread(target=sink.close, daemon=True)
        t.start()
        t.join(10)
        self.assertFalse(t.is_alive(), "close() hung on a stalled client")
        self.assertIsNone(q.get_nowait())


def _poisoned_outbox() -> Any:
    path = os.path.join(tempfile.mkdtemp(), "o.db")
    out = SQLiteOutboxStore(SQLiteStore(path))
    out.add("t", Envelope.new(type="a", subject="s"))
    out.add("t", Envelope.new(type="b", subject="s"))
    conn = out._conn()
    conn.execute(
        "UPDATE xsm_outbox SET envelope = ? WHERE seq = 1", ("{not json",)
    )
    conn.commit()
    return out


class TestEda03CorruptOutboxRow(unittest.TestCase):
    def test_bad_row_does_not_block_the_rows_behind_it(self) -> None:
        out = _poisoned_outbox()
        broker = FakeBrokerAdapter()
        relay = OutboxRelay(out, broker, owner="r1")
        self.assertEqual(asyncio.run(relay.relay_once()), 1)
        self.assertEqual([e.type for e in broker.published_on("t")], ["b"])
        self.assertEqual(asyncio.run(relay.relay_once()), 0)

    def test_pending_skips_an_undecodable_row(self) -> None:
        out = _poisoned_outbox()
        self.assertEqual([r.envelope.type for r in out.pending()], ["b"])


class _FutureBroker(FakeBrokerAdapter):
    """publish returns an asyncio.Future instead of a coroutine."""

    def __init__(self) -> None:
        super().__init__()
        self.got: List[str] = []

    def publish(self, topic: str, envelope: Envelope) -> Any:  # type: ignore
        fut = asyncio.get_event_loop().create_future()

        async def finish() -> None:
            self.got.append(envelope.type)
            fut.set_result(None)

        asyncio.ensure_future(finish())
        return fut


class TestEda04AwaitableResults(unittest.TestCase):
    def test_relay_awaits_a_future_before_marking_sent(self) -> None:
        async def go() -> Any:
            store = MemoryOutboxStore()
            store.add("t", Envelope.new(type="x", subject="s"))
            broker = _FutureBroker()
            n = await OutboxRelay(store, broker).relay_once()
            return n, broker.got

        self.assertEqual(asyncio.run(go()), (1, ["x"]))

    def test_settle_awaitable_runs_a_future(self) -> None:
        from src.xstate_statemachine.eda.broker import settle_awaitable

        async def go() -> int:
            fut = asyncio.get_running_loop().create_future()
            tasks: List[Any] = []
            settle_awaitable(fut, tasks=tasks)
            fut.set_result(None)
            await asyncio.gather(*tasks)
            return len(tasks)

        self.assertEqual(asyncio.run(go()), 1)


class _DownStore(MemoryStore):
    def save(self, *a: Any, **k: Any) -> Any:
        raise StoreError("store down")


class TestEda05StoreOutageNotPoison(unittest.TestCase):
    def test_outage_inside_the_run_is_never_dead_lettered(self) -> None:
        dlq = MemoryDeadLetterStore()
        d = InboundDispatcher(
            _DownStore(),
            {"xsm.counter.ADD": _counter()},
            max_attempts=2,
            dead_letters=dlq,
        )
        env = Envelope.new(type="xsm.counter.ADD", subject="c-1")
        for _ in range(5):
            res = d.handle(env, topic="in")
            self.assertEqual(res.outcomes[-1][1], "retry")
        self.assertEqual(len(dlq), 0)


class TestEda15NoDoubleBump(unittest.TestCase):
    def test_dlq_down_counts_the_attempt_once(self) -> None:
        class Down(MemoryDeadLetterStore):
            def put(self, record: Any) -> None:
                raise RuntimeError("dlq down")

        def boom(i: Any, c: Any, e: Any, a: Any) -> None:
            raise RuntimeError("boom")

        m = create_machine(
            COUNTER, logic=MachineLogic(actions={"record": boom})
        )
        d = InboundDispatcher(
            MemoryStore(),
            {"xsm.counter.ADD": m},
            max_attempts=2,
            dead_letters=Down(),
        )
        env = Envelope.new(type="xsm.counter.ADD", subject="c-1")
        d.handle(env, topic="in")
        d.handle(env, topic="in")  # reaches the cap, DLQ down -> requeue
        self.assertEqual(d.attempts_of(env), 2)


class TestEda06NanIsRefused(unittest.TestCase):
    def test_to_json_refuses_nan(self) -> None:
        env = Envelope.new(type="x", data={"v": float("nan")})
        with self.assertRaises(EnvelopeCorruptError):
            env.to_json()


class TestEda07Ipv6Bind(unittest.TestCase):
    def test_loopback_v6_binds(self) -> None:
        from src.xstate_statemachine.inspect import SseSink

        try:
            sink = SseSink("::1")
        except OSError as exc:  # host without IPv6
            self.skipTest(f"no IPv6 loopback: {exc}")
        try:
            self.assertIn("[::1]", sink.url)
        finally:
            sink.close()


class TestEda10SendEncodesFirst(unittest.TestCase):
    def test_unencodable_message_leaves_no_trace(self) -> None:
        from src.xstate_statemachine.inspect import SseSink

        sink = SseSink()
        try:
            circular: Dict[str, Any] = {}
            circular["self"] = circular
            with self.assertRaises(ValueError):
                sink.send(circular)
            self.assertEqual(sink.messages, [])
            self.assertEqual(sink.sent, 0)
        finally:
            sink.close()


_PUBLISH_CHART = {
    "id": "m",
    "initial": "a",
    "context": {"total": 1},
    "states": {
        "a": {
            "on": {
                "GO": {
                    "target": "b",
                    "meta": {"publish": {"type": "x.y", "data": ["totl"]}},
                }
            }
        },
        "b": {},
    },
}


class TestEda12PublishValidation(unittest.TestCase):
    def test_bad_meta_publish_is_reported_at_start(self) -> None:
        from src.xstate_statemachine.eda import OutboxPlugin

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": {"target": "b", "meta": {"publish": 5}}}},
                "b": {},
            },
        }

        class Interp:
            machine = create_machine(cfg)

        with self.assertRaises(ValueError):
            OutboxPlugin(MemoryOutboxStore()).on_interpreter_start(Interp())

    def test_missing_field_is_logged(self) -> None:
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.eda import OutboxPlugin

        store = MemoryOutboxStore()
        i = SyncInterpreter(create_machine(_PUBLISH_CHART))
        i.use(OutboxPlugin(store))
        with self.assertLogs(
            "src.xstate_statemachine.eda.outbox", level="WARNING"
        ) as cm:
            i.start()
            i.send("GO")
        self.assertTrue(any("totl" in m for m in cm.output))
        i.stop()


class TestEda14GatherAll(unittest.TestCase):
    def test_every_task_is_awaited_before_the_first_error_raises(self) -> None:
        async def go() -> List[int]:
            done: List[int] = []

            async def bad() -> None:
                raise RuntimeError("first")

            async def good() -> None:
                await asyncio.sleep(0)
                done.append(1)

            sink = BrokerDeadLetterSink(FakeBrokerAdapter(), "t")
            sink._tasks = [
                asyncio.ensure_future(bad()),
                asyncio.ensure_future(good()),
            ]
            with self.assertRaises(RuntimeError):
                await sink.flush()
            return done

        self.assertEqual(asyncio.run(go()), [1])


class TestEda09ContextNotADict(unittest.TestCase):
    def test_non_dict_context_is_empty(self) -> None:
        from src.xstate_statemachine.inspect import (
            InspectorPlugin,
            MemorySink,
        )

        class Interp:
            context = object()

        p = InspectorPlugin(MemorySink(), context_allowlist=["a"])
        self.assertEqual(p._context(Interp()), {})


class TestEda19ReadJsonlDeepNesting(unittest.TestCase):
    def test_deeply_nested_line_is_a_value_error(self) -> None:
        from src.xstate_statemachine.inspect import read_jsonl

        path = os.path.join(tempfile.mkdtemp(), "r.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("[" * 100000 + "]" * 100000 + "\n")
        with self.assertRaises(ValueError):
            list(read_jsonl(path))


class TestEda13BatchValidated(unittest.TestCase):
    def test_non_positive_batch_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            OutboxRelay(MemoryOutboxStore(), FakeBrokerAdapter(), batch=0)


if __name__ == "__main__":
    unittest.main()
