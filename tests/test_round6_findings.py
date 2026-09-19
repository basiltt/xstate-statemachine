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
    Interpreter,
    MachineLogic,
    RunawayChainError,
    SyncInterpreter,
    create_machine,
)
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


if __name__ == "__main__":
    unittest.main()
