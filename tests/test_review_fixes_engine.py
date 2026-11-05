# tests/test_review_fixes_engine.py
# -----------------------------------------------------------------------------
# 🧪 Regression tests for the 0.12.0 engine review (group "engine").
# -----------------------------------------------------------------------------
# Each class pins one finding from the module review of `base_interpreter`,
# `interpreter` and `sync_interpreter`. The finding id is in the class
# docstring so a red test points straight at the rationale comment in the
# source. Every semantic test runs on BOTH engines unless the finding is
# engine-specific (threads, the async run loop).
# -----------------------------------------------------------------------------
"""Regression tests for the engine review fixes (BI-*, ENG-*)."""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import copy
import json
import logging
import threading
import time
import unittest
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    Event,
    InvalidEventError,
    Interpreter,
    MachineLogic,
    NotSupportedError,
    OverflowPolicy,
    PluginBase,
    SimulatedClock,
    SnapshotVersionError,
    StateNotFoundError,
    SyncInterpreter,
    create_machine,
)

ENGINES = ("sync", "async")


class _Quiet(unittest.TestCase):
    """Silence library logging for ONE test (project convention)."""

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class _Recorder(PluginBase):  # type: ignore[type-arg]
    """Records the hooks the tests assert on."""

    def __init__(self) -> None:
        self.dropped: List[Tuple[str, str]] = []
        self.starts = 0
        self.transitions: List[Any] = []
        self.service_hooks: List[str] = []

    def on_event_dropped(
        self, interpreter: Any, event: Any, reason: str
    ) -> None:
        self.dropped.append((event.type, reason))

    def on_interpreter_start(self, interpreter: Any) -> None:
        self.starts += 1

    def on_transition(
        self, interpreter: Any, from_states: Any, to_states: Any, t: Any
    ) -> None:
        self.transitions.append(to_states)

    def on_service_start(self, interpreter: Any, invocation: Any) -> None:
        self.service_hooks.append("start")

    def on_service_done(
        self, interpreter: Any, invocation: Any, r: Any
    ) -> None:
        self.service_hooks.append("done")

    def on_service_error(
        self, interpreter: Any, invocation: Any, e: Any
    ) -> None:
        self.service_hooks.append("error")


def _run(
    engine: str,
    config: Dict[str, Any],
    script: Callable[[Any], Any],
    *,
    actions: Optional[Dict[str, Any]] = None,
    services: Optional[Dict[str, Any]] = None,
    plugin: Optional[PluginBase] = None,  # type: ignore[type-arg]
) -> Any:
    """Start *config* on *engine*, run *script(interp)*, return the result.

    Sync: the live interpreter. Async: a snapshot of the observable
    surface taken INSIDE the loop and the interpreter stopped, because a
    run loop still alive when `asyncio.run` closes is cancelled and the
    machine reports itself dead (#148) -- not what these tests observe.
    """
    machine = create_machine(
        config,
        logic=MachineLogic(actions=actions or {}, services=services or {}),
    )
    if engine == "sync":
        interp: Any = SyncInterpreter(machine)
        if plugin is not None:
            interp.use(plugin)
        interp.start()
        script(interp)
        return interp

    async def main() -> Any:
        interp = Interpreter(machine)
        if plugin is not None:
            interp.use(plugin)
        await interp.start()
        result = script(interp)
        if asyncio.iscoroutine(result):
            await result
        for _ in range(5):
            await asyncio.sleep(0)
        await asyncio.sleep(0.01)
        observed = SimpleNamespace(
            current_state_ids=set(interp.current_state_ids),
            context=copy.deepcopy(interp.context),
            status=interp.status,
            last_transition_ok=interp.last_transition_ok,
        )
        if interp.status == "running":
            await interp.stop()
        return observed

    return asyncio.run(main())


async def _asend(interp: Any, *events: str) -> None:
    for ev in events:
        await interp.send(ev, wait=True)


def _send(engine: str, *events: str) -> Callable[[Any], Any]:
    if engine == "sync":
        return lambda i: [i.send(ev) for ev in events]
    return lambda i: _asend(i, *events)


def _boom(i: Any, c: Any, e: Any, a: Any) -> None:
    raise ValueError("boom")


def _setx(i: Any, c: Any, e: Any, a: Any) -> None:
    c["x"] = 1


def _enqueue_boom(args: Dict[str, Any]) -> None:
    args["enqueue"]("boom")


# -----------------------------------------------------------------------------
# 🧾 Action-error transactions
# -----------------------------------------------------------------------------
class TestNestedActionFailuresHonourPolicy(_Quiet):
    """BI-01: a failure inside choose / pure / enqueueActions reaches
    `actionErrorPolicy` exactly like a top-level failure."""

    NESTED = {
        "choose": {
            "type": "choose",
            "params": {"branches": [{"actions": ["boom"]}]},
        },
        "pure": {"type": "pure", "params": {"get": lambda a: ["boom"]}},
        "enqueueActions": {
            "type": "enqueueActions",
            "params": {"callback": _enqueue_boom},
        },
    }

    def _config(self, policy: str, nested: Any) -> Dict[str, Any]:
        return {
            "id": "c",
            "initial": "a",
            "context": {"x": 0},
            "actionErrorPolicy": policy,
            "states": {
                "a": {
                    "on": {"GO": {"target": "b", "actions": ["setx", nested]}}
                },
                "b": {},
            },
        }

    def test_rollback_and_fail_apply_to_nested_actions(self) -> None:
        for engine in ENGINES:
            for name, nested in self.NESTED.items():
                for policy, ids, status in (
                    ("rollback", {"c.a"}, "running"),
                    ("fail", set(), "stopped"),
                ):
                    with self.subTest(engine=engine, wrap=name, policy=policy):
                        i = _run(
                            engine,
                            self._config(policy, nested),
                            _send(engine, "GO"),
                            actions={"setx": _setx, "boom": _boom},
                        )
                        self.assertEqual(i.current_state_ids, ids)
                        self.assertEqual(i.context, {"x": 0})
                        self.assertEqual(i.status, status)
                        self.assertFalse(i.last_transition_ok)


class TestRolledBackStepDoesNotComplete(_Quiet):
    """BI-02: a failing entry on a top-level final state under rollback /
    fail must not leave the machine "done" with a rolled-back
    configuration."""

    CONFIG = {
        "id": "c",
        "initial": "a",
        "states": {
            "a": {"on": {"GO": "f"}},
            "f": {"type": "final", "entry": "boom"},
        },
    }

    def test_rollback_keeps_running_and_fail_stops(self) -> None:
        for engine in ENGINES:
            for policy, ids, status in (
                ("rollback", {"c.a"}, "running"),
                ("fail", set(), "stopped"),
                ("continue", {"c.f"}, "done"),
            ):
                with self.subTest(engine=engine, policy=policy):
                    cfg = dict(self.CONFIG, actionErrorPolicy=policy)
                    i = _run(
                        engine,
                        cfg,
                        _send(engine, "GO"),
                        actions={"boom": _boom},
                    )
                    self.assertEqual(i.current_state_ids, ids)
                    self.assertEqual(i.status, status)


class TestAssignNonMappingIsAnActionError(_Quiet):
    """BI-14: an assigner returning a non-mapping is an action error;
    ``None`` stays an explicit no-op."""

    def test_non_mapping_rolls_back_and_none_is_ok(self) -> None:
        for engine in ENGINES:
            for produced, ok in (
                (["x"], False),
                (None, True),
                ({"x": 2}, True),
            ):
                with self.subTest(engine=engine, produced=produced):
                    cfg = {
                        "id": "m",
                        "initial": "a",
                        "context": {"x": 0},
                        "actionErrorPolicy": "rollback",
                        "states": {
                            "a": {
                                "on": {
                                    "GO": {
                                        "target": "b",
                                        "actions": {
                                            "type": "assign",
                                            "params": {
                                                "assignment": (
                                                    lambda a, p=produced: p
                                                )
                                            },
                                        },
                                    }
                                }
                            },
                            "b": {},
                        },
                    }
                    i = _run(engine, cfg, _send(engine, "GO"))
                    self.assertEqual(i.last_transition_ok, ok)
                    self.assertEqual(
                        i.current_state_ids, {"m.b"} if ok else {"m.a"}
                    )


# -----------------------------------------------------------------------------
# 🔁 Start-up settle, notifications, plugins
# -----------------------------------------------------------------------------
class TestInitialAlwaysRaiseIsInternal(_Quiet):
    """ENG-01: a `raise` in an initial `always` transition is processed
    after the microstep on both engines."""

    def test_raised_event_drives_the_next_state(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "always": {
                        "target": "b",
                        "actions": [
                            {"type": "raise", "params": {"event": "X"}}
                        ],
                    }
                },
                "b": {"on": {"X": "c"}},
                "c": {},
            },
        }
        for engine in ENGINES:
            with self.subTest(engine=engine):
                i = _run(engine, cfg, lambda i: None)
                self.assertEqual(i.current_state_ids, {"m.c"})


class TestActionsOnlyMicrostepNotifiesSubscribers(_Quiet):
    """BI-03: an assign-only transition notifies `subscribe()` listeners."""

    def test_counter_notifies(self) -> None:
        def inc(i: Any, c: Any, e: Any, a: Any) -> None:
            c["n"] += 1

        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"n": 0},
            "states": {"a": {"on": {"INC": {"actions": "inc"}}}},
        }
        for engine in ENGINES:
            with self.subTest(engine=engine):
                seen: List[int] = []

                def script(i: Any, seen: List[int] = seen) -> Any:
                    i.subscribe(lambda s: seen.append(s.context["n"]))
                    return _send(engine, "INC", "INC")(i)

                i = _run(engine, cfg, script, actions={"inc": inc})
                self.assertEqual(i.context, {"n": 2})
                self.assertEqual(seen, [1, 2])


class TestInternalTransitionHandsPluginsACopy(_Quiet):
    """BI-07: mutating `to_states` in a plugin cannot corrupt the
    configuration of an actions-only transition."""

    def test_mutation_does_not_leak(self) -> None:
        class Vandal(PluginBase):  # type: ignore[type-arg]
            def on_transition(self, i: Any, f: Any, t: Any, tr: Any) -> None:
                t.clear()

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"PING": {"actions": "noop"}}}},
        }
        for engine in ENGINES:
            with self.subTest(engine=engine):
                i = _run(
                    engine,
                    cfg,
                    _send(engine, "PING"),
                    actions={"noop": lambda *a: None},
                    plugin=Vandal(),
                )
                self.assertEqual(i.current_state_ids, {"m.a"})


class TestStartFailureStopsTheMachine(_Quiet):
    """ENG-12: a failing start leaves BOTH engines "stopped"."""

    def test_configuration_error_during_entry(self) -> None:
        def misconfigured(*a: Any) -> None:
            # A configuration error is not contained (it is not a user
            # action failure), so it escapes `start()` on both engines.
            raise NotSupportedError("misconfigured")

        cfg = {"id": "m", "initial": "a", "states": {"a": {"entry": "bad"}}}
        machine = create_machine(
            cfg, logic=MachineLogic(actions={"bad": misconfigured})
        )
        sync = SyncInterpreter(machine)
        with self.assertRaises(NotSupportedError):
            sync.start()
        self.assertEqual(sync.status, "stopped")

        async def main() -> str:
            interp = Interpreter(machine)
            with self.assertRaises(NotSupportedError):
                await interp.start()
            return interp.status

        self.assertEqual(asyncio.run(main()), "stopped")


# -----------------------------------------------------------------------------
# 🛑 Draining after the end
# -----------------------------------------------------------------------------
class TestNothingRunsAfterTheEnd(_Quiet):
    """ENG-02 / ENG-03 / ENG-11: queued events never run on a finished or
    stopped machine, and every stranded event is reported."""

    def test_event_queued_behind_completion_is_dropped(self) -> None:
        ran: List[str] = []
        cfg = {
            "id": "m",
            "initial": "a",
            "on": {"X": {"actions": "x"}},
            "states": {"a": {"on": {"FIN": "f"}}, "f": {"type": "final"}},
        }
        rec = _Recorder()
        m = create_machine(
            cfg,
            logic=MachineLogic(
                actions={"x": lambda i, *_: ran.append(i.status)}
            ),
        )
        s = SyncInterpreter(m)
        s.use(rec)
        s.start()
        s.send_events(["FIN", "X"])
        self.assertEqual(s.status, "done")
        self.assertEqual(ran, [])
        self.assertIn(("X", "not_running"), rec.dropped)

    def test_stop_drain_from_an_action_finishes_the_queue(self) -> None:
        ran: List[str] = []

        def stopper(i: Any, *_: Any) -> None:
            i.send("A")
            i.stop(drain=True)
            ran.append("after-stop:" + i.status)

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {"GO": {"actions": "stopper"}, "A": {"actions": "x"}}
                }
            },
        }
        rec = _Recorder()
        m = create_machine(
            cfg,
            logic=MachineLogic(
                actions={
                    "stopper": stopper,
                    "x": lambda i, *_: ran.append(i.status),
                }
            ),
        )
        s = SyncInterpreter(m)
        s.use(rec)
        s.start()
        s.send("GO")
        self.assertEqual(ran, ["after-stop:running", "running"])
        self.assertEqual(s.status, "stopped")
        self.assertEqual(rec.dropped, [])

    def test_internal_queue_is_reported_on_stop(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "actions": [
                                {"type": "raise", "params": {"event": "A"}},
                                "halt",
                            ]
                        }
                    }
                }
            },
        }
        rec = _Recorder()
        m = create_machine(
            cfg, logic=MachineLogic(actions={"halt": lambda i, *_: i.stop()})
        )
        s = SyncInterpreter(m)
        s.use(rec)
        s.start()
        s.send("GO")
        self.assertEqual(rec.dropped, [("A", "stopped")])

    def test_async_inbox_left_by_completion_is_reported(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "on": {"X": {"actions": "x"}},
            "states": {"a": {"on": {"FIN": "f"}}, "f": {"type": "final"}},
        }
        rec = _Recorder()
        m = create_machine(
            cfg, logic=MachineLogic(actions={"x": lambda *a: None})
        )

        async def main() -> Any:
            i = Interpreter(m)
            i.use(rec)
            await i.start()
            i.send("FIN")
            receipt = await i.send("X", wait=True)
            await asyncio.sleep(0.01)
            return receipt

        receipt = asyncio.run(main())
        self.assertIsNotNone(receipt.error)
        self.assertIn(("X", "not_running"), rec.dropped)


# -----------------------------------------------------------------------------
# 🧵 Sync threads: mailbox, pump threads, blocking spawns, clocks
# -----------------------------------------------------------------------------
class TestMailboxDrainSurvivesARaisingEvent(_Quiet):
    """ENG-04: one mailbox event that raises does not lose the rest of the
    batch nor the owner's own event."""

    def test_batch_and_caller_event_still_run(self) -> None:
        seen: List[str] = []

        async def bad(i: Any, c: Any, e: Any, a: Any) -> None:  # async!
            pass

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "BAD": {"actions": "bad"},
                        "G1": {"actions": "rec"},
                        "G2": {"actions": "rec"},
                        "MINE": {"actions": "rec"},
                    }
                }
            },
        }
        m = create_machine(
            cfg,
            logic=MachineLogic(
                actions={
                    "bad": bad,
                    "rec": lambda i, c, e, a: seen.append(e.type),
                }
            ),
        )
        s = SyncInterpreter(m).start()
        for ev in ("BAD", "G1", "G2"):
            s.send_threadsafe(ev)
        s.send("MINE")
        self.assertEqual(seen, ["G1", "G2", "MINE"])


class TestNonBlockingChildCompletionRunsOnOwnerThread(_Quiet):
    """ENG-05 / ENG-15: a non-blocking invoked child's `onDone` runs on
    the owner's thread (via `tick()`), never on the pump thread."""

    def test_on_done_thread(self) -> None:
        threads: List[str] = []
        kid = create_machine(
            {
                "id": "k",
                "initial": "w",
                "states": {
                    "w": {"after": {"20": "f"}},
                    "f": {"type": "final"},
                },
            }
        )
        cfg = {
            "id": "p",
            "initial": "w",
            "states": {
                "w": {"invoke": {"src": "kid", "onDone": "d"}},
                "d": {"entry": "mark"},
            },
        }
        m = create_machine(
            cfg,
            logic=MachineLogic(
                services={"kid": kid},
                actions={
                    "mark": lambda *a: threads.append(
                        threading.current_thread().name
                    )
                },
            ),
        )
        rec = _Recorder()
        p = SyncInterpreter(m)
        p.use(rec)
        p.start()
        self.addCleanup(p.stop)
        deadline = time.monotonic() + 5
        while "p.d" not in p.current_state_ids and time.monotonic() < deadline:
            time.sleep(0.005)
            p.tick()
        self.assertEqual(p.current_state_ids, {"p.d"})
        self.assertEqual(threads, [threading.current_thread().name])
        # ENG-14: the sync engine reports the invoked machine to plugins.
        self.assertEqual(rec.service_hooks, ["start", "done"])


class TestChildPumpDoesNotFireParentTimers(_Quiet):
    """ENG-06: with a RealClock, a non-blocking child's pump thread no
    longer fires the parent's deadlines."""

    def test_parent_timer_waits_for_the_parent(self) -> None:
        kid = create_machine(
            {
                "id": "k",
                "initial": "w",
                "states": {
                    "w": {"after": {"5000": "f"}},
                    "f": {"type": "final"},
                },
            }
        )
        cfg = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {"entry": "spawn_kid", "after": {"30": "b"}},
                "b": {},
            },
        }
        m = create_machine(cfg, logic=MachineLogic(services={"kid": kid}))
        p = SyncInterpreter(m).start()
        self.addCleanup(p.stop)
        time.sleep(0.1)
        self.assertEqual(list(p._event_queue), [])
        p.tick()
        self.assertEqual(p.current_state_ids, {"p.b"})


class TestBlockingSpawnPumpsTheChild(_Quiet):
    """ENG-07: a blocking spawn of a timer-driven child returns as soon as
    the child finishes, not after the whole timeout."""

    def test_returns_early_and_child_is_done(self) -> None:
        kid = create_machine(
            {
                "id": "ch",
                "initial": "w",
                "states": {
                    "w": {"after": {"20": "f"}},
                    "f": {"type": "final"},
                },
            }
        )
        cfg = {
            "id": "p",
            "initial": "a",
            "spawnBlockingTimeout": 3000,
            "states": {"a": {"entry": "spawn_blocking_kid"}},
        }
        m = create_machine(cfg, logic=MachineLogic(services={"kid": kid}))
        t0 = time.monotonic()
        p = SyncInterpreter(m).start()
        self.addCleanup(p.stop)
        self.assertLess(time.monotonic() - t0, 2.0)


class TestSendEventsHonoursTheMailboxAndPump(_Quiet):
    """ENG-25: sync `send_events` runs mailbox events first, like send()."""

    def test_order(self) -> None:
        seen: List[str] = []
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"T": {"actions": "r"}, "U": {"actions": "r"}}}
            },
        }
        m = create_machine(
            cfg,
            logic=MachineLogic(
                actions={"r": lambda i, c, e, a: seen.append(e.type)}
            ),
        )
        s = SyncInterpreter(m).start()
        s.send_threadsafe("T")
        s.send_events(["U"])
        self.assertEqual(seen, ["T", "U"])


# -----------------------------------------------------------------------------
# ⚡ Async engine
# -----------------------------------------------------------------------------
class TestAsyncActionShapes(_Quiet):
    """ENG-08: async callables and coroutine-returning defs RUN on the
    async engine; the sync engine refuses a returned coroutine."""

    def test_async_engine_awaits_them(self) -> None:
        hits: List[str] = []

        class AsyncCallable:
            async def __call__(self, i: Any, c: Any, e: Any, a: Any) -> None:
                hits.append("callable")

        async def _body() -> None:
            hits.append("returned")

        def returns_coro(i: Any, c: Any, e: Any, a: Any) -> Any:
            return _body()

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": {"actions": ["one", "two"]}}}},
        }
        m = create_machine(
            cfg,
            logic=MachineLogic(
                actions={"one": AsyncCallable(), "two": returns_coro}
            ),
        )

        async def main() -> Any:
            i = await Interpreter(m).start()
            r = await i.send("GO", wait=True)
            await i.stop()
            return r

        receipt = asyncio.run(main())
        self.assertIsNone(receipt.error)
        self.assertEqual(hits, ["callable", "returned"])

    def test_sync_engine_refuses_a_returned_coroutine(self) -> None:
        async def _body() -> None:
            pass

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": {"actions": "x"}}}},
        }
        m = create_machine(
            cfg, logic=MachineLogic(actions={"x": lambda *a: _body()})
        )
        s = SyncInterpreter(m).start()
        with self.assertRaises(NotSupportedError):
            s.send("GO")


class TestAsyncSendEventsBlockPolicy(_Quiet):
    """ENG-09: `send_events` waits under BLOCK instead of raising."""

    def test_batch_larger_than_the_inbox(self) -> None:
        seen: List[int] = []
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"E": {"actions": "r"}}}},
        }
        m = create_machine(
            cfg, logic=MachineLogic(actions={"r": lambda *a: seen.append(1)})
        )

        async def main() -> None:
            i = Interpreter(
                m, max_queue_size=2, overflow_policy=OverflowPolicy.BLOCK
            )
            await i.start()
            await i.send_events(["E"] * 10)
            await i.stop(drain=True)

        asyncio.run(main())
        self.assertEqual(len(seen), 10)


class TestAsyncFatalBaseExceptionPublishesDeath(_Quiet):
    """ENG-10: a BaseException escaping the run loop leaves status
    "error" (not a silent "stopped") and the receipt is not left hanging."""

    def test_status_is_error(self) -> None:
        class Fatal(BaseException):
            pass

        def explode(*a: Any) -> None:
            raise Fatal()

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": {"actions": "x"}}}},
        }
        m = create_machine(cfg, logic=MachineLogic(actions={"x": explode}))

        async def main() -> Tuple[str, Any]:
            i = await Interpreter(m).start()
            fut = asyncio.ensure_future(i.send("GO", wait=True))
            done, _ = await asyncio.wait({fut}, timeout=2)
            await asyncio.sleep(0.01)
            return i.status, done

        status, done = asyncio.run(main())
        self.assertEqual(status, "error")
        self.assertTrue(done)


class TestAsyncRestoredDoneRootStartsOnce(_Quiet):
    """ENG-28: re-starting a restored done root fires the hook once."""

    def test_hook_once(self) -> None:
        cfg = {"id": "m", "initial": "f", "states": {"f": {"type": "final"}}}
        m = create_machine(cfg)
        blob = SyncInterpreter(m).start().get_snapshot()

        async def main() -> int:
            rec = _Recorder()
            i = Interpreter.from_snapshot(blob, m, plugins=[rec])
            await i.start()
            await i.start()
            return rec.starts

        self.assertEqual(asyncio.run(main()), 1)


# -----------------------------------------------------------------------------
# 📨 Events, delays, delivery built-ins
# -----------------------------------------------------------------------------
class TestEventNormalisation(_Quiet):
    """BI-11 / BI-12: empty type refused; payload kwargs never dropped."""

    CFG = {
        "id": "m",
        "initial": "a",
        "states": {"a": {"on": {"X": {"actions": "r"}}}},
    }

    def test_empty_type_is_refused(self) -> None:
        s = SyncInterpreter(
            create_machine(
                self.CFG, logic=MachineLogic(actions={"r": lambda *a: None})
            )
        ).start()
        with self.assertRaises(InvalidEventError):
            s.send("")

    def test_payload_merges_into_an_event_object(self) -> None:
        got: List[Dict[str, Any]] = []
        m = create_machine(
            self.CFG,
            logic=MachineLogic(
                actions={"r": lambda i, c, e, a: got.append(e.payload)}
            ),
        )
        s = SyncInterpreter(m).start()
        s.send(Event(type="X", payload={"a": 1}), foo=2)
        self.assertEqual(got, [{"a": 1, "foo": 2}])


class TestDelayResolution(_Quiet):
    """BI-16: an inline delay callable that raises is contained like a
    named one; a bool is not a delay."""

    def test_raising_inline_delay_is_contained(self) -> None:
        def raising(args: Any) -> float:
            raise RuntimeError("nope")

        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "actions": {
                                "type": "raise",
                                "params": {"event": "Y", "delay": raising},
                            }
                        },
                        "Y": "b",
                    }
                },
                "b": {},
            },
        }
        s = SyncInterpreter(create_machine(cfg)).start()
        s.send("GO")  # used to raise out of the step
        # 📝 An unresolvable delay means "no delay" (the documented
        #    named-delay rule), so the raise is delivered at once.
        self.assertEqual(s.current_state_ids, {"m.b"})

    def test_bool_named_delay_disables_the_after_timer(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"after": {"flag": "b"}}, "b": {}},
        }
        clock = SimulatedClock()
        m = create_machine(cfg, logic=MachineLogic(delays={"flag": True}))
        s = SyncInterpreter(m, clock=clock).start()
        clock.increment(10)
        self.assertEqual(s.current_state_ids, {"m.a"})


class TestSendParentWithoutParentIsReported(_Quiet):
    """BI-15: `sendParent` / `escalate` with no parent are reported drops."""

    def test_reported(self) -> None:
        for action in (
            {"type": "sendParent", "params": {"event": "X"}},
            {"type": "escalate", "params": {"error": "boom"}},
        ):
            for engine in ENGINES:
                with self.subTest(engine=engine, action=action["type"]):
                    rec = _Recorder()
                    cfg = {
                        "id": "m",
                        "initial": "a",
                        "states": {"a": {"on": {"GO": {"actions": action}}}},
                    }
                    i = _run(engine, cfg, _send(engine, "GO"), plugin=rec)
                    self.assertTrue(
                        any(r == "unresolved_target" for _, r in rec.dropped)
                    )
                    self.assertFalse(i.last_transition_ok)


class TestExitActionsRunBeforeInvokesStop(_Quiet):
    """BI-09: an exit action can still address the state's own invoke."""

    def test_send_to_invoke_from_exit(self) -> None:
        kid = create_machine(
            {
                "id": "k",
                "initial": "w",
                "states": {"w": {"on": {"FLUSH": {"actions": "flushed"}}}},
            },
            logic=MachineLogic(actions={"flushed": lambda *a: None}),
        )
        cfg = {
            "id": "p",
            "initial": "w",
            "states": {
                "w": {
                    "invoke": {"id": "kid", "src": "kid"},
                    "exit": {
                        "type": "sendTo",
                        "params": {"to": "kid", "event": "FLUSH"},
                    },
                    "on": {"GO": "d"},
                },
                "d": {},
            },
        }
        for engine in ENGINES:
            with self.subTest(engine=engine):
                rec = _Recorder()
                i = _run(
                    engine,
                    cfg,
                    _send(engine, "GO"),
                    services={"kid": kid},
                    plugin=rec,
                )
                self.addCleanup(
                    lambda i=i: i.stop() if engine == "sync" else None
                )
                self.assertEqual(i.current_state_ids, {"p.d"})
                self.assertNotIn(("FLUSH", "unresolved_target"), rec.dropped)
                self.assertTrue(i.last_transition_ok)


# -----------------------------------------------------------------------------
# 💾 Restore
# -----------------------------------------------------------------------------
class TestDormantTimersPerState(_Quiet):
    """BI-04: one re-armed region does not hide another dormant one, and
    a fired-but-refused timer is not dormant."""

    def test_parallel_restore(self) -> None:
        cfg = {
            "id": "p",
            "type": "parallel",
            "states": {
                "r1": {
                    "initial": "x",
                    "states": {
                        "x": {"after": {"1000": "y"}, "on": {"GO": "z"}},
                        "y": {},
                        "z": {"after": {"500": "y"}},
                    },
                },
                "r2": {
                    "initial": "u",
                    "states": {"u": {"after": {"1000": "v"}}, "v": {}},
                },
            },
        }
        m = create_machine(cfg)
        blob = (
            SyncInterpreter(m, clock=SimulatedClock()).start().get_snapshot()
        )
        r = SyncInterpreter.from_snapshot(
            blob, m, restart_timers=False, clock=SimulatedClock()
        )
        r.start()
        self.assertTrue(r.has_dormant_timers)
        r.send("GO")
        self.assertTrue(r.has_dormant_timers)

    def test_refused_timer_is_not_dormant(self) -> None:
        cfg = {
            "id": "g",
            "initial": "a",
            "states": {
                "a": {"after": {"100": {"target": "b", "guard": "no"}}},
                "b": {},
            },
        }
        m = create_machine(
            cfg, logic=MachineLogic(guards={"no": lambda c, e: False})
        )
        clock = SimulatedClock()
        s = SyncInterpreter(m, clock=clock).start()
        clock.increment(200)
        self.assertFalse(s.has_dormant_timers)


class TestOrphanDeadlineFailsBeforeArming(_Quiet):
    """BI-08: an orphan parked deadline refuses `start()` without consuming
    the parked records."""

    def test_records_survive_the_refusal(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"after": {"1000": "b"}}, "b": {}},
        }
        m = create_machine(cfg)
        blob = json.loads(
            SyncInterpreter(m, clock=SimulatedClock()).start().get_snapshot()
        )
        self.assertTrue(blob["deadlines"])
        ghost = dict(blob["deadlines"][0], state_id="m.ghost")
        blob["deadlines"].append(ghost)
        r = SyncInterpreter.from_snapshot(
            json.dumps(blob),
            m,
            restart_timers="resume",
            clock=SimulatedClock(),
        )
        with self.assertRaises(StateNotFoundError):
            r.start()
        self.assertEqual(len(r._restored_deadlines), 2)


class TestChildRestoreHonoursMinimumVersion(_Quiet):
    """BI-05: a nested child record cannot pick its own checking level."""

    def test_version_stripped_child_is_refused(self) -> None:
        kid = create_machine({"id": "k", "initial": "w", "states": {"w": {}}})
        cfg = {
            "id": "p",
            "initial": "a",
            "states": {"a": {"entry": "spawn_kid"}},
        }
        m = create_machine(cfg, logic=MachineLogic(services={"kid": kid}))
        p = SyncInterpreter(m).start()
        self.addCleanup(p.stop)
        blob = json.loads(p.get_snapshot())
        self.assertTrue(blob["actors"])
        for record in blob["actors"].values():
            record["snapshot"].pop("version", None)
            record["snapshot"].pop("machine_hash", None)
        with self.assertRaises(SnapshotVersionError):
            SyncInterpreter.from_snapshot(
                json.dumps(blob), m, minimum_version=1
            )


class TestSnapshotTakenAtUsesWallNow(_Quiet):
    """BI-17: `taken_at` follows the clock's wall time."""

    def test_simulated_wall_start(self) -> None:
        cfg = {"id": "m", "initial": "a", "states": {"a": {}}}
        s = SyncInterpreter(
            create_machine(cfg), clock=SimulatedClock(wall_start=1000.0)
        ).start()
        self.assertAlmostEqual(
            json.loads(s.get_snapshot())["taken_at"], 1000.0
        )


if __name__ == "__main__":
    unittest.main()
