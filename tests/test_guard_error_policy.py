# tests/test_guard_error_policy.py
# -----------------------------------------------------------------------------
# 🏛️ #35 (LC-09): a raising guard must be distinguishable from a False one
# -----------------------------------------------------------------------------
"""`guardErrorPolicy`: false (default) | true | raise."""

import asyncio
import logging
import unittest
from typing import Any, Dict, List

from src.xstate_statemachine import (
    Interpreter,
    InvalidConfigError,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.plugins import PluginBase


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


def _cfg(policy: str = None) -> Dict[str, Any]:
    cfg: Dict[str, Any] = {
        "id": "m",
        "initial": "s",
        "states": {
            "s": {
                "on": {
                    "GO": [
                        {"target": "guarded", "guard": "risk_ok"},
                        {"target": "fallback"},
                    ]
                }
            },
            "guarded": {},
            "fallback": {},
        },
    }
    if policy is not None:
        cfg["guardErrorPolicy"] = policy
    return cfg


def _raising_logic() -> MachineLogic:
    def risk_ok(c, e):
        raise ValueError("risk service unavailable")

    return MachineLogic(guards={"risk_ok": risk_ok})


class Spy(PluginBase):
    def __init__(self) -> None:
        self.seen: List[Any] = []

    def on_guard_evaluated(self, i, name, event, result):
        self.seen.append(("evaluated", name, result))

    def on_guard_error(self, i, name, event, error):
        self.seen.append(("error", name, type(error).__name__))


class TestDefaultFalse(_Quiet):
    def test_raising_guard_defaults_to_false(self) -> None:
        spy = Spy()
        i = SyncInterpreter(create_machine(_cfg(), logic=_raising_logic()))
        i.use(spy)
        i.start()
        i.send("GO")
        # 0.7.x behaviour preserved: falls to the unguarded branch.
        self.assertEqual(i.current_state_ids, {"m.fallback"})
        self.assertEqual(i.status, "running")
        # ...but the failure is now observable, BEFORE the substituted result.
        self.assertEqual(
            spy.seen,
            [
                ("error", "risk_ok", "ValueError"),
                ("evaluated", "risk_ok", False),
            ],
        )

    def test_false_returning_guard_does_not_fire_error_hook(self) -> None:
        """The whole point: a raise and a False must look DIFFERENT."""
        spy = Spy()
        logic = MachineLogic(guards={"risk_ok": lambda c, e: False})
        i = SyncInterpreter(create_machine(_cfg(), logic=logic))
        i.use(spy)
        i.start()
        i.send("GO")
        self.assertEqual(spy.seen, [("evaluated", "risk_ok", False)])


class TestTruePolicy(_Quiet):
    def test_true_selects_guarded_branch(self) -> None:
        i = SyncInterpreter(
            create_machine(_cfg("true"), logic=_raising_logic())
        )
        i.start()
        i.send("GO")
        self.assertEqual(i.current_state_ids, {"m.guarded"})


class TestRaisePolicy(_Quiet):
    def test_raise_propagates_in_sync_interpreter(self) -> None:
        i = SyncInterpreter(
            create_machine(_cfg("raise"), logic=_raising_logic())
        )
        i.start()
        with self.assertRaises(ValueError):
            i.send("GO")
        # #152: the raise cancels only ITS candidate. The unguarded
        # fallback in the same array is still taken, and the exception
        # still reaches the caller. Machine intact and still usable.
        self.assertEqual(i.current_state_ids, {"m.fallback"})
        self.assertEqual(i.status, "running")
        self.assertFalse(i.last_transition_ok)
        self.assertIsInstance(i.last_error, ValueError)

    def test_raise_keeps_async_interpreter_running(self) -> None:
        async def main():
            spy = Spy()
            i = Interpreter(
                create_machine(_cfg("raise"), logic=_raising_logic())
            )
            i.use(spy)
            await i.start()
            await i.send("GO")
            await asyncio.sleep(0.05)
            out = (i.current_state_ids, i.status, spy.seen)
            await i.stop()
            return out

        state, status, seen = asyncio.run(main())
        # The run loop contains the error and stays alive.
        self.assertEqual(state, {"m.fallback"})  # #152: fallback taken
        self.assertEqual(status, "running")
        self.assertEqual(seen, [("error", "risk_ok", "ValueError")])


class TestValidation(_Quiet):
    def test_invalid_policy_rejected(self) -> None:
        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(_cfg("maybe"), logic=_raising_logic())
        self.assertIn("guardErrorPolicy", str(cm.exception))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
