# tests/patterns/test_retry.py
"""#265: `RetryPolicy` delay formulas (property-style) and the retry loop
driven end-to-end on both engines with `DeadLetterPlugin` receiving the
final record."""

from __future__ import annotations

import asyncio
import random
import unittest
from typing import Any, List

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.patterns import (
    DeadLetterPlugin,
    DeadLetterStore,
    RetryPolicy,
)


class TestDelayFormulas(unittest.TestCase):
    def test_none_is_pure_exponential_capped(self) -> None:
        p = RetryPolicy(base_ms=100, factor=2, max_ms=1000, jitter="none")
        self.assertEqual(
            [p.delay_ms(a) for a in range(1, 7)],
            [100, 200, 400, 800, 1000, 1000],
        )

    def test_full_and_equal_bounded_and_deterministic(self) -> None:
        for mode, lo_frac in (("full", 0.0), ("equal", 0.5)):
            for seed in range(20):
                rng = random.Random(seed).random
                p = RetryPolicy(
                    base_ms=50, factor=3, max_ms=5000, jitter=mode, rng=rng
                )
                p2 = RetryPolicy(
                    base_ms=50,
                    factor=3,
                    max_ms=5000,
                    jitter=mode,
                    rng=random.Random(seed).random,
                )
                for a in range(1, 12):
                    exp = p.exponential_ms(a)
                    d = p.delay_ms(a)
                    self.assertGreaterEqual(d, lo_frac * exp - 1e-9, (mode, a))
                    self.assertLessEqual(d, exp + 1e-9, (mode, a))
                    self.assertLessEqual(d, 5000 + 1e-9)
                    self.assertEqual(d, p2.delay_ms(a))  # deterministic

    def test_none_and_equal_monotone_envelope(self) -> None:
        # Monotone in the attempt for the deterministic modes' upper bound.
        p = RetryPolicy(base_ms=10, factor=2, max_ms=10_000, jitter="none")
        seq = [p.delay_ms(a) for a in range(1, 15)]
        self.assertEqual(seq, sorted(seq))

    def test_decorrelated_bounded_by_base_and_cap(self) -> None:
        rng = random.Random(7).random
        p = RetryPolicy(
            base_ms=100, max_ms=2000, jitter="decorrelated", rng=rng
        )
        prev = None
        for a in range(1, 40):
            d = p.delay_ms(a, previous_ms=prev)
            self.assertGreaterEqual(d, 100 - 1e-9)
            self.assertLessEqual(d, 2000 + 1e-9)
            if prev is not None:
                self.assertLessEqual(d, max(100, prev * 3) + 1e-9)
            prev = d

    def test_validation(self) -> None:
        for kw in (
            {"max_attempts": 0},
            {"factor": 0.5},
            {"base_ms": -1},
            {"jitter": "wat"},
        ):
            with self.assertRaises(ValueError, msg=kw):
                RetryPolicy(**kw)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            RetryPolicy().exponential_ms(0)


class TestRetryLogic(unittest.TestCase):
    def test_logic_names_and_behaviour(self) -> None:
        p = RetryPolicy(max_attempts=3, base_ms=100, jitter="none")
        lg = p.logic()
        self.assertEqual(set(lg.actions), {"retryBump", "retryReset"})
        self.assertEqual(set(lg.guards), {"retryCanRetry"})
        self.assertEqual(set(lg.delays), {"retryDelay"})
        ctx: dict = {}
        self.assertTrue(lg.guards["retryCanRetry"](ctx, None))
        lg.actions["retryBump"](None, ctx, None, None)
        self.assertEqual(lg.delays["retryDelay"](ctx, None), 100)  # attempt 1
        lg.actions["retryBump"](None, ctx, None, None)
        self.assertEqual(lg.delays["retryDelay"](ctx, None), 200)
        lg.actions["retryBump"](None, ctx, None, None)
        self.assertFalse(lg.guards["retryCanRetry"](ctx, None))  # 3 >= 3
        lg.actions["retryReset"](None, ctx, None, None)
        self.assertEqual(ctx["attempt"], 0)

    def test_decorrelated_delay_remembers_previous_in_context(self) -> None:
        p = RetryPolicy(
            base_ms=100, jitter="decorrelated", rng=random.Random(1).random
        )
        d = p.as_delay()
        ctx = {"attempt": 1}
        first = d(ctx, None)
        self.assertEqual(ctx["attempt_delay_ms"], first)
        p.action_reset()(None, ctx, None, None)
        self.assertNotIn("attempt_delay_ms", ctx)

    def test_merge_does_not_mutate(self) -> None:
        a = MachineLogic(actions={"x": lambda *_: None})
        b = RetryPolicy().logic()
        m = a.merge(b)
        self.assertIn("x", m.actions)
        self.assertIn("retryBump", m.actions)
        self.assertNotIn("retryBump", a.actions)
        self.assertIn("retryDelay", m.delays)

    def test_merge_is_not_scanned_as_subclass_logic(self) -> None:
        # A strict MachineLogic subclass must not trip over the base
        # class's own public `merge` (it is not user logic).
        from src.xstate_statemachine import guard

        class Strict(MachineLogic):
            @guard
            def ok(self, ctx: Any, e: Any) -> bool:
                return True

        lg = Strict(strict=True)
        self.assertIn("ok", lg.guards)
        merged = lg.merge(RetryPolicy().logic())
        self.assertIn("ok", merged.guards)
        self.assertIn("retryCanRetry", merged.guards)


RETRY_CFG = {
    "id": "job",
    "initial": "attempting",
    "context": {"attempt": 0, "password": "hunter2"},
    "states": {
        "attempting": {
            "invoke": {
                "src": "work",
                "onDone": {"target": "done", "actions": "retryReset"},
                "onError": {"target": "retrying", "actions": "retryBump"},
            }
        },
        "retrying": {
            "after": {
                "retryDelay": [
                    {"guard": "retryCanRetry", "target": "attempting"},
                    {"target": "deadLettered"},
                ]
            }
        },
        "done": {"type": "final"},
        "deadLettered": {"type": "final", "tags": ["dead-letter"]},
    },
}


def _flaky(fail_times: int):
    calls = {"n": 0}

    def work(i: Any, c: Any, e: Any) -> str:
        calls["n"] += 1
        if calls["n"] <= fail_times:
            raise ConnectionError(f"boom #{calls['n']}")
        return "ok"

    return work, calls


class TestRetryLoopSync(unittest.TestCase):
    def _run(self, fail_times: int, max_attempts: int):
        p = RetryPolicy(max_attempts=max_attempts, base_ms=100, jitter="none")
        work, calls = _flaky(fail_times)
        m = create_machine(
            RETRY_CFG,
            logic=p.logic().merge(MachineLogic(services={"work": work})),
        )
        clk = SimulatedClock()
        store = DeadLetterStore()
        i = SyncInterpreter(m, clock=clk).use(DeadLetterPlugin(store)).start()
        for _ in range(max_attempts + 2):
            clk.increment(100_000)  # generous: every delay is < 100 s
        return i, calls, store

    def test_three_failures_then_success(self) -> None:
        i, calls, store = self._run(fail_times=3, max_attempts=5)
        self.assertIn("job.done", i.current_state_ids)
        self.assertEqual(calls["n"], 4)
        self.assertEqual(i.context["attempt"], 0)  # reset on success
        self.assertEqual(len(store), 0)

    def test_gives_up_and_dead_letters_with_error_chain(self) -> None:
        i, calls, store = self._run(fail_times=10, max_attempts=3)
        self.assertIn("job.deadLettered", i.current_state_ids)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(len(store), 1)
        dl = store.all()[0]
        self.assertEqual(dl.machine_id, "job")
        self.assertEqual(dl.state_id, "job.deadLettered")
        self.assertEqual(dl.attempts, 3)
        self.assertEqual(
            [e["message"] for e in dl.errors],
            ["boom #1", "boom #2", "boom #3"],
        )
        self.assertTrue(all(e["type"] == "ConnectionError" for e in dl.errors))
        self.assertTrue(all(e["source"] == "service" for e in dl.errors))
        # X0: the snapshot's context is redacted before it reaches the sink
        self.assertEqual(dl.snapshot["context"]["password"], "***")
        self.assertEqual(dl.snapshot["version"], 4)
        self.assertTrue(dl.event["type"].startswith("after."))
        # JSON-serialisable
        import json

        json.loads(dl.to_json())


class TestRetryLoopAsync(unittest.TestCase):
    def test_gives_up_and_dead_letters_async(self) -> None:
        async def go():
            p = RetryPolicy(max_attempts=3, base_ms=100, jitter="none")
            work, calls = _flaky(10)

            async def awork(i: Any, c: Any, e: Any) -> str:
                return work(i, c, e)

            m = create_machine(
                RETRY_CFG,
                logic=p.logic().merge(MachineLogic(services={"work": awork})),
            )
            clk = SimulatedClock()
            store = DeadLetterStore()
            i = Interpreter(m, clock=clk).use(DeadLetterPlugin(store))
            await i.start()
            for _ in range(5):
                await clk.increment(100_000)
                await asyncio.sleep(0)
            ids = set(i.current_state_ids)
            await i.stop()
            return ids, calls, store

        ids, calls, store = asyncio.run(go())
        self.assertIn("job.deadLettered", ids)
        self.assertEqual(calls["n"], 3)
        self.assertEqual(len(store), 1)
        self.assertEqual(store.all()[0].attempts, 3)
        self.assertEqual(len(store.all()[0].errors), 3)


class TestDeadLetterStore(unittest.TestCase):
    def test_purge_older_than(self) -> None:
        from src.xstate_statemachine.patterns import DeadLetter

        st = DeadLetterStore()
        for t in (10.0, 20.0, 30.0):
            st(DeadLetter("m", "m.x", {}, None, [], {}, t))
        self.assertEqual(st.purge_older_than(20.0), 1)
        self.assertEqual([r.taken_at for r in st.all()], [20.0, 30.0])
        st.clear()
        self.assertEqual(len(st), 0)

    def test_explicit_state_ids_and_no_snapshot(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"X": "poison"}}, "poison": {}},
        }
        store = DeadLetterStore()
        plugin = DeadLetterPlugin(
            store, state_ids=["m.poison"], include_snapshot=False
        )
        i = SyncInterpreter(create_machine(cfg)).use(plugin).start()
        i.send("X", token="s3cret")
        self.assertEqual(len(store), 1)
        dl = store.all()[0]
        self.assertEqual(dl.snapshot, {})
        self.assertEqual(dl.event, {"type": "X", "payload": {"token": "***"}})
        self.assertIsNone(dl.attempts)
        i.stop()


if __name__ == "__main__":
    unittest.main()
