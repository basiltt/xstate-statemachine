# tests/contrib/agents/test_battle_287_review.py
"""#287 independent review -- regressions.

* **H1** a hung SYNC model under `run_agent` must not pin the loop's
  default executor: `asyncio.run(run_agent(..., timeout_s=))` returns;
* **M1** `FakeModel` ids are unique across instances (a store resume
  with a fresh scripted model is not a "duplicate id"); ids from turns
  the window trimmed are still remembered (`spent_call_ids`);
* **M2** the message window never strands a `tool` result;
* **M3** a validation error that is not `ToolDeniedError` still ends in
  `tool_denied` and clears the pending calls;
* **L1** `Usage.from_dict` takes ``"1.5"`` token counts;
* **L3** the human sees exactly the arguments `run_tool` executes
  (strict schema: ``"42"`` is refused, not coerced).
"""

from __future__ import annotations

import asyncio
import time
import unittest

import pytest

pytest.importorskip("pydantic")

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    run_agent,
    tool,
    tool_registry,
)
from src.xstate_statemachine.contrib.agents.messages import Usage  # noqa: E402
from src.xstate_statemachine.persistence import MemoryStore  # noqa: E402


def ping() -> str:
    return "pong"


def refund(order_id: int, amount_cents: int) -> str:
    return f"{order_id}:{amount_cents}"


class TestHungSyncModel(unittest.TestCase):
    def test_asyncio_run_returns_despite_a_hung_sync_model(self) -> None:
        def hung(messages, tools):  # a sync SDK call that never returns
            time.sleep(30)

        t0 = time.perf_counter()
        try:
            res = asyncio.run(
                run_agent(
                    model=hung,
                    tools=tool_registry(ping),
                    prompt="x",
                    model_timeout_s=0.2,
                    timeout_s=2.0,
                )
            )
            ended = res.final_state
        except asyncio.TimeoutError:
            ended = "timeout_s"  # the documented real-time bound
        took = time.perf_counter() - t0
        # 🔥 the point: `asyncio.run` RETURNS (the default executor would
        #    have waited for the 30 s sleep on exit)
        self.assertLess(took, 6.0, took)
        self.assertTrue(ended == "timeout_s" or ended.endswith("error"), ended)


class TestCallIds(unittest.TestCase):
    def test_fresh_fake_model_after_resume_is_not_a_duplicate(self) -> None:
        store = MemoryStore()
        tools = tool_registry(tool(refund, timeout_s=5, side_effect=True))
        first = asyncio.run(
            run_agent(
                model=FakeModel(
                    [
                        {
                            "tool": "refund",
                            "args": {"order_id": 1, "amount_cents": 5},
                        }
                    ]
                ),
                tools=tools,
                prompt="x",
                store=store,
                key="k",
            )
        )
        self.assertTrue(first.waiting)
        # a restarted process: a NEW FakeModel continuing the conversation
        second = asyncio.run(
            run_agent(
                model=FakeModel([{"text": "done"}]),
                tools=tools,
                store=store,
                key="k",
                approve=True,
            )
        )
        self.assertTrue(second.final_state.endswith("done"), second.error)

    def test_reused_id_from_a_trimmed_turn_is_still_denied(self) -> None:
        script = [
            {"tool_calls": [{"id": "fixed", "name": "ping", "arguments": {}}]}
        ]
        script = script * 4 + [{"text": "done"}]
        res = asyncio.run(
            run_agent(
                model=FakeModel(script),
                tools=tool_registry(ping),
                prompt="x",
                max_messages=3,
                max_turns=10,
            )
        )
        self.assertTrue(res.final_state.endswith("error"), res.final_state)
        self.assertEqual(res.error["kind"], "tool_denied")
        self.assertIn("duplicate", res.error["message"])


class TestWindow(unittest.TestCase):
    def test_no_orphan_tool_result_after_trimming(self) -> None:
        res = asyncio.run(
            run_agent(
                model=FakeModel([{"tool": "ping"}] * 6 + [{"text": "done"}]),
                tools=tool_registry(ping),
                prompt="TASK",
                max_messages=4,
                max_turns=20,
            )
        )
        msgs = res.context["messages"]
        self.assertEqual(msgs[0]["content"], "TASK")
        for prev, cur in zip(msgs, msgs[1:]):
            if cur["role"] == "tool":
                self.assertEqual(prev["role"], "assistant", msgs)


class TestValidationFailures(unittest.TestCase):
    def test_non_tooldenied_validation_error_is_tool_denied(self) -> None:
        from src.xstate_statemachine.contrib.agents import tools as tmod

        reg = tool_registry(tool(refund, timeout_s=5, side_effect=True))
        t = reg.get("refund")
        real = t.args_model

        class Boom:
            @staticmethod
            def model_validate(args):
                raise RuntimeError("schema machinery broke")

            @staticmethod
            def model_json_schema():
                return real.model_json_schema()

            model_fields: dict = {}

        # frozen dataclass: swap the args model underneath
        object.__setattr__(t, "args_model", Boom)
        try:
            res = asyncio.run(
                run_agent(
                    model=FakeModel(
                        [
                            {
                                "tool": "refund",
                                "args": {"order_id": 1, "amount_cents": 5},
                            }
                        ]
                    ),
                    tools=reg,
                    prompt="x",
                )
            )
        finally:
            object.__setattr__(t, "args_model", real)
        self.assertEqual(res.error["kind"], "tool_denied", res.error)
        self.assertEqual(res.context["pending_tool_calls"], [])
        del tmod

    def test_strict_schema_refuses_coercible_strings(self) -> None:
        res = asyncio.run(
            run_agent(
                model=FakeModel(
                    [
                        {
                            "tool": "refund",
                            "args": {"order_id": "42", "amount_cents": 5},
                        }
                    ]
                ),
                tools=tool_registry(
                    tool(refund, timeout_s=5, side_effect=True)
                ),
                prompt="x",
            )
        )
        self.assertFalse(res.waiting)  # never shown to a human
        self.assertEqual(res.error["kind"], "tool_denied")
        self.assertNotIn("42", res.error["message"])


class TestUsage(unittest.TestCase):
    def test_float_strings_are_token_counts(self) -> None:
        u = Usage.from_dict({"input_tokens": "1.5", "output_tokens": 2.0})
        self.assertEqual((u.input_tokens, u.output_tokens), (1, 2))
