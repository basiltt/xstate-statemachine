"""Regression tests for the round-6 re-verification findings (#166–#175).

One class per issue. Each test is the reporter's acceptance criterion in
miniature, so a future regression names the issue it reopens. Where an
issue is about engine parity the test runs BOTH engines.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import unittest
import warnings
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Event,
    Interpreter,
    MachineLogic,
    RunawayChainError,
    SnapshotMidStepError,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import InterpreterStoppedError
from src.xstate_statemachine.interpreter import DEFAULT_SERVICE_POOL_SIZE
from src.xstate_statemachine.plugins import PluginBase


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)


def _run(coro: Any, timeout: float = 20.0) -> Any:
    return asyncio.run(asyncio.wait_for(coro, timeout))


def _mk(cfg: Dict[str, Any], **kw: Any) -> Any:
    return create_machine(json.loads(json.dumps(cfg)), **kw)


class _Drops(PluginBase):
    def __init__(self) -> None:
        self.dropped: List[str] = []

    def on_event_dropped(self, interp: Any, event: Any, reason: str) -> None:
        self.dropped.append(reason)


# =============================================================================
# #166 — `always` into an invoking child: async settle budget is per macrostep
# =============================================================================
class TestAsyncSettleBudgetIsPerMacrostep(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "on": {"GO": {"target": "#m.a", "internal": True}},
        "states": {
            "a": {
                "initial": "a",
                "always": {"target": "#m.a.a", "guard": "g"},
                "states": {"a": {"invoke": {"id": "i", "src": "svc"}}},
            }
        },
    }

    @staticmethod
    def _logic() -> MachineLogic:
        return MachineLogic(
            guards={"g": lambda c, e: True},
            services={"svc": lambda i, c, e: 1},
        )

    def test_sync_trips(self) -> None:
        s = SyncInterpreter(_mk(self.CFG, logic=self._logic())).start()
        s.send("GO")
        self.assertIsInstance(s.last_error, RunawayChainError)

    def test_async_trips_instead_of_hanging(self) -> None:
        async def main() -> Any:
            i = await Interpreter(_mk(self.CFG, logic=self._logic())).start()
            await asyncio.sleep(0.05)
            receipt = await asyncio.wait_for(i.send("GO", wait=True), 5)
            await i.stop()
            return receipt

        r = _run(main())
        self.assertIsInstance(r.error, RunawayChainError)


# =============================================================================
# #167 — rollback -> re-arm -> done -> rollback cycle is bounded on async
# =============================================================================
class TestAsyncRollbackRearmCycleBounded(_Quiet):
    CFG = {
        "id": "spin",
        "actionErrorPolicy": "rollback",
        "initial": "starting",
        "context": {},
        "states": {
            "starting": {
                "invoke": {
                    "id": "s",
                    "src": "svc",
                    "onDone": {"target": "#spin.recording"},
                }
            },
            "recording": {"entry": ["boom"]},
        },
    }

    def test_service_calls_bounded_by_max_iterations(self) -> None:
        calls = [0]

        def boom(*a: Any) -> None:
            raise RuntimeError("boom")

        def svc(i: Any, c: Any, e: Any) -> int:
            calls[0] += 1
            return 1

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(
                _mk(
                    self.CFG,
                    logic=MachineLogic(
                        actions={"boom": boom}, services={"svc": svc}
                    ),
                )
            ).use(d)
            await i.start()
            await asyncio.sleep(0.6)
            first = calls[0]
            await asyncio.sleep(0.3)
            out = (first, calls[0], i.status, d.dropped)
            await i.stop()
            return out

        first, later, status, dropped = _run(main())
        self.assertEqual(status, "running")
        self.assertLessEqual(first, 1001 + 2)
        self.assertEqual(first, later, "cycle must stop, not keep spinning")
        self.assertIn("chain_budget", dropped)


# =============================================================================
# #168 — invoke ping-pong (`ver -> arm -> ver`) trips the async chain budget
# =============================================================================
class TestAsyncInvokeCycleTrips(_Quiet):
    CFG = {
        "id": "cyc",
        "initial": "idle",
        "maxIterations": 50,
        "states": {
            "idle": {"on": {"GO": "ver"}},
            "ver": {
                "invoke": {
                    "id": "ver",
                    "src": "svc",
                    "onDone": {"target": "#cyc.arm"},
                }
            },
            "arm": {
                "invoke": {
                    "id": "arm",
                    "src": "svc",
                    "onDone": {"target": "#cyc.ver"},
                }
            },
        },
    }

    def test_parity_with_sync(self) -> None:
        laps = {"s": 0, "a": 0}

        def logic(k: str) -> MachineLogic:
            def svc(i: Any, c: Any, e: Any) -> int:
                laps[k] += 1
                return 1

            return MachineLogic(services={"svc": svc})

        ds = _Drops()
        s = SyncInterpreter(_mk(self.CFG, logic=logic("s"))).use(ds).start()
        r = s.send("GO", wait=True)
        self.assertIsInstance(r.error, RunawayChainError)
        self.assertIn("chain_budget", ds.dropped)

        async def main() -> Any:
            da = _Drops()
            i = Interpreter(_mk(self.CFG, logic=logic("a"))).use(da)
            await i.start()
            await i.send("GO")
            await asyncio.sleep(0.5)
            out = (i.last_transition_ok, type(i.last_error), da.dropped)
            await i.stop()
            return out

        ok, err, dropped = _run(main())
        self.assertFalse(ok)
        self.assertIs(err, RunawayChainError)
        self.assertIn("chain_budget", dropped)
        # Same lap count on both engines: the budget is the same rule.
        self.assertEqual(laps["a"], laps["s"])

    def test_late_completion_after_idle_trip_is_delivered(self) -> None:
        # #120 guard: a trip that ends with nothing pending must not cut a
        # service that finishes later.
        cfg = {
            "id": "m",
            "maxIterations": 5,
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {"id": "svc", "src": "svc", "onDone": "ok"},
                    "on": {
                        "SPIN": {
                            "actions": [
                                {"type": "raise", "params": {"event": "SPIN"}}
                            ]
                        }
                    },
                },
                "ok": {},
            },
        }

        async def svc(i: Any, c: Any, e: Any) -> int:
            await asyncio.sleep(0.05)
            return 1

        async def main() -> Any:
            i = await Interpreter(
                _mk(cfg, logic=MachineLogic(services={"svc": svc}))
            ).start()
            await i.send("SPIN")
            await asyncio.sleep(0.4)
            v = i.value
            await i.stop()
            return v

        self.assertEqual(_run(main()), "ok")


# =============================================================================
# #169 — a snapshot from inside an entry action is refused on both engines
# =============================================================================
class TestEntryActionSnapshotRefused(_Quiet):
    CFG = {
        "id": "oms",
        "initial": "open",
        "context": {"filled_qty": 0},
        "states": {
            "open": {"on": {"FILL": "filled"}},
            "filled": {"entry": ["record_fill"]},
        },
    }

    def _logic(self, res: Dict[str, Any]) -> MachineLogic:
        def record_fill(i: Any, c: Any, e: Any, a: Any) -> None:
            c["filled_qty"] = 0
            try:
                i.get_persisted_snapshot()
                res["r"] = "ACCEPTED"
            except SnapshotMidStepError:
                res["r"] = "REFUSED"
            c["filled_qty"] = 100

        return MachineLogic(actions={"record_fill": record_fill})

    def test_sync(self) -> None:
        res: Dict[str, Any] = {}
        s = SyncInterpreter(_mk(self.CFG, logic=self._logic(res))).start()
        s.send("FILL")
        self.assertEqual(res["r"], "REFUSED")
        self.assertEqual(s.context["filled_qty"], 100)
        snap = s.get_persisted_snapshot()  # settled: fine
        self.assertEqual(snap["context"]["filled_qty"], 100)

    def test_async(self) -> None:
        res: Dict[str, Any] = {}

        async def main() -> int:
            i = Interpreter(_mk(self.CFG, logic=self._logic(res)))
            await i.start()
            await i.send("FILL", wait=True)
            qty = i.get_persisted_snapshot()["context"]["filled_qty"]
            await i.stop()
            return qty

        self.assertEqual(_run(main()), 100)
        self.assertEqual(res["r"], "REFUSED")


# =============================================================================
# #170 — a guard that CRASHED under "raise" is not `denied`
# =============================================================================
class TestCrashedGuardIsNotDenied(_Quiet):
    CFG = {
        "id": "g",
        "initial": "a",
        "guardErrorPolicy": "raise",
        "states": {
            "a": {"on": {"EV": {"target": "b", "guard": "raises"}}},
            "b": {},
        },
    }

    @staticmethod
    def _logic() -> MachineLogic:
        def raises(c: Any, e: Any) -> bool:
            raise RuntimeError("guard boom")

        return MachineLogic(guards={"raises": raises})

    def test_sync(self) -> None:
        s = SyncInterpreter(_mk(self.CFG, logic=self._logic())).start()
        try:
            r = s.send("EV", wait=True)
        except RuntimeError:
            r = None
        if r is not None:
            self.assertFalse(r.denied)
            self.assertIsInstance(r.error, RuntimeError)
        self.assertFalse(s._guard_denied_this_step)

    def test_async(self) -> None:
        async def main() -> Any:
            i = await Interpreter(_mk(self.CFG, logic=self._logic())).start()
            r = await i.send("EV", wait=True)
            await i.stop()
            return r

        r = _run(main())
        self.assertFalse(r.denied)
        self.assertIsInstance(r.error, RuntimeError)

    def test_false_guard_is_still_denied(self) -> None:
        logic = MachineLogic(guards={"raises": lambda c, e: False})
        s = SyncInterpreter(_mk(self.CFG, logic=logic)).start()
        self.assertTrue(s.send("EV", wait=True).denied)


# =============================================================================
# #171 — async start() returns with initial children registered / services done
# =============================================================================
class TestAsyncStartAwaitsInitialInvokes(_Quiet):
    def test_child_actor_registered_before_start_returns(self) -> None:
        child = {
            "id": "kid",
            "initial": "w",
            "states": {"w": {"on": {"POKE": "p"}}, "p": {}},
        }
        cfg = {
            "id": "par",
            "initial": "s",
            "states": {
                "s": {
                    "invoke": {"id": "kid", "src": "kidm"},
                    "on": {
                        "GO": {
                            "actions": [
                                {
                                    "type": "sendTo",
                                    "params": {"to": "kid", "event": "POKE"},
                                }
                            ]
                        }
                    },
                }
            },
        }

        async def main() -> Any:
            i = Interpreter(
                _mk(cfg, logic=MachineLogic(services={"kidm": _mk(child)}))
            )
            await i.start()
            actors = sorted(i._actors)
            await i.send("GO", wait=True)
            await asyncio.sleep(0.02)
            kid_value = i._actors["par:kid"].value
            await i.stop()
            return actors, kid_value

        actors, kid_value = _run(main())
        self.assertEqual(actors, ["par:kid"])
        self.assertEqual(kid_value, "p")

    def test_initial_plain_service_completion_precedes_first_event(
        self,
    ) -> None:
        # #149 requires `start()` to return while a plain service runs; the
        # parity #171 asks for is that its completion still lands AHEAD of
        # the first event the caller sends after `start()` (#116).
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {"id": "s", "src": "svc", "onDone": "b"},
                    "on": {"CANCEL": "c"},
                },
                "b": {"on": {"CANCEL": "b_cancelled"}},
                "b_cancelled": {},
                "c": {},
            },
        }
        logic = MachineLogic(services={"svc": lambda i, c, e: 1})
        s = SyncInterpreter(_mk(cfg, logic=logic)).start()
        s.send("CANCEL")
        self.assertEqual(s.value, "b_cancelled")

        async def main() -> Any:
            i = await Interpreter(_mk(cfg, logic=logic)).start()
            await i.send("CANCEL", wait=True)
            v = i.value
            await i.stop()
            return v

        self.assertEqual(_run(main()), "b_cancelled")


# =============================================================================
# #172 — threadsafe self-send counter balances on every outcome
# =============================================================================
class TestThreadsafeInFlightCounterBalances(_Quiet):
    def test_counter_zero_after_stop_with_undelivered_sends(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"EV": {"actions": []}}}},
        }

        async def main() -> int:
            i = await Interpreter(_mk(cfg)).start()
            for _ in range(5):
                i.send_threadsafe("EV", internal=True)
            await i.stop()
            await asyncio.sleep(0.05)
            return i._threadsafe_self_sends_in_flight

        self.assertEqual(_run(main()), 0)


# =============================================================================
# #173 — service_pool_size is public and honoured
# =============================================================================
class TestServicePoolSize(_Quiet):
    def test_default_and_override(self) -> None:
        cfg = {"id": "m", "initial": "a", "states": {"a": {}}}
        self.assertEqual(DEFAULT_SERVICE_POOL_SIZE, 4)
        i = Interpreter(_mk(cfg), service_pool_size=9)
        ex = i._get_service_executor()
        self.assertEqual(ex._max_workers, 9)  # type: ignore[attr-defined]
        ex.shutdown(wait=False)
        with self.assertRaises(ValueError):
            Interpreter(_mk(cfg), service_pool_size=0)

    def test_nine_concurrent_plain_services_run_in_one_wave(self) -> None:
        regions = {
            f"r{k}": {
                "initial": "w",
                "states": {
                    "w": {
                        "invoke": {
                            "id": f"s{k}",
                            "src": "svc",
                            "onDone": "d",
                        }
                    },
                    "d": {"type": "final"},
                },
            }
            for k in range(9)
        }
        cfg = {"id": "fan", "type": "parallel", "states": regions}

        def svc(i: Any, c: Any, e: Any) -> int:
            time.sleep(0.15)
            return 1

        async def main() -> float:
            i = Interpreter(
                _mk(cfg, logic=MachineLogic(services={"svc": svc})),
                service_pool_size=9,
            )
            t0 = time.monotonic()
            await i.start()
            while not all(v == "d" for v in i.value.values()):
                await asyncio.sleep(0.005)
            took = time.monotonic() - t0
            await i.stop()
            return took

        # with the old pool of 4 this is >= 3 waves (0.45 s)
        self.assertLess(_run(main()), 0.15 * 2.5)


# =============================================================================
# #175 — receipts racing stop(): "ok" iff the event was applied
# =============================================================================
class TestReceiptsRacingStop(_Quiet):
    def test_ok_receipts_equal_applied_events(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {
                "a": {"on": {"EV": {"target": "b", "actions": ["slow"]}}},
                "b": {"on": {"EV": {"target": "a", "actions": ["slow"]}}},
            },
        }

        async def slow(i: Any, c: Any, e: Any, a: Any) -> None:
            await asyncio.sleep(0.001)
            c["n"] += 1

        async def trial(delay: float) -> None:
            i = await Interpreter(
                _mk(cfg, logic=MachineLogic(actions={"slow": slow}))
            ).start()
            ev = Event("EV")  # one instance, reused: the #175 shape
            tasks = [
                asyncio.ensure_future(i.send(ev, wait=True)) for _ in range(12)
            ]
            await asyncio.sleep(delay)
            await i.stop()
            applied = i.context["n"]
            res = await asyncio.gather(*tasks)
            ok = sum(1 for r in res if r.error is None)
            stopped = sum(
                1 for r in res if isinstance(r.error, InterpreterStoppedError)
            )
            self.assertEqual(ok, applied)
            self.assertEqual(ok + stopped, 12)

        async def main() -> None:
            for d in (0.0, 0.002, 0.005, 0.009, 0.015):
                await trial(d)

        _run(main())


if __name__ == "__main__":
    unittest.main()


# =============================================================================
# #157 (reopened) — loop-side RAISE refusals from send_threadsafe are observable
# =============================================================================
class TestThreadsafeLoopSideRefusalObservable(_Quiet):
    def test_warning_and_hook_for_loop_side_refusal(self) -> None:
        from src.xstate_statemachine import OverflowPolicy, QueueOverflowError

        cfg = {
            "id": "ctr",
            "initial": "a",
            "states": {"a": {"on": {"PING": {"actions": ["slow"]}}}},
        }

        async def slow(i: Any, c: Any, e: Any, a: Any) -> None:
            await asyncio.sleep(0.05)

        pkg = SyncInterpreter.__module__.rsplit(".", 1)[0]
        records: List[logging.LogRecord] = []

        class _Cap(logging.Handler):
            def emit(self, r: logging.LogRecord) -> None:
                records.append(r)

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(
                _mk(cfg, logic=MachineLogic(actions={"slow": slow})),
                max_queue_size=2,
                overflow_policy=OverflowPolicy.RAISE,
            ).use(d)
            await i.start()
            for _ in range(2):
                await i.send("PING")
            # The optimistic call-site check refuses a VISIBLY full inbox on
            # the producer thread; the reopen is about the racing producer
            # whose check passed and who is refused ON THE LOOP. Drive that
            # path directly.
            futs = [
                asyncio.run_coroutine_threadsafe(_deliver_full(i), i._loop)
                for _ in range(5)
            ]
            refused = 0
            await asyncio.sleep(0.02)
            for f in futs:
                if f.done() and isinstance(f.exception(), QueueOverflowError):
                    refused += 1
            out = (refused, list(d.dropped))
            await i.stop()
            return out

        async def _deliver_full(i: Any) -> None:
            i._enqueue_from_thread(Event("PING"))

        logging.disable(logging.NOTSET)
        lg = logging.getLogger(pkg)
        h = _Cap()
        lg.addHandler(h)
        old = lg.level
        lg.setLevel(logging.WARNING)
        try:
            refused, dropped = _run(main())
        finally:
            lg.removeHandler(h)
            lg.setLevel(old)
            logging.disable(logging.CRITICAL)

        self.assertGreater(refused, 0)
        self.assertEqual(dropped.count("queue_full"), refused)
        warned = [
            r
            for r in records
            if r.levelno == logging.WARNING and "refused" in r.getMessage()
        ]
        self.assertEqual(len(warned), refused)
