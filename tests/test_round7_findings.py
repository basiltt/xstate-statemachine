"""Regression tests for the round-7 re-verification findings (#179–#190;
reopened #167 / #168 / #175).

One class per issue. Every test that involves a service or an action is
parametrised over how it is spelled (``def`` / ``async def``) -- the
round-6 pins declared ``def`` only and were structurally blind to the
coroutine lane (#179). Where an issue is about engine parity the test runs
BOTH engines. The suite is `unittest`-based like its siblings; the
parametrisation is `subTest`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import time
import unittest
import warnings
from typing import Any, Callable, Dict, List, Tuple

from src.xstate_statemachine import (
    Event,
    Interpreter,
    MachineLogic,
    RunawayChainError,
    SnapshotCorruptError,
    SnapshotDriftError,
    SnapshotMidStepError,
    SyncInterpreter,
    UnhandledEventError,
    UnknownEventError,
    create_machine,
)
from src.xstate_statemachine.exceptions import InterpreterStoppedError
from src.xstate_statemachine.interpreter import DEFAULT_CHILDREN_TIMEOUT
from src.xstate_statemachine.plugins import PluginBase

#: The package's logger root as IMPORTED here (tests import via `src.`).
_PKG_LOGGER = SyncInterpreter.__module__.rsplit(".", 1)[0]

#: Service / action spellings every behavioural test is run under (#179).
KINDS: Tuple[str, ...] = ("def", "async def")


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


def _svc(kind: str, body: Callable[[], Any]) -> Callable[..., Any]:
    """A service spelled *kind* that runs *body* and returns its result."""
    if kind == "def":

        def plain(i: Any, c: Any, e: Any) -> Any:
            return body()

        return plain

    async def coro(i: Any, c: Any, e: Any) -> Any:
        await asyncio.sleep(0)
        return body()

    return coro


def _act(kind: str, body: Callable[[Any, Any], None]) -> Callable[..., Any]:
    """An action spelled *kind* that runs ``body(interpreter, context)``."""
    if kind == "def":

        def plain(i: Any, c: Any, e: Any, a: Any) -> None:
            body(i, c)

        return plain

    async def coro(i: Any, c: Any, e: Any, a: Any) -> None:
        await asyncio.sleep(0)
        body(i, c)

    return coro


class _Drops(PluginBase):
    def __init__(self) -> None:
        self.dropped: List[str] = []

    def on_event_dropped(self, interp: Any, event: Any, reason: str) -> None:
        self.dropped.append(reason)


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


# =============================================================================
# #179 (+ reopened #167 / #168) — every service kind is charged on one lane
# =============================================================================
class TestInvokeCycleBoundedForEveryServiceKind(_Quiet):
    """`a -> done -> b -> done -> a` trips at ~maxIterations laps, whatever
    the service is spelled as, on the async engine; the sync engine (which
    only runs `def`) is the reference."""

    LIMIT = 20
    CFG = {
        "id": "cyc",
        "initial": "idle",
        "maxIterations": LIMIT,
        "states": {
            "idle": {"on": {"GO": "a"}},
            "a": {"invoke": {"id": "sa", "src": "svc", "onDone": "b"}},
            "b": {"invoke": {"id": "sb", "src": "svc", "onDone": "a"}},
        },
    }

    def _laps(self, kind: str) -> Tuple[int, Any, List[str]]:
        laps = [0]

        def bump() -> int:
            laps[0] += 1
            return 1

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(
                _mk(
                    self.CFG,
                    logic=MachineLogic(services={"svc": _svc(kind, bump)}),
                )
            ).use(d)
            await i.start()
            await i.send("GO")
            await asyncio.sleep(0.5)
            out = (laps[0], type(i.last_error), list(d.dropped))
            await i.stop()
            return out

        return _run(main())

    def test_invoke_cycle_is_bounded_by_max_iterations(self) -> None:
        laps_sync = [0]

        def bump() -> int:
            laps_sync[0] += 1
            return 1

        s = SyncInterpreter(
            _mk(
                self.CFG,
                logic=MachineLogic(services={"svc": _svc("def", bump)}),
            )
        ).start()
        r = s.send("GO", wait=True)
        self.assertIsInstance(r.error, RunawayChainError)

        for kind in KINDS:
            with self.subTest(kind=kind):
                laps, err, dropped = self._laps(kind)
                self.assertIs(err, RunawayChainError)
                self.assertIn("chain_budget", dropped)
                # Bounded: within a couple of laps of the sync engine.
                self.assertLessEqual(abs(laps - laps_sync[0]), 2)
                self.assertLess(laps, 3 * self.LIMIT)

    def test_invoke_done_event_is_charged_regardless_of_kind(self) -> None:
        # Lane assertion: a completion that lands while the chain is open
        # raises `_raise_depth`, for both kinds.
        cfg = {
            "id": "one",
            "initial": "a",
            "maxIterations": 50,
            "states": {
                "a": {"invoke": {"id": "s", "src": "svc", "onDone": "b"}},
                "b": {"invoke": {"id": "t", "src": "svc", "onDone": "c"}},
                "c": {},
            },
        }
        for kind in KINDS:
            with self.subTest(kind=kind):
                seen: List[int] = []

                def probe(i: Any, c: Any, e: Any, a: Any) -> None:
                    seen.append(i._raise_depth)

                cfg2 = json.loads(json.dumps(cfg))
                cfg2["states"]["c"]["entry"] = ["probe"]

                async def main() -> None:
                    i = await Interpreter(
                        create_machine(
                            cfg2,
                            logic=MachineLogic(
                                services={"svc": _svc(kind, lambda: 1)},
                                actions={"probe": probe},
                            ),
                        )
                    ).start()
                    await asyncio.sleep(0.2)
                    self.assertEqual(i.value, "c")
                    await i.stop()

                _run(main())
                # #201: the FIRST completion of a chain that starts from the
                # initial state is the SEED (user standing, like the sync
                # drain's seed rule); its descendant -- the second
                # completion -- is generated event #1. So `c` is entered at
                # depth 1, matching the sync engine's lap count exactly.
                self.assertEqual(seen, [1])

    def test_independent_completions_do_not_accumulate(self) -> None:
        # Converse: a long-running service beside heavy independent traffic
        # (each event raising once) never trips -- #180's provenance rule
        # and #179's "this step armed nothing outstanding" reset together.
        cfg = {
            "id": "m",
            "initial": "a",
            "maxIterations": 20,
            "states": {
                "a": {
                    "invoke": {"id": "long", "src": "long", "onDone": "done"},
                    "on": {
                        "EV": {
                            "actions": [
                                {"type": "raise", "params": {"event": "INNER"}}
                            ]
                        },
                        "INNER": {"actions": []},
                    },
                },
                "done": {},
            },
        }

        async def long(i: Any, c: Any, e: Any) -> int:
            await asyncio.sleep(0.3)
            return 1

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(
                _mk(cfg, logic=MachineLogic(services={"long": long}))
            ).use(d)
            await i.start()
            for _ in range(300):
                await i.send("EV", wait=True)
            await asyncio.sleep(0.4)
            out = (d.dropped, i.last_error, i.value)
            await i.stop()
            return out

        dropped, err, value = _run(main())
        self.assertEqual(dropped, [])
        self.assertIsNone(err)
        self.assertEqual(value, "done")

    def test_timer_driven_poller_never_trips(self) -> None:
        # fetch -> onDone -> wait(after) -> fetch is a legitimate periodic
        # process, not a runaway: the timer is external time passing.
        cfg = {
            "id": "p",
            "initial": "fetch",
            "maxIterations": 10,
            "states": {
                "fetch": {
                    "invoke": {"id": "f", "src": "svc", "onDone": "wait"}
                },
                "wait": {"after": {5: "fetch"}},
            },
        }
        for kind in KINDS:
            with self.subTest(kind=kind):
                laps = [0]

                def bump() -> int:
                    laps[0] += 1
                    return 1

                async def main() -> Any:
                    d = _Drops()
                    i = Interpreter(
                        _mk(
                            cfg,
                            logic=MachineLogic(
                                services={"svc": _svc(kind, bump)}
                            ),
                        )
                    ).use(d)
                    await i.start()
                    await asyncio.sleep(0.4)
                    out = (laps[0], d.dropped, i.last_error)
                    await i.stop()
                    return out

                n, dropped, err = _run(main())
                self.assertGreater(n, 10)
                # stop() may report the in-flight completion as "stopped";
                # what must never appear is a chain-budget cut.
                self.assertNotIn("chain_budget", dropped)
                self.assertIsNone(err)


class TestRollbackReinvokeCycleBoundedForEveryKind(_Quiet):
    """#167 reopen: `actionErrorPolicy: rollback` + `invoke.onDone` whose
    entry fails re-arms the invoke; bounded for both service kinds."""

    CFG = {
        "id": "spin",
        "actionErrorPolicy": "rollback",
        "maxIterations": 20,
        "initial": "starting",
        "context": {},
        "states": {
            "starting": {
                "invoke": {"id": "s", "src": "svc", "onDone": "recording"}
            },
            "recording": {"entry": ["boom"]},
        },
    }

    def test_rollback_reinvoke_cycle_is_bounded(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                calls = [0]

                def bump() -> int:
                    calls[0] += 1
                    return 1

                def boom(*a: Any) -> None:
                    raise RuntimeError("boom")

                async def main() -> Any:
                    d = _Drops()
                    i = Interpreter(
                        _mk(
                            self.CFG,
                            logic=MachineLogic(
                                actions={"boom": boom},
                                services={"svc": _svc(kind, bump)},
                            ),
                        )
                    ).use(d)
                    await i.start()
                    await asyncio.sleep(0.4)
                    first = calls[0]
                    await asyncio.sleep(0.2)
                    out = (
                        first,
                        calls[0],
                        i.status,
                        type(i.last_error),
                        d.dropped,
                    )
                    await i.stop()
                    return out

                first, later, status, err, dropped = _run(main())
                self.assertEqual(status, "running")
                self.assertLess(first, 3 * 20)
                self.assertEqual(first, later, "cycle must stop, not spin")
                self.assertIs(err, RunawayChainError)
                self.assertIn("chain_budget", dropped)

    def test_configuration_never_empty_while_running(self) -> None:
        # #179 consequence 1: a resolved `send(wait=True)` on a running
        # machine never leaves an empty configuration behind.
        cfg = {
            "id": "m",
            "initial": "idle",
            "maxIterations": 10,
            "states": {
                "idle": {"on": {"GO": "a"}},
                "a": {"invoke": {"id": "sa", "src": "svc", "onDone": "b"}},
                "b": {"invoke": {"id": "sb", "src": "svc", "onDone": "a"}},
            },
        }
        for kind in KINDS:
            with self.subTest(kind=kind):

                async def main() -> Any:
                    i = await Interpreter(
                        _mk(
                            cfg,
                            logic=MachineLogic(
                                services={"svc": _svc(kind, lambda: 1)}
                            ),
                        )
                    ).start()
                    await i.send("GO", wait=True)
                    await asyncio.sleep(0.3)
                    out = (i.status, sorted(i.current_state_ids))
                    await i.stop()
                    return out

                status, ids = _run(main())
                self.assertEqual(status, "running")
                self.assertTrue(ids, "running machine must have a leaf")


# =============================================================================
# #180 — an EXTERNAL `send(priority=True)` is never charged
# =============================================================================
class TestExternalPrioritySendNeverCharged(_Quiet):
    CFG = {
        "id": "ext",
        "maxIterations": 25,
        "initial": "up",
        "context": {"n": 0},
        "states": {"up": {"on": {"TICK": {"actions": ["work"]}}}},
    }

    def _load(self, kind: str, priority: bool) -> Tuple[int, List[str]]:
        processed = [0]

        def body(i: Any, c: Any) -> None:
            processed[0] += 1

        if kind == "def":
            work: Callable[..., Any] = _act("def", body)
        else:

            async def work(i: Any, c: Any, e: Any, a: Any) -> None:  # type: ignore[misc]
                processed[0] += 1
                # A real await keeps the loop mid-macrostep while the next
                # external send lands (the #180 condition). `sleep(0)`,
                # not a timed sleep: Windows' 15 ms timer floor would make
                # 400 timed sleeps take seconds and mask the assertion.
                await asyncio.sleep(0)

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(
                _mk(self.CFG, logic=MachineLogic(actions={"work": work}))
            ).use(d)
            await i.start()
            for _ in range(400):
                i.send("TICK", priority=priority)
                await asyncio.sleep(0)
            deadline = time.monotonic() + 10
            while (
                processed[0] < 400 - len(d.dropped)
                and time.monotonic() < deadline
            ):
                await asyncio.sleep(0.01)
            out = (processed[0], list(d.dropped))
            await i.stop()
            return out

        return _run(main())

    def test_external_priority_send_is_never_charged_to_chain_budget(
        self,
    ) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                n, dropped = self._load(kind, priority=True)
                self.assertNotIn("chain_budget", dropped)
                self.assertEqual(n, 400)

    def test_priority_lane_matches_non_priority_drop_count(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                _, with_p = self._load(kind, priority=True)
                _, without = self._load(kind, priority=False)
                self.assertEqual(with_p.count("chain_budget"), 0)
                self.assertEqual(with_p, without)

    def test_self_raised_chain_still_trips_with_external_priority(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "maxIterations": 5,
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "SPIN": {
                            "actions": [
                                {"type": "raise", "params": {"event": "SPIN"}}
                            ]
                        },
                        "TICK": {"actions": []},
                    }
                }
            },
        }

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(_mk(cfg)).use(d)
            await i.start()
            await i.send("SPIN")
            for _ in range(20):
                i.send("TICK", priority=True)
                await asyncio.sleep(0)
            await asyncio.sleep(0.1)
            out = d.dropped.count("chain_budget")
            await i.stop()
            return out

        # The trip is observable through the hook; `last_error` is per step
        # and the TICKs that followed succeeded.
        self.assertGreater(_run(main()), 0)

    def test_sync_engine_priority_is_external_too(self) -> None:
        d = _Drops()
        s = (
            SyncInterpreter(
                _mk(
                    self.CFG,
                    logic=MachineLogic(actions={"work": lambda *a: None}),
                )
            )
            .use(d)
            .start()
        )
        for _ in range(100):
            s.send("TICK")
        self.assertNotIn("chain_budget", d.dropped)


# =============================================================================
# #181 — `start()` bounds the wait for invoked children
# =============================================================================
class TestStartBoundsChildBringup(_Quiet):
    def _cfg(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        child = {
            "id": "kid",
            "initial": "w",
            "states": {"w": {"entry": ["slow"], "on": {"POKE": "p"}}, "p": {}},
        }
        parent = {
            "id": "par",
            "initial": "s",
            "states": {
                "s": {
                    "invoke": {"id": "kid", "src": "kidm"},
                    "on": {"EV": {"actions": []}},
                }
            },
        }
        return parent, child

    def test_start_returns_within_bringup_timeout(self) -> None:
        parent, child = self._cfg()
        for kind in KINDS:
            with self.subTest(kind=kind):
                if kind == "def":
                    slow: Callable[..., Any] = lambda i, c, e, a: time.sleep(
                        0.05
                    )
                else:

                    async def slow(i: Any, c: Any, e: Any, a: Any) -> None:  # type: ignore[misc]
                        await asyncio.sleep(3.0)

                async def main() -> Any:
                    kid = create_machine(
                        child, logic=MachineLogic(actions={"slow": slow})
                    )
                    i = Interpreter(
                        _mk(parent, logic=MachineLogic(services={"kidm": kid}))
                    )
                    t0 = time.monotonic()
                    await i.start(children_timeout=0.2)
                    took = time.monotonic() - t0
                    status = i.status
                    r = await asyncio.wait_for(i.send("EV", wait=True), 2)
                    await asyncio.wait_for(i.stop(), 5)
                    return took, status, r.error

                took, status, err = _run(main())
                self.assertLess(took, 1.0)
                self.assertEqual(status, "running")
                self.assertIsNone(err)

    def test_bringup_timeout_is_observable(self) -> None:
        parent, child = self._cfg()

        async def slow(i: Any, c: Any, e: Any, a: Any) -> None:
            await asyncio.sleep(1.0)

        cap = _Capture()
        logging.disable(logging.NOTSET)
        lg = logging.getLogger(_PKG_LOGGER)
        lg.addHandler(cap)
        old = lg.level
        lg.setLevel(logging.WARNING)
        try:

            async def main() -> None:
                kid = create_machine(
                    child, logic=MachineLogic(actions={"slow": slow})
                )
                i = Interpreter(
                    _mk(parent, logic=MachineLogic(services={"kidm": kid}))
                )
                await i.start(children_timeout=0.1)
                await i.stop()

            _run(main())
        finally:
            lg.removeHandler(cap)
            lg.setLevel(old)
            logging.disable(logging.CRITICAL)
        self.assertTrue(
            any("still starting" in r.getMessage() for r in cap.records)
        )

    def test_fast_child_still_addressable_after_start(self) -> None:
        parent, child = self._cfg()

        async def main() -> Any:
            kid = create_machine(
                child, logic=MachineLogic(actions={"slow": lambda *a: None})
            )
            i = Interpreter(
                _mk(parent, logic=MachineLogic(services={"kidm": kid}))
            )
            await i.start()
            actors = sorted(i._actors)
            await i.stop()
            return actors

        self.assertEqual(_run(main()), ["par:kid"])

    def test_default_is_bounded(self) -> None:
        self.assertIsNotNone(DEFAULT_CHILDREN_TIMEOUT)
        self.assertGreater(DEFAULT_CHILDREN_TIMEOUT, 0)


# =============================================================================
# #182 / #187 — the in-flight flag covers start() and every action hook
# =============================================================================
class TestInFlightFlagCoversStartAndHooks(_Quiet):
    CFG = {
        "id": "oms",
        "initial": "filled",
        "context": {"filled_qty": 0, "avg_px": 0},
        "states": {"filled": {"entry": ["record"]}},
    }

    def test_snapshot_from_initial_entry_action_is_refused(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                res: Dict[str, Any] = {}

                def body(i: Any, c: Any) -> None:
                    c["filled_qty"] = 100
                    try:
                        i.get_persisted_snapshot()
                        res["r"] = "ACCEPTED"
                    except SnapshotMidStepError:
                        res["r"] = "REFUSED"
                    c["avg_px"] = 101

                logic = MachineLogic(actions={"record": _act(kind, body)})
                if kind == "def":
                    s = SyncInterpreter(_mk(self.CFG, logic=logic)).start()
                    self.assertEqual(res["r"], "REFUSED")
                    s.stop()
                    res.clear()

                async def main() -> Any:
                    i = await Interpreter(_mk(self.CFG, logic=logic)).start()
                    flag = i._processing
                    snap = i.get_persisted_snapshot()
                    await i.stop()
                    return flag, snap["context"]

                flag, ctx = _run(main())
                self.assertEqual(res["r"], "REFUSED")
                self.assertFalse(flag, "flag restored after start()")
                self.assertEqual(ctx, {"filled_qty": 100, "avg_px": 101})

    def test_step_in_flight_is_true_during_initial_descent(self) -> None:
        seen: List[bool] = []

        def probe(i: Any, c: Any, e: Any, a: Any) -> None:
            seen.append(i._step_in_flight())

        logic = MachineLogic(actions={"record": probe})
        SyncInterpreter(_mk(self.CFG, logic=logic)).start().stop()

        async def main() -> None:
            i = await Interpreter(_mk(self.CFG, logic=logic)).start()
            await i.stop()

        _run(main())
        self.assertEqual(seen, [True, True])

    def test_processing_flag_restored_after_start_raises(self) -> None:
        def boom(*a: Any) -> None:
            raise RuntimeError("entry boom")

        cfg = json.loads(json.dumps(self.CFG))
        cfg["actionErrorPolicy"] = "fail"

        async def main() -> Any:
            i = Interpreter(
                _mk(cfg, logic=MachineLogic(actions={"record": boom}))
            )
            try:
                await i.start()
            except Exception:
                pass
            return i._processing

        self.assertFalse(_run(main()))

    def test_snapshot_from_on_action_execute_is_refused_on_both_engines(
        self,
    ) -> None:
        cfg = {
            "id": "ord",
            "initial": "one",
            "context": {"n": 0},
            "states": {
                "one": {
                    "entry": ["act"],
                    "on": {"STEP": {"target": "two", "actions": ["act"]}},
                },
                "two": {"entry": ["act"]},
            },
        }
        rows: List[str] = []

        class Grab(PluginBase):
            def on_action_execute(self, interp: Any, action_def: Any) -> None:
                try:
                    interp.get_persisted_snapshot()
                    rows.append("RETURNED")
                except SnapshotMidStepError:
                    rows.append("REFUSED")

        for kind in KINDS:
            with self.subTest(kind=kind):
                rows.clear()
                logic = MachineLogic(
                    actions={"act": _act(kind, lambda i, c: None)}
                )

                async def main() -> None:
                    i = Interpreter(_mk(cfg, logic=logic)).use(Grab())
                    await i.start()
                    await i.send("STEP", wait=True)
                    await i.stop()

                _run(main())
                self.assertTrue(rows)
                self.assertEqual(set(rows), {"REFUSED"})
        rows.clear()
        s = (
            SyncInterpreter(
                _mk(cfg, logic=MachineLogic(actions={"act": lambda *a: None}))
            )
            .use(Grab())
            .start()
        )
        s.send("STEP")
        self.assertEqual(set(rows), {"REFUSED"})


# =============================================================================
# #183 / #184 — a child mid-step is never harvested half-applied, and the
# wait never spins the event loop
# =============================================================================
class TestChildMidStepSnapshot(_Quiet):
    CHILD = {
        "id": "kid",
        "initial": "x",
        "context": {"q": 0, "p": 0},
        "states": {"x": {"on": {"GO": "y"}}, "y": {"entry": ["pair"]}},
    }
    PARENT = {
        "id": "par",
        "initial": "s",
        "states": {"s": {"invoke": {"id": "kid", "src": "kidm"}}},
    }

    def test_root_snapshot_refuses_while_async_child_is_mid_step(self) -> None:
        box: Dict[str, asyncio.Event] = {}

        async def pair(i: Any, c: Any, e: Any, a: Any) -> None:
            c["q"] = 100
            box["started"].set()
            await box["gate"].wait()
            c["p"] = 101

        async def main() -> Any:
            # Created INSIDE the running loop: on 3.9 an `asyncio.Event()`
            # built at test-definition time binds to no loop and raises.
            box["gate"], box["started"] = asyncio.Event(), asyncio.Event()
            gate, started = box["gate"], box["started"]
            kid = create_machine(
                self.CHILD, logic=MachineLogic(actions={"pair": pair})
            )
            i = await Interpreter(
                _mk(self.PARENT, logic=MachineLogic(services={"kidm": kid}))
            ).start()
            child = i._actors["par:kid"]
            await child.send("GO")
            await started.wait()
            t0 = time.monotonic()
            try:
                i.get_persisted_snapshot()
                verdict = "ACCEPTED"
            except SnapshotMidStepError as exc:
                verdict = "REFUSED" if exc.child else "REFUSED-root"
            blocked = time.monotonic() - t0
            gate.set()
            await asyncio.sleep(0.02)
            settled = i.get_persisted_snapshot()["actors"]["par:kid"][
                "snapshot"
            ]["context"]
            await i.stop()
            return verdict, blocked, settled

        verdict, blocked, settled = _run(main())
        self.assertEqual(verdict, "REFUSED")
        self.assertLess(blocked, 0.1, "must not spin the loop (#184)")
        self.assertEqual(settled, {"q": 100, "p": 101})

    def test_child_blob_context_is_never_half_applied(self) -> None:
        # Property form: a child stepping on its own thread (non-blocking
        # sync actor) is waited for; every accepted blob has both halves.
        child = {
            "id": "kid",
            "initial": "x",
            "context": {"q": 0, "p": 0},
            "states": {
                "x": {"on": {"GO": {"target": "x", "actions": ["pair"]}}}
            },
        }
        parent = {
            "id": "par",
            "initial": "s",
            "context": {},
            "states": {
                "s": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "w"},
                        }
                    ]
                }
            },
        }

        def pair(i: Any, c: Any, e: Any, a: Any) -> None:
            c["q"] += 1
            time.sleep(0.002)
            c["p"] += 1

        kid_logic = MachineLogic(actions={"pair": pair})
        p = SyncInterpreter(
            create_machine(
                parent,
                logic=MachineLogic(
                    services={
                        "kid": lambda i, c, e: create_machine(
                            child, logic=kid_logic
                        )
                    }
                ),
            )
        ).start()
        self.addCleanup(p.stop)
        kid = p._actors["par:w"]
        stop = threading.Event()

        def driver() -> None:
            # Paced: the child steps for ~2 ms every ~3 ms on another
            # thread, so a parent snapshot catches it mid-step often and
            # the bounded wait CAN let it settle.
            while not stop.is_set():
                kid.send("GO")
                time.sleep(0.001)

        th = threading.Thread(target=driver, daemon=True)
        th.start()
        torn = 0
        accepted = 0
        refused = 0
        try:
            for _ in range(150):
                try:
                    blob = p.get_persisted_snapshot()
                except SnapshotMidStepError:
                    refused += 1
                    continue
                accepted += 1
                ctx = blob["actors"][kid.id]["snapshot"]["context"]
                if ctx["q"] != ctx["p"]:
                    torn += 1
        finally:
            stop.set()
            th.join(timeout=2)
        self.assertGreater(accepted, 0)
        self.assertEqual(
            torn, 0, f"{torn} torn of {accepted} ({refused} refused)"
        )

    def test_settled_hierarchical_snapshot_still_captures_children(
        self,
    ) -> None:
        async def main() -> Any:
            kid = create_machine(
                self.CHILD,
                logic=MachineLogic(actions={"pair": lambda *a: None}),
            )
            i = await Interpreter(
                _mk(self.PARENT, logic=MachineLogic(services={"kidm": kid}))
            ).start()
            snap = i.get_persisted_snapshot()
            await i.stop()
            return sorted(snap["actors"])

        self.assertEqual(_run(main()), ["par:kid"])


# =============================================================================
# #185 — a versioned payload without machine_hash is drift, not a bypass
# =============================================================================
class TestMissingMachineHashIsDrift(_Quiet):
    CFG = {"id": "m", "initial": "a", "states": {"a": {}, "b": {}}}

    def _blob(self) -> Dict[str, Any]:
        s = SyncInterpreter(_mk(self.CFG)).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        return blob

    def test_null_and_absent_hash_are_refused_on_versioned_payload(
        self,
    ) -> None:
        for mutate in ("null", "absent"):
            with self.subTest(mutate=mutate):
                blob = self._blob()
                if mutate == "null":
                    blob["machine_hash"] = None
                else:
                    del blob["machine_hash"]
                with self.assertRaises(SnapshotDriftError):
                    SyncInterpreter.from_snapshot(
                        json.dumps(blob), _mk(self.CFG)
                    )
                # explicit opt-out still works
                r = SyncInterpreter.from_snapshot(
                    json.dumps(blob), _mk(self.CFG), verify_machine_hash=False
                )
                self.assertEqual(r.value, "a")

    def test_legacy_v0_payload_still_accepted(self) -> None:
        blob = {"status": "running", "context": {}, "state_ids": ["m.a"]}
        r = SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))
        self.assertEqual(r.value, "a")

    def test_honest_hash_accepted_wrong_hash_refused(self) -> None:
        blob = self._blob()
        SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))
        blob["machine_hash"] = "0" * 16
        with self.assertRaises(SnapshotDriftError):
            SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))


# =============================================================================
# #186 — a contradictory `configuration` is corrupt, not a silent fallback
# =============================================================================
class TestContradictoryConfigurationRefused(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "states": {"a": {}, "b": {}},
    }

    def _blob(self) -> Dict[str, Any]:
        s = SyncInterpreter(_mk(self.CFG)).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        return blob

    def test_empty_configuration_with_state_ids_is_refused(self) -> None:
        blob = self._blob()
        blob["configuration"] = []
        with self.assertRaises(SnapshotCorruptError):
            SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))

    def test_configuration_missing_a_leaf_is_refused(self) -> None:
        blob = self._blob()
        blob["configuration"] = ["m", "m.b"]  # state_ids still says m.a
        with self.assertRaises(SnapshotCorruptError):
            SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))

    def test_agreeing_fields_restore_and_v0_may_omit_configuration(
        self,
    ) -> None:
        blob = self._blob()
        SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))
        # #198: a VERSIONED blob must carry `configuration`; only a v0
        # (pre-`configuration`) payload may restore from `state_ids` alone.
        del blob["configuration"]
        with self.assertRaises(SnapshotCorruptError):
            SyncInterpreter.from_snapshot(json.dumps(blob), _mk(self.CFG))
        v0 = {"status": "running", "context": {}, "state_ids": ["m.a"]}
        r = SyncInterpreter.from_snapshot(json.dumps(v0), _mk(self.CFG))
        self.assertEqual(r.value, "a")


# =============================================================================
# #188 — sync per-step scopes are cleared on the fire-and-forget path
# =============================================================================
class TestSyncDeferredThisStepCleared(_Quiet):
    def test_no_accumulation_across_wait_false_sends(self) -> None:
        cfg = {
            "id": "d",
            "initial": "a",
            "onUnhandled": "defer",
            "states": {"a": {"on": {"KNOWN": {}}}},
        }
        s = SyncInterpreter(_mk(cfg)).start()
        for _ in range(500):
            s.send("LATER")
        self.assertLessEqual(len(s._deferred_this_step), 1)
        r = s.send("KNOWN", wait=True)
        self.assertFalse(r.deferred, "receipt must not be contaminated")


# =============================================================================
# #189 — the onUnhandled: "error" kill is visible on the sender's receipt
# =============================================================================
class TestUnhandledErrorKillVisibleOnReceipt(_Quiet):
    CFG = {
        "id": "cp",
        "initial": "a",
        "onUnhandled": "error",
        "states": {"a": {"on": {"KNOWN": {}}}},
    }

    def test_sync_receipt_carries_the_error(self) -> None:
        s = SyncInterpreter(_mk(self.CFG)).start()
        r = s.send("NOPE", wait=True)
        self.assertIsInstance(r.error, UnhandledEventError)
        self.assertFalse(r.changed)
        self.assertEqual(s.status, "error")

    def test_async_receipt_carries_the_error(self) -> None:
        async def main() -> Any:
            i = await Interpreter(_mk(self.CFG)).start()
            r = await i.send("NOPE", wait=True)
            status = i.status
            await i.stop()
            return r, status

        r, status = _run(main())
        self.assertIsInstance(r.error, UnhandledEventError)
        self.assertEqual(status, "error")

    def test_known_event_receipt_is_still_clean(self) -> None:
        s = SyncInterpreter(_mk(self.CFG)).start()
        r = s.send("KNOWN", wait=True)
        self.assertIsNone(r.error)


# =============================================================================
# #190 — a "*" handler does not defeat strict event-name enforcement
# =============================================================================
class TestWildcardDoesNotDefeatStrict(_Quiet):
    CFG = {
        "id": "w",
        "initial": "a",
        "states": {"a": {"on": {"KNOWN": {}, "*": {"actions": ["log"]}}}},
    }

    def test_wildcard_does_not_defeat_is_known_event(self) -> None:
        m = _mk(self.CFG)
        self.assertFalse(m.is_known_event("UNDECLARED_NAME", user_sent=True))
        self.assertTrue(m.is_known_event("KNOWN"))
        # dispatch question: the wildcard does catch it
        self.assertTrue(
            m.is_known_event("UNDECLARED_NAME", wildcard_matches=True)
        )

    def test_strict_true_rejects_undeclared_name_with_wildcard_present(
        self,
    ) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                cfg = json.loads(json.dumps(self.CFG))
                cfg["states"]["a"]["invoke"] = {"id": "s", "src": "svc"}
                logic = MachineLogic(
                    actions={"log": lambda *a: None},
                    services={"svc": _svc(kind, lambda: 1)},
                )
                if kind == "def":
                    s = SyncInterpreter(
                        _mk(cfg, logic=logic), strict=True
                    ).start()
                    with self.assertRaises(UnknownEventError):
                        s.send("CANCLE")
                    s.stop()

                async def main() -> None:
                    i = await Interpreter(
                        _mk(cfg, logic=logic), strict=True
                    ).start()
                    try:
                        with self.assertRaises(UnknownEventError):
                            await i.send("CANCLE")
                    finally:
                        await i.stop()

                _run(main())

    def test_config_level_strict_rejects_undeclared_name(self) -> None:
        cfg = json.loads(json.dumps(self.CFG))
        cfg["strict"] = True
        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(actions={"log": lambda *a: None}))
        ).start()
        with self.assertRaises(UnknownEventError):
            s.send("CANCLE")

    def test_wildcard_dispatch_unaffected(self) -> None:
        hits: List[str] = []
        s = SyncInterpreter(
            _mk(
                self.CFG,
                logic=MachineLogic(
                    actions={"log": lambda i, c, e, a: hits.append(e.type)}
                ),
            )
        ).start()
        s.send("CANCLE")
        self.assertEqual(hits, ["CANCLE"])


# =============================================================================
# #175 reopen (case D) — every receipt still QUEUED at stop() is stopped
# =============================================================================
class TestStopResolvesQueuedDuplicateInstanceReceipts(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "context": {"n": 0},
        "states": {"a": {"on": {"EV": {"actions": ["slow"]}}}},
    }

    def test_stop_resolves_duplicate_instance_receipts(self) -> None:
        # Case D as filed: N sends of ONE Event instance, then stop() before
        # the loop has run. Every receipt resolves InterpreterStoppedError.
        for kind in KINDS:
            with self.subTest(kind=kind):

                def body(i: Any, c: Any) -> None:
                    c["n"] += 1

                async def main() -> Any:
                    i = await Interpreter(
                        _mk(
                            self.CFG,
                            logic=MachineLogic(
                                actions={"slow": _act(kind, body)}
                            ),
                        )
                    ).start()
                    ev = Event("EV")
                    tasks = [
                        asyncio.ensure_future(i.send(ev, wait=True))
                        for _ in range(20)
                    ]
                    await i.stop()
                    res = await asyncio.gather(*tasks)
                    return [type(r.error) for r in res], i.context["n"]

                kinds, applied = _run(main())
                self.assertEqual(applied, 0)
                self.assertEqual(kinds, [InterpreterStoppedError] * 20)

    def test_queued_at_stop_means_stopped_applied_means_ok(self) -> None:
        # The racing window, characterised exactly: a receipt is "ok" iff
        # its event was applied before stop(); every event still queued at
        # stop() (readable via `pending_events`) resolves as stopped.
        async def slow(i: Any, c: Any, e: Any, a: Any) -> None:
            await asyncio.sleep(0.001)
            c["n"] += 1

        async def main() -> None:
            for delay in (0.0, 0.002, 0.005, 0.009):
                i = await Interpreter(
                    _mk(self.CFG, logic=MachineLogic(actions={"slow": slow}))
                ).start()
                ev = Event("EV")
                tasks = [
                    asyncio.ensure_future(i.send(ev, wait=True))
                    for _ in range(12)
                ]
                await asyncio.sleep(delay)
                queued = len(i.pending_events)
                await i.stop()
                res = await asyncio.gather(*tasks)
                ok = sum(1 for r in res if r.error is None)
                stopped = sum(
                    1
                    for r in res
                    if isinstance(r.error, InterpreterStoppedError)
                )
                self.assertEqual(ok, i.context["n"])
                self.assertEqual(ok + stopped, 12)
                self.assertGreaterEqual(stopped, queued)

        _run(main())


if __name__ == "__main__":
    unittest.main()
