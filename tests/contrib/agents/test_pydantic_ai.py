"""#289 E3: pydantic-ai service + tool (skipped without pydantic-ai)."""

from __future__ import annotations

import asyncio
import os
from typing import Any, List

import pytest

from src.xstate_statemachine import Interpreter, MachineLogic, create_machine

from ..conftest import requires_extra

pytestmark = requires_extra("agents")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")
pytest.importorskip("pydantic_ai")

from pydantic import BaseModel  # noqa: E402
from pydantic_ai import Agent  # noqa: E402
from pydantic_ai.models.test import TestModel  # noqa: E402

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    budget_guards,
    run_agent,
)
from src.xstate_statemachine.contrib.agents.pydantic_ai import (  # noqa: E402
    agent_tool_from_machine,
    pydantic_ai_service,
    usage_logic,
)

#: `ask` loops through `checking` (the budget gate) until DONE or error.
CHART = {
    "id": "pa",
    "initial": "checking",
    "context": {"turns": 0, "tokens_in": 0, "tokens_out": 0, "result": None},
    "states": {
        "checking": {
            "always": [
                {"guard": "!underTokenBudget", "target": "over_budget"},
                {"target": "asking"},
            ]
        },
        "asking": {
            "invoke": {
                "src": "ask",
                "onDone": {
                    "target": "answered",
                    "actions": "recordAgentUsage",
                },
                "onError": "failed",
            },
            "on": {"STREAM": {"actions": "keepDelta"}},
        },
        "answered": {"on": {"AGAIN": "checking"}},
        "over_budget": {"type": "final"},
        "failed": {"type": "final"},
    },
}


def _machine(service: Any, max_tokens: Any = None) -> Any:
    deltas: List[str] = []

    def keep(i: Any, ctx: Any, e: Any, a: Any) -> None:
        d = e.data.get("data") or {}
        if "delta" in d:
            deltas.append(d["delta"])

    logic = MachineLogic(
        actions={"keepDelta": keep}, services={"ask": service}
    ).merge(usage_logic(), budget_guards(max_tokens=max_tokens))
    return create_machine(CHART, logic=logic), deltas


async def _settle(interp: Any, leaf: str) -> None:
    for _ in range(400):
        if any(s.endswith(leaf) for s in interp.current_state_ids):
            return
        await asyncio.sleep(0.005)
    raise AssertionError(interp.current_state_ids)


def _agent(**kw: Any) -> Any:
    return Agent(TestModel(**kw))


class TestService:
    def test_completes_and_counts_usage(self) -> None:
        svc = pydantic_ai_service(
            _agent(custom_output_text="hello"),
            prompt_from=lambda ctx, e: "hi",
        )
        m, _ = _machine(svc)

        async def go() -> Any:
            i = await Interpreter(m).start()
            await _settle(i, "answered")
            await i.stop()
            return i.context

        ctx = asyncio.run(go())
        assert ctx["result"] == "hello"
        assert ctx["turns"] == 1 and ctx["tokens_in"] > 0
        assert ctx["tokens_out"] > 0

    def test_structured_output_is_dumped(self) -> None:
        class City(BaseModel):
            name: str

        agent = Agent(
            TestModel(custom_output_args={"name": "Kochi"}), output_type=City
        )
        svc = pydantic_ai_service(agent, prompt_from=lambda c, e: "x")

        async def go() -> Any:
            return await svc(None, {}, None)

        out = asyncio.run(go())
        assert out["output"] == {"name": "Kochi"}
        assert out["usage"]["requests"] >= 1

    def test_deps_are_passed(self) -> None:
        seen: List[Any] = []

        class A:
            async def run(self, prompt: str, **kw: Any) -> Any:
                seen.append(kw)

                class R:
                    output = "ok"
                    usage = None

                return R()

        svc = pydantic_ai_service(
            A(), prompt_from=lambda c, e: "p", deps_from=lambda c, e: 7
        )
        out = asyncio.run(svc(None, {}, None))
        assert seen == [{"deps": 7}]
        assert out == {
            "output": "ok",
            "usage": {"input_tokens": 0, "output_tokens": 0, "requests": 0},
        }

    def test_budget_guard_stops_the_next_turn(self) -> None:
        svc = pydantic_ai_service(
            _agent(custom_output_text="x"), prompt_from=lambda c, e: "hi"
        )
        m, _ = _machine(svc, max_tokens=1)

        async def go() -> Any:
            i = await Interpreter(m).start()
            await _settle(i, "answered")
            await i.send("AGAIN")
            await _settle(i, "over_budget")
            await i.stop()
            return i.context

        assert asyncio.run(go())["turns"] == 1

    def test_error_is_on_error(self) -> None:
        class Boom:
            async def run(self, prompt: str, **kw: Any) -> Any:
                raise RuntimeError("provider down")

        m, _ = _machine(
            pydantic_ai_service(Boom(), prompt_from=lambda c, e: "")
        )

        async def go() -> None:
            i = await Interpreter(m).start()
            await _settle(i, "failed")
            await i.stop()

        asyncio.run(go())

    def test_streaming_sends_stream_events(self) -> None:
        svc = pydantic_ai_service(
            _agent(custom_output_text="streamed words here"),
            prompt_from=lambda c, e: "hi",
            stream=True,
        )
        m, deltas = _machine(svc)

        async def go() -> Any:
            i = await Interpreter(m).start()
            await _settle(i, "answered")
            await i.stop()
            return i.context

        ctx = asyncio.run(go())
        assert "".join(deltas) == "streamed words here"
        assert ctx["result"] == "streamed words here"
        assert ctx["tokens_out"] > 0


class TestAgentTool:
    def test_statechart_run_as_pydantic_ai_tool(self) -> None:
        model = FakeModel([{"text": "42 is the answer"}])

        def runner(prompt: str) -> Any:
            return run_agent(model, prompt=prompt, max_turns=2)

        t = agent_tool_from_machine(runner, name="ask_chart")
        assert t.name == "ask_chart"
        agent = Agent(TestModel(call_tools=["ask_chart"]), tools=[t])
        res = agent.run_sync("use the tool")
        assert "42 is the answer" in str(res.output)
        assert model.calls  # the statechart really ran

    def test_sync_runner_and_plain_value(self) -> None:
        t = agent_tool_from_machine(lambda p: {"echo": p})
        out = asyncio.run(t.function("x"))  # type: ignore[misc]
        assert out == {"state": None, "output": {"echo": "x"}, "error": None}
