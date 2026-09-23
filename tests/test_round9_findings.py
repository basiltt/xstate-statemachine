"""Regression tests for the round-9 re-verification findings (#203–#210).

One class per issue. Every test that involves a service or an action is
parametrised over how it is spelled (``def`` / ``async def``); where an
issue is about engine parity the test runs BOTH engines. `unittest`-based
like its siblings; the parametrisation is `subTest`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import unittest
import warnings
from typing import Any, Callable, Dict, List, Tuple

from src.xstate_statemachine import (
    AfterEvent,
    Interpreter,
    MachineLogic,
    RunawayChainError,
    SimulatedClock,
    SnapshotDriftError,
    SnapshotVersionError,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.events import persist_event
from src.xstate_statemachine.plugins import PluginBase

KINDS: Tuple[str, ...] = ("def", "async def")


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        warnings.simplefilter("ignore", DeprecationWarning)
        self.addCleanup(warnings.resetwarnings)


def _run(coro: Any, timeout: float = 30.0) -> Any:
    return asyncio.run(asyncio.wait_for(coro, timeout))


def _mk(cfg: Dict[str, Any], **kw: Any) -> Any:
    return create_machine(json.loads(json.dumps(cfg)), **kw)


def _svc(kind: str, body: Callable[[], Any]) -> Callable[..., Any]:
    if kind == "def":

        def plain(i: Any, c: Any, e: Any) -> Any:
            return body()

        return plain

    async def coro(i: Any, c: Any, e: Any) -> Any:
        await asyncio.sleep(0)
        return body()

    return coro


def _act(kind: str, body: Callable[[Any, Any], None]) -> Callable[..., Any]:
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
        self.dropped: List[Tuple[str, str]] = []
        self.stranded: List[Tuple[str, str]] = []

    def on_event_dropped(self, interp: Any, event: Any, reason: str) -> None:
        self.dropped.append((event.type, reason))

    def on_invocation_stranded(
        self, interp: Any, state_id: str, invoke_id: str, error: Any
    ) -> None:
        self.stranded.append((state_id, invoke_id))


async def _plateau(read: Callable[[], int], stable: int = 5) -> int:
    """Poll until *read()* is unchanged for *stable* consecutive samples."""
    last, n, deadline = -1, 0, time.monotonic() + 20
    while n < stable and time.monotonic() < deadline:
        await asyncio.sleep(0.05)
        cur = read()
        if cur == last:
            n += 1
        else:
            last, n = cur, 0
    return last


# =============================================================================
# #203 — `after` transitions match only engine-minted AfterEvents
# =============================================================================
class TestAfterEventProvenanceInSelection(_Quiet):
    CFG = {
        "id": "t",
        "initial": "waiting",
        "context": {"fired": 0},
        "states": {
            "waiting": {
                "after": {60000: {"target": "done", "actions": ["mark"]}}
            },
            "done": {},
        },
    }

    def _logic(self) -> MachineLogic:
        return MachineLogic(
            actions={"mark": lambda i, c, e, a: c.__setitem__("fired", 1)}
        )

    def test_hand_built_after_event_does_not_fire_timer(self) -> None:
        name = "after.60000.t.waiting"
        s = SyncInterpreter(_mk(self.CFG, logic=self._logic())).start()
        s.send(AfterEvent(name))
        self.assertEqual((s.value, s.context["fired"]), ("waiting", 0))

        async def main() -> Any:
            i = await Interpreter(_mk(self.CFG, logic=self._logic())).start()
            await i.send(AfterEvent(name), wait=True)
            out = (i.value, i.context["fired"])
            await i.stop()
            return out

        self.assertEqual(_run(main()), ("waiting", 0))

    def test_forged_snapshot_record_does_not_fire_timer(self) -> None:
        s = SyncInterpreter(_mk(self.CFG, logic=self._logic())).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        # a hand-written record (no "engine": true) restores as user traffic
        blob["pending_events"] = [
            {"kind": "after", "type": "after.60000.t.waiting"}
        ]
        for engine in (SyncInterpreter, Interpreter):
            with self.subTest(engine=engine.__name__):
                r = engine.from_snapshot(
                    json.dumps(blob), _mk(self.CFG, logic=self._logic())
                )
                if engine is SyncInterpreter:
                    r.start()
                    self.assertEqual(
                        (r.value, r.context["fired"]), ("waiting", 0)
                    )
                    r.stop()
                else:

                    async def main(r: Any = r) -> Any:
                        await r.start()
                        await asyncio.sleep(0.05)
                        out = (r.value, r.context["fired"])
                        await r.stop()
                        return out

                    self.assertEqual(_run(main()), ("waiting", 0))

    def test_genuine_persisted_after_event_still_fires(self) -> None:
        # A genuine engine-minted AfterEvent persisted mid-flight keeps its
        # provenance and drives the transition on restore.
        from src.xstate_statemachine.events import engine_after

        s = SyncInterpreter(_mk(self.CFG, logic=self._logic())).start()
        blob = s.get_persisted_snapshot()
        s.stop()
        blob["pending_events"] = [
            persist_event(engine_after("after.60000.t.waiting", 1.0, 61.0))
        ]
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(self.CFG, logic=self._logic())
        ).start()
        self.assertEqual((r.value, r.context["fired"]), ("done", 1))


# =============================================================================
# #204 — SCXML 6.1: a state exited within its entering macrostep never invokes
# =============================================================================
class TestStatesToInvoke(_Quiet):
    def _chart(self, case: str) -> Dict[str, Any]:
        sub: Dict[str, Any] = {
            "entry": ["bump"],
            "invoke": {
                "id": "kid",
                "src": "svc",
                "onDone": {"target": "#m.armed"},
            },
        }
        if case == "always":
            sub["always"] = [{"target": "#m.armed", "guard": "roll_forward"}]
        return {
            "id": "m",
            "initial": "armed",
            "actionErrorPolicy": "rollback",
            "context": {"n": 0},
            "states": {
                "armed": {"on": {"GO": "#m.submitting"}},
                "submitting": sub,
            },
        }

    def test_rolled_forward_or_back_state_never_invokes(self) -> None:
        for case in ("always", "rollback"):
            for kind in KINDS:
                with self.subTest(case=case, kind=kind):
                    calls: List[str] = []

                    def bump(i: Any, c: Any, e: Any, a: Any) -> None:
                        if case == "rollback":
                            raise RuntimeError("entry failed")
                        c["n"] += 1

                    logic = MachineLogic(
                        actions={"bump": bump},
                        guards={"roll_forward": lambda c, e: True},
                        services={
                            "svc": _svc(kind, lambda: calls.append("svc") or 1)
                        },
                    )
                    if kind == "def":
                        s = SyncInterpreter(
                            _mk(self._chart(case), logic=logic)
                        ).start()
                        s.send("GO")
                        self.assertEqual(s.value, "armed")
                        self.assertEqual(calls, [], f"sync {case}")
                        calls.clear()

                    async def main() -> Any:
                        i = await Interpreter(
                            _mk(self._chart(case), logic=logic)
                        ).start()
                        await i.send("GO", wait=True)
                        await asyncio.sleep(0.1)
                        v = i.value
                        await i.stop()
                        return v

                    self.assertEqual(_run(main()), "armed")
                    self.assertEqual(calls, [], f"async {case} {kind}")

    def test_settled_state_still_invokes_once(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {
                    "always": {"target": "c", "guard": "no"},
                    "invoke": {"id": "s", "src": "svc", "onDone": "d"},
                },
                "c": {},
                "d": {},
            },
        }
        for kind in KINDS:
            with self.subTest(kind=kind):
                calls: List[str] = []
                logic = MachineLogic(
                    guards={"no": lambda c, e: False},
                    services={
                        "svc": _svc(kind, lambda: calls.append("svc") or 1)
                    },
                )
                if kind == "def":
                    s = SyncInterpreter(_mk(cfg, logic=logic)).start()
                    s.send("GO")
                    self.assertEqual((s.value, calls), ("d", ["svc"]))
                    calls.clear()

                async def main() -> Any:
                    i = await Interpreter(_mk(cfg, logic=logic)).start()
                    await i.send("GO", wait=True)
                    await asyncio.sleep(0.1)
                    v = i.value
                    await i.stop()
                    return v

                self.assertEqual(_run(main()), "d")
                self.assertEqual(calls, ["svc"])


# =============================================================================
# #205 — authenticity affordances
# =============================================================================
class TestSnapshotAuthenticityAffordances(_Quiet):
    CFG = {"id": "m", "initial": "a", "states": {"a": {}, "b": {}}}

    def _blob(self) -> Dict[str, Any]:
        s = SyncInterpreter(_mk(self.CFG)).start()
        b = s.get_persisted_snapshot()
        s.stop()
        return b

    def test_minimum_version_refuses_downgrade(self) -> None:
        blob = self._blob()
        for mutate in ("zero", "absent"):
            with self.subTest(mutate=mutate):
                b = dict(blob)
                if mutate == "zero":
                    b["version"] = 0
                else:
                    del b["version"]
                del b["machine_hash"]
                # legacy default accepts it (documented)...
                SyncInterpreter.from_snapshot(json.dumps(b), _mk(self.CFG))
                # ...the floor refuses it
                with self.assertRaises(SnapshotVersionError) as cm:
                    SyncInterpreter.from_snapshot(
                        json.dumps(b), _mk(self.CFG), minimum_version=1
                    )
                self.assertEqual(cm.exception.minimum, 1)
        # an honest versioned blob passes the floor
        SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(self.CFG), minimum_version=1
        )

    def test_expected_machine_hash_is_compared_not_trusted(self) -> None:
        blob = self._blob()
        good = _mk(self.CFG).structure_hash
        SyncInterpreter.from_snapshot(
            json.dumps(blob), _mk(self.CFG), expected_machine_hash=good
        )
        for mutate in ("wrong", "null", "absent", "v0"):
            with self.subTest(mutate=mutate):
                b = dict(blob)
                if mutate == "wrong":
                    b["machine_hash"] = "0" * 16
                elif mutate == "null":
                    b["machine_hash"] = None
                elif mutate == "absent":
                    del b["machine_hash"]
                else:
                    b["version"] = 0
                    del b["machine_hash"]
                with self.assertRaises(SnapshotDriftError):
                    SyncInterpreter.from_snapshot(
                        json.dumps(b),
                        _mk(self.CFG),
                        expected_machine_hash=good,
                    )
        # a payload that matches the caller's fingerprint but not the machine
        with self.assertRaises(SnapshotDriftError):
            SyncInterpreter.from_snapshot(
                json.dumps(blob), _mk(self.CFG), expected_machine_hash="f" * 16
            )

    def test_async_engine_has_the_same_knobs(self) -> None:
        blob = self._blob()
        good = _mk(self.CFG).structure_hash

        async def main() -> str:
            i = Interpreter.from_snapshot(
                json.dumps(blob),
                _mk(self.CFG),
                minimum_version=1,
                expected_machine_hash=good,
            )
            return i.value

        self.assertEqual(_run(main()), "a")


# =============================================================================
# #206 -> #212 — a delayed self-send is a TIMER: never charged as a chain
# =============================================================================
class TestDelayedSelfSendIsATimer(_Quiet):
    """#206 charged a `raise(delay=)` self-send as a chain link; #212 showed
    that killed every self-paced heartbeat at `maxIterations` beats. The rule
    is now the `after` rule: the delay ends the arming step's chain, and the
    firing is a clock event. A 1 ms `raise(delay=)` ping-pong is a periodic
    process exactly as an `after: 1` ping-pong is; `maxIterations` bounds
    work the machine feeds itself WITHIN a step."""

    @staticmethod
    def _raise_cfg(period: int, limit: int = 8) -> Dict[str, Any]:
        arm = {"type": "raise", "params": {"event": "BEAT", "delay": period}}
        return {
            "id": "hb",
            "initial": "up",
            "maxIterations": limit,
            "context": {"n": 0},
            "states": {
                "up": {"entry": [arm, "beat"], "on": {"BEAT": "down"}},
                "down": {"entry": [arm, "beat"], "on": {"BEAT": "up"}},
            },
        }

    @staticmethod
    def _after_cfg(period: int, limit: int = 8) -> Dict[str, Any]:
        return {
            "id": "hb",
            "initial": "up",
            "maxIterations": limit,
            "context": {"n": 0},
            "states": {
                "up": {"entry": ["beat"], "after": {period: "down"}},
                "down": {"entry": ["beat"], "after": {period: "up"}},
            },
        }

    def _beats(self, cfg: Dict[str, Any], kind: str, window: float) -> Any:
        def bump(i: Any, c: Any) -> None:
            c["n"] += 1

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(
                _mk(
                    cfg, logic=MachineLogic(actions={"beat": _act(kind, bump)})
                )
            ).use(d)
            await i.start()
            await asyncio.sleep(window)
            out = (i.context["n"], i.last_error, [r for _, r in d.dropped])
            await i.stop()
            return out

        return _run(main())

    def test_raise_delay_heartbeat_survives_max_iterations(self) -> None:
        # #212: with maxIterations 8, every period must beat PAST 8 with no
        # error and no drop, for both action kinds. The window is sized per
        # period so the floor is comfortably above the old cut-off (9).
        for kind in KINDS:
            for period, window, floor in (
                (30, 1.0, 20),
                (100, 2.0, 14),
                (250, 3.5, 10),
            ):
                with self.subTest(kind=kind, period=period):
                    n, err, drops = self._beats(
                        self._raise_cfg(period), kind, window
                    )
                    self.assertGreater(n, floor)
                    self.assertIsNone(err)
                    self.assertNotIn("chain_budget", drops)

    def test_raise_delay_matches_after_idiom(self) -> None:
        # The two spellings of a heartbeat behave alike (within jitter).
        for kind in KINDS:
            with self.subTest(kind=kind):
                r, _, _ = self._beats(self._raise_cfg(30), kind, 1.0)
                a, _, _ = self._beats(self._after_cfg(30), kind, 1.0)
                self.assertGreater(r, 15)
                self.assertGreater(a, 15)
                self.assertLess(abs(r - a), max(6, a // 3))

    def test_after_heartbeat_unaffected(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                n, err, drops = self._beats(self._after_cfg(30), kind, 1.0)
                self.assertGreater(n, 20)
                self.assertIsNone(err)
                self.assertEqual(drops, [])

    def test_zero_delay_raise_cycle_still_trips(self) -> None:
        # The chain budget's actual target is untouched: a same-step
        # self-raise cycle trips at maxIterations on both action kinds.
        cfg = self._raise_cfg(0)
        for st in cfg["states"].values():
            st["entry"][0] = {"type": "raise", "params": {"event": "BEAT"}}
        for kind in KINDS:
            with self.subTest(kind=kind):
                n, err, drops = self._beats(cfg, kind, 0.5)
                self.assertIs(type(err), RunawayChainError)
                self.assertIn("chain_budget", drops)
                self.assertLess(n, 3 * 8)

    def test_external_delayed_send_is_not_charged(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "maxIterations": 5,
            "context": {"n": 0},
            "states": {"a": {"on": {"EV": {"actions": ["tick"]}}}},
        }

        async def main() -> Any:
            d = _Drops()
            i = Interpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(
                        actions={
                            "tick": lambda i, c, e, a: c.__setitem__(
                                "n", c["n"] + 1
                            )
                        }
                    ),
                )
            ).use(d)
            await i.start()
            for _ in range(20):
                await i._deliver(i, i._prepare_event("EV"), 1, None)
            await asyncio.sleep(0.3)
            out = (i.context["n"], d.dropped)
            await i.stop()
            return out

        n, drops = _run(main())
        self.assertEqual(n, 20)
        self.assertEqual(drops, [])

    def test_sync_engine_timer_paced_cycle_is_a_periodic_process(self) -> None:
        # Same rule on the SyncInterpreter: a timer-paced self-send is
        # driven by the caller's `tick()` and is a periodic process.
        clock = SimulatedClock()
        s = SyncInterpreter(
            _mk(
                self._raise_cfg(1, 20),
                logic=MachineLogic(
                    actions={
                        "beat": lambda i, c, e, a: c.__setitem__(
                            "n", c["n"] + 1
                        )
                    }
                ),
            ),
            clock=clock,
        ).start()
        for _ in range(60):
            clock.increment(1)
        self.assertGreaterEqual(s.context["n"], 20)
        self.assertIsNone(s.last_error)


# =============================================================================
# #207 — a chain cut that strands an invoking state is observable as such
# =============================================================================
class TestStrandedInvocationObservable(_Quiet):
    def _cfg(self, limit: Any = None) -> Dict[str, Any]:
        c: Dict[str, Any] = {
            "id": "spin",
            "actionErrorPolicy": "rollback",
            "initial": "idle",
            "states": {
                "idle": {"on": {"GO": "starting"}},
                "starting": {
                    "invoke": {
                        "id": "sub",
                        "src": "svc",
                        "onDone": "recording",
                    }
                },
                "recording": {"entry": ["boom"]},
            },
        }
        if limit is not None:
            c["maxIterations"] = limit
        return c

    def test_default_limit_trips_and_names_the_stranded_invocation(
        self,
    ) -> None:
        def boom(*a: Any) -> None:
            raise RuntimeError("entry failed")

        for kind in KINDS:
            with self.subTest(kind=kind):
                n = [0]

                async def main() -> Any:
                    d = _Drops()
                    i = Interpreter(
                        _mk(
                            self._cfg(),
                            logic=MachineLogic(
                                actions={"boom": boom},
                                services={
                                    "svc": _svc(
                                        kind,
                                        lambda: n.__setitem__(0, n[0] + 1)
                                        or 1,
                                    )
                                },
                            ),
                        )
                    ).use(d)
                    await i.start()
                    await i.send("GO")
                    plateau = await _plateau(lambda: n[0])
                    out = (
                        plateau,
                        i.last_error,
                        d.stranded,
                        i.has_dormant_invocations,
                        i.value,
                    )
                    await i.stop()
                    return out

                plateau, err, stranded, dormant, value = _run(main())
                self.assertEqual(plateau, 1000 + 2)
                self.assertIsInstance(err, RunawayChainError)
                self.assertEqual(err.stranded, ("sub",))
                self.assertEqual(stranded, [("spin.starting", "sub")])
                self.assertTrue(dormant)
                self.assertEqual(value, "starting")

    def test_sync_engine_reports_the_same(self) -> None:
        def boom(*a: Any) -> None:
            raise RuntimeError("entry failed")

        d = _Drops()
        s = (
            SyncInterpreter(
                _mk(
                    self._cfg(10),
                    logic=MachineLogic(
                        actions={"boom": boom},
                        services={"svc": lambda i, c, e: 1},
                    ),
                )
            )
            .use(d)
            .start()
        )
        r = s.send("GO", wait=True)
        self.assertIsInstance(r.error, RunawayChainError)
        self.assertEqual(r.error.stranded, ("sub",))
        self.assertEqual(d.stranded, [("spin.starting", "sub")])
        self.assertTrue(s.has_dormant_invocations)

    def test_bounded_case_still_trips_at_low_limits(self) -> None:
        def boom(*a: Any) -> None:
            raise RuntimeError("entry failed")

        for limit in (10, 50):
            for kind in KINDS:
                with self.subTest(limit=limit, kind=kind):
                    n = [0]

                    async def main() -> Any:
                        i = await Interpreter(
                            _mk(
                                self._cfg(limit),
                                logic=MachineLogic(
                                    actions={"boom": boom},
                                    services={
                                        "svc": _svc(
                                            kind,
                                            lambda: n.__setitem__(0, n[0] + 1)
                                            or 1,
                                        )
                                    },
                                ),
                            )
                        ).start()
                        await i.send("GO")
                        p = await _plateau(lambda: n[0])
                        out = (p, type(i.last_error))
                        await i.stop()
                        return out

                    p, err = _run(main())
                    self.assertEqual(p, limit + 2)
                    self.assertIs(err, RunawayChainError)

    def test_clean_completion_strands_nothing(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "maxIterations": 5,
            "states": {
                "a": {"invoke": {"id": "s", "src": "svc", "onDone": "b"}},
                "b": {},
            },
        }
        d = _Drops()
        s = (
            SyncInterpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(services={"svc": lambda i, c, e: 1}),
                )
            )
            .use(d)
            .start()
        )
        self.assertEqual(
            (s.value, d.stranded, s.has_dormant_invocations), ("b", [], False)
        )


# =============================================================================
# #208 — a receipt is never success-shaped over an empty configuration
# =============================================================================
class TestReceiptNeverOkOverEmptyConfiguration(_Quiet):
    CFG = {
        "id": "m197",
        "initial": "a",
        "maxIterations": 38,
        "after": {"17": {"target": "#m197.a.c"}},
        "states": {
            "a": {
                "initial": "a",
                "always": {"target": "#m197.a.a.a"},
                "states": {
                    "a": {
                        "initial": "a",
                        "invoke": {"id": "inv", "src": "svc"},
                        "states": {"a": {"type": "final"}},
                    },
                    "c": {},
                },
            }
        },
    }

    def test_property_over_kinds(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):

                async def main() -> None:
                    i = await Interpreter(
                        _mk(
                            self.CFG,
                            logic=MachineLogic(
                                services={"svc": _svc(kind, lambda: 1)}
                            ),
                        )
                    ).start()
                    for _ in range(25):
                        r = await i.send("PING", wait=True)
                        if r.error is None:
                            self.assertTrue(
                                i.current_state_ids,
                                "ok receipt over empty configuration",
                            )
                        await asyncio.sleep(0.005)
                    await i.stop()

                _run(main())

    def test_receipt_reports_illegal_configuration(self) -> None:
        # Unit: force the post-step configuration illegal and check the
        # receipt carries an error rather than `ok`.
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"EV": {"actions": ["wreck"]}}}, "b": {}},
        }

        def wreck(i: Any, c: Any, e: Any, a: Any) -> None:
            i._active_state_nodes.clear()

        async def main() -> Any:
            i = await Interpreter(
                _mk(cfg, logic=MachineLogic(actions={"wreck": wreck}))
            ).start()
            r = await i.send("EV", wait=True)
            ok = i.last_transition_ok
            await i.stop()
            return r.error, ok

        err, ok = _run(main())
        self.assertIsNotNone(err)
        self.assertFalse(ok)


# =============================================================================
# #209 — three-lane lap parity at odd AND even limits, both shapes
# =============================================================================
class TestLapParityAtEveryLimit(_Quiet):
    def _rollback(self, mi: int) -> Dict[str, Any]:
        return {
            "id": "m0",
            "initial": "a",
            "actionErrorPolicy": "rollback",
            "maxIterations": mi,
            "states": {
                "a": {
                    "invoke": {
                        "id": "i1",
                        "src": "svc",
                        "onDone": {"target": "b"},
                    }
                },
                "b": {"always": {"target": "a"}},
            },
        }

    def _nested(self, mi: int) -> Dict[str, Any]:
        # 🔁 #228: `i2`'s completion RE-ENTERS the outer `a` (not its child
        #    `a`), so `a` is exited and `i1` re-arms: a genuine completion
        #    cycle whose call count scales with `maxIterations` (mi + 3)
        #    and trips the guard. The pre-#228 shape targeted `#m0.a.a`
        #    from inside `a`, never exited `a`, fired exactly 2 calls at
        #    every limit and could not fail -- a constant agreeing with
        #    itself. `TestLivelockPinsAreLimitDependent` guards against
        #    that shape coming back.
        return {
            "id": "m0",
            "initial": "a",
            "maxIterations": mi,
            "states": {
                "a": {
                    "initial": "a",
                    "invoke": {
                        "id": "i1",
                        "src": "svc",
                        "onDone": {"target": "#m0.a.b"},
                    },
                    "states": {
                        "a": {},
                        "b": {
                            "invoke": {
                                "id": "i2",
                                "src": "svc",
                                "onDone": {"target": "#m0.a", "reenter": True},
                            }
                        },
                    },
                }
            },
        }

    def test_service_calls_identical_on_all_lanes(self) -> None:
        for name, mk in (
            ("rollback_ondone", self._rollback),
            ("nested_invoke", self._nested),
        ):
            for mi in (1, 2, 3, 4, 5, 7, 10, 15, 20, 25):
                n = [0]

                def bump() -> int:
                    n[0] += 1
                    return 1

                SyncInterpreter(
                    _mk(
                        mk(mi),
                        logic=MachineLogic(
                            services={"svc": _svc("def", bump)}
                        ),
                    )
                ).start()
                sync_n = n[0]
                for kind in KINDS:
                    with self.subTest(shape=name, limit=mi, kind=kind):
                        n[0] = 0

                        async def main() -> int:
                            i = await Interpreter(
                                _mk(
                                    mk(mi),
                                    logic=MachineLogic(
                                        services={"svc": _svc(kind, bump)}
                                    ),
                                )
                            ).start()
                            p = await _plateau(lambda: n[0], stable=4)
                            await i.stop()
                            return p

                        self.assertEqual(_run(main()), sync_n)


# =============================================================================
# #228 — meta-test: every livelock / runaway pin in this file MUST have
# dynamic range across the limit it claims to sweep
# =============================================================================
class TestLivelockPinsAreLimitDependent(_Quiet):
    """A pin that fires the same count at every `maxIterations` cannot
    fail however the chain accounting changes, so a green result proves
    nothing (#228). For each shape the lap-parity sweep uses, assert that
    the call count DIFFERS between two limits and that at least one limit
    trips the guard (`chain_trips >= 1`)."""

    LOW, HIGH = 1, 10

    def _count(self, cfg: Dict[str, Any]) -> Tuple[int, int]:
        n = [0]

        def bump() -> int:
            n[0] += 1
            return 1

        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(services={"svc": _svc("def", bump)}))
        ).start()
        trips = s.chain_trips
        s.stop()
        return n[0], trips

    def test_every_lap_parity_shape_varies_with_the_limit(self) -> None:
        shapes = TestLapParityAtEveryLimit()
        for name, mk in (
            ("rollback_ondone", shapes._rollback),
            ("nested_invoke", shapes._nested),
        ):
            with self.subTest(shape=name):
                low_n, low_t = self._count(mk(self.LOW))
                high_n, high_t = self._count(mk(self.HIGH))
                self.assertNotEqual(
                    low_n,
                    high_n,
                    f"{name}: {low_n} calls at limit {self.LOW} and at "
                    f"limit {self.HIGH} -- the pin is inert",
                )
                self.assertGreaterEqual(
                    max(low_t, high_t),
                    1,
                    f"{name}: never trips the runaway guard at either limit",
                )


if __name__ == "__main__":
    unittest.main()
