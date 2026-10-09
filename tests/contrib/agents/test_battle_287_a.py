# tests/contrib/agents/test_battle_287_a.py
"""#287 battle, adversary A: the agent safety surface (X0.13) and the
loop under faults. Every test here failed before its fix."""

from __future__ import annotations

import asyncio
import logging
import math
import time
import unittest
from typing import Any, Dict, List

import pytest

pytest.importorskip("pydantic")

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    agent_logic,
    run_agent,
    run_agent_sync,
    tool,
    tool_registry,
)
from src.xstate_statemachine.contrib.agents.core import (  # noqa: E402
    Budget,
)
from src.xstate_statemachine.contrib.agents.messages import (  # noqa: E402
    AgentConfigError,
    ModelResponse,
    ToolCall,
)
from src.xstate_statemachine.contrib.agents.providers.anthropic import (  # noqa: E402
    from_anthropic_response,
    to_anthropic_messages,
)
from src.xstate_statemachine.contrib.agents.providers.openai import (  # noqa: E402
    to_openai_messages,
)
from src.xstate_statemachine.patterns.retry import RetryPolicy  # noqa: E402
from src.xstate_statemachine.persistence import MemoryStore  # noqa: E402

RAN: List[str] = []


def look(q: str) -> str:
    RAN.append(q)
    return "r"


def ping() -> str:
    RAN.append("ping")
    return "pong"


def refund(n: int) -> str:
    RAN.append(f"refund {n}")
    return "ok"


def _sync(resp: Any, **kw: Any) -> Any:
    # 📝 One proposed call, then a final answer.
    model = FakeModel([resp, {"text": "ok"}], is_async=False)
    return run_agent_sync(
        model=model, tools=tool_registry(look, ping), prompt="x", **kw
    )


def _deep(n: int) -> Dict[str, Any]:
    d: Dict[str, Any] = {}
    for _ in range(n):
        d = {"q": d}
    return d


class TestArgumentShapes(unittest.TestCase):
    """🛡️ Non-object arguments are denied, never coerced or crashed on."""

    def setUp(self) -> None:
        RAN.clear()
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)

    def _denied(self, args: Any) -> None:
        resp = ModelResponse(tool_calls=[ToolCall("c1", "look", args)])
        res = _sync(resp)
        self.assertTrue(res.final_state.endswith("error"), res.final_state)
        self.assertEqual(res.error["kind"], "tool_denied")
        self.assertEqual(RAN, [])

    def test_list_of_pairs_is_not_coerced_to_an_object(self) -> None:
        # 🔥 was: dict([["q","a"]]) → {"q": "a"} and the tool RAN.
        self._denied([["q", "a"]])

    def test_string_arguments_denied_not_crash(self) -> None:
        # 🔥 was: TypeError in denyTool → machine stopped mid-transition.
        self._denied("q=a")

    def test_int_arguments_denied_not_crash(self) -> None:
        self._denied(5)

    def test_deeply_nested_arguments_are_denied_not_retried(self) -> None:
        # 🔥 was: RecursionError in callModel → timed_out → re-billed.
        self._denied(_deep(1500))


class TestNameSpoofing(unittest.TestCase):
    def setUp(self) -> None:
        RAN.clear()

    def test_case_space_unicode_variants_denied(self) -> None:
        for name in ("Look", "look ", "ｌook", "LOOK"):
            resp = ModelResponse(tool_calls=[ToolCall("c", name, {"q": "a"})])
            res = _sync(resp)
            self.assertEqual(res.error["kind"], "tool_denied", name)
        self.assertEqual(RAN, [])


class TestCallIdReuse(unittest.TestCase):
    """🔥 A model re-using an approved call id must not let a replayed
    HUMAN_APPROVED (or a stale reviewer page) approve a NEW call."""

    def setUp(self) -> None:
        RAN.clear()

    def test_reused_id_is_denied_before_the_human(self) -> None:
        tools = tool_registry(look, tool(refund, side_effect=True))
        model = FakeModel(
            [
                {"tool": "refund", "args": {"n": 1}, "id": "X"},
                {"tool": "refund", "args": {"n": 999}, "id": "X"},
                {"text": "ok"},
            ]
        )
        store = MemoryStore()

        async def go() -> Any:
            kw = dict(model=model, tools=tools, store=store, key="k")
            await run_agent(prompt="p", **kw)
            approve = {"type": "HUMAN_APPROVED", "call_ids": ["X"]}
            await run_agent(event=approve, **kw)
            return await run_agent(event=approve, **kw)

        res = asyncio.run(go())
        self.assertEqual(RAN, ["refund 1"])
        self.assertEqual(res.error["kind"], "tool_denied")
        self.assertIn("duplicate", res.error["message"])


class TestBudgetValidation(unittest.TestCase):
    def test_bad_budgets_fail_loudly(self) -> None:
        bad = (
            {"max_tokens": "20"},
            {"max_turns": True},
            {"max_turns": -1},
            {"max_turns": 2.5},
            {"max_usd": math.nan},
            {"max_usd": -0.01},
            {"max_usd": math.inf},
            {"max_tokens": 10, "bogus": 1},
        )
        for b in bad:
            with self.assertRaises(AgentConfigError, msg=repr(b)):
                agent_logic(FakeModel([]), budgets=b)

    def test_good_budgets_accepted(self) -> None:
        Budget(max_tokens=0, max_usd=1, max_turns=0)
        Budget(max_usd=0.5, max_turns=None)

    def test_max_turns_zero_refuses_the_first_turn(self) -> None:
        model = FakeModel([{"text": "ok"}], is_async=False)
        res = run_agent_sync(model=model, prompt="x", max_turns=0)
        self.assertEqual(res.error["kind"], "budget")
        self.assertEqual(model.calls, [])


class TestHostileUsage(unittest.TestCase):
    def _run(self, usage: Dict[str, Any], **budget: Any) -> Any:
        script: List[Any] = [{"tool": "ping", "usage": usage}]
        script += [{"tool": "ping"}] * 5 + [{"text": "ok"}]
        model = FakeModel(script, is_async=False)
        res = run_agent_sync(
            model=model,
            tools=tool_registry(ping),
            prompt="x",
            budgets={"max_turns": None, **budget},
        )
        return res, model

    def test_negative_tokens_cannot_refund_the_budget(self) -> None:
        # 🔥 was: -1000 tokens bought ~65 more turns under max_tokens=20.
        res, model = self._run({"input_tokens": -1000}, max_tokens=20)
        self.assertEqual(res.error["kind"], "budget")
        self.assertEqual(len(model.calls), 2)
        self.assertGreaterEqual(res.context["tokens_in"], 0)

    def test_negative_cost_cannot_refund_the_budget(self) -> None:
        # 📝 was: cost_usd went to -50, a credit against every later turn.
        res, _ = self._run({"cost_usd": -50.0}, max_turns=3)
        self.assertEqual(res.context["cost_usd"], 0.0)

    def test_nan_and_huge_usage_fail_closed(self) -> None:
        res, _ = self._run({"cost_usd": math.inf}, max_usd=1.0)
        self.assertEqual(res.error["kind"], "budget")
        self.assertTrue(math.isfinite(res.context["cost_usd"]))
        res, _ = self._run({"input_tokens": 10**30}, max_tokens=10**9)
        self.assertEqual(res.error["kind"], "budget")


class TestOutputModelSpec(unittest.TestCase):
    def test_unresolvable_module_is_agent_config_error(self) -> None:
        for spec in ("no_such_mod_xyz:Model", "json:NoSuchAttr"):
            with self.assertRaises(AgentConfigError, msg=spec):
                agent_logic(FakeModel([]), output_model=spec)


def _slow_model(delay: float) -> Any:
    def call(messages: Any, tools: Any) -> Dict[str, Any]:
        time.sleep(delay)
        return {"text": "late"}

    return call


class TestHungSyncModelUnderAsync(unittest.TestCase):
    """🔥 A sync model under `run_agent` blocked the macrostep: neither
    `model_timeout_s` nor `timeout_s` could fire until it returned."""

    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)

    def tearDown(self) -> None:
        logging.disable(logging.NOTSET)

    def test_model_timeout_pre_empts_a_hung_sync_model(self) -> None:
        policy = RetryPolicy(max_attempts=1, base_ms=1, jitter="none")

        async def go() -> Any:
            t0 = time.monotonic()
            res = await run_agent(
                model=_slow_model(1.5),
                prompt="x",
                model_timeout_s=0.1,
                retry=policy,
            )
            return res, time.monotonic() - t0

        res, took = asyncio.run(go())
        self.assertTrue(res.final_state.endswith("error"))
        self.assertLess(took, 1.0)

    def test_run_timeout_bounds_the_whole_run(self) -> None:
        async def go() -> float:
            t0 = time.monotonic()
            with self.assertRaises(asyncio.TimeoutError):
                await run_agent(
                    model=_slow_model(1.5), prompt="x", timeout_s=0.2
                )
            return time.monotonic() - t0

        self.assertLess(asyncio.run(go()), 1.0)


class TestProviderContracts(unittest.TestCase):
    def test_anthropic_non_object_input_is_kept_for_denial(self) -> None:
        # 🔥 was: input="oops" became {} and a no-arg tool RAN.
        resp = {
            "content": [
                {"type": "tool_use", "id": "t1", "name": "ping", "input": "x"}
            ],
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        call = from_anthropic_response(resp).tool_calls[0]
        self.assertNotEqual(call.arguments, {})

    def test_orphan_tool_results_are_not_sent(self) -> None:
        # 🔥 `max_messages` trimming can cut the assistant turn; the
        #    providers reject a tool result with no matching tool call.
        msgs = [
            {"role": "user", "content": "task"},
            {"role": "tool", "tool_call_id": "gone", "content": "r"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"id": "c2", "name": "ping", "arguments": {}}],
            },
            {"role": "tool", "tool_call_id": "c2", "content": "pong"},
        ]
        oa = to_openai_messages(msgs)
        self.assertEqual(
            [m.get("tool_call_id") for m in oa if m["role"] == "tool"],
            ["c2"],
        )
        _, an = to_anthropic_messages(msgs)
        ids = [
            b["tool_use_id"]
            for m in an
            if isinstance(m["content"], list)
            for b in m["content"]
            if b.get("type") == "tool_result"
        ]
        self.assertEqual(ids, ["c2"])
