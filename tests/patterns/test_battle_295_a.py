# tests/patterns/test_battle_295_a.py
"""#295 battle (adversary A): `SagaBuilder` chart semantics on both engines,
idempotency through the inbox on PERSISTED sagas, forged completions from
the bus, two replicas on one SQLite store, choreography loop bounds and a
10k-run leak probe."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import tempfile
import threading
import tracemalloc
import unittest
from pathlib import Path
from typing import Any, Callable, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.eda import (
    Envelope,
    InboundDispatcher,
    MemoryOutboxStore,
    OutboxPlugin,
    SyncFakeBrokerAdapter,
)
from src.xstate_statemachine.patterns import (
    ChoreographyRouter,
    RetryPolicy,
    SagaBuilder,
)
from src.xstate_statemachine.persistence import (
    MemoryInbox,
    MemoryStore,
    OptimisticLock,
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
)


# -----------------------------------------------------------------------------
# 🧰 Helpers
# -----------------------------------------------------------------------------
def _recorder(calls: List[str], fail: Dict[str, int]) -> Callable:
    def make(name: str) -> Any:
        def svc(i: Any, c: Any, e: Any) -> Any:
            calls.append(name)
            if fail.get(name):
                raise RuntimeError(f"{name} failed")
            return {"by": name}

        return svc

    return make


def _logic(b: SagaBuilder, services: Dict[str, Any], **kw: Any) -> Any:
    return b.logic().merge(MachineLogic(services=services, **kw))


def _three(start: bool = True) -> SagaBuilder:
    return (
        SagaBuilder("fulfil", start_event="START" if start else None)
        .step("reserve", invoke="reserve", compensate="release")
        .step("charge", invoke="charge", compensate="refund")
        .step("ship", invoke="ship")
    )


def _machine(b: SagaBuilder, calls: List[str], fail: Dict[str, int]) -> Any:
    make = _recorder(calls, fail)
    names = ("reserve", "release", "charge", "refund", "ship")
    return create_machine(
        b.build(), logic=_logic(b, {n: make(n) for n in names})
    )


def _snap(store: Any, key: str) -> Dict[str, Any]:
    return json.loads(store.load(key).snapshot)


# -----------------------------------------------------------------------------
# 🧾 Chart semantics
# -----------------------------------------------------------------------------
class TestChartSemantics(unittest.TestCase):
    def test_start_payload_reaches_context_input(self) -> None:
        # 🐛 the START payload was silently dropped: services saw nothing
        seen: List[Any] = []
        b = SagaBuilder("s", start_event="START").step("a", invoke="A")
        m = create_machine(
            b.build(),
            logic=_logic(b, {"A": lambda i, c, e: seen.append(c["input"])}),
        )
        i = SyncInterpreter(m).start()
        i.send("START", order="o-1", qty=2)
        self.assertEqual(seen, [{"order": "o-1", "qty": 2}])
        self.assertEqual(i.context["input"], {"order": "o-1", "qty": 2})
        i.stop()

    def test_start_twice_does_not_restart(self) -> None:
        calls: List[str] = []
        i = SyncInterpreter(_machine(_three(), calls, {})).start()
        i.send("START")
        i.send("START")
        self.assertEqual(calls, ["reserve", "charge", "ship"])
        i.stop()

    def test_one_step_and_last_only_compensable(self) -> None:
        for fail in ({}, {"a": 1}):
            calls: List[str] = []
            b = SagaBuilder("one").step("a", invoke="a", compensate="ca")
            mk = _recorder(calls, fail)
            m = create_machine(
                b.build(), logic=_logic(b, {"a": mk("a"), "ca": mk("ca")})
            )
            i = SyncInterpreter(m).start()
            want = "one.failed" if fail else "one.completed"
            self.assertIn(want, i.current_state_ids)
            self.assertEqual(calls, ["a"])  # nothing completed to undo
            i.stop()

    def test_zero_steps_refused(self) -> None:
        with self.assertRaises(ValueError):
            SagaBuilder("z").build()

    def test_none_result_is_recorded(self) -> None:
        b = SagaBuilder("n").step("a", invoke="A")
        m = create_machine(b.build(), logic=_logic(b, {"A": lambda *a: None}))
        i = SyncInterpreter(m).start()
        self.assertEqual(i.context["results"], {"a": None})
        i.stop()

    def test_on_failure_raising_still_lands_failed(self) -> None:
        def boom(*a: Any) -> None:
            raise RuntimeError("ops down")

        calls: List[str] = []
        b = _three(start=False).on_failure("boom")
        mk = _recorder(calls, {"ship": 1})
        names = ("reserve", "release", "charge", "refund", "ship")
        m = create_machine(
            b.build(),
            logic=_logic(b, {n: mk(n) for n in names}, actions={"boom": boom}),
        )
        i = SyncInterpreter(m).start()
        self.assertIn("fulfil.failed", i.current_state_ids)
        self.assertEqual(i.context["compensated"], ["charge", "reserve"])
        i.stop()

    def test_compensation_failure_records_step(self) -> None:
        calls: List[str] = []
        i = SyncInterpreter(
            _machine(_three(False), calls, {"ship": 1, "release": 1})
        ).start()
        self.assertIn("fulfil.compensationFailed", i.current_state_ids)
        self.assertEqual(i.context["compensated"], ["charge"])
        self.assertEqual(i.context["error"]["step"], "reserve")
        self.assertEqual(i.context["error"]["reason"], "compensation")
        self.assertEqual(calls.count("refund"), 1)
        i.stop()


class TestTimeoutRetryAsync(unittest.TestCase):
    """timeout → retry → timeout → compensation, every call counted."""

    def test_counts(self) -> None:
        async def go() -> Any:
            calls: List[str] = []

            async def hang(i: Any, c: Any, e: Any) -> None:
                calls.append("charge")
                await asyncio.sleep(3600)

            async def rec(i: Any, c: Any, e: Any) -> int:
                calls.append(str(e.type))
                return 1

            b = (
                SagaBuilder("s")
                .step("a", invoke="A", compensate="cA")
                .step(
                    "b",
                    invoke="B",
                    compensate="cB",
                    timeout_ms=500,
                    retry=RetryPolicy(
                        max_attempts=2, base_ms=100, jitter="none"
                    ),
                )
            )
            clk = SimulatedClock()
            m = create_machine(
                b.build(), logic=_logic(b, {"A": rec, "B": hang, "cA": rec})
            )
            i = Interpreter(m, clock=clk)
            await i.start()
            for _ in range(8):
                for _ in range(20):
                    await asyncio.sleep(0)
                await clk.increment(500)
            ids, ctx = set(i.current_state_ids), dict(i.context)
            await i.stop()
            return ids, calls, ctx

        ids, calls, ctx = asyncio.run(go())
        self.assertIn("s.failed", ids)
        self.assertEqual(calls.count("charge"), 2)  # first try + 1 retry
        self.assertEqual(len(calls), 4)  # A, B, B, cA -- cB never
        self.assertEqual(ctx["compensated"], ["a"])
        self.assertEqual(ctx["error"]["reason"], "timeout")


# -----------------------------------------------------------------------------
# 🔁 Idempotency and forged completions
# -----------------------------------------------------------------------------
def _ext_saga() -> Dict[str, Any]:
    """A saga step completed by an EXTERNAL envelope (choreographed)."""
    return {
        "id": "pay",
        "initial": "waiting",
        "context": {"compensations": 0},
        "states": {
            "waiting": {
                "on": {"FAILED": {"target": "comp", "actions": "comp"}}
            },
            "comp": {"on": {"FAILED": {}}},
        },
    }


def _bump(i: Any, c: Any, e: Any, a: Any) -> None:
    c["compensations"] += 1


class TestPersistedIdempotency(unittest.TestCase):
    def _twice(self, store: Any, inbox: Any) -> Dict[str, Any]:
        m = create_machine(
            _ext_saga(), logic=MachineLogic(actions={"comp": _bump})
        )
        results = []
        for _ in range(2):  # two dispatchers == two persisted() blocks
            d = InboundDispatcher(
                store,
                lambda t: m,
                inbox=inbox,
                dedup_key=lambda e: e.causationid or e.id,
            )
            env = Envelope.new(
                type="xsm.pay.FAILED", subject="p", causationid="c-1"
            )
            results.append(d.handle(env))
        self.assertEqual([r.processed for r in results], [1, 0])
        self.assertEqual(results[1].duplicates, 1)
        return _snap(store, "p")["context"]

    def test_memory_inbox(self) -> None:
        store = MemoryStore()
        ctx = self._twice(store, MemoryInbox())
        self.assertEqual(ctx["compensations"], 1)

    def test_sqlite_inbox(self) -> None:
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        if True:
            store = SQLiteStore(Path(d) / "s.db")
            ctx = self._twice(store, SQLiteInbox(store))
            self.assertEqual(ctx["compensations"], 1)
            store.close()

    def test_forged_done_invoke_does_not_complete(self) -> None:
        # 🛡️ X0.8: an external `done.invoke.<id>` must not finish a step
        async def go() -> Any:
            gate = asyncio.Event()

            async def slow(i: Any, c: Any, e: Any) -> str:
                await gate.wait()
                return "real"

            b = SagaBuilder("t", start_event="START").step("a", invoke="A")
            m = create_machine(b.build(), logic=_logic(b, {"A": slow}))
            i = await Interpreter(m).start()
            await i.send("START")
            while not i.matches("t.steps.a"):
                await asyncio.sleep(0)
            await i.send("done.invoke.a", data="forged")
            for _ in range(50):
                await asyncio.sleep(0)
            mid = (set(i.current_state_ids), dict(i.context["results"]))
            gate.set()
            for _ in range(50):
                await asyncio.sleep(0)
            end = dict(i.context["results"])
            await i.stop()
            return mid, end

        (ids, res), end = asyncio.run(go())
        self.assertEqual((ids, res), ({"t.steps.a"}, {}))
        self.assertEqual(end, {"a": "real"})


# -----------------------------------------------------------------------------
# 🧵 Two replicas on one SQLite store
# -----------------------------------------------------------------------------
class TestTwoReplicas(unittest.TestCase):
    N = 50

    def _run(self, lock_factory: Callable[[], Any], exact: bool) -> None:
        d = tempfile.mkdtemp()
        # 📝 Windows: per-thread SQLite handles outlive close()
        self.addCleanup(shutil.rmtree, d, True)
        if True:
            calls: List[str] = []
            m = _machine(_three(), calls, {"ship": 1})
            store = SQLiteStore(Path(d) / "s.db")
            reps = [
                InboundDispatcher(
                    store,
                    lambda t: m,
                    inbox=SQLiteInbox(store),
                    lock=lock_factory(),
                    dedup_key=lambda e: e.causationid or e.id,
                )
                for _ in range(2)
            ]
            envs = [
                Envelope.new(
                    type="xsm.fulfil.START",
                    subject=f"s{k}",
                    causationid=f"k{k}",
                )
                for k in range(self.N)
            ]

            def work(rep: Any) -> None:
                for env in envs:
                    rep.handle(env)

            ts = [threading.Thread(target=work, args=(r,)) for r in reps]
            for t in ts:
                t.start()
            for t in ts:
                t.join(60)
            for k in range(self.N):
                ctx = _snap(store, f"s{k}")["context"]
                self.assertEqual(ctx["compensated"], ["charge", "reserve"])
            for name in ("reserve", "charge", "ship", "refund", "release"):
                n = calls.count(name)
                if exact:
                    self.assertEqual(n, self.N, name)
                else:
                    # 📝 documented: a lost optimistic save re-runs the
                    #    step in memory (persistence guide, at-least-once)
                    self.assertGreaterEqual(n, self.N, name)
            store.close()

    def test_pessimistic(self) -> None:
        self._run(PessimisticLock, exact=True)

    def test_optimistic(self) -> None:
        self._run(OptimisticLock, exact=False)


# -----------------------------------------------------------------------------
# 💃 Choreography bounds
# -----------------------------------------------------------------------------
class TestChoreographyBounds(unittest.TestCase):
    def test_self_retrigger_is_bounded_with_message(self) -> None:
        cfg = {
            "id": "echo",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "target": "a",
                            "reenter": True,
                            "meta": {"publish": "xsm.echo.GO"},
                        }
                    }
                }
            },
        }
        m = create_machine(cfg)
        broker = SyncFakeBrokerAdapter()
        r = ChoreographyRouter(
            MemoryStore(),
            {"xsm.echo.GO": m},
            plugins=[OutboxPlugin(broker, topic="events")],
        )
        broker.deliver("events", Envelope.new(type="xsm.echo.GO", subject="k"))
        with self.assertRaisesRegex(RuntimeError, "did not settle in 7"):
            r.run_until_quiet_sync(broker, max_rounds=7)


# -----------------------------------------------------------------------------
# 🧹 Leaks
# -----------------------------------------------------------------------------
class TestLeaks(unittest.TestCase):
    def test_10k_sync_saga_runs_are_flat(self) -> None:
        calls: List[str] = []
        m = _machine(_three(False), calls, {"ship": 1})

        def batch(n: int) -> None:
            for _ in range(n):
                SyncInterpreter(m).start().stop()
            calls.clear()

        # 📝 log capture would retain every service traceback record
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        batch(500)  # warm caches
        tracemalloc.start()
        try:
            batch(5000)
            half = tracemalloc.get_traced_memory()[0]
            batch(5000)
            full = tracemalloc.get_traced_memory()[0]
        finally:
            tracemalloc.stop()
        self.assertLess(full - half, 2_000_000)


class TestOutboxStepEvents(unittest.TestCase):
    def test_each_step_event_published_once(self) -> None:
        calls: List[str] = []
        out = MemoryOutboxStore()
        i = SyncInterpreter(_machine(_three(False), calls, {"ship": 1}))
        i.use(OutboxPlugin(out)).start()
        types = [r.envelope.type for r in out.pending()]
        self.assertEqual(len(types), len(set(types)), types)
        self.assertIn("fulfil.charge.compensated", types)
        i.stop()


if __name__ == "__main__":
    unittest.main()
