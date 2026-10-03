# tests/patterns/test_battle_265_circuit_breaker.py
"""#265 battle (adversary B): `CircuitBreaker` under hostile use.

Probe races at 32/128/512 threads and 500 tasks, late results from a
stale window, tick/lock re-entrancy, clock semantics, exception
classification, `reset()` / `close()`, the decorator, observability and
leak / parallelism checks. Every test is under a 30 s timeout.
"""

from __future__ import annotations

import asyncio
import functools
import gc
import inspect
import json
import math
import os
import subprocess
import sys
import threading
import time
import tracemalloc
import unittest
from pathlib import Path
from typing import Any, List

import pytest

from src.xstate_statemachine import (
    PluginBase,
    SimulatedClock,
    SyncInterpreter,
)
from src.xstate_statemachine.exceptions import InterpreterStoppedError
from src.xstate_statemachine.patterns import (
    CIRCUIT_BREAKER_CONFIG,
    CircuitBreaker,
    CircuitOpenError,
    circuit_breaker,
)

pytestmark = pytest.mark.timeout(30)
ROOT = Path(__file__).resolve().parents[2]


def boom() -> None:
    raise ValueError("down")


def _trip(cb: CircuitBreaker, n: int = 1) -> None:
    for _ in range(n):
        try:
            cb.call(boom)
        except (ValueError, CircuitOpenError):
            pass


def _half_open(max_calls: int) -> Any:
    clk = SimulatedClock()
    cb = CircuitBreaker(
        failure_threshold=1,
        cooldown_ms=1000,
        half_open_max_calls=max_calls,
        clock=clk,
    )
    _trip(cb)
    clk.increment(1001)
    return cb, clk


class _Counter:
    def __init__(self) -> None:
        self.n = 0
        self.lock = threading.Lock()

    def bump(self) -> None:
        with self.lock:
            self.n += 1


# -----------------------------------------------------------------------------
# 1. Half-open probe race
# -----------------------------------------------------------------------------
class TestProbeRace(unittest.TestCase):
    def _hammer(
        self,
        threads: int,
        max_calls: int,
        fn: Any,
        on_reject: Any = None,
    ) -> List[Any]:
        cb, _ = _half_open(max_calls)
        self.assertEqual(cb.state, "half_open")
        barrier = threading.Barrier(threads)
        outcomes: List[Any] = []
        olock = threading.Lock()

        def worker() -> None:
            barrier.wait()
            try:
                r: Any = cb.call(fn)
            except CircuitOpenError as e:
                r = e
                if on_reject is not None:
                    on_reject()
            except ValueError as e:
                r = e
            with olock:
                outcomes.append(r)

        ts = [threading.Thread(target=worker) for _ in range(threads)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(20)
        self.assertEqual(len(outcomes), threads)
        return [cb, outcomes]

    def test_exactly_max_calls_probes_admitted(self) -> None:
        for threads in (32, 128, 512):
            for max_calls in (1, 2, 7):
                with self.subTest(threads=threads, max_calls=max_calls):
                    hits = _Counter()
                    gate = threading.Event()
                    # 📝 Release the probes only once EVERY other caller has
                    #    been refused -- a fixed 0.3 s timer let a slow
                    #    512-thread start on Python 3.9 open the gate before
                    #    all callers had reached the breaker, so a late
                    #    caller found a CLOSED circuit and was counted as a
                    #    hit (real-3.9 run).
                    decided = threading.Semaphore(0)

                    def fn() -> str:
                        hits.bump()
                        gate.wait(10)  # hold probes in flight
                        return "ok"

                    def release_when_all_decided() -> None:
                        for _ in range(threads - max_calls):
                            decided.acquire(timeout=10)
                        gate.set()

                    t = threading.Thread(target=release_when_all_decided)
                    t.start()
                    cb, outs = self._hammer(
                        threads, max_calls, fn, on_reject=decided.release
                    )
                    t.join(15)
                    rejected = [o for o in outs if isinstance(o, Exception)]
                    self.assertEqual(hits.n, max_calls)
                    self.assertEqual(len(rejected), threads - max_calls)
                    self.assertTrue(
                        all(e.state == "half_open" for e in rejected)
                    )
                    self.assertEqual(cb.state, "closed")

    def test_one_probe_fails_reopens_late_success_ignored(self) -> None:
        cb, clk = _half_open(2)
        w1 = cb._admit()
        w2 = cb._admit()
        cb._record(False, w1)  # probe 1 fails -> open
        self.assertEqual(cb.state, "open")
        opened = cb.opened_count
        cb._record(True, w2)  # late SUCCESS from probe 2
        self.assertEqual(cb.state, "open")
        self.assertEqual(cb.opened_count, opened)
        # ... and still ignored after the NEXT half-open window starts
        clk.increment(1001)
        self.assertEqual(cb.state, "half_open")
        cb._record(True, w2)
        self.assertEqual(cb.state, "half_open")

    def test_late_closed_window_success_cannot_close_half_open(self) -> None:
        # 🔥 Was a BUG: slow call admitted while closed returned SUCCESS
        #    after open -> half_open, and closed the circuit unprobed.
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=100, clock=clk)
        slow = cb._admit()
        _trip(cb)
        clk.increment(101)
        self.assertEqual(cb.state, "half_open")
        cb._record(True, slow)
        self.assertEqual(cb.state, "half_open")
        cb._record(False, slow)  # a late FAILURE does not re-open either
        self.assertEqual(cb.state, "half_open")

    def test_late_failure_from_previous_closed_window_ignored(self) -> None:
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=100, clock=clk)
        slow = cb._admit()
        _trip(cb)
        clk.increment(101)
        cb.call(lambda: 1)  # probe closes it
        self.assertEqual(cb.state, "closed")
        cb._record(False, slow)  # stale: a new closed window
        self.assertEqual(cb.state, "closed")

    def test_hung_probe_holds_window_documented(self) -> None:
        # 📝 DOCUMENTED limitation: no probe timeout. A probe that never
        #    returns keeps the half-open window full; callers are
        #    rejected until it returns or `reset()` is called.
        cb, clk = _half_open(1)
        cb._admit()  # the hung probe
        clk.increment(10_000_000)
        with self.assertRaises(CircuitOpenError):
            cb.call(lambda: 1)
        cb.reset()
        self.assertEqual(cb.call(lambda: 2), 2)

    def test_acall_500_tasks_one_loop(self) -> None:
        cb, _ = _half_open(3)
        hits = _Counter()

        async def target() -> str:
            hits.bump()
            await asyncio.sleep(0.05)
            return "ok"

        async def main() -> List[Any]:
            return await asyncio.gather(
                *(cb.acall(target) for _ in range(500)),
                return_exceptions=True,
            )

        outs = asyncio.run(main())
        self.assertEqual(hits.n, 3)
        self.assertEqual(
            sum(isinstance(o, CircuitOpenError) for o in outs), 497
        )
        self.assertEqual(cb.state, "closed")

    def test_threads_and_tasks_mixed(self) -> None:
        cb, _ = _half_open(2)
        hits = _Counter()

        def fn() -> str:
            hits.bump()
            time.sleep(0.1)
            return "ok"

        async def afn() -> str:
            hits.bump()
            await asyncio.sleep(0.1)
            return "ok"

        rejected = _Counter()
        barrier = threading.Barrier(65)

        def thread_worker() -> None:
            barrier.wait()
            try:
                cb.call(fn)
            except CircuitOpenError:
                rejected.bump()

        async def task_worker() -> None:
            try:
                await cb.acall(afn)
            except CircuitOpenError:
                rejected.bump()

        def loop_thread() -> None:
            barrier.wait()

            async def main() -> None:
                await asyncio.gather(*(task_worker() for _ in range(64)))

            asyncio.run(main())

        ts = [threading.Thread(target=thread_worker) for _ in range(64)]
        ts.append(threading.Thread(target=loop_thread))
        for t in ts:
            t.start()
        for t in ts:
            t.join(20)
        self.assertEqual(hits.n, 2)
        self.assertEqual(rejected.n, 126)


# -----------------------------------------------------------------------------
# 2. tick() + lock, re-entrancy
# -----------------------------------------------------------------------------
class TestTickAndReentrancy(unittest.TestCase):
    def test_state_from_observer_thread_is_never_stale(self) -> None:
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=100, clock=clk)
        _trip(cb)
        # SimulatedClock.increment settles attached sync interpreters
        clk.increment(101)
        seen: List[str] = []
        t = threading.Thread(target=lambda: seen.append(cb.state))
        t.start()
        t.join(5)
        self.assertEqual(seen, ["half_open"])

    def test_real_clock_half_opens_only_when_pumped(self) -> None:
        # 📝 PINNED: RealClock timers are a heap pumped by tick(); there
        #    is no background thread. A breaker left open with no traffic
        #    half-opens on the next `state` / `call()`, not on its own.
        before = threading.active_count()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=30)
        _trip(cb)
        self.assertEqual(threading.active_count(), before)
        time.sleep(0.1)
        self.assertEqual(cb._leaf(), "open")  # nobody pumped yet
        self.assertEqual(cb.state, "half_open")

    def test_plugin_reading_state_in_on_transition_no_deadlock(self) -> None:
        seen: List[str] = []
        holder: List[CircuitBreaker] = []

        class P(PluginBase):
            def on_transition(self, *a: Any, **k: Any) -> None:
                if holder:
                    seen.append(holder[0].state)  # re-entrant tick

        clk = SimulatedClock()
        cb = CircuitBreaker(
            failure_threshold=1, cooldown_ms=100, clock=clk, plugins=[P()]
        )
        holder.append(cb)
        _trip(cb)
        clk.increment(101)
        self.assertEqual(cb.state, "half_open")
        self.assertIn("open", seen)
        self.assertIn("half_open", seen)

    def test_fn_calling_same_breaker_is_admitted_nested(self) -> None:
        # 📝 DECIDED: allowed (RLock is not held while fn runs); nested
        #    admission is a normal independent call.
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=2, cooldown_ms=100, clock=clk)
        self.assertEqual(cb.call(lambda: cb.call(lambda: 7) + 1), 8)

        def outer() -> None:
            try:
                cb.call(boom)
            except ValueError:
                pass
            raise ValueError("outer")

        with self.assertRaises(ValueError):
            cb.call(outer)
        self.assertEqual(cb.state, "open")


# -----------------------------------------------------------------------------
# 3. Clock semantics / validation
# -----------------------------------------------------------------------------
class TestClockSemantics(unittest.TestCase):
    def test_bad_cooldowns_rejected(self) -> None:
        # 🔥 Was a BUG: NaN / inf = open forever; negative = instant.
        for bad in (-1, float("nan"), float("inf"), -math.inf):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                CircuitBreaker(cooldown_ms=bad)

    def test_zero_cooldown_half_opens_on_next_read(self) -> None:
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=0, clock=clk)
        _trip(cb)
        self.assertEqual(cb.state, "half_open")
        self.assertEqual(cb.opened_count, 1)

    def test_threshold_one(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, clock=SimulatedClock())
        _trip(cb)
        self.assertEqual(cb.state, "open")

    def test_shared_simulated_clock_with_app_machine(self) -> None:
        from src.xstate_statemachine import create_machine

        clk = SimulatedClock()
        app = SyncInterpreter(
            create_machine(
                {
                    "id": "app",
                    "initial": "a",
                    "states": {"a": {"after": {"500": "b"}}, "b": {}},
                }
            ),
            clock=clk,
        ).start()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=1000, clock=clk)
        _trip(cb)
        clk.increment(600)
        self.assertIn("app.b", app.current_state_ids)
        self.assertEqual(cb.state, "open")
        clk.increment(500)
        self.assertEqual(cb.state, "half_open")
        app.stop()


# -----------------------------------------------------------------------------
# 4. Exception classification
# -----------------------------------------------------------------------------
class TestExceptionClassification(unittest.TestCase):
    def test_unlisted_exception_untouched(self) -> None:
        cb = CircuitBreaker(
            failure_threshold=2,
            exceptions=(ValueError,),
            clock=SimulatedClock(),
        )
        _trip(cb)
        self.assertEqual(cb.failures, 1)
        with self.assertRaises(KeyError):
            cb.call(lambda: {}["x"])
        self.assertEqual(cb.failures, 1)
        self.assertEqual(cb.state, "closed")

    def test_base_exceptions_never_count(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, clock=SimulatedClock())
        for exc in (KeyboardInterrupt, SystemExit, GeneratorExit):

            def fn(e: Any = exc) -> None:
                raise e()

            with self.subTest(exc=exc), self.assertRaises(exc):
                cb.call(fn)
        self.assertEqual(cb.state, "closed")
        self.assertEqual(cb.failures, 0)

    def test_cancelled_in_acall_never_counts(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, clock=SimulatedClock())

        async def hang() -> None:
            await asyncio.sleep(10)

        async def main() -> None:
            t = asyncio.ensure_future(cb.acall(hang))
            await asyncio.sleep(0.01)
            t.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await t

        asyncio.run(main())
        self.assertEqual(cb.state, "closed")

    def test_call_returning_coroutine_is_not_awaited(self) -> None:
        # 📝 DOCUMENTED: `call()` is the sync path; a coroutine result is
        #    returned as-is and counted a SUCCESS. Use `acall()`.
        cb = CircuitBreaker(clock=SimulatedClock())

        async def coro() -> int:
            raise ValueError("never seen by the breaker")

        result = cb.call(coro)
        self.assertTrue(inspect.iscoroutine(result))
        result.close()
        self.assertEqual(cb.failures, 0)

    def test_acall_awaits_failing_future(self) -> None:
        cb = CircuitBreaker(failure_threshold=1, clock=SimulatedClock())

        async def main() -> None:
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            loop.call_later(0.01, fut.set_exception, ValueError("late"))
            with self.assertRaises(ValueError):
                await cb.acall(lambda: fut)

        asyncio.run(main())
        self.assertEqual(cb.state, "open")


# -----------------------------------------------------------------------------
# 5/6. reset() and close()
# -----------------------------------------------------------------------------
class TestResetClose(unittest.TestCase):
    def test_reset_from_open_keeps_plugins_count_no_heap_leak(self) -> None:
        events: List[Any] = []

        class P(PluginBase):
            def on_transition(self, *a: Any, **k: Any) -> None:
                events.append(1)

        clk = SimulatedClock()
        cb = CircuitBreaker(
            failure_threshold=1, cooldown_ms=100, clock=clk, plugins=[P()]
        )
        _trip(cb)
        self.assertIsNotNone(clk.next_due())
        cb.reset()
        self.assertIsNone(clk.next_due())  # old cooldown cancelled
        self.assertEqual(cb.state, "closed")
        self.assertEqual(cb.opened_count, 1)  # 🔥 was reset to 0
        n = len(events)
        _trip(cb)
        self.assertGreater(len(events), n)
        self.assertEqual(cb.opened_count, 2)

    def test_reset_from_half_open_with_probes_in_flight(self) -> None:
        cb, _ = _half_open(2)
        w = cb._admit()
        cb.reset()
        self.assertEqual(cb.state, "closed")
        cb._record(False, w)  # stale probe failure
        self.assertEqual(cb.state, "closed")

    def test_thousand_resets_flat(self) -> None:
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=100, clock=clk)
        threads = threading.active_count()
        for _ in range(1000):
            _trip(cb)
            cb.reset()
        self.assertEqual(clk.pending, 0)
        self.assertEqual(threading.active_count(), threads)
        self.assertEqual(cb.opened_count, 1000)

    def test_reset_racing_admit_is_consistent(self) -> None:
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=100, clock=clk)
        stop = threading.Event()
        bad: List[Any] = []

        def caller() -> None:
            while not stop.is_set():
                try:
                    cb.call(boom)
                except (ValueError, CircuitOpenError):
                    pass
                except Exception as e:  # pragma: no cover - failure path
                    bad.append(e)

        ts = [threading.Thread(target=caller) for _ in range(4)]
        for t in ts:
            t.start()
        for _ in range(200):
            cb.reset()
        stop.set()
        for t in ts:
            t.join(5)
        self.assertEqual(bad, [])
        self.assertIn(cb.state, ("closed", "open"))

    def test_call_after_close_is_typed_error(self) -> None:
        # 🔥 Was a BUG: after close() call() ran fn unprotected.
        cb = CircuitBreaker(clock=SimulatedClock())
        cb.close()
        cb.close()  # idempotent
        hits = _Counter()
        with self.assertRaises(InterpreterStoppedError):
            cb.call(hits.bump)
        with self.assertRaises(InterpreterStoppedError):
            asyncio.run(cb.acall(hits.bump))
        self.assertEqual(hits.n, 0)

    def test_close_racing_call(self) -> None:
        cb = CircuitBreaker(clock=SimulatedClock())
        bad: List[Any] = []

        def caller() -> None:
            for _ in range(500):
                try:
                    cb.call(lambda: 1)
                except InterpreterStoppedError:
                    return
                except Exception as e:  # pragma: no cover
                    bad.append(e)

        t = threading.Thread(target=caller)
        t.start()
        cb.close()
        t.join(5)
        self.assertEqual(bad, [])


# -----------------------------------------------------------------------------
# 7. Decorator
# -----------------------------------------------------------------------------
class TestDecorator(unittest.TestCase):
    def test_method_shares_one_breaker_per_class(self) -> None:
        # 📝 DOCUMENTED: decoration happens once at class creation, so all
        #    instances share ONE breaker named after the function.
        class Svc:
            @circuit_breaker(failure_threshold=1, clock=SimulatedClock())
            def fetch(self, x: int) -> int:
                if x < 0:
                    raise ValueError("neg")
                return x

        a, b = Svc(), Svc()
        with self.assertRaises(ValueError):
            a.fetch(-1)
        with self.assertRaises(CircuitOpenError):
            b.fetch(1)
        self.assertEqual(Svc.fetch.breaker.name, "fetch")

    def test_static_class_method_and_partial(self) -> None:
        class K:
            @staticmethod
            @circuit_breaker(clock=SimulatedClock())
            def s(x: int) -> int:
                return x

            @classmethod
            @circuit_breaker(clock=SimulatedClock())
            def c(cls, x: int) -> int:
                return x

        self.assertEqual(K.s(1), 1)
        self.assertEqual(K.c(2), 2)
        p = circuit_breaker(clock=SimulatedClock())(
            functools.partial(lambda a, b: a + b, 1)
        )
        self.assertEqual(p(2), 3)
        self.assertEqual(p.breaker.name, "circuitBreaker")

    def test_generator_refused(self) -> None:
        def gen() -> Any:
            yield 1

        async def agen() -> Any:
            yield 1

        for fn in (gen, agen):
            with self.assertRaises(TypeError):
                circuit_breaker()(fn)

    def test_independent_state_and_reused_decorator(self) -> None:
        deco = circuit_breaker(failure_threshold=1, clock=SimulatedClock())

        @deco
        def f1() -> None:
            raise ValueError("x")

        @deco
        def f2() -> int:
            return 2

        with self.assertRaises(ValueError):
            f1()
        self.assertEqual(f2(), 2)
        self.assertIsNot(f1.breaker, f2.breaker)
        self.assertEqual(f2.breaker.name, "f2")  # 🔥 was "f1"

    def test_wraps_preserves_metadata(self) -> None:
        @circuit_breaker()
        def documented(a: int, b: str = "x") -> str:
            """Docs."""
            return b * a

        self.assertEqual(documented.__name__, "documented")
        self.assertEqual(documented.__doc__, "Docs.")
        sig = inspect.signature(documented)
        self.assertEqual(list(sig.parameters), ["a", "b"])
        self.assertEqual(sig.parameters["b"].default, "x")


# -----------------------------------------------------------------------------
# 8. Observability
# -----------------------------------------------------------------------------
class TestObservability(unittest.TestCase):
    def test_snapshot_round_trip(self) -> None:
        # 📝 DOCUMENTED: no public `CircuitBreaker.from_snapshot`; the
        #    snapshot restores into a plain SyncInterpreter only.
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=100, clock=clk)
        _trip(cb)
        snap = cb.interpreter.get_snapshot()
        restored = SyncInterpreter.from_snapshot(
            snap, cb.interpreter.machine, clock=SimulatedClock()
        )
        self.assertEqual(
            restored.current_state_ids, cb.interpreter.current_state_ids
        )
        self.assertEqual(restored.context["opened_count"], 1)
        restored.stop()
        self.assertFalse(hasattr(CircuitBreaker, "from_snapshot"))

    def test_logging_inspector_shows_trip(self) -> None:
        from src.xstate_statemachine import LoggingInspector

        with self.assertLogs("xstate_statemachine", level="INFO") as cm:
            cb = CircuitBreaker(
                failure_threshold=1,
                clock=SimulatedClock(),
                plugins=[LoggingInspector()],
            )
            _trip(cb)
        self.assertTrue(any("open" in m for m in cm.output))

    def _cli(self, *args: str, tmp: Path) -> str:
        p = tmp / "cb.json"
        p.write_text(json.dumps(CIRCUIT_BREAKER_CONFIG), encoding="utf-8")
        # 📝 Force UTF-8 in the CHILD: without it the CLI writes its table
        #    in the console code page (cp1252 on Windows -- a "·" is 0xb7),
        #    the parent's utf-8 reader thread dies on it and `r.stdout`
        #    comes back None (handover §1; it passed only when an earlier
        #    test had leaked PYTHONIOENCODING into os.environ).
        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "PYTHONPATH": str(ROOT / "src"),
        }
        r = subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", *args, str(p)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=25,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_cli_inspect_and_validate(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            out = self._cli("inspect", tmp=Path(d))
            for leaf in ("closed", "open", "half_open"):
                self.assertIn(leaf, out)
            self._cli("validate", "--plain", tmp=Path(d))
        self.assertEqual(CIRCUIT_BREAKER_CONFIG["version"], "1")


# -----------------------------------------------------------------------------
# 9. Leaks / perf / parallelism
# -----------------------------------------------------------------------------
class TestLeaksAndPerf(unittest.TestCase):
    def test_closed_calls_memory_and_threads_flat(self) -> None:
        cb = CircuitBreaker(clock=SimulatedClock())
        threads = threading.active_count()
        fn = int

        def run(n: int) -> None:
            for _ in range(n):
                cb.call(fn)

        run(5_000)
        gc.collect()
        tracemalloc.start()
        run(50_000)
        gc.collect()
        half, _ = tracemalloc.get_traced_memory()
        run(50_000)
        gc.collect()
        full, _ = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        self.assertLess(full - half, 64 * 1024)
        self.assertEqual(threading.active_count(), threads)

    def test_cycles_on_simulated_clock(self) -> None:
        clk = SimulatedClock()
        cb = CircuitBreaker(failure_threshold=1, cooldown_ms=10, clock=clk)
        for _ in range(10_000):
            _trip(cb)
            clk.increment(11)
            cb.call(int)
        self.assertEqual(cb.state, "closed")
        self.assertEqual(cb.opened_count, 10_000)
        self.assertEqual(clk.pending, 0)

    def test_fn_runs_outside_the_lock(self) -> None:
        cb = CircuitBreaker(clock=SimulatedClock())
        ts = [
            threading.Thread(target=cb.call, args=(time.sleep, 0.2))
            for _ in range(8)
        ]
        start = time.perf_counter()
        for t in ts:
            t.start()
        for t in ts:
            t.join(5)
        self.assertLess(time.perf_counter() - start, 1.0)  # not 1.6 s


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
