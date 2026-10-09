# tests/contrib/agents/test_battle_289_review.py
"""#289 independent review -- regressions.

* **R1** a `field_validator` whose message quotes the value, and a
  dict-typed field whose `loc` carries the reply's own keys, never leak
  into the retry prompt or `context["error"]`;
* **R2** `_detail` never returns the validated VALUE when a flaky
  validator succeeds on the second run;
* **R3** a `field_serializer` raising / non-UTF-8 bytes in the model's
  dump is an invalid reply, not a stopped machine;
* **R4** `_jsonable` makes non-UTF-8 bytes and unknown classes JSON-safe;
* **R5** a SYNC runner behind `agent_tool_from_machine` does not block
  the event loop (two calls overlap);
* **R8** `usage_logic` tolerates junk `turns` and a datetime output.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict

import pytest

pytest.importorskip("pydantic")

from pydantic import BaseModel, field_serializer, field_validator  # noqa

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    run_agent_sync,
    structured_output,
)
from src.xstate_statemachine.contrib.agents._output import (  # noqa: E402
    _validate_output,
)
from src.xstate_statemachine.contrib.agents.core import load_chart  # noqa


class Quoting(BaseModel):
    x: str
    m: Dict[str, int]

    @field_validator("x")
    @classmethod
    def _v(cls, v: str) -> str:
        raise ValueError(f"bad value {v}")


class Nested(BaseModel):
    inner: Quoting


_FLIP = {"n": 0}


class Flaky(BaseModel):
    y: int

    @field_validator("y")
    @classmethod
    def _v(cls, v: int) -> int:
        _FLIP["n"] += 1
        if _FLIP["n"] % 2 == 1:
            raise ValueError("odd call")
        return v


class BadDump(BaseModel):
    z: str

    @field_serializer("z")
    def _s(self, v: str) -> str:
        raise RuntimeError("serializer broke")


MOD = __name__


def _chart(model: str) -> Dict[str, Any]:
    chart = load_chart()
    chart["states"]["awaiting_model"]["meta"][
        "output_model"
    ] = f"{MOD}:{model}"
    return chart


def test_r1_validator_message_and_dict_keys_never_leak() -> None:
    ok, detail = _validate_output(
        Quoting, '{"x": "SSN-123", "m": {"INJECTED-KEY": "str"}}'
    )
    assert not ok
    assert "SSN-123" not in detail and "INJECTED-KEY" not in detail, detail
    assert "x: value_error" in detail and "m.*:" in detail, detail
    # nested models keep their real field names
    ok, detail = _validate_output(Nested, '{"inner": {"x": "S", "m": {}}}')
    assert "inner.x: value_error" in detail and '"S"' not in detail, detail
    # end to end: the retry prompt and the error carry nothing of the reply
    res = run_agent_sync(
        _chart("Quoting"),
        model=FakeModel(
            [{"text": '{"x": "SSN-123", "m": {"INJECTED": 1}}'}] * 3,
            is_async=False,
        ),
        prompt="go",
        **structured_output(retries=1, use_instructor=False),
    )
    assert res.error["kind"] == "output"
    text = json.dumps(res.context["messages"][1:]) + json.dumps(res.error)
    retry = [
        m for m in res.context["messages"] if "RETRY_OUTPUT" in m["content"]
    ]
    assert retry, res.context["messages"]
    assert "SSN-123" not in json.dumps(retry) and "INJECTED" not in json.dumps(
        retry
    )
    assert "SSN-123" not in json.dumps(res.error), res.error
    del text


def test_r2_detail_never_returns_the_validated_value() -> None:
    _FLIP["n"] = 0
    res = run_agent_sync(
        _chart("Flaky"),
        model=FakeModel([{"text": '{"y": 7}'}] * 2, is_async=False),
        prompt="go",
        **structured_output(retries=0, use_instructor=False),
    )
    assert res.error and res.error["kind"] == "output", res.error
    assert "7" not in res.error["message"].replace("retries", ""), res.error
    assert res.output is None


def test_r3_serializer_failure_is_an_invalid_reply() -> None:
    ok, detail = _validate_output(BadDump, '{"z": "hi"}')
    assert not ok and "PydanticSerializationError" in detail, detail
    res = run_agent_sync(
        _chart("BadDump"),
        model=FakeModel([{"text": '{"z": "hi"}'}] * 2, is_async=False),
        prompt="go",
        **structured_output(retries=0, use_instructor=False),
    )
    assert res.final_state.endswith("error") and res.error["kind"] == "output"


def test_r4_jsonable_handles_bytes_and_unknown_classes() -> None:
    from src.xstate_statemachine.contrib.agents.pydantic_ai import _jsonable

    class K:
        pass

    out = _jsonable(
        {"b": b"\xff\x00", "k": K(), "t": datetime.now(timezone.utc)}
    )
    json.dumps(out)  # JSON-safe, never raises
    assert out["b"] in ("/wA=", "_wA=") and out["k"].startswith("<")


def test_r5_sync_runner_does_not_block_the_loop() -> None:
    pytest.importorskip("pydantic_ai")
    from src.xstate_statemachine.contrib.agents.pydantic_ai import (
        agent_tool_from_machine,
    )

    class R:
        final_state = "m.done"
        output = "ok"
        error = None

    def slow(prompt: str) -> Any:
        time.sleep(0.3)
        return R()

    tool = agent_tool_from_machine(slow)

    async def both() -> float:
        t0 = time.perf_counter()
        outs = await asyncio.gather(tool.function("a"), tool.function("b"))
        assert [o["output"] for o in outs] == ["ok", "ok"]
        return time.perf_counter() - t0

    assert asyncio.run(both()) < 0.55  # overlapped, not 0.6 serial


def test_r8_usage_logic_tolerates_junk_turns_and_datetime_output() -> None:
    pytest.importorskip("pydantic_ai")
    from src.xstate_statemachine.contrib.agents.pydantic_ai import usage_logic
    from src.xstate_statemachine.events import DoneEvent

    rec = usage_logic().actions["recordAgentUsage"]
    ctx: Dict[str, Any] = {"turns": "junk"}
    rec(
        None,
        ctx,
        DoneEvent("done.invoke.x", {"output": datetime(2020, 1, 1)}, "x"),
        None,
    )
    json.dumps(ctx)
    assert ctx["turns"] >= 1 and ctx["result"] == "2020-01-01T00:00:00"
