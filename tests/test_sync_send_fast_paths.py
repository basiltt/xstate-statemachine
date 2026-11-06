# -------------------------------------------------------------------------
# 🧪 Pin tests for the inlined `SyncInterpreter.send()` gates
# -------------------------------------------------------------------------
"""Pins the gates that commit c97f0764 inlined into the sync hot path.

🏛️ That commit made `SyncInterpreter.send()` / `_process_event_queue()`
cheaper by reading each helper's early-return condition at the call site
(plugins, strict / event schemas, mailbox, timer pump, `always`, chain
reset) and gave `BaseInterpreter._process_event` an actions-only fast
path. A gate that reads the wrong thing silently skips real work, so each
test below makes the skipped work observable (hook counts, state ids,
context values) and fails if its gate were broken.
"""

from __future__ import annotations

import logging
import threading
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Event,
    Interpreter,
    MachineLogic,
    PluginBase,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import (
    InvalidEventPayloadError,
    UnknownEventError,
)

_SIMPLE = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {"on": {"GO": {"target": "b"}, "INC": {"actions": "inc"}}},
        "b": {"on": {"BACK": "a"}},
    },
}
# Same chart without the `inc` action, for tests that need no logic.
_PLAIN = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"BACK": "a"}}},
}
# 📝 The package may be imported as `xstate_statemachine` or (in this test
#    tree) as `src.xstate_statemachine`; the logger is named after the module.
_LOGGER_NAME = SyncInterpreter.__module__.rsplit(".", 1)[0]


def _inc(i: Any, ctx: Any, e: Any, a: Any) -> None:
    ctx["n"] = ctx.get("n", 0) + 1


class _Counting(PluginBase):
    """Records the type of every event offered to `on_before_send`."""

    def __init__(self) -> None:
        self.before: List[str] = []

    def on_before_send(self, interpreter: Any, event: Any) -> None:
        self.before.append(event.type)
        return None


# -------------------------------------------------------------------------
# 1-3. plugins / strict / mailbox gates
# -------------------------------------------------------------------------
class TestSendGates(unittest.TestCase):
    def test_plugin_attached_after_start_sees_plain_str_send(self) -> None:
        # Arrange: the gate reads the LIVE plugin list, not a start-time copy
        interp = SyncInterpreter(
            create_machine(_SIMPLE, logic=MachineLogic(actions={"inc": _inc}))
        ).start()
        plugin = _Counting()
        interp.use(plugin)
        # Act
        interp.send("INC")
        interp.send("INC")
        # Assert
        self.assertEqual(plugin.before, ["INC", "INC"])
        self.assertEqual(interp.context["n"], 2)
        interp.stop()

    def test_send_without_plugins_still_runs_the_action(self) -> None:
        interp = SyncInterpreter(
            create_machine(_SIMPLE, logic=MachineLogic(actions={"inc": _inc}))
        ).start()
        interp.send("INC")
        self.assertEqual(interp.context["n"], 1)
        interp.stop()

    def test_strict_constructor_flag_rejects_undeclared_event(self) -> None:
        interp = SyncInterpreter(create_machine(_PLAIN), strict=True).start()
        with self.assertRaises(UnknownEventError):
            interp.send("TYPO")
        interp.send("GO")  # a declared event still goes through
        self.assertEqual(interp.current_state_ids, {"m.b"})
        interp.stop()

    def test_strict_toggled_after_start_is_honoured(self) -> None:
        # 📝 `strict` is a plain attribute read live at the call site, so
        #    flipping it after start() must take effect on the next send.
        interp = SyncInterpreter(create_machine(_PLAIN)).start()
        interp.send("TYPO")  # lenient: silently unhandled
        interp.strict = True
        with self.assertRaises(UnknownEventError):
            interp.send("TYPO")
        interp.stop()

    def test_event_schema_rejects_bad_payload_without_strict(self) -> None:
        def schema(payload: Any) -> None:
            if "ok" not in payload:
                raise ValueError("missing ok")

        machine = create_machine(_PLAIN, event_schemas={"GO": schema})
        interp = SyncInterpreter(machine).start()
        with self.assertRaises(InvalidEventPayloadError):
            interp.send("GO")
        self.assertEqual(interp.current_state_ids, {"m.a"})
        interp.send("GO", ok=1)
        self.assertEqual(interp.current_state_ids, {"m.b"})
        interp.stop()

    def test_threadsafe_event_is_delivered_by_next_owner_send(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"order": []},
            "states": {
                "a": {
                    "on": {
                        "X": {"actions": "mark"},
                        "Y": {"actions": "mark"},
                    }
                }
            },
        }

        def mark(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ctx["order"].append(e.type)

        interp = SyncInterpreter(
            create_machine(cfg, logic=MachineLogic(actions={"mark": mark}))
        ).start()
        t = threading.Thread(target=lambda: interp.send_threadsafe("X"))
        t.start()
        t.join()
        self.assertEqual(interp.context["order"], [])  # parked, not run
        interp.send("Y")
        self.assertEqual(interp.context["order"], ["X", "Y"])
        interp.stop()


# -------------------------------------------------------------------------
# 4. timer pump gate
# -------------------------------------------------------------------------
class _CountingClock(SimulatedClock):
    """A subclass: `type(clock)` is not exactly `SimulatedClock`."""

    def __init__(self) -> None:
        super().__init__()
        self.pumps = 0

    def pump(self) -> int:
        self.pumps += 1
        return super().pump()


_TIMED = {
    "id": "t",
    "initial": "wait",
    "states": {
        "wait": {"after": {"100": "fired"}, "on": {"NOISE": {}}},
        "fired": {},
    },
}


class TestTimerPumpGate(unittest.TestCase):
    def test_clock_subclass_is_pumped_even_with_no_timers(self) -> None:
        clock = _CountingClock()
        interp = SyncInterpreter(create_machine(_PLAIN), clock=clock).start()
        before = clock.pumps
        interp.send("GO")
        self.assertGreater(clock.pumps, before)
        interp.stop()

    def test_simulated_clock_pending_timer_fires_on_unrelated_send(
        self,
    ) -> None:
        clock = SimulatedClock()
        interp = SyncInterpreter(create_machine(_TIMED), clock=clock).start()
        # 📝 `advance_sync` would fire the timer itself, which would hide
        #    the gate. Move virtual time directly so the deadline is DUE but
        #    still sitting in the heap; only send()'s pump can deliver it.
        clock._now += 0.15
        self.assertEqual(interp.current_state_ids, {"t.wait"})  # not pumped
        interp.send("NOISE")  # unrelated event -> send() pumps the heap
        self.assertEqual(interp.current_state_ids, {"t.fired"})
        interp.stop()


# -------------------------------------------------------------------------
# 5. always / invoke arming gate
# -------------------------------------------------------------------------
class TestAlwaysAndInvokeGate(unittest.TestCase):
    def test_sync_invoke_without_always_reaches_on_done(self) -> None:
        cfg = {
            "id": "m",
            "initial": "idle",
            "context": {"got": None},
            "states": {
                "idle": {"on": {"START": "loading"}},
                "loading": {
                    "invoke": {
                        "src": "svc",
                        "onDone": {"target": "done", "actions": "store"},
                    }
                },
                "done": {},
            },
        }

        def store(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ctx["got"] = e.data

        machine = create_machine(
            cfg,
            logic=MachineLogic(
                actions={"store": store},
                services={"svc": lambda i, ctx, e: 42},
            ),
        )
        self.assertFalse(machine.has_always_transitions)
        interp = SyncInterpreter(machine).start()
        interp.send("START")
        self.assertEqual(interp.current_state_ids, {"m.done"})
        self.assertEqual(interp.context["got"], 42)
        interp.stop()

    def test_machine_with_always_still_takes_it_after_event(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"ok": True},
            "states": {
                "a": {"on": {"GO": "check"}},
                "check": {"always": [{"target": "b", "guard": "isOk"}]},
                "b": {},
            },
        }
        machine = create_machine(
            cfg,
            logic=MachineLogic(guards={"isOk": lambda c, e: c["ok"]}),
        )
        self.assertTrue(machine.has_always_transitions)
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertEqual(interp.current_state_ids, {"m.b"})
        interp.stop()


# -------------------------------------------------------------------------
# 6. chain-reset ordering
# -------------------------------------------------------------------------
class TestChainResetOrder(unittest.TestCase):
    def test_self_send_chain_with_queued_caller_events(self) -> None:
        steps = 5
        cfg = {
            "id": "m",
            "initial": "a",
            "context": {"chain": 0, "work": 0, "order": []},
            "states": {
                "a": {
                    "on": {
                        "CHAIN": {"actions": "chain"},
                        "WORK": {"actions": "work"},
                    }
                }
            },
        }
        holder: Dict[str, Any] = {}

        def chain(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ctx["chain"] += 1
            ctx["order"].append("C")
            if ctx["chain"] < steps:
                holder["i"].send("CHAIN")  # self-send: queued behind us

        def work(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ctx["work"] += 1
            ctx["order"].append("W")

        interp = SyncInterpreter(
            create_machine(
                cfg, logic=MachineLogic(actions={"chain": chain, "work": work})
            )
        ).start()
        holder["i"] = interp
        # Two caller events already in the inbox when the drain opens.
        interp._event_queue.append(Event("WORK"))
        interp._event_queue.append(Event("WORK"))
        interp.send("CHAIN")
        self.assertEqual(interp.context["chain"], steps)
        self.assertEqual(interp.context["work"], 2)
        self.assertEqual(interp.context["order"], ["W", "W"] + ["C"] * steps)
        self.assertEqual(interp.status, "running")
        interp.stop()

    def test_runaway_raise_chain_is_cut_by_max_iterations(self) -> None:
        # 📝 The budget resets only when a chain has ENDED: internal queue
        #    empty and the inbox not grown. A reset taken while raised
        #    events are still queued would let this loop run forever, so
        #    the drain runs on its own thread under a watchdog.
        limit = 12
        cfg = {
            "id": "m",
            "initial": "a",
            "maxIterations": limit,
            "context": {"n": 0},
            "states": {
                "a": {
                    "on": {
                        "PING": {
                            "actions": [
                                "count",
                                {"type": "raise", "params": {"event": "PING"}},
                            ]
                        }
                    }
                }
            },
        }

        def count(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ctx["n"] += 1

        machine = create_machine(
            cfg, logic=MachineLogic(actions={"count": count})
        )
        result: Dict[str, Any] = {}

        def run() -> None:  # the interpreter lives on this thread
            interp = SyncInterpreter(machine).start()
            interp.send("PING")
            result["trips"] = interp.chain_trips
            result["n"] = interp.context["n"]
            result["status"] = interp.status
            interp.stop()

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(10.0)
        self.assertFalse(worker.is_alive(), "the raise loop was never cut")
        self.assertEqual(result["trips"], 1)
        # The caller's PING plus at most `limit` raised ones ran.
        self.assertGreaterEqual(result["n"], 1)
        self.assertLessEqual(result["n"], limit + 1)
        self.assertEqual(result["status"], "running")


# -------------------------------------------------------------------------
# 7. actions-only microstep, both engines
# -------------------------------------------------------------------------
def _shape_config(shape: str) -> Dict[str, Any]:
    side = {"entry": "enter", "exit": "leave"}
    if shape == "targetless":
        a = {"on": {"GO": {"actions": "act"}}, **side}
        return {"id": "m", "initial": "a", "states": {"a": a}}
    if shape == "self":
        a = {"on": {"GO": {"target": "a", "actions": "act"}}, **side}
        return {"id": "m", "initial": "a", "states": {"a": a}}
    if shape == "reenter":
        a = {
            "on": {"GO": {"target": "a", "reenter": True, "actions": "act"}},
            **side,
        }
        return {"id": "m", "initial": "a", "states": {"a": a}}
    # 📝 XState v5: a transition to the state itself is internal unless
    #    `reenter`, so a compound self-target only runs its actions too,
    #    but it takes the generic microstep (the fast path is atomic-only).
    p = {
        "initial": "c1",
        "on": {
            "GO": {
                "target": "p",
                "actions": "act",
                **({"reenter": True} if shape == "compound_reenter" else {}),
            }
        },
        "states": {"c1": {}},
        **side,
    }
    return {"id": "m", "initial": "p", "states": {"p": p}}


# shape -> whether exit/entry actions must run on each send
_SHAPES = {
    "targetless": False,
    "self": False,
    "reenter": True,
    "compound": False,
    "compound_reenter": True,
}


_ATOMIC = ("targetless", "self", "reenter")


def _shape_logic(log: List[str]) -> MachineLogic:
    return MachineLogic(
        actions={
            "act": lambda i, c, e, a: log.append("act"),
            "enter": lambda i, c, e, a: log.append("enter"),
            "leave": lambda i, c, e, a: log.append("leave"),
        }
    )


def _first_transition(machine: Any, shape: str) -> Any:
    node = machine.states["a" if shape in _ATOMIC else "p"]
    found = node.on["GO"]
    return found[0] if isinstance(found, (list, tuple)) else found


class _MicrostepAssertions:
    """Shared assertions; mixed into a `unittest.TestCase`."""

    def check(self, shape: str, log: List[str], notified: List[Any]) -> None:
        edges = 1 if _SHAPES[shape] else 0
        self.assertEqual(log.count("act"), 1, shape)  # type: ignore
        self.assertEqual(log.count("leave"), edges, shape)  # type: ignore
        self.assertEqual(log.count("enter"), edges, shape)  # type: ignore
        self.assertEqual(len(notified), 1, shape)  # type: ignore

    def check_plan(self, interp: Any, machine: Any, shape: str) -> None:
        plan = interp._plan_transition(
            _first_transition(machine, shape), Event("GO")
        )
        # 📝 The fast-path predicate and `_plan_transition` must agree:
        #    None exactly for the targetless and atomic-self shapes. The
        #    compound self-target is NOT None (it re-enters its initial
        #    child, which is why the fast path excludes `source.states`).
        if shape in ("targetless", "self"):
            self.assertIsNone(plan, shape)  # type: ignore
        else:
            self.assertIsNotNone(plan, shape)  # type: ignore


class TestActionsOnlyMicrostepSync(unittest.TestCase, _MicrostepAssertions):
    def test_each_shape(self) -> None:
        for shape in _SHAPES:
            with self.subTest(shape=shape):
                log: List[str] = []
                machine = create_machine(
                    _shape_config(shape), logic=_shape_logic(log)
                )
                interp = SyncInterpreter(machine).start()
                notified: List[Any] = []
                interp.subscribe(notified.append)
                log.clear()
                interp.send("GO")
                self.check(shape, log, notified)
                self.check_plan(interp, machine, shape)
                interp.stop()


class TestActionsOnlyMicrostepAsync(
    unittest.IsolatedAsyncioTestCase, _MicrostepAssertions
):
    async def test_each_shape(self) -> None:
        for shape in _SHAPES:
            with self.subTest(shape=shape):
                log: List[str] = []
                machine = create_machine(
                    _shape_config(shape), logic=_shape_logic(log)
                )
                interp = await Interpreter(machine).start()
                notified: List[Any] = []
                interp.subscribe(notified.append)
                log.clear()
                await interp.send("GO", wait=True)
                self.check(shape, log, notified)
                self.check_plan(interp, machine, shape)
                await interp.stop()


# -------------------------------------------------------------------------
# 8. guard DEBUG log
# -------------------------------------------------------------------------
class TestGuardLog(unittest.TestCase):
    def _machine(self, allowed: bool) -> Any:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": {"target": "b", "guard": "g"}}},
                "b": {},
            },
        }
        return create_machine(
            cfg,
            logic=MachineLogic(guards={"g": lambda c, e: allowed}),
        )

    def test_debug_logger_emits_evaluating_guard_record(self) -> None:
        interp = SyncInterpreter(self._machine(True)).start()
        with self.assertLogs(_LOGGER_NAME, level="DEBUG") as cm:
            interp.send("GO")
        self.assertTrue(
            any("Evaluating guard" in line for line in cm.output), cm.output
        )
        interp.stop()

    def test_guard_decides_transition_at_info_level(self) -> None:
        log = logging.getLogger(_LOGGER_NAME)
        old = log.level
        log.setLevel(logging.INFO)
        try:
            for allowed, expected in ((True, {"m.b"}), (False, {"m.a"})):
                interp = SyncInterpreter(self._machine(allowed)).start()
                interp.send("GO")
                self.assertEqual(interp.current_state_ids, expected)
                interp.stop()
        finally:
            log.setLevel(old)


if __name__ == "__main__":
    unittest.main()
