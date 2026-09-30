# tests/patterns/test_saga.py
"""#295: `SagaBuilder` emits plain, strict-clean JSON; on `SimulatedClock`:
happy path with results in context; failure at step 2 compensates in
reverse exactly once; timeout at step 1 → retry → compensation; both
engines; idempotent completion via the inbox on ``causationid``."""

from __future__ import annotations

import asyncio
import json
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
    wait_for,
)
from src.xstate_statemachine.eda import (
    Envelope,
    InboundDispatcher,
    MemoryOutboxStore,
    OutboxPlugin,
    publish_specs,
)
from src.xstate_statemachine.patterns import (
    DeadLetterPlugin,
    DeadLetterStore,
    RetryPolicy,
    SagaBuilder,
)
from src.xstate_statemachine.persistence import MemoryInbox, MemoryStore


def _services(calls: List[str], fail: Dict[str, int]) -> Dict[str, Any]:
    """Recording services; ``fail[name] = k`` fails the first k calls
    (``-1`` = always, ``"hang"`` handled by `_hanging`)."""

    def make(name: str) -> Any:
        def svc(i: Any, c: Any, e: Any) -> str:
            calls.append(name)
            left = fail.get(name, 0)
            if left:
                if left > 0:
                    fail[name] = left - 1
                raise RuntimeError(f"{name} failed")
            return f"{name}-ok"

        return svc

    names = ("reserve", "release", "charge", "refund", "ship")
    return {n: make(n) for n in names}


def _builder(**step1: Any) -> SagaBuilder:
    return (
        SagaBuilder("fulfil")
        .step("reserve_stock", invoke="reserve", compensate="release", **step1)
        .step("charge_card", invoke="charge", compensate="refund")
        .step("ship", invoke="ship")
        .on_failure("notifyOps")
    )


def _machine(b: SagaBuilder, services: Dict[str, Any], ops: List[str]) -> Any:
    logic = b.logic().merge(
        MachineLogic(
            services=services,
            actions={"notifyOps": lambda i, c, e, a: ops.append("notified")},
        )
    )
    return create_machine(b.build(), logic=logic, strict_config=True)


class TestJSON(unittest.TestCase):
    def test_plain_json_a_human_could_write(self) -> None:
        cfg = _builder(timeout_ms=5000).build()
        json.dumps(cfg)  # plain data, no callables
        self.assertEqual(cfg["id"], "fulfil")
        steps = cfg["states"]["steps"]["states"]
        self.assertEqual(list(steps), ["reserve_stock", "charge_card", "ship"])
        self.assertEqual(steps["reserve_stock"]["invoke"]["src"], "reserve")
        self.assertIn("5000", steps["reserve_stock"]["after"])
        comp = cfg["states"]["compensating"]["states"]
        self.assertEqual(list(comp), ["charge_card", "reserve_stock"])
        # a failure at step k enters compensating.<k-1>
        self.assertEqual(
            steps["ship"]["invoke"]["onError"]["target"],
            "#fulfil.compensating.charge_card",
        )
        self.assertEqual(
            steps["reserve_stock"]["invoke"]["onError"]["target"],
            "#fulfil.failed",
        )
        self.assertEqual(cfg, _builder(timeout_ms=5000).build())

    def test_every_step_transition_is_published(self) -> None:
        b = _builder()
        m = _machine(b, _services([], {}), [])
        types = {s["type"] for s in publish_specs(m)}
        for step in ("reserve_stock", "charge_card", "ship"):
            self.assertIn(f"fulfil.{step}.completed", types)
            self.assertIn(f"fulfil.{step}.failed", types)
        self.assertIn("fulfil.charge_card.compensated", types)

    def test_builder_validation(self) -> None:
        with self.assertRaises(ValueError):
            SagaBuilder("bad name")
        with self.assertRaises(ValueError):
            SagaBuilder("s").step("x y", invoke="a")
        with self.assertRaises(ValueError):
            SagaBuilder("s").step("a", invoke="a").step("a", invoke="b")
        with self.assertRaises(ValueError):
            SagaBuilder("s").step("a", invoke="a", timeout_ms=0)
        with self.assertRaises(ValueError):
            SagaBuilder("s").build()
        self.assertEqual(len(_builder().steps), 3)

    def test_start_event_waits_in_idle(self) -> None:
        b = SagaBuilder("s", start_event="START").step("a", invoke="reserve")
        calls: List[str] = []
        m = _machine(b, _services(calls, {}), [])
        i = SyncInterpreter(m, clock=SimulatedClock()).start()
        self.assertEqual(calls, [])
        i.send("START")
        self.assertEqual(calls, ["reserve"])
        self.assertIn("s.completed", i.current_state_ids)
        i.stop()


class TestSyncRuns(unittest.TestCase):
    def _run(self, b: SagaBuilder, fail: Dict[str, int]) -> Any:
        calls: List[str] = []
        ops: List[str] = []
        clk = SimulatedClock()
        i = SyncInterpreter(
            _machine(b, _services(calls, fail), ops), clock=clk
        )
        i.start()
        for _ in range(10):
            clk.increment(10_000)
        return i, calls, ops

    def test_happy_path_results_in_context(self) -> None:
        i, calls, ops = self._run(_builder(), {})
        self.assertIn("fulfil.completed", i.current_state_ids)
        self.assertEqual(calls, ["reserve", "charge", "ship"])
        self.assertEqual(
            i.context["results"],
            {
                "reserve_stock": "reserve-ok",
                "charge_card": "charge-ok",
                "ship": "ship-ok",
            },
        )
        self.assertEqual((i.context["compensated"], ops), ([], []))
        i.stop()

    def test_failure_at_step_2_compensates_in_reverse_exactly_once(
        self,
    ) -> None:
        i, calls, ops = self._run(_builder(), {"charge": -1})
        self.assertIn("fulfil.failed", i.current_state_ids)
        self.assertEqual(calls, ["reserve", "charge", "release"])
        self.assertEqual(i.context["compensated"], ["reserve_stock"])
        self.assertEqual(i.context["error"]["step"], "charge_card")
        self.assertEqual(ops, ["notified"])
        i.stop()

    def test_failure_at_step_3_compensates_both_in_reverse(self) -> None:
        i, calls, _ = self._run(_builder(), {"ship": -1})
        self.assertEqual(
            calls, ["reserve", "charge", "ship", "refund", "release"]
        )
        self.assertEqual(
            i.context["compensated"], ["charge_card", "reserve_stock"]
        )
        self.assertEqual(calls.count("refund"), 1)
        self.assertEqual(calls.count("release"), 1)
        i.stop()

    def test_retry_then_success(self) -> None:
        b = _builder(
            retry=RetryPolicy(max_attempts=3, base_ms=100, jitter="none")
        )
        i, calls, _ = self._run(b, {"reserve": 2})
        self.assertIn("fulfil.completed", i.current_state_ids)
        self.assertEqual(calls.count("reserve"), 3)
        self.assertEqual(i.context["attempt_reserve_stock"], 0)  # reset
        i.stop()

    def test_failed_compensation_is_dead_lettered(self) -> None:
        b = _builder()
        store = DeadLetterStore()
        calls: List[str] = []
        m = _machine(b, _services(calls, {"ship": -1, "refund": -1}), [])
        i = SyncInterpreter(m, clock=SimulatedClock()).use(
            DeadLetterPlugin(store)
        )
        i.start()
        self.assertIn("fulfil.compensationFailed", i.current_state_ids)
        self.assertEqual(len(store), 1)
        i.stop()


def _hanging_services(calls: List[str], hang: str) -> Dict[str, Any]:
    """Async services; *hang* never returns on its first call."""
    base = _services(calls, {})
    seen = {"n": 0}

    def make(name: str) -> Any:
        async def svc(i: Any, c: Any, e: Any) -> Any:
            if name == hang:
                seen["n"] += 1
                if seen["n"] == 1:
                    calls.append(name)
                    await asyncio.sleep(3600)
            return base[name](i, c, e)

        return svc

    return {n: make(n) for n in base}


async def _until(cond: Any, timeout: float = 5.0) -> None:
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while not cond():
        if loop.time() > end:
            raise AssertionError("condition not reached")
        await asyncio.sleep(0.001)


class TestAsyncTimeout(unittest.TestCase):
    def test_timeout_at_step_1_retries_then_succeeds(self) -> None:
        async def go() -> Any:
            calls: List[str] = []
            b = _builder(
                timeout_ms=1000,
                retry=RetryPolicy(max_attempts=2, base_ms=100, jitter="none"),
            )
            m = _machine(b, _hanging_services(calls, "reserve"), [])
            clk = SimulatedClock()
            i = Interpreter(m, clock=clk)
            await i.start()
            await _until(lambda: calls == ["reserve"])  # step 1 hangs
            await clk.increment(1000)  # step-1 timeout fires
            await wait_for(
                i,
                lambda x: x.matches("fulfil.steps.reserve_stockRetrying"),
                timeout=5,
            )
            await clk.increment(100)  # retry delay
            await wait_for(
                i,
                lambda x: x.status != "running"
                or x.matches("fulfil.completed"),
                timeout=5,
            )
            ids, ctx = set(i.current_state_ids), dict(i.context)
            await i.stop()
            return ids, calls, ctx

        ids, calls, ctx = asyncio.run(go())
        self.assertIn("fulfil.completed", ids)
        self.assertEqual(calls, ["reserve", "reserve", "charge", "ship"])

    def test_timeout_exhausts_retries_then_compensates(self) -> None:
        async def go() -> Any:
            calls: List[str] = []
            b = (
                SagaBuilder("s")
                .step("a", invoke="reserve", compensate="release")
                .step(
                    "b",
                    invoke="charge",
                    timeout_ms=500,
                    retry=RetryPolicy(
                        max_attempts=1, base_ms=10, jitter="none"
                    ),
                )
            )
            svcs = _services(calls, {})

            async def hang(i: Any, c: Any, e: Any) -> None:
                calls.append("charge")
                await asyncio.sleep(3600)

            svcs["charge"] = hang
            m = _machine(b, svcs, [])
            clk = SimulatedClock()
            i = Interpreter(m, clock=clk)
            await i.start()
            await _until(lambda: calls == ["reserve", "charge"])
            await clk.increment(500)
            await wait_for(
                i, lambda x: x.matches("s.steps.bRetrying"), timeout=5
            )
            await clk.increment(10)
            await wait_for(i, lambda x: x.matches("s.failed"), timeout=5)
            ctx = dict(i.context)
            await i.stop()
            return calls, ctx

        calls, ctx = asyncio.run(go())
        self.assertEqual(calls, ["reserve", "charge", "release"])
        self.assertEqual(ctx["error"]["reason"], "timeout")
        self.assertEqual(ctx["compensated"], ["a"])


class TestIdempotentCompletion(unittest.TestCase):
    """Replaying the same completion (dedup on ``causationid`` via the
    inbox) must not double-compensate."""

    def test_replayed_done_does_not_double_compensate(self) -> None:
        # The saga waits for external completion events per step (the
        # choreographed shape): steps.<n> is completed by an envelope.
        cfg = {
            "id": "pay",
            "initial": "charging",
            "context": {"compensations": 0},
            "states": {
                "charging": {
                    "on": {
                        "CHARGE_FAILED": {
                            "target": "compensating",
                            "meta": {"publish": "pay.charge.failed"},
                        }
                    }
                },
                "compensating": {
                    "entry": "compensate",
                    "on": {"CHARGE_FAILED": {}},
                },
            },
        }
        m = create_machine(
            cfg,
            logic=MachineLogic(
                actions={
                    "compensate": lambda i, c, e, a: c.__setitem__(
                        "compensations", c["compensations"] + 1
                    )
                }
            ),
        )
        store, inbox, out = MemoryStore(), MemoryInbox(), MemoryOutboxStore()
        disp = InboundDispatcher(
            store,
            lambda t: m,
            inbox=inbox,
            plugins=[OutboxPlugin(out)],
            dedup_key=lambda e: e.causationid or e.id,
        )
        upstream = "evt-charge-1"
        first = Envelope.new(
            type="xsm.pay.CHARGE_FAILED", subject="p-1", causationid=upstream
        )
        # a redelivery re-minted upstream: NEW envelope id, SAME cause
        again = Envelope.new(
            type="xsm.pay.CHARGE_FAILED", subject="p-1", causationid=upstream
        )
        self.assertEqual(disp.handle(first).processed, 1)
        self.assertEqual(disp.handle(again).duplicates, 1)
        ctx = json.loads(store.load("p-1").snapshot)["context"]
        self.assertEqual(ctx["compensations"], 1)
        self.assertEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
