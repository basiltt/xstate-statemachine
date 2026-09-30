# tests/eda/test_dead_letter.py
"""#293: `DeadLetterStore` protocol, `SQLiteDeadLetterStore` (redacted,
0600 file, audit), `BrokerDeadLetterSink` → ``<topic>.dlq``, the extended
`DeadLetterPlugin`, and `replay_dead_letter` (reuses the id, refuses a
changed machine without force, marks resolved, audits)."""

from __future__ import annotations

import asyncio
import os
import stat
import tempfile
import time
import unittest
from typing import Any

from src.xstate_statemachine import (
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.eda import (
    BrokerDeadLetterSink,
    DeadLetter,
    DeadLetterPlugin,
    DeadLetterStore,
    Envelope,
    FakeBrokerAdapter,
    InboundDispatcher,
    MemoryDeadLetterStore,
    ReplayRefusedError,
    SQLiteDeadLetterStore,
    SyncFakeBrokerAdapter,
    dlq_topic,
    replay_dead_letter,
)
from src.xstate_statemachine.persistence import MemoryInbox, MemoryStore

CFG = {
    "id": "counter",
    "version": "1",
    "initial": "on",
    "context": {"n": 0},
    "actionErrorPolicy": "fail",
    "states": {"on": {"on": {"ADD": {"actions": "add"}}}},
}


def _machine(broken: bool = False, version: str = "1") -> Any:
    def add(i: Any, c: Any, e: Any, a: Any) -> None:
        if broken:
            raise RuntimeError("bug")
        c["n"] += 1

    return create_machine(
        dict(CFG, version=version), logic=MachineLogic(actions={"add": add})
    )


def _record(**kw: Any) -> DeadLetter:
    base = dict(
        machine_id="m",
        state_id="",
        event={"type": "E", "payload": {"password": "p"}},
        attempts=1,
        errors=[],
        snapshot={"context": {"api_key": "k"}},
        taken_at=time.time(),
    )
    base.update(kw)
    return DeadLetter(**base)


class _StoreContract:
    def make(self) -> Any:  # pragma: no cover - abstract
        raise NotImplementedError

    def test_put_get_list_resolve_delete_purge(self) -> None:
        s = self.make()
        self.assertIsInstance(s, DeadLetterStore)  # type: ignore[attr-defined]
        a = _record(id="a", taken_at=100.0)
        b = _record(id="b", taken_at=200.0)
        s.put(a)
        s(b)  # callable as a sink
        s.put(a)  # upsert, not a duplicate
        self.assertEqual([r.id for r in s.list()], ["a", "b"])  # type: ignore[attr-defined]
        self.assertEqual(s.get("a").id, "a")  # type: ignore[attr-defined]
        self.assertIsNone(s.get("zz"))  # type: ignore[attr-defined]
        self.assertTrue(s.mark_resolved("a", 5.0))  # type: ignore[attr-defined]
        self.assertFalse(s.mark_resolved("zz", 5.0))  # type: ignore[attr-defined]
        self.assertEqual([r.id for r in s.list()], ["b"])  # type: ignore[attr-defined]
        self.assertEqual(len(s.list(include_resolved=True)), 2)  # type: ignore[attr-defined]
        self.assertEqual(s.get("a").resolved_at, 5.0)  # type: ignore[attr-defined]
        self.assertEqual(s.purge_older_than(150.0), 1)  # type: ignore[attr-defined]
        self.assertTrue(s.delete("b"))  # type: ignore[attr-defined]
        self.assertFalse(s.delete("b"))  # type: ignore[attr-defined]
        self.assertEqual(len(s), 0)  # type: ignore[attr-defined]


class TestMemoryStore(_StoreContract, unittest.TestCase):
    def make(self) -> Any:
        return MemoryDeadLetterStore()


class TestSQLiteStore(_StoreContract, unittest.TestCase):
    def make(self) -> Any:
        return SQLiteDeadLetterStore(
            os.path.join(tempfile.mkdtemp(), "dlq.db")
        )

    def test_redacted_before_write(self) -> None:
        s = self.make()
        s.put(_record(id="x", envelope={"data": {"token": "t"}}))
        r = s.get("x")
        self.assertEqual(r.event["payload"]["password"], "***")
        self.assertEqual(r.snapshot["context"]["api_key"], "***")
        self.assertEqual(r.envelope["data"]["token"], "***")
        s.close()

    @unittest.skipUnless(os.name == "posix", "POSIX file modes")
    def test_file_is_0600(self) -> None:  # pragma: no cover - posix only
        path = os.path.join(tempfile.mkdtemp(), "dlq.db")
        SQLiteDeadLetterStore(path).close()
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_audit_log(self) -> None:
        s = self.make()
        s.audit("purge", None, "cleanup", {"secret": "x"}, actor="ops")
        [row] = s.audit_log()
        self.assertEqual(
            (row["action"], row["actor"], row["reason"]),
            ("purge", "ops", "cleanup"),
        )
        self.assertEqual(row["detail"]["secret"], "***")
        s.audit("purge", None, "again")
        self.assertTrue(s.audit_log()[1]["actor"])
        s.close()

    def test_shares_a_sqlite_store(self) -> None:
        from src.xstate_statemachine.persistence import SQLiteStore

        st = SQLiteStore(os.path.join(tempfile.mkdtemp(), "x.db"))
        s = SQLiteDeadLetterStore(st)
        s.put(_record(id="q"))
        self.assertEqual(len(s), 1)
        s.close()  # does not close the shared store
        self.assertEqual(st.health()["ok"], True)
        st.close()


class TestBrokerSink(unittest.TestCase):
    def test_sync_broker(self) -> None:
        broker = SyncFakeBrokerAdapter()
        store = MemoryDeadLetterStore()
        sink = BrokerDeadLetterSink(broker, "orders", store=store)
        sink(_record(id="r1", envelope={"subject": "o-1"}))
        [env] = broker.published_on("orders.dlq")
        self.assertEqual(dlq_topic("orders"), "orders.dlq")
        self.assertEqual((env.type, env.subject), ("xsm.deadletter", "o-1"))
        self.assertEqual(env.data["id"], "r1")
        self.assertEqual(env.data["event"]["payload"]["password"], "***")
        self.assertEqual(len(store), 1)

    def test_async_broker_inside_a_loop(self) -> None:
        async def go() -> int:
            broker = FakeBrokerAdapter()
            sink = BrokerDeadLetterSink(broker, "t")
            sink.put(_record())
            await sink.flush()
            return len(broker.published_on("t.dlq"))

        self.assertEqual(asyncio.run(go()), 1)

    def test_plugin_to_dlq_topic(self) -> None:
        """#293 criterion: `DeadLetterPlugin` → `.dlq` topic."""
        cfg = {
            "id": "job",
            "initial": "run",
            "states": {
                "run": {
                    "invoke": {"src": "work", "onError": "dead"},
                },
                "dead": {"tags": ["dead-letter"]},
            },
        }

        def work(i: Any, c: Any, e: Any) -> None:
            raise ConnectionError("down")

        m = create_machine(cfg, logic=MachineLogic(services={"work": work}))
        broker = SyncFakeBrokerAdapter()
        store = MemoryDeadLetterStore()
        i = (
            SyncInterpreter(m, clock=SimulatedClock())
            .use(DeadLetterPlugin(BrokerDeadLetterSink(broker, "jobs")))
            .use(DeadLetterPlugin(store))  # an object with put() works too
            .start()
        )
        [env] = broker.published_on("jobs.dlq")
        self.assertEqual(env.data["state_id"], "job.dead")
        self.assertTrue(env.data["machine_hash"])
        self.assertEqual(len(store), 1)
        i.stop()


class TestReplay(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryStore()
        self.dlq = SQLiteDeadLetterStore(
            os.path.join(tempfile.mkdtemp(), "d.db")
        )
        self.broken = InboundDispatcher(
            self.store,
            lambda t: _machine(broken=True),
            max_attempts=1,
            dead_letters=self.dlq,
            inbox=MemoryInbox(),
        )
        self.env = Envelope.new(type="xsm.counter.ADD", subject="c-1")
        self.broken.handle(self.env, topic="in")
        [self.rec] = self.dlq.list()

    def tearDown(self) -> None:
        self.dlq.close()

    def _fixed(self, version: str = "1", **kw: Any) -> InboundDispatcher:
        return InboundDispatcher(
            self.store,
            lambda t: _machine(version=version),
            dead_letters=self.dlq,
            **kw,
        )

    def test_dry_run_is_the_default_and_changes_nothing(self) -> None:
        res = replay_dead_letter(
            self.dlq, self.rec.id, self._fixed(), reason="bug fixed"
        )
        self.assertEqual((res.dry_run, res.outcome), (True, "would_replay"))
        self.assertIsNone(self.store.load("c-1"))
        self.assertEqual(self.dlq.audit_log(), [])

    def test_replay_reuses_the_id_marks_resolved_and_audits(self) -> None:
        inbox = MemoryInbox()
        d = self._fixed(inbox=inbox)
        res = replay_dead_letter(
            self.dlq, self.rec.id, d, reason="bug fixed", dry_run=False
        )
        self.assertEqual(res.outcome, "processed")
        self.assertEqual(self.rec.id, self.env.id)
        self.assertIsNotNone(self.dlq.get(self.rec.id).resolved_at)
        [audit] = self.dlq.audit_log()
        self.assertEqual(
            (audit["action"], audit["reason"]), ("replay", "bug fixed")
        )
        # a double replay is deduplicated by the inbox (same envelope id)
        again = replay_dead_letter(
            self.dlq, self.rec.id, d, reason="oops", dry_run=False
        )
        self.assertEqual(again.outcome, "duplicate")
        import json

        self.assertEqual(
            json.loads(self.store.load("c-1").snapshot)["context"]["n"], 1
        )

    def test_refuses_a_changed_machine_without_force(self) -> None:
        d = self._fixed(version="2")
        with self.assertRaises(ReplayRefusedError) as cm:
            replay_dead_letter(
                self.dlq, self.rec.id, d, reason="r", dry_run=False
            )
        self.assertIn("version", str(cm.exception))
        res = replay_dead_letter(
            self.dlq, self.rec.id, d, reason="r", dry_run=False, force=True
        )
        self.assertEqual(res.outcome, "processed")
        self.assertTrue(res.warnings)
        self.assertTrue(self.dlq.audit_log()[0]["detail"]["forced"])

    def test_refusals(self) -> None:
        d = self._fixed()
        with self.assertRaises(ReplayRefusedError):
            replay_dead_letter(self.dlq, self.rec.id, d, reason=" ")
        with self.assertRaises(ReplayRefusedError):
            replay_dead_letter(self.dlq, "missing", d, reason="r")
        self.dlq.put(_record(id="chart"))
        with self.assertRaises(ReplayRefusedError):
            replay_dead_letter(self.dlq, "chart", d, reason="r")
        other = InboundDispatcher(self.store, lambda t: None)
        with self.assertRaises(ReplayRefusedError):
            replay_dead_letter(self.dlq, self.rec.id, other, reason="r")


if __name__ == "__main__":
    unittest.main()
