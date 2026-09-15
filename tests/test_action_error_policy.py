# tests/test_action_error_policy.py
# -----------------------------------------------------------------------------
# 🏛️ #27 (LC-01): an action that raises must not silently commit
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: before 0.8.0 `_execute_actions` returned None
# whether or not an action raised, so the transition committed either way and
# `on_transition` — documented as firing after a *successful* transition —
# reported a state whose own actions never finished building. On an order
# lifecycle that state was then persisted as truth.
#
# The fix is a per-machine `actionErrorPolicy` with the 0.7.x behaviour as the
# default, and a programmatic error channel under EVERY policy so a partial
# action list is always distinguishable from a complete one.
# -----------------------------------------------------------------------------
"""`actionErrorPolicy`: continue (default) | rollback | fail."""

import asyncio
import logging
import unittest
import warnings
from typing import Any, Dict, List, Tuple

from src.xstate_statemachine import (
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    TransitionFailedError,
    create_machine,
)
from src.xstate_statemachine.plugins import PluginBase


class _Quiet(unittest.TestCase):
    """Silence the library's logging for the duration of ONE test.

    🛡️ A module-level `logging.disable(CRITICAL)` leaks into every test
    that runs afterwards in the same process and breaks `assertLogs` there.
    Scoping it per-test with a cleanup is the project's convention.
    """

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


def _config(policy: str = None) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
        "id": "oms",
        "initial": "a",
        "context": {"trace": [], "n": 0},
        "states": {
            "a": {
                "on": {
                    "GO": {
                        "target": "b",
                        "actions": ["first", "explode", "third"],
                    }
                }
            },
            "b": {"entry": ["entry_b"]},
        },
    }
    if policy is not None:
        cfg["actionErrorPolicy"] = policy
    return cfg


def _logic() -> MachineLogic:
    def first(i, c, e, a):
        c["trace"].append("first")
        c["n"] += 1

    def explode(i, c, e, a):
        c["trace"].append("explode")
        raise RuntimeError("exchange rejected the order")

    def third(i, c, e, a):
        c["trace"].append("third")

    def entry_b(i, c, e, a):
        c["trace"].append("entry_b")

    return MachineLogic(
        actions={
            "first": first,
            "explode": explode,
            "third": third,
            "entry_b": entry_b,
        }
    )


class Spy(PluginBase):
    def __init__(self) -> None:
        self.transitions: List[List[str]] = []
        self.failed: List[List[str]] = []
        self.errors: List[str] = []
        self.order: List[str] = []

    def on_transition(self, interp, from_states, to_states, transition):
        # 📝 `start()` fires on_transition for the initial entry (event type
        #    `___xstate_statemachine_init___`). That is not the transition
        #    under test, so it is filtered out to keep assertions precise.
        if transition.source is interp.machine:
            return
        self.transitions.append(sorted(interp.current_state_ids))
        self.order.append("on_transition")

    def on_transition_failed(self, interp, transition, failed_actions):
        self.failed.append([a.type for a, _ in failed_actions])
        self.order.append("on_transition_failed")

    def on_error(self, interp, error):
        self.errors.append(type(error).__name__)


class TestContinueIsDefault(_Quiet):
    """`continue` keeps 0.7.x behaviour, but now REPORTS the failure."""

    def test_continue_is_default_and_reports_failed_actions(self) -> None:
        spy = Spy()
        interp = SyncInterpreter(create_machine(_config(), logic=_logic()))
        interp.use(spy)
        interp.start()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            interp.send("GO")

        # Byte-identical to 0.7.0: the transition committed.
        self.assertEqual(sorted(interp.current_state_ids), ["oms.b"])
        self.assertEqual(
            interp.context["trace"], ["first", "explode", "entry_b"]
        )
        self.assertEqual(interp.status, "running")
        # But the failure is now observable.
        self.assertFalse(interp.last_transition_ok)
        self.assertEqual(spy.failed, [["explode"]])
        # Ordering: failed BEFORE the (still-committed) on_transition.
        self.assertEqual(spy.order, ["on_transition_failed", "on_transition"])
        # And a one-shot DeprecationWarning about the 1.0 default flip.
        deprecations = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        self.assertEqual(len(deprecations), 1)
        self.assertIn("actionErrorPolicy", str(deprecations[0].message))

    def test_explicit_continue_emits_no_deprecation(self) -> None:
        interp = SyncInterpreter(
            create_machine(_config("continue"), logic=_logic())
        )
        interp.start()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            interp.send("GO")
        self.assertEqual(
            [w for w in caught if issubclass(w.category, DeprecationWarning)],
            [],
        )

    def test_successful_transition_sets_last_transition_ok(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
        interp = SyncInterpreter(create_machine(cfg, logic=MachineLogic()))
        interp.start()
        interp.send("GO")
        self.assertTrue(interp.last_transition_ok)


class TestRollback(_Quiet):
    """`rollback` aborts the transition and restores everything."""

    def test_rollback_does_not_commit_transition(self) -> None:
        spy = Spy()
        interp = SyncInterpreter(
            create_machine(_config("rollback"), logic=_logic())
        )
        interp.use(spy)
        interp.start()
        interp.send("GO")

        self.assertEqual(sorted(interp.current_state_ids), ["oms.a"])
        self.assertNotIn("entry_b", interp.context["trace"])
        self.assertEqual(interp.status, "running")
        self.assertFalse(interp.last_transition_ok)
        self.assertEqual(spy.failed, [["explode"]])
        # on_transition must NOT report a success that never happened.
        self.assertEqual(spy.transitions, [])

    def test_rollback_restores_context(self) -> None:
        interp = SyncInterpreter(
            create_machine(_config("rollback"), logic=_logic())
        )
        interp.start()
        interp.send("GO")
        # `first` incremented n and appended to trace; both are undone.
        self.assertEqual(interp.context["n"], 0)
        self.assertEqual(interp.context["trace"], [])

    def test_machine_keeps_working_after_rollback(self) -> None:
        """A rolled-back machine is not dead: it still handles events."""
        cfg = _config("rollback")
        cfg["states"]["a"]["on"]["OK"] = "b"
        interp = SyncInterpreter(create_machine(cfg, logic=_logic()))
        interp.start()
        interp.send("GO")  # rolled back
        interp.send("OK")  # clean path
        self.assertEqual(sorted(interp.current_state_ids), ["oms.b"])
        self.assertTrue(interp.last_transition_ok)


class TestFail(_Quiet):
    """`fail` rolls back then stops the interpreter."""

    def test_fail_stops_interpreter_with_error(self) -> None:
        spy = Spy()
        interp = SyncInterpreter(
            create_machine(_config("fail"), logic=_logic())
        )
        interp.use(spy)
        interp.start()
        interp.send("GO")

        self.assertEqual(interp.status, "error")
        self.assertIsInstance(interp.error, TransitionFailedError)
        # The ORIGINAL exception is retrievable, not just a message.
        self.assertIsInstance(interp.error.__cause__, RuntimeError)
        self.assertEqual(interp.error.action_type, "explode")
        self.assertEqual(sorted(interp.current_state_ids), ["oms.a"])
        self.assertEqual(spy.errors, ["TransitionFailedError"])


class TestAsyncInterpreterHonoursPolicy(_Quiet):
    """Both engines must agree — this is the class of bug #60 describes."""

    def _run(self, policy: str) -> Tuple[Any, Spy]:
        async def main():
            spy = Spy()
            interp = Interpreter(
                create_machine(_config(policy), logic=_logic())
            )
            interp.use(spy)
            await interp.start()
            await interp.send("GO")
            await asyncio.sleep(0.05)
            state = sorted(interp.current_state_ids)
            status = interp.status
            trace = list(interp.context["trace"])
            ok = interp.last_transition_ok
            await interp.stop()
            return (state, status, trace, ok), spy

        return asyncio.run(main())

    def test_async_rollback(self) -> None:
        (state, status, trace, ok), spy = self._run("rollback")
        self.assertEqual(state, ["oms.a"])
        self.assertEqual(status, "running")
        self.assertEqual(trace, [])
        self.assertFalse(ok)
        self.assertEqual(spy.failed, [["explode"]])
        self.assertEqual(spy.transitions, [])

    def test_async_fail(self) -> None:
        (state, status, trace, ok), spy = self._run("fail")
        self.assertEqual(status, "error")
        self.assertEqual(state, ["oms.a"])

    def test_async_continue_reports(self) -> None:
        (state, status, trace, ok), spy = self._run("continue")
        self.assertEqual(state, ["oms.b"])
        self.assertFalse(ok)
        self.assertEqual(spy.failed, [["explode"]])


class TestValidation(_Quiet):
    def test_invalid_policy_rejected_at_create(self) -> None:
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(_config("rollbak"), logic=_logic())
        self.assertIn("actionErrorPolicy", str(cm.exception))
        self.assertIn("rollbak", str(cm.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
