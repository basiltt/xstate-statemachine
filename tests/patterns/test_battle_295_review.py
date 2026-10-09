# tests/patterns/test_battle_295_review.py
"""#295 independent review -- regressions.

* **H2** `context.input` exists in BOTH chart shapes (immediate start has
  no START; services read ``None``, never `KeyError`);
* **H3** `timeout_ms=5000.0` (and any integral number) keeps working;
  ``True`` / ``0`` / ``1.5`` / ``"abc"`` are refused;
* **M5** a wildcard or whitespace `start_event` is refused;
* **C1** the generated chart's structure hash CHANGED (the `sagaStart`
  action): a snapshot of a saga built by the previous builder does not
  load without `verify_machine_hash=False` -- pinned here so the fact is
  visible, and documented in the EDA guide's upgrade note.
"""

from __future__ import annotations

import unittest

from src.xstate_statemachine import (
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.patterns import SagaBuilder


def _svc(seen: list):
    def svc(i, ctx, e):
        seen.append(ctx["input"])  # must never KeyError
        return 1

    return svc


class TestInput(unittest.TestCase):
    def test_immediate_start_has_input_none(self) -> None:
        seen: list = []
        b = SagaBuilder("s").step("a", invoke="A")
        m = create_machine(
            b.build(),
            logic=b.logic().merge(MachineLogic(services={"A": _svc(seen)})),
        )
        i = SyncInterpreter(m).start()
        self.assertIn("s.completed", i.current_state_ids)
        self.assertEqual(seen, [None])
        i.stop()

    def test_start_event_payload_is_input(self) -> None:
        seen: list = []
        b = SagaBuilder("s", start_event="GO").step("a", invoke="A")
        m = create_machine(
            b.build(),
            logic=b.logic().merge(MachineLogic(services={"A": _svc(seen)})),
        )
        i = SyncInterpreter(m).start()
        self.assertIsNone(i.context["input"])
        i.send("GO", order="o-1")
        self.assertEqual(seen, [{"order": "o-1"}])
        i.stop()


class TestTimeout(unittest.TestCase):
    def test_integral_numbers_accepted(self) -> None:
        for v in (5000, 5000.0):
            b = SagaBuilder("s").step("a", invoke="A", timeout_ms=v)
            self.assertEqual(b.steps[0].timeout_ms, 5000)

    def test_bad_values_refused(self) -> None:
        for v in (True, 0, -1, 1.5, "abc", float("nan")):
            with self.assertRaises(ValueError, msg=repr(v)):
                SagaBuilder("s").step("a", invoke="A", timeout_ms=v)


class TestStartEvent(unittest.TestCase):
    def test_wildcard_and_whitespace_refused(self) -> None:
        for ev in ("*", "ORDER.*", "GO NOW", " GO"):
            with self.assertRaises(ValueError, msg=ev):
                SagaBuilder("s", start_event=ev)


class TestHashChange(unittest.TestCase):
    def test_start_transition_now_carries_saga_start(self) -> None:
        cfg = SagaBuilder("s", start_event="GO").step("a", invoke="A").build()
        self.assertEqual(
            cfg["states"]["idle"]["on"]["GO"],
            {"target": "steps", "actions": ["sagaStart"]},
        )
        self.assertIn("input", cfg["context"])
