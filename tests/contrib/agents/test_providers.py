"""#287 E1: provider adapters, contract-tested against RECORDED fixtures.

`fixtures/provider_responses.json` holds response bodies in the shape the
OpenAI Chat Completions and Anthropic Messages APIs return. The adapters'
mapping functions are exercised on them directly, and end-to-end through a
fake client whose ``create()`` returns the fixture -- no network, no SDK
needed for the mapping tests. A real-call smoke test runs only when the
API key is set (never in CI).
"""

from __future__ import annotations

import asyncio
import builtins
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("agents")
pytest.importorskip("pydantic")

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    ModelResponse,
    run_agent,
    tool_registry,
)
from src.xstate_statemachine.contrib.agents.providers import (  # noqa: E402
    price,
)
from src.xstate_statemachine.contrib.agents.providers.anthropic import (  # noqa: E402
    anthropic_model,
    from_anthropic_response,
    to_anthropic_messages,
    to_anthropic_tools,
)
from src.xstate_statemachine.contrib.agents.providers.openai import (  # noqa: E402
    from_openai_response,
    openai_model,
    to_openai_messages,
    to_openai_tools,
)
from src.xstate_statemachine.exceptions import MissingExtraError  # noqa: E402

FIX = json.loads(
    (Path(__file__).parent / "fixtures" / "provider_responses.json").read_text(
        encoding="utf-8"
    )
)

CONVO: List[Dict[str, Any]] = [
    {"role": "system", "content": "be brief"},
    {"role": "user", "content": "weather?"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"id": "c1", "name": "get_weather", "arguments": {"city": "K"}},
            {"id": "c2", "name": "get_weather", "arguments": {"city": "L"}},
        ],
    },
    {
        "role": "tool",
        "tool_call_id": "c1",
        "name": "get_weather",
        "content": "a",
    },
    {
        "role": "tool",
        "tool_call_id": "c2",
        "name": "get_weather",
        "content": "b",
    },
]
TOOLS = [
    {
        "name": "get_weather",
        "description": "d",
        "parameters": {"type": "object", "properties": {}},
    }
]


class _Obj:
    """Attribute-access view of a fixture, like an SDK pydantic object.
    Free-form JSON payloads (``input``) stay dicts, as in the SDKs."""

    def __init__(self, d: Any) -> None:
        self._d = d

    def __getattr__(self, name: str) -> Any:
        v = self._d.get(name)
        if isinstance(v, dict) and name != "input":
            return _Obj(v)
        if isinstance(v, list):
            return [_Obj(x) if isinstance(x, dict) else x for x in v]
        return v


class _FakeCreate:
    def __init__(self, responses: List[Any]) -> None:
        self.responses = list(responses)
        self.kwargs: List[Dict[str, Any]] = []

    async def create(self, **kw: Any) -> Any:
        self.kwargs.append(kw)
        return self.responses.pop(0)


class TestOpenAIContract:
    @pytest.mark.parametrize("wrap", [dict, _Obj])
    def test_tool_call_fixture(self, wrap: Any) -> None:
        r = from_openai_response(wrap(FIX["openai_tool_call"]))
        assert r.tool_calls[0].name == "get_weather"
        assert r.tool_calls[0].arguments == {"city": "Kochi"}
        assert r.tool_calls[0].id == "call_7Qx"
        assert r.text == ""
        assert (r.usage.input_tokens, r.usage.output_tokens) == (82, 17)
        assert r.model.startswith("gpt-4o-mini")

    def test_text_fixture_with_prices(self) -> None:
        r = from_openai_response(
            FIX["openai_text"],
            prices={"input_per_mtok": 0.15, "output_per_mtok": 0.6},
        )
        assert r.text == "It is sunny in Kochi."
        assert r.usage.cost_usd == pytest.approx((120 * 0.15 + 9 * 0.6) / 1e6)

    def test_malformed_arguments_are_not_guessed(self) -> None:
        bad = json.loads(json.dumps(FIX["openai_tool_call"]))
        bad["choices"][0]["message"]["tool_calls"][0]["function"][
            "arguments"
        ] = "{not json"
        r = from_openai_response(bad)
        assert "__unparseable__" in r.tool_calls[0].arguments

    def test_request_mapping(self) -> None:
        msgs = to_openai_messages(CONVO)
        assert msgs[2]["tool_calls"][0]["function"]["arguments"] == (
            '{"city": "K"}'
        )
        assert msgs[3] == {
            "role": "tool",
            "tool_call_id": "c1",
            "content": "a",
        }
        assert to_openai_tools(TOOLS)[0]["type"] == "function"

    def test_end_to_end_with_fake_client(self) -> None:
        pytest.importorskip("openai")
        comp = _FakeCreate([FIX["openai_tool_call"], FIX["openai_text"]])
        chat = type("Chat", (), {"completions": comp})()
        client = type("Client", (), {"chat": chat})()

        def get_weather(city: str) -> str:
            return "sunny"

        res = asyncio.run(
            run_agent(
                openai_model(client, model="gpt-4o-mini"),
                tools=tool_registry(get_weather),
                prompt="weather?",
                timeout_s=5,
            )
        )
        assert res.output == "It is sunny in Kochi."
        assert res.usage["input_tokens"] == 202
        assert comp.kwargs[0]["tools"][0]["function"]["name"] == "get_weather"
        assert comp.kwargs[1]["messages"][-1]["role"] == "tool"


class TestAnthropicContract:
    @pytest.mark.parametrize("wrap", [dict, _Obj])
    def test_tool_use_fixture(self, wrap: Any) -> None:
        r = from_anthropic_response(wrap(FIX["anthropic_tool_use"]))
        assert r.text == "Let me check."
        assert r.tool_calls[0].arguments == {"city": "Kochi"}
        assert r.tool_calls[0].id.startswith("toolu_")
        assert (r.usage.input_tokens, r.usage.output_tokens) == (396, 57)

    def test_request_mapping_merges_tool_results(self) -> None:
        system, msgs = to_anthropic_messages(CONVO)
        assert system == "be brief"
        assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
        assert [b["type"] for b in msgs[1]["content"]] == [
            "tool_use",
            "tool_use",
        ]
        assert [b["tool_use_id"] for b in msgs[2]["content"]] == ["c1", "c2"]
        assert to_anthropic_tools(TOOLS)[0]["input_schema"]["type"] == (
            "object"
        )

    def test_assistant_text_with_tool_use(self) -> None:
        _, msgs = to_anthropic_messages(
            [
                {
                    "role": "assistant",
                    "content": "thinking",
                    "tool_calls": [{"id": "x", "name": "f"}],
                }
            ]
        )
        assert msgs[0]["content"][0] == {"type": "text", "text": "thinking"}

    def test_end_to_end_with_fake_client(self) -> None:
        pytest.importorskip("anthropic")
        msgs = _FakeCreate([FIX["anthropic_tool_use"], FIX["anthropic_text"]])
        client = type("A", (), {"messages": msgs})()

        def get_weather(city: str) -> str:
            return "sunny"

        res = asyncio.run(
            run_agent(
                anthropic_model(client),
                tools=tool_registry(get_weather),
                prompt="weather?",
                system_prompt="be brief",
                timeout_s=5,
            )
        )
        assert res.output == "It is sunny in Kochi."
        assert msgs.kwargs[0]["system"] == "be brief"
        assert msgs.kwargs[0]["tools"][0]["input_schema"]
        assert msgs.kwargs[1]["messages"][-1]["content"][0]["type"] == (
            "tool_result"
        )


class TestSoftImports:
    @pytest.mark.parametrize(
        "factory,module",
        [(openai_model, "openai"), (anthropic_model, "anthropic")],
    )
    def test_missing_sdk_names_pip_install(
        self, monkeypatch: Any, factory: Any, module: str
    ) -> None:
        real = builtins.__import__

        def block(name: str, *a: Any, **kw: Any) -> Any:
            if name.split(".")[0] == module:
                raise ImportError(f"blocked {name}")
            return real(name, *a, **kw)

        monkeypatch.setattr(builtins, "__import__", block)
        with pytest.raises(MissingExtraError, match=f"pip install {module}"):
            factory(object())

    def test_price_without_sheet_is_zero(self) -> None:
        assert price(None, 100, 100) == 0.0


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set"
)
def test_openai_real_call_smoke() -> None:  # pragma: no cover - opt-in
    openai = pytest.importorskip("openai")
    model = openai_model(openai.AsyncOpenAI(), model="gpt-4o-mini")
    r = asyncio.run(model([{"role": "user", "content": "Say OK."}], []))
    assert isinstance(r, ModelResponse) and r.usage.input_tokens > 0


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_anthropic_real_call_smoke() -> None:  # pragma: no cover - opt-in
    anthropic = pytest.importorskip("anthropic")
    model = anthropic_model(anthropic.AsyncAnthropic(), max_tokens=16)
    r = asyncio.run(model([{"role": "user", "content": "Say OK."}], []))
    assert isinstance(r, ModelResponse) and r.usage.input_tokens > 0
