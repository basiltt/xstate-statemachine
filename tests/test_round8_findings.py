"""Regression tests for the round-8 re-verification findings (#192–#201;
reopened #181 / #186).

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
    DoneEvent,
    Event,
    Interpreter,
    MachineLogic,
    RunawayChainError,
    SnapshotCorruptError,
    SnapshotMidStepError,
    SyncInterpreter,
    UnhandledEventError,
    UnknownEventError,
    create_machine,
    is_system_event,
)
from src.xstate_statemachine.events import (
    engine_done,
    persist_event,
    restore_event,
)
from src.xstate_statemachine.plugins import PluginBase

_PKG_LOGGER = SyncInterpreter.__module__.rsplit(".", 1)[0]
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

    def on_event_dropped(self, interp: Any, event: Any, reason: str) -> None:
        self.dropped.append((event.type, reason))


class _Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


# =============================================================================
# #192 — priority lane: charge AND shed by provenance
# =============================================================================
class TestPriorityLaneProvenance(_Quiet):
    LIMIT = 25

    def test_priority_self_send_is_charged(self) -> None:
        # A `send(priority=True)` issued from an entry action is
        # self-generated: it trips at the same lap as the `raise` control.
        for kind in KINDS:
            with self.subTest(kind=kind):
                laps = {"p": 0, "r": 0}
                cfg_p = {
                    "id": "p",
                    "maxIterations": self.LIMIT,
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "SPIN": {"target": "a", "actions": ["self"]}
                            }
                        }
                    },
                }
                cfg_r = json.loads(json.dumps(cfg_p))
                cfg_r["states"]["a"]["on"]["SPIN"]["actions"] = [
                    {"type": "raise", "params": {"event": "SPIN"}}
                ]

                def body_p(i: Any, c: Any) -> None:
                    laps["p"] += 1
                    i.send("SPIN", priority=True)

                async def main() -> Any:
                    dp = _Drops()
                    ip = Interpreter(
                        _mk(
                            cfg_p,
                            logic=MachineLogic(
                                actions={"self": _act(kind, body_p)}
                            ),
                        )
                    ).use(dp)
                    await ip.start()
                    await ip.send("SPIN")
                    await asyncio.sleep(0.3)
                    out_p = (
                        laps["p"],
                        type(ip.last_error),
                        [r for _, r in dp.dropped],
                    )
                    await ip.stop()
                    return out_p

                n, err, drops = _run(main())
                self.assertIs(err, RunawayChainError)
                self.assertIn("chain_budget", drops)
                self.assertLess(n, 3 * self.LIMIT)

    def test_external_priority_never_shed_when_chain_tripped(self) -> None:
        cfg = {
            "id": "m",
            "maxIterations": 5,
            "initial": "a",
            "context": {"ext": 0},
            "states": {
                "a": {
                    "on": {
                        "SPIN": {
                            "actions": [
                                {"type": "raise", "params": {"event": "SPIN"}}
                            ]
                        },
                        "EXT": {"actions": ["bump"]},
                    }
                }
            },
        }
        for kind in KINDS:
            with self.subTest(kind=kind):

                async def main() -> Any:
                    d = _Drops()
                    i = Interpreter(
                        _mk(
                            cfg,
                            logic=MachineLogic(
                                actions={
                                    "bump": _act(
                                        kind,
                                        lambda i, c: c.__setitem__(
                                            "ext", c["ext"] + 1
                                        ),
                                    )
                                }
                            ),
                        )
                    ).use(d)
                    await i.start()
                    await i.send("SPIN")  # trips the chain
                    for _ in range(300):
                        i.send("EXT", priority=True)
                        await asyncio.sleep(0)
                    deadline = time.monotonic() + 10
                    while (
                        i.context["ext"] < 300 and time.monotonic() < deadline
                    ):
                        await asyncio.sleep(0.01)
                    out = (
                        i.context["ext"],
                        [t for t, r in d.dropped if r == "chain_budget"],
                    )
                    await i.stop()
                    return out

                applied, cut_types = _run(main())
                self.assertEqual(applied, 300)
                self.assertNotIn("EXT", cut_types)
                self.assertTrue(all(t == "SPIN" for t in cut_types))

    def test_priority_lane_charge_matrix(self) -> None:
        # issuer ∈ {external, action, engine} × chain ∈ {untripped, tripped}
        cfg = {
            "id": "m",
            "maxIterations": 5,
            "initial": "a",
            "context": {"ext": 0},
            "states": {
                "a": {
                    "on": {
                        "SPIN": {
                            "actions": [
                                {"type": "raise", "params": {"event": "SPIN"}}
                            ]
                        },
                        "EXT": {"actions": ["bump"]},
                        "SELF": {"actions": ["self_pri"]},
                    }
                }
            },
        }

        async def main() -> Any:
            rows = []
            for tripped in (False, True):
                d = _Drops()
                i = Interpreter(
                    _mk(
                        cfg,
                        logic=MachineLogic(
                            actions={
                                "bump": lambda i, c, e, a: c.__setitem__(
                                    "ext", c["ext"] + 1
                                ),
                                "self_pri": lambda i, c, e, a: i.send(
                                    "SELF", priority=True
                                ),
                            }
                        ),
                    )
                ).use(d)
                await i.start()
                if tripped:
                    await i.send("SPIN")
                    await asyncio.sleep(0.05)
                # external
                i.send("EXT", priority=True)
                await asyncio.sleep(0.05)
                ext_applied = i.context["ext"] == 1
                # action-issued (self-feeding): must be cut eventually
                await i.send("SELF")
                await asyncio.sleep(0.2)
                self_cut = any(
                    t == "SELF" and r == "chain_budget" for t, r in d.dropped
                )
                ext_cut = any(t == "EXT" for t, _ in d.dropped)
                rows.append((tripped, ext_applied, self_cut, ext_cut))
                await i.stop()
            return rows

        for tripped, ext_applied, self_cut, ext_cut in _run(main()):
            with self.subTest(tripped=tripped):
                self.assertTrue(ext_applied, "external priority send applied")
                self.assertFalse(ext_cut, "external is never shed")
                self.assertTrue(
                    self_cut, "action-issued priority send is charged and cut"
                )

    def test_sync_engine_has_no_priority_lane(self) -> None:
        # `SyncInterpreter.send` processes synchronously; there is no lane
        # to shed from. Assert the absence explicitly.
        s = SyncInterpreter(
            _mk({"id": "s", "initial": "a", "states": {"a": {}}})
        ).start()
        self.assertFalse(hasattr(s, "_priority_queue"))


# =============================================================================
# #193 — a `def` service is unwound by rollback / roll-forward; a stale
# completion never lands in an exited state
# =============================================================================
class TestPlainServiceUnwound(_Quiet):
    def test_rollback_unwinds_invoke_arming(self) -> None:
        cfg = {
            "id": "m",
            "initial": "idle",
            "actionErrorPolicy": "rollback",
            "states": {
                "idle": {"on": {"GO": "busy"}},
                "busy": {
                    "entry": ["boom"],
                    "invoke": {"id": "w", "src": "svc", "onDone": "done"},
                },
                "done": {},
            },
        }

        def boom(*a: Any) -> None:
            raise RuntimeError("boom")

        for kind in KINDS:
            with self.subTest(kind=kind):
                calls: List[str] = []

                async def main() -> Any:
                    i = await Interpreter(
                        _mk(
                            cfg,
                            logic=MachineLogic(
                                services={
                                    "svc": _svc(
                                        kind, lambda: calls.append("svc") or 1
                                    )
                                },
                                actions={"boom": boom},
                            ),
                        )
                    ).start()
                    await i.send("GO", wait=True)
                    await asyncio.sleep(0.1)
                    v = i.value
                    await i.stop()
                    return v

                self.assertEqual(_run(main()), "idle")
                self.assertEqual(calls, [])

    def test_stale_completion_never_lands_in_exited_state(self) -> None:
        # The documented plain-`def` contract: the entering step awaits the
        # service (#116/#149), so `CANCEL` is processed AFTER `onDone` on
        # both engines and the result is applied to the state that invoked
        # it -- never to a state the machine has left (SCXML 6.4.2). The
        # `async def` spelling is interruptible: exit cancels the task.
        cfg = {
            "id": "m",
            "initial": "idle",
            "context": {"cursor": 0},
            "states": {
                "idle": {"on": {"GO": "busy"}},
                "busy": {
                    "invoke": {
                        "id": "w",
                        "src": "work",
                        "onDone": {"target": "done", "actions": ["land"]},
                    },
                    "on": {"CANCEL": "cancelled"},
                },
                "done": {"on": {"CANCEL": {}}},
                "cancelled": {},
            },
        }

        def land(i: Any, c: Any, e: Any, a: Any) -> None:
            c["cursor"] = e.data["cursor"]

        async def main() -> Dict[str, Any]:
            out: Dict[str, Any] = {}

            def work_def(i: Any, c: Any, e: Any) -> Any:
                time.sleep(0.15)
                return {"cursor": 42}

            async def work_async(i: Any, c: Any, e: Any) -> Any:
                await asyncio.sleep(0.15)
                return {"cursor": 42}

            for kind, work in (("def", work_def), ("async def", work_async)):
                i = await Interpreter(
                    _mk(
                        cfg,
                        logic=MachineLogic(
                            services={"work": work}, actions={"land": land}
                        ),
                    )
                ).start()
                go = asyncio.ensure_future(i.send("GO", wait=True))
                await asyncio.sleep(0.05)
                await asyncio.wait_for(i.send("CANCEL", wait=True), 5)
                await go
                await asyncio.sleep(0.3)
                out[kind] = (i.value, i.context["cursor"])
                await i.stop()
            return out

        res = _run(main())
        # async def: exit cancels the task; nothing lands.
        self.assertEqual(res["async def"], ("cancelled", 0))
        # def: the step awaited the service; onDone applied IN `busy`, then
        # CANCEL was processed in `done` (declared, no-op). Never `cancelled`
        # with a cursor written after exit.
        self.assertEqual(res["def"], ("done", 42))

    def test_always_rollforward_matches_sync(self) -> None:
        # An `always` out of the invoking state: both engines arm and
        # complete the plain service inside the step (SCXML lets the
        # invoke start once the state is entered); parity is the contract.
        cfg = {
            "id": "m",
            "initial": "idle",
            "states": {
                "idle": {"on": {"GO": "busy"}},
                "busy": {
                    "always": "out",
                    "invoke": {"id": "w", "src": "svc", "onDone": "done"},
                },
                "out": {},
                "done": {},
            },
        }
        calls = {"s": 0, "a": 0}
        s = SyncInterpreter(
            _mk(
                cfg,
                logic=MachineLogic(
                    services={
                        "svc": lambda i, c, e: calls.__setitem__(
                            "s", calls["s"] + 1
                        )
                        or 1
                    }
                ),
            )
        ).start()
        s.send("GO")

        async def main() -> Any:
            i = await Interpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(
                        services={
                            "svc": lambda i, c, e: calls.__setitem__(
                                "a", calls["a"] + 1
                            )
                            or 1
                        }
                    ),
                )
            ).start()
            await i.send("GO", wait=True)
            await asyncio.sleep(0.05)
            v = i.value
            await i.stop()
            return v

        self.assertEqual(_run(main()), s.value)
        self.assertEqual(calls["a"], calls["s"])


# =============================================================================
# #194 / #181 reopen — children_timeout: per child, observable, honest
# =============================================================================
class TestChildrenTimeoutPerChildAndObservable(_Quiet):
    @staticmethod
    def _mk(n: int, kind: str, d: float) -> Any:
        child = {
            "id": "kid",
            "initial": "w",
            "states": {"w": {"entry": ["slow"]}},
        }
        regions = {
            f"r{k}": {
                "initial": "s",
                "states": {"s": {"invoke": {"id": f"k{k}", "src": "kidm"}}},
            }
            for k in range(n)
        }
        if kind == "def":

            def slow(i: Any, c: Any, e: Any, a: Any) -> None:
                time.sleep(d)

        else:

            async def slow(i: Any, c: Any, e: Any, a: Any) -> None:  # type: ignore[misc]
                await asyncio.sleep(d)

        return create_machine(
            {"id": "par", "type": "parallel", "states": regions},
            logic=MachineLogic(
                services={
                    "kidm": create_machine(
                        child, logic=MachineLogic(actions={"slow": slow})
                    )
                }
            ),
        )

    def test_children_timeout_is_per_child_not_aggregate(self) -> None:
        # Coroutine entry actions run concurrently: N children x D settle in ~D.
        async def main() -> Any:
            out = []
            for n in (1, 5, 20):
                t = time.monotonic()
                i = await Interpreter(self._mk(n, "async def", 0.3)).start(
                    children_timeout=0.1
                )
                out.append(time.monotonic() - t)
                await i.stop()
            return out

        times = _run(main())
        for t in times:
            self.assertLess(t, 0.6, times)
        self.assertLess(max(times) - min(times), 0.3, "flat in N")

    def test_children_timeout_warning_is_logged(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):
                cap = _Capture()
                logging.disable(logging.NOTSET)
                lg = logging.getLogger(_PKG_LOGGER)
                lg.addHandler(cap)
                old = lg.level
                lg.setLevel(logging.WARNING)
                try:

                    async def main() -> None:
                        i = await Interpreter(self._mk(1, kind, 0.3)).start(
                            children_timeout=0.05
                        )
                        await i.stop()

                    _run(main())
                finally:
                    lg.removeHandler(cap)
                    lg.setLevel(old)
                    logging.disable(logging.CRITICAL)
                self.assertTrue(
                    any(
                        "children_timeout" in r.getMessage()
                        for r in cap.records
                    ),
                    kind,
                )

    def test_children_timeout_none_is_unbounded(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):

                async def main() -> float:
                    t = time.monotonic()
                    i = await Interpreter(self._mk(1, kind, 0.25)).start(
                        children_timeout=None
                    )
                    took = time.monotonic() - t
                    await i.stop()
                    return took

                self.assertGreaterEqual(_run(main()), 0.2)

    def test_coroutine_entry_is_bounded_def_entry_is_reported(self) -> None:
        # The honest contract: a coroutine child is pre-empted by the bound;
        # a non-yielding `def` child cannot be (single thread) -- and the
        # overrun is still reported (see the WARNING test above).
        async def main() -> Tuple[float, float]:
            t = time.monotonic()
            i = await Interpreter(self._mk(1, "async def", 1.0)).start(
                children_timeout=0.1
            )
            a = time.monotonic() - t
            await i.stop()
            t = time.monotonic()
            i = await Interpreter(self._mk(1, "def", 0.3)).start(
                children_timeout=0.1
            )
            d = time.monotonic() - t
            await i.stop()
            return a, d

        a, d = _run(main())
        self.assertLess(a, 0.5)
        self.assertGreaterEqual(d, 0.25)


# =============================================================================
# #195 — engine events carry provenance; forgeries are user traffic
# =============================================================================
class TestEngineEventProvenance(_Quiet):
    CFG = {
        "id": "sec",
        "initial": "a",
        "strict": True,
        "onUnhandled": "error",
        "states": {
            "a": {
                "invoke": [
                    {
                        "id": "k",
                        "src": "svc",
                        "onDone": {"target": "done_", "actions": ["stash"]},
                    }
                ]
            },
            "done_": {},
        },
    }

    def test_hand_built_engine_events_are_user_traffic(self) -> None:
        self.assertFalse(is_system_event(DoneEvent("done.invoke.k", {}, "k")))
        self.assertFalse(is_system_event(AfterEvent("after.1.x")))
        self.assertTrue(is_system_event(engine_done("done.invoke.k", {}, "k")))
        # public surface unchanged
        g = engine_done("done.invoke.k", {"n": 1}, "k")
        self.assertIsInstance(g, DoneEvent)
        self.assertEqual(g, DoneEvent("done.invoke.k", {"n": 1}, "k"))

    def test_doneevent_forgery_rejected(self) -> None:
        for kind in KINDS:
            with self.subTest(kind=kind):

                async def slow_body() -> int:
                    await asyncio.sleep(30)
                    return 1

                svc: Callable[..., Any]
                if kind == "def":
                    svc = lambda i, c, e: time.sleep(0.3) or 1  # noqa: E731
                else:
                    svc = lambda i, c, e: slow_body()  # noqa: E731

                async def main() -> Any:
                    i = await Interpreter(
                        _mk(
                            self.CFG,
                            logic=MachineLogic(
                                services={"svc": svc},
                                actions={
                                    "stash": lambda i, c, e, a: c.__setitem__(
                                        "got", e.data
                                    )
                                },
                            ),
                        )
                    ).start(children_timeout=0.1)
                    forged = DoneEvent("done.invoke.k", {"forged": True}, "k")
                    try:
                        await i.send(forged, wait=True)
                        raised = None
                    except UnknownEventError as exc:
                        raised = exc
                    got = i.context.get("got")
                    await i.stop()
                    return raised, got

                raised, got = _run(main())
                self.assertIsInstance(raised, UnknownEventError)
                self.assertIn("engine-generated", str(raised))
                self.assertNotEqual(got, {"forged": True})

    def test_forgery_under_on_unhandled_error_kills_not_transitions(
        self,
    ) -> None:
        cfg = json.loads(json.dumps(self.CFG))
        cfg["strict"] = False

        async def main() -> Any:
            async def svc(i: Any, c: Any, e: Any) -> int:
                await asyncio.sleep(30)
                return 1

            i = await Interpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(
                        services={"svc": svc},
                        actions={"stash": lambda *a: None},
                    ),
                )
            ).start()
            r = await i.send(
                DoneEvent("done.invoke.k", {"forged": True}, "k"), wait=True
            )
            out = (type(r.error), i.value, i.status)
            await i.stop()
            return out

        err, value, status = _run(main())
        self.assertIs(err, UnhandledEventError)
        self.assertEqual(value, "a")
        self.assertEqual(status, "error")

    def test_restore_event_keeps_provenance_honestly(self) -> None:
        # attacker record -> user provenance; genuine round-trip -> engine
        forged = restore_event(
            {
                "kind": "done",
                "type": "done.invoke.k",
                "data": {"px": 9e9},
                "src": "k",
            }
        )
        self.assertFalse(is_system_event(forged))
        genuine = restore_event(
            json.loads(
                json.dumps(
                    persist_event(engine_done("done.invoke.k", {"n": 1}, "k"))
                )
            )
        )
        self.assertTrue(is_system_event(genuine))
        self.assertEqual(genuine.data, {"n": 1})

    def test_genuine_completion_survives_snapshot_round_trip(self) -> None:
        # A persisted pending `done.invoke` still drives onDone on restore.
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"invoke": {"id": "k", "src": "svc", "onDone": "b"}},
                "b": {},
            },
        }
        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(services={"svc": lambda i, c, e: 1}))
        ).start()
        self.assertEqual(s.value, "b")
        blob = s.get_persisted_snapshot()
        blob["state_ids"] = ["m.a"]
        blob["configuration"] = ["m", "m.a"]
        blob["pending_events"] = [
            persist_event(engine_done("done.invoke.k", 1, "k"))
        ]
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob),
            _mk(cfg, logic=MachineLogic(services={"svc": lambda i, c, e: 1})),
        ).start()
        self.assertEqual(r.value, "b")


# =============================================================================
# #196 — `always` never competes for a named event; trip is observable
# =============================================================================
class TestAlwaysDoesNotConsumeNamedEvents(_Quiet):
    CFG = {
        "id": "m",
        "initial": "a",
        "maxIterations": 50,
        "context": {"ext": 0},
        "on": {"EXT": {"actions": ["extbump"]}},
        "states": {
            "a": {"on": {"GO": "b"}},
            "b": {
                "always": {"target": "b2"},
                "initial": "b2",
                "states": {
                    "b2": {
                        "invoke": {
                            "id": "s",
                            "src": "svc",
                            "onDone": {"target": "#m.a"},
                        }
                    }
                },
            },
        },
    }

    def test_external_applies_under_spinning_always_both_engines(
        self,
    ) -> None:
        def bump(i: Any, c: Any, e: Any, a: Any) -> None:
            c["ext"] += 1

        kid = {"id": "kid", "initial": "w", "states": {"w": {}}}
        s = SyncInterpreter(
            _mk(
                self.CFG,
                logic=MachineLogic(
                    services={"svc": _mk(kid)}, actions={"extbump": bump}
                ),
            )
        ).start()
        self.addCleanup(s.stop)  # the child actor is an infinite machine
        s.send("GO")
        self.assertIsInstance(s.last_error, RunawayChainError)
        for _ in range(10):
            r = s.send("EXT", wait=True)
            # the trip is observable on EVERY step under the spin
            self.assertIsInstance(r.error, RunawayChainError)
        self.assertEqual(s.context["ext"], 10)

        for kind in KINDS:
            with self.subTest(kind=kind):

                async def main() -> Any:
                    i = await Interpreter(
                        _mk(
                            self.CFG,
                            logic=MachineLogic(
                                services={"svc": _svc(kind, lambda: 1)},
                                actions={"extbump": bump},
                            ),
                        )
                    ).start()
                    r = await i.send("GO", wait=True)
                    errs = []
                    for _ in range(10):
                        rr = await i.send("EXT", wait=True, priority=True)
                        errs.append(type(rr.error))
                    out = (type(r.error), i.context["ext"], errs)
                    await i.stop()
                    return out

                err, applied, errs = _run(main())
                # The GO step trips and REPORTS it; every external event
                # then applies. Whether later steps also report the trip
                # depends on where the machine sits: a `def` service
                # completes inside the GO step and the machine is back in
                # `a` (clean steps); an `async def` leaves it spinning in
                # `b` and every step re-trips -- and says so.
                self.assertIs(err, RunawayChainError)
                self.assertEqual(applied, 10, "external traffic applies")
                if kind == "async def":
                    self.assertTrue(
                        all(e is RunawayChainError for e in errs),
                        "the settle trip is observable on every step",
                    )

    def test_named_event_handler_outranks_deeper_always(self) -> None:
        # The selection rule itself: an `always` on a deeper state must not
        # be chosen for a NAMED event whose handler sits on an ancestor.
        cfg = {
            "id": "m",
            "initial": "b",
            "context": {"ext": 0},
            "on": {"EXT": {"actions": ["bump"]}},
            "states": {
                "b": {"always": {"target": "c", "guard": "go"}},
                "c": {},
            },
        }
        s = SyncInterpreter(
            _mk(
                cfg,
                logic=MachineLogic(
                    actions={
                        "bump": lambda i, c, e, a: c.__setitem__("ext", 1)
                    },
                    guards={"go": lambda c, e: True},
                ),
            )
        ).start()
        # Put the machine back in `b` with the always still armed, then ask
        # the selector directly: a NAMED event must never pick `""`.
        s._active_state_nodes = {s.machine, s.machine.states["b"]}
        sel = s._select_transitions(Event("EXT"))
        self.assertEqual([t.event for t in sel], ["EXT"])

    def test_ablations_are_clean(self) -> None:
        # invoke-only cycle: applies everything, trips the chain budget;
        # always-only: trips the settle budget and still applies EXT.
        def bump(i: Any, c: Any, e: Any, a: Any) -> None:
            c["ext"] += 1

        no_always = json.loads(json.dumps(self.CFG))
        del no_always["states"]["b"]["always"]
        no_invoke = json.loads(json.dumps(self.CFG))
        no_invoke["states"]["b"]["states"]["b2"] = {}
        for label, cfg in (("no_always", no_always), ("no_invoke", no_invoke)):
            for kind in KINDS:
                with self.subTest(label=label, kind=kind):

                    async def main() -> Any:
                        i = await Interpreter(
                            _mk(
                                cfg,
                                logic=MachineLogic(
                                    services={"svc": _svc(kind, lambda: 1)},
                                    actions={"extbump": bump},
                                ),
                            )
                        ).start()
                        await i.send("GO")
                        for _ in range(30):
                            i.send("EXT", priority=True)
                            await asyncio.sleep(0)
                        deadline = time.monotonic() + 10
                        while (
                            i.context["ext"] < 30
                            and time.monotonic() < deadline
                        ):
                            await asyncio.sleep(0.01)
                        n = i.context["ext"]
                        await i.stop()
                        return n

                    self.assertEqual(_run(main()), 30)


# =============================================================================
# #197 — a resolved send(wait=True) never leaves an empty configuration
# =============================================================================
class TestNoEmptyConfigurationWhileRunning(_Quiet):
    def test_property_over_service_kinds_and_engines(self) -> None:
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
        s = SyncInterpreter(
            _mk(cfg, logic=MachineLogic(services={"svc": lambda i, c, e: 1}))
        ).start()
        for _ in range(5):
            s.send("GO", wait=True)
            self.assertTrue(s.current_state_ids)
        for kind in KINDS:
            with self.subTest(kind=kind):

                async def main() -> None:
                    i = await Interpreter(
                        _mk(
                            cfg,
                            logic=MachineLogic(
                                services={"svc": _svc(kind, lambda: 1)}
                            ),
                        )
                    ).start()
                    for _ in range(15):
                        r = await i.send("GO", wait=True)
                        self.assertTrue(i.current_state_ids, r)
                        await asyncio.sleep(0.01)
                        self.assertTrue(i.current_state_ids)
                    await i.stop()

                _run(main())


# =============================================================================
# #198 / #186 reopen — versioned payloads carry BOTH fields, and they agree
# =============================================================================
class TestConfigurationFieldsMustAgreeBothWays(_Quiet):
    CFG = {"id": "m", "initial": "a", "states": {"a": {}, "b": {}}}

    def _blob(self) -> Dict[str, Any]:
        s = SyncInterpreter(_mk(self.CFG)).start()
        b = s.get_persisted_snapshot()
        s.stop()
        return b

    def _restore(self, engine: Any, blob: Dict[str, Any]) -> Any:
        return engine.from_snapshot(json.dumps(blob), _mk(self.CFG))

    def test_emptied_state_ids_on_versioned_payload_refused(self) -> None:
        for engine in (SyncInterpreter, Interpreter):
            with self.subTest(engine=engine.__name__):
                blob = self._blob()
                blob["state_ids"] = []
                with self.assertRaises(SnapshotCorruptError):
                    self._restore(engine, blob)

    def test_dropped_configuration_on_versioned_payload_refused(self) -> None:
        for engine in (SyncInterpreter, Interpreter):
            with self.subTest(engine=engine.__name__):
                blob = self._blob()
                del blob["configuration"]
                with self.assertRaises(SnapshotCorruptError):
                    self._restore(engine, blob)
                blob = self._blob()
                blob["configuration"] = []
                with self.assertRaises(SnapshotCorruptError):
                    self._restore(engine, blob)

    def test_contradicting_fields_still_refused(self) -> None:
        blob = self._blob()
        blob["configuration"] = ["m", "m.b"]
        with self.assertRaises(SnapshotCorruptError):
            self._restore(SyncInterpreter, blob)

    def test_legacy_v0_state_ids_only_payload_accepted(self) -> None:
        v0 = {"status": "running", "context": {}, "state_ids": ["m.a"]}
        r = self._restore(SyncInterpreter, v0)
        self.assertEqual(r.value, "a")
        blob = self._blob()  # agreeing versioned blob still restores
        self.assertEqual(self._restore(SyncInterpreter, blob).value, "a")


# =============================================================================
# #199 — on_interpreter_start is inside the in-flight window
# =============================================================================
class TestOnInterpreterStartSnapshotRefused(_Quiet):
    def test_refused_on_both_engines(self) -> None:
        cfg = {"id": "m", "initial": "a", "states": {"a": {"entry": ["noop"]}}}
        rows: List[str] = []

        class Grab(PluginBase):
            def on_interpreter_start(self, interp: Any) -> None:
                try:
                    interp.get_persisted_snapshot()
                    rows.append("RETURNED")
                except SnapshotMidStepError:
                    rows.append("REFUSED")

        for kind in KINDS:
            with self.subTest(kind=kind):
                rows.clear()
                logic = MachineLogic(
                    actions={"noop": _act(kind, lambda i, c: None)}
                )
                if kind == "def":
                    s = (
                        SyncInterpreter(_mk(cfg, logic=logic))
                        .use(Grab())
                        .start()
                    )
                    self.assertEqual(rows, ["REFUSED"])
                    self.assertTrue(s.get_persisted_snapshot()["state_ids"])
                    s.stop()
                    rows.clear()

                async def main() -> Any:
                    i = Interpreter(_mk(cfg, logic=logic)).use(Grab())
                    await i.start()
                    snap = i.get_persisted_snapshot()
                    await i.stop()
                    return snap["state_ids"]

                ids = _run(main())
                self.assertEqual(rows, ["REFUSED"])
                self.assertEqual(ids, ["m.a"])


# =============================================================================
# #200 — the owed-completion ledger is task-keyed and leak-free
# =============================================================================
class TestChainOwedLedger(_Quiet):
    class _Boom(BaseException):
        pass

    def test_released_on_base_exception_exit(self) -> None:
        cfg = {
            "id": "m",
            "initial": "idle",
            "states": {
                "idle": {"on": {"GO": "a"}},
                "a": {"invoke": {"id": "k", "src": "svc", "onDone": "b"}},
                "b": {},
            },
        }
        boom = self._Boom

        for kind in KINDS:
            with self.subTest(kind=kind):
                if kind == "def":

                    def svc(i: Any, c: Any, e: Any) -> Any:
                        raise boom("exit")

                else:

                    async def svc(i: Any, c: Any, e: Any) -> Any:  # type: ignore[misc]
                        await asyncio.sleep(0)
                        raise boom("exit")

                async def main() -> int:
                    i = await Interpreter(
                        _mk(cfg, logic=MachineLogic(services={"svc": svc}))
                    ).start()
                    try:
                        await asyncio.wait_for(i.send("GO", wait=True), 5)
                    except (
                        BaseException
                    ):  # noqa: BLE001 -- the simulated exit may surface
                        pass
                    await asyncio.sleep(0.1)
                    owed = i._chain_owed
                    try:
                        await asyncio.wait_for(i.stop(), 5)
                    except BaseException:  # noqa: BLE001
                        pass
                    return owed

                self.assertEqual(_run(main()), 0)

    def test_debt_is_keyed_to_invocation(self) -> None:
        # Two concurrent coroutine services; one completes, the other's debt
        # stays open until IT completes.
        cfg = {
            "id": "m",
            "type": "parallel",
            "states": {
                "r1": {
                    "initial": "s",
                    "states": {
                        "s": {
                            "invoke": {
                                "id": "fast",
                                "src": "fast",
                                "onDone": "d",
                            }
                        },
                        "d": {},
                    },
                },
                "r2": {
                    "initial": "s",
                    "states": {
                        "s": {
                            "invoke": {
                                "id": "slow",
                                "src": "slow",
                                "onDone": "d",
                            }
                        },
                        "d": {},
                    },
                },
            },
        }

        async def main() -> Tuple[int, int, int]:
            gate = asyncio.Event()

            async def fast(i: Any, c: Any, e: Any) -> int:
                return 1

            async def slow(i: Any, c: Any, e: Any) -> int:
                await gate.wait()
                return 2

            i = await Interpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(services={"fast": fast, "slow": slow}),
                )
            ).start()
            await asyncio.sleep(0.05)
            after_fast = i._chain_owed
            gate.set()
            await asyncio.sleep(0.05)
            after_slow = i._chain_owed
            await i.stop()
            return 2, after_fast, after_slow

        _, after_fast, after_slow = _run(main())
        self.assertEqual(
            after_fast, 1, "the slow invocation's debt is still open"
        )
        self.assertEqual(after_slow, 0)


# =============================================================================
# #201 — lap parity, stated exactly, for every lane and shape
# =============================================================================
class TestLapParityStatedExactly(_Quiet):
    def test_invoke_pingpong_from_initial_state_identical_laps(self) -> None:
        for limit in (3, 20):
            cfg = {
                "id": "lv",
                "initial": "ver",
                "maxIterations": limit,
                "context": {"n": 0},
                "states": {
                    "ver": {
                        "entry": ["bump"],
                        "invoke": [{"id": "k", "src": "svc", "onDone": "arm"}],
                    },
                    "arm": {
                        "entry": ["bump"],
                        "invoke": [
                            {"id": "k2", "src": "svc", "onDone": "ver"}
                        ],
                    },
                },
            }

            def bump(i: Any, c: Any, e: Any, a: Any) -> None:
                c["n"] += 1

            s = SyncInterpreter(
                _mk(
                    cfg,
                    logic=MachineLogic(
                        actions={"bump": bump},
                        services={"svc": lambda i, c, e: 1},
                    ),
                )
            ).start()
            sync_n = s.context["n"]
            self.assertIsInstance(s.last_error, RunawayChainError)
            for kind in KINDS:
                with self.subTest(limit=limit, kind=kind):

                    async def main() -> Tuple[int, Any]:
                        i = await Interpreter(
                            _mk(
                                cfg,
                                logic=MachineLogic(
                                    actions={"bump": bump},
                                    services={"svc": _svc(kind, lambda: 1)},
                                ),
                            )
                        ).start()
                        await asyncio.sleep(0.3)
                        out = (i.context["n"], type(i.last_error))
                        await i.stop()
                        return out

                    n, err = _run(main())
                    self.assertEqual(n, sync_n)
                    self.assertIs(err, RunawayChainError)

    def test_rollback_ondone_async_lanes_identical_sync_stops_early(
        self,
    ) -> None:
        # Stated exactly: the two async lanes trip at the same lap; the
        # SYNC engine does not re-arm a rolled-back invoke inside the same
        # drain and stops after the first rollback with that RuntimeError.
        cfg = {
            "id": "lv",
            "initial": "a",
            "maxIterations": 20,
            "actionErrorPolicy": "rollback",
            "states": {
                "a": {
                    "invoke": [
                        {
                            "id": "k",
                            "src": "svc",
                            "onDone": {"target": "b", "actions": ["blow"]},
                        }
                    ]
                },
                "b": {"always": {"target": "a"}},
            },
        }

        def blow(*a: Any) -> None:
            raise RuntimeError("rollback")

        calls = {"s": 0}
        s = SyncInterpreter(
            _mk(
                cfg,
                logic=MachineLogic(
                    actions={"blow": blow},
                    services={
                        "svc": lambda i, c, e: calls.__setitem__(
                            "s", calls["s"] + 1
                        )
                        or 1
                    },
                ),
            )
        ).start()
        self.assertIsInstance(s.last_error, RuntimeError)
        self.assertLessEqual(calls["s"], 2)

        laps: Dict[str, int] = {}
        for kind in KINDS:
            with self.subTest(kind=kind):
                n = [0]

                async def main() -> Any:
                    d = _Drops()
                    i = Interpreter(
                        _mk(
                            cfg,
                            logic=MachineLogic(
                                actions={"blow": blow},
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
                    await asyncio.sleep(0.4)
                    # `last_error` is per step and the rollback's own
                    # RuntimeError may be the most recent one; the trip is
                    # asserted through the drop hook, which is cumulative.
                    out = [r for _, r in d.dropped]
                    await i.stop()
                    return out

                self.assertIn("chain_budget", _run(main()))
                laps[kind] = n[0]
        self.assertEqual(laps["def"], laps["async def"])


if __name__ == "__main__":
    unittest.main()
