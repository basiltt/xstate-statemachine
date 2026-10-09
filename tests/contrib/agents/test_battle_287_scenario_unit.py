# tests/contrib/agents/test_battle_287_scenario_unit.py
"""#287 battle (scenario finding): tool arguments were validated only in
`run_tool`, AFTER the human gate -- a reviewer was asked to approve
`refund_order(amount_cents="all")`, a call that could never run. The
`toolAllowed` guard now validates arguments against the tool's schema,
so a schema-invalid call is `tool_denied` before anything is shown to a
human or executed; the error text names the field, never the value."""

from __future__ import annotations

import asyncio
import unittest

import pytest

pytest.importorskip("pydantic")

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    run_agent,
    tool,
    tool_registry,
)


def refund(order_id: int, amount_cents: int) -> str:
    return f"refunded {amount_cents} on {order_id}"


class TestArgsBeforeHumanGate(unittest.TestCase):
    def _run(self, args: dict) -> object:
        tools = tool_registry(tool(refund, timeout_s=5, side_effect=True))
        model = FakeModel([{"tool": "refund", "args": args}, {"text": "done"}])
        return asyncio.run(run_agent(model=model, tools=tools, prompt="x"))

    def test_bad_args_are_denied_not_parked(self) -> None:
        res = self._run({"order_id": 1, "amount_cents": "all-of-it"})
        self.assertFalse(res.waiting)
        self.assertTrue(res.final_state.endswith("error"), res.final_state)
        self.assertEqual(res.error["kind"], "tool_denied")
        self.assertIn("amount_cents", res.error["message"])
        self.assertNotIn("all-of-it", res.error["message"])

    def test_good_args_still_park_for_the_human(self) -> None:
        res = self._run({"order_id": 1, "amount_cents": 5})
        self.assertTrue(res.waiting)
        self.assertTrue(res.final_state.endswith("awaiting_human"))
