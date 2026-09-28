# tests/patterns/test_circuit_breaker.py
"""#265: `CircuitBreaker` state machine, fast-fail, half-open probe
admission under 32 threads, async twin, decorator, `xsm inspect` render."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from typing import Any, List

from src.xstate_statemachine import SimulatedClock, create_machine
from src.xstate_statemachine.patterns import (
    CIRCUIT_BREAKER_CONFIG,
    CircuitBreaker,
    CircuitOpenError,
    circuit_breaker,
    circuit_breaker_logic,
)
from src.xstate_statemachine.validation import walk

ROOT = Path(__file__).resolve().parents[2]


def boom() -> None:
    raise RuntimeError("down")


class TestCircuitBreaker(unittest.TestCase):
    def _cb(self, **kw: Any):
        clk = SimulatedClock()
        kw.setdefault("failure_threshold", 3)
        kw.setdefault("cooldown_ms", 1000)
        return CircuitBreaker(clock=clk, **kw), clk

    def test_opens_after_threshold_and_rejects_fast(self) -> None:
        cb, _ = self._cb()
        for n in range(2):
            with self.assertRaises(RuntimeError):
                cb.call(boom)
            self.assertEqual(cb.state, "closed")
            self.assertEqual(cb.failures, n + 1)
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        self.assertEqual(cb.state, "open")
        self.assertEqual(cb.opened_count, 1)
        called: List[int] = []
        with self.assertRaises(CircuitOpenError) as cm:
            cb.call(lambda: called.append(1))
        self.assertEqual(called, [])  # target never invoked
        self.assertEqual(cm.exception.state, "open")
        self.assertEqual(cm.exception.breaker, "circuitBreaker")

    def test_success_resets_consecutive_count(self) -> None:
        cb, _ = self._cb()
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        self.assertEqual(cb.call(lambda: 1), 1)
        self.assertEqual(cb.failures, 0)
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        self.assertEqual(cb.state, "closed")

    def test_half_open_probe_success_closes_failure_reopens(self) -> None:
        cb, clk = self._cb(failure_threshold=1)
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        self.assertEqual(cb.state, "open")
        clk.increment(999)
        self.assertEqual(cb.state, "open")
        clk.increment(2)
        self.assertEqual(cb.state, "half_open")
        with self.assertRaises(RuntimeError):
            cb.call(boom)  # the probe fails -> re-open
        self.assertEqual(cb.state, "open")
        self.assertEqual(cb.opened_count, 2)
        clk.increment(1001)
        self.assertEqual(cb.state, "half_open")
        self.assertEqual(cb.call(lambda: "ok"), "ok")
        self.assertEqual(cb.state, "closed")

    def test_half_open_admits_exactly_max_calls(self) -> None:
        cb, clk = self._cb(failure_threshold=1, half_open_max_calls=2)
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        clk.increment(1001)
        self.assertEqual(cb.state, "half_open")
        started = threading.Event()
        gate = threading.Event()
        admitted: List[int] = []
        rejected: List[int] = []

        def slow() -> str:
            started.set()
            gate.wait(5)
            return "ok"

        def worker(n: int) -> None:
            try:
                cb.call(slow)
                admitted.append(n)
            except CircuitOpenError:
                rejected.append(n)

        ts = [threading.Thread(target=worker, args=(n,)) for n in range(32)]
        for t in ts:
            t.start()
        started.wait(5)
        gate.set()
        for t in ts:
            t.join(10)
        self.assertEqual(len(admitted), 2)
        self.assertEqual(len(rejected), 30)
        self.assertEqual(cb.state, "closed")  # probes succeeded

    def test_non_counted_exception_propagates_untouched(self) -> None:
        cb, _ = self._cb(failure_threshold=1, exceptions=(ValueError,))

        def kb() -> None:
            raise KeyError("x")

        with self.assertRaises(KeyError):
            cb.call(kb)
        self.assertEqual(cb.state, "closed")
        self.assertEqual(cb.failures, 0)

    def test_reset_from_open_and_half_open(self) -> None:
        cb, clk = self._cb(failure_threshold=1)
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        self.assertEqual(cb.state, "open")
        cb.reset()
        self.assertEqual(cb.state, "closed")
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        clk.increment(1001)
        self.assertEqual(cb.state, "half_open")
        cb.reset()
        self.assertEqual(cb.state, "closed")
        cb.close()

    def test_validation(self) -> None:
        with self.assertRaises(ValueError):
            CircuitBreaker(failure_threshold=0)
        with self.assertRaises(ValueError):
            CircuitBreaker(half_open_max_calls=0)

    def test_async_twin(self) -> None:
        async def go() -> Any:
            clk = SimulatedClock()
            cb = CircuitBreaker(
                failure_threshold=2, cooldown_ms=500, clock=clk
            )

            async def aboom() -> None:
                await asyncio.sleep(0)
                raise RuntimeError("down")

            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    await cb.acall(aboom)
            self.assertEqual(cb.state, "open")
            with self.assertRaises(CircuitOpenError):
                await cb.acall(aboom)
            # SimulatedClock inside a loop returns an awaitable; the sync
            # interpreter under the breaker is settled by tick() in .state
            await clk.increment(501)
            self.assertEqual(cb.state, "half_open")

            async def ok() -> str:
                return "ok"

            self.assertEqual(await cb.acall(ok), "ok")
            # a sync callable through acall works too
            self.assertEqual(await cb.acall(lambda: 3), 3)
            return cb.state

        self.assertEqual(asyncio.run(go()), "closed")

    def test_decorator_sync_and_async(self) -> None:
        clk = SimulatedClock()

        @circuit_breaker(failure_threshold=1, cooldown_ms=100, clock=clk)
        def f(x: int) -> int:
            if x < 0:
                raise ValueError("neg")
            return x * 2

        self.assertEqual(f(2), 4)
        with self.assertRaises(ValueError):
            f(-1)
        with self.assertRaises(CircuitOpenError):
            f(1)
        self.assertEqual(f.breaker.name, "f")  # type: ignore[attr-defined]

        @circuit_breaker(failure_threshold=1, clock=clk)
        async def g(x: int) -> int:
            return x + 1

        self.assertEqual(asyncio.run(g(1)), 2)
        self.assertEqual(g.breaker.state, "closed")  # type: ignore[attr-defined]

    def test_plugins_attach(self) -> None:
        from src.xstate_statemachine import PluginBase

        class P(PluginBase):
            def __init__(self) -> None:
                self.n = 0

            def on_transition(self, *a: Any) -> None:
                self.n += 1

        p = P()
        cb, _ = self._cb(failure_threshold=1, plugins=[p])
        with self.assertRaises(RuntimeError):
            cb.call(boom)
        self.assertGreaterEqual(p.n, 1)


class TestConfigAsChart(unittest.TestCase):
    def test_config_builds_with_logic_and_has_3_states_1_timer(self) -> None:
        m = create_machine(
            CIRCUIT_BREAKER_CONFIG, logic=circuit_breaker_logic(1000)
        )
        leaves = [n for n in walk(m) if n is not m]
        self.assertEqual(
            sorted(n.id.rsplit(".", 1)[-1] for n in leaves),
            ["closed", "half_open", "open"],
        )
        self.assertEqual(sum(len(n.after) for n in leaves), 1)
        self.assertEqual(m.version, "1")

    def test_xsm_inspect_renders(self) -> None:
        tmp = ROOT / "tests" / "patterns" / "_cb_tmp.json"
        tmp.write_text(json.dumps(CIRCUIT_BREAKER_CONFIG), encoding="utf-8")
        try:
            out = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "xstate_statemachine",
                    "inspect",
                    str(tmp),
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                env={
                    **__import__("os").environ,
                    "PYTHONPATH": str(ROOT / "src"),
                },
            )
            data = json.loads(out.stdout)
        finally:
            tmp.unlink(missing_ok=True)
        self.assertEqual(
            sorted(data["state_kinds"]),
            [
                "circuitBreaker.closed",
                "circuitBreaker.half_open",
                "circuitBreaker.open",
            ],
        )
        self.assertEqual(data["version"], "1")
        self.assertIn("cooldown", data.get("delays", []))


if __name__ == "__main__":
    unittest.main()
