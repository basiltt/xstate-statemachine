# tests/test_unhandled_events.py
# -----------------------------------------------------------------------------
# 🏛️ #28 (LC-03): events with no handler must not vanish without trace
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: per XState an unhandled event is silently
# ignored, and that stays the default. But an OMS machine awaiting an
# exchange ack loses every fill that arrives one microstep early -- no
# error, no hook, no way to test for it. `onUnhandled` makes the behaviour a
# per-machine policy, and `on_unhandled_event` makes every drop observable
# regardless of policy.
#
# `defer` is library-owned rather than a userland pattern because that is
# what makes it correct: replay is at the HEAD of the queue in original order
# (ahead of live traffic), the buffer survives a snapshot, and it is bounded.
# -----------------------------------------------------------------------------
"""`onUnhandled`: ignore (default) | defer | error."""

import asyncio
import logging
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    UnhandledEventError,
    create_machine,
)
from src.xstate_statemachine.plugins import PluginBase


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


def _oms(policy: str = None) -> Dict[str, Any]:
    """The filer's OMS shape: `submitting` has no PARTIAL/FILL handler."""
    cfg: Dict[str, Any] = {
        "id": "oms",
        "initial": "idle",
        "context": {"filled": 0, "seen": []},
        "states": {
            "idle": {"on": {"NEW": "submitting"}},
            "submitting": {"on": {"ACK": "live"}},
            "live": {
                "on": {
                    "PARTIAL": {"actions": ["apply"]},
                    "FILL": {"target": "filled", "actions": ["apply"]},
                }
            },
            "filled": {"type": "final"},
        },
    }
    if policy is not None:
        cfg["onUnhandled"] = policy
    return cfg


def _logic() -> MachineLogic:
    def apply(i, c, e, a):
        c["filled"] += e.payload["qty"]
        c["seen"].append(e.payload["qty"])

    return MachineLogic(actions={"apply": apply})


class Spy(PluginBase):
    def __init__(self) -> None:
        self.unhandled: List[Any] = []

    def on_unhandled_event(self, interp, event, active, disposition):
        self.unhandled.append((event.type, sorted(active), disposition))


class TestIgnoreIsDefault(_Quiet):
    def test_ignore_is_default_and_unchanged(self) -> None:
        spy = Spy()
        i = SyncInterpreter(create_machine(_oms(), logic=_logic()))
        i.use(spy)
        i.start()
        i.send("NEW")
        i.send({"type": "PARTIAL", "qty": 10})
        # 0.7.0 behaviour: dropped, machine unaffected...
        self.assertEqual(i.context["filled"], 0)
        self.assertEqual(sorted(i.current_state_ids), ["oms.submitting"])
        self.assertEqual(i.status, "running")
        # ...but now OBSERVABLE.
        self.assertEqual(
            spy.unhandled, [("PARTIAL", ["oms.submitting"], "ignored")]
        )

    def test_system_events_are_not_reported_as_unhandled(self) -> None:
        """`after.*` / `done.*` the machine did not ask for are exempt."""
        spy = Spy()
        cfg = {
            "id": "t",
            "initial": "a",
            "onUnhandled": "error",
            "states": {"a": {"after": {"10": "b"}}, "b": {}},
        }
        i = SyncInterpreter(create_machine(cfg, logic=MachineLogic()))
        i.use(spy)
        i.start()
        import time

        time.sleep(0.1)
        i.tick()  # #50: the sync engine delivers due timers on a pump
        self.assertEqual(sorted(i.current_state_ids), ["t.b"])
        self.assertEqual(i.status, "running")
        self.assertEqual(spy.unhandled, [])
        i.stop()


class TestErrorPolicy(_Quiet):
    def test_error_policy_raises_unhandled_event_error(self) -> None:
        spy = Spy()
        i = SyncInterpreter(create_machine(_oms("error"), logic=_logic()))
        i.use(spy)
        i.start()
        i.send("NEW")
        i.send({"type": "PARTIAL", "qty": 10})

        self.assertEqual(i.status, "error")
        self.assertIsInstance(i.error, UnhandledEventError)
        self.assertEqual(i.error.event_type, "PARTIAL")
        self.assertEqual(i.error.active_states, ["oms.submitting"])
        self.assertIn("PARTIAL", str(i.error))
        self.assertIn("oms.submitting", str(i.error))
        self.assertEqual(
            spy.unhandled, [("PARTIAL", ["oms.submitting"], "errored")]
        )


class TestDeferPolicy(_Quiet):
    def test_defer_delivers_after_state_change(self) -> None:
        i = SyncInterpreter(create_machine(_oms("defer"), logic=_logic()))
        i.start()
        i.send("NEW")
        i.send({"type": "PARTIAL", "qty": 10})
        i.send({"type": "PARTIAL", "qty": 10})
        i.send({"type": "FILL", "qty": 10})
        self.assertEqual(i.deferred_count, 3)
        self.assertEqual(i.context["filled"], 0)

        i.send("ACK")  # -> live; deferred fills replay

        self.assertEqual(sorted(i.current_state_ids), ["oms.filled"])
        self.assertEqual(i.context["filled"], 30)
        self.assertEqual(i.deferred_count, 0)

    def test_defer_preserves_original_order_ahead_of_live_traffic(
        self,
    ) -> None:
        """Deferred events run BEFORE anything sent after the state change."""
        cfg = _oms("defer")
        # Make live handle a LATE event too, so we can see ordering.
        cfg["states"]["live"]["on"]["LATE"] = {"actions": ["apply"]}
        i = SyncInterpreter(create_machine(cfg, logic=_logic()))
        i.start()
        i.send("NEW")
        i.send({"type": "PARTIAL", "qty": 1})
        i.send({"type": "PARTIAL", "qty": 2})
        # ACK moves to live; the deferred 1,2 must land before LATE(99).
        i.send("ACK")
        i.send({"type": "LATE", "qty": 99})
        self.assertEqual(i.context["seen"], [1, 2, 99])

    def test_still_unhandled_events_stay_deferred_not_dropped(self) -> None:
        spy = Spy()
        cfg = {
            "id": "m",
            "initial": "a",
            "onUnhandled": "defer",
            "states": {
                "a": {"on": {"NEXT": "b"}},
                "b": {"on": {"NEXT": "c"}},
                "c": {"on": {"X": "d"}},
                "d": {},
            },
        }
        i = SyncInterpreter(create_machine(cfg, logic=MachineLogic()))
        i.use(spy)
        i.start()
        i.send("X")  # unhandled in a -> deferred
        i.send("NEXT")  # a->b; X replayed, still unhandled -> re-deferred
        self.assertEqual(sorted(i.current_state_ids), ["m.b"])
        self.assertEqual(i.deferred_count, 1)
        i.send("NEXT")  # b->c; X replayed, NOW handled -> d
        self.assertEqual(sorted(i.current_state_ids), ["m.d"])
        self.assertEqual(i.deferred_count, 0)
        dispositions = [d for _, _, d in spy.unhandled]
        self.assertNotIn("dropped", dispositions)

    def test_defer_survives_snapshot_restore(self) -> None:
        i = SyncInterpreter(create_machine(_oms("defer"), logic=_logic()))
        i.start()
        i.send("NEW")
        i.send({"type": "PARTIAL", "qty": 10})
        i.send({"type": "PARTIAL", "qty": 10})
        i.send({"type": "FILL", "qty": 10})
        persisted = i.get_persisted_snapshot()
        self.assertEqual(len(persisted["deferred"]), 3)
        snap = i.get_snapshot()

        machine = create_machine(_oms("defer"), logic=_logic())
        j = SyncInterpreter.from_snapshot(snap, machine)
        self.assertEqual(j.deferred_count, 3)
        j.send("ACK")
        self.assertEqual(j.context["filled"], 30)
        self.assertEqual(sorted(j.current_state_ids), ["oms.filled"])

    def test_defer_max_overflow_is_reported(self) -> None:
        spy = Spy()
        cfg = {
            "id": "m",
            "initial": "a",
            "onUnhandled": "defer",
            "states": {"a": {}},
        }
        i = SyncInterpreter(create_machine(cfg, logic=MachineLogic()))
        i.DEFER_MAX = 3
        i.use(spy)
        i.start()
        for n in range(5):
            i.send({"type": "E", "n": n})
        self.assertEqual(i.deferred_count, 3)
        dropped = [(e, d) for e, _, d in spy.unhandled if d == "dropped"]
        self.assertEqual(len(dropped), 2)


class TestValidation(_Quiet):
    def test_invalid_policy_rejected(self) -> None:
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(_oms("maybe"), logic=_logic())
        self.assertIn("onUnhandled", str(cm.exception))


class TestAsyncParity(_Quiet):
    """The async engine must behave identically -- the #60 class of bug."""

    def test_async_defer_with_invoke_done(self) -> None:
        """The filer's exact scenario: fills arrive while an invoke is pending."""
        cfg = {
            "id": "oms",
            "initial": "idle",
            "context": {"filled": 0},
            "onUnhandled": "defer",
            "states": {
                "idle": {"on": {"NEW": "submitting"}},
                "submitting": {
                    "invoke": {"src": "place", "onDone": {"target": "live"}}
                },
                "live": {
                    "on": {
                        "PARTIAL": {"actions": ["apply"]},
                        "FILL": {"target": "filled", "actions": ["apply"]},
                    }
                },
                "filled": {"type": "final"},
            },
        }

        async def main():
            def apply(i, c, e, a):
                c["filled"] += e.payload["qty"]

            async def place(i, c, e):
                await asyncio.sleep(0.05)
                return "ok"

            logic = MachineLogic(
                actions={"apply": apply}, services={"place": place}
            )
            i = Interpreter(create_machine(cfg, logic=logic))
            await i.start()
            await i.send("NEW")
            await i.send({"type": "PARTIAL", "qty": 10})
            await i.send({"type": "PARTIAL", "qty": 10})
            await i.send({"type": "FILL", "qty": 10})
            await asyncio.sleep(0.3)
            out = (sorted(i.current_state_ids), i.context["filled"], i.status)
            await i.stop()
            return out

        state, filled, status = asyncio.run(main())
        self.assertEqual(state, ["oms.filled"])
        self.assertEqual(filled, 30)
        self.assertEqual(status, "done")

    def test_async_error_policy(self) -> None:
        async def main():
            i = Interpreter(create_machine(_oms("error"), logic=_logic()))
            await i.start()
            await i.send("NEW")
            await i.send({"type": "PARTIAL", "qty": 10})
            await asyncio.sleep(0.05)
            out = (i.status, type(i.error).__name__)
            await i.stop()
            return out

        status, err = asyncio.run(main())
        self.assertEqual(status, "error")
        self.assertEqual(err, "UnhandledEventError")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
