"""#289 battle (B): docs truth for pydantic-ai + structured output.

Every public name is documented, the version check is soft, the output
exhaustion error names the last detail, and the streaming payload shape
the guide promises is the one the code sends.
"""

import asyncio
import importlib
import os
import warnings
from pathlib import Path

import pytest

pytest.importorskip("pydantic")

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine.contrib.agents import (  # noqa: E402
    FakeModel,
    run_agent_sync,
    structured_output,
)

ROOT = Path(__file__).resolve().parents[1]
GUIDE = (ROOT / "docs/_guide/integration-agents.md").read_text("utf-8")
API = (ROOT / "docs/api/index.md").read_text("utf-8")
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")


@pytest.mark.parametrize(
    "mod",
    [
        "xstate_statemachine.contrib.agents.structured",
        "xstate_statemachine.contrib.agents.pydantic_ai",
    ],
)
def test_every_public_name_is_documented(mod: str) -> None:
    if mod.endswith("pydantic_ai"):
        pytest.importorskip("pydantic_ai")
    names = importlib.import_module(mod).__all__
    for name in names:
        assert f"`{name}`" in API, f"{name} missing from docs/api/index.md"
        assert name in GUIDE, f"{name} missing from integration-agents.md"


def test_output_exhaustion_names_last_detail() -> None:
    from pydantic import BaseModel, Field

    class Ref(BaseModel):
        order_id: int = Field(gt=0)

    res = run_agent_sync(
        model=FakeModel([{"text": '{"order_id": -1}'}] * 3, is_async=False),
        prompt="x",
        **structured_output(Ref, retries=1, use_instructor=False),
    )
    assert res.error["kind"] == "output"
    assert "order_id" in res.error["message"]
    assert "-1" not in res.error["message"]  # 🔒 values never echoed
    assert res.context.get("result") is None


def test_max_turns_beats_retries() -> None:
    from pydantic import BaseModel

    class W(BaseModel):
        city: str

    res = run_agent_sync(
        model=FakeModel([{"text": "prose"}] * 9, is_async=False),
        prompt="x",
        max_turns=2,
        **structured_output(W, retries=5, use_instructor=False),
    )
    assert res.error == {"kind": "budget", "message": "turn limit reached"}
    assert res.usage["turns"] == 2


def test_version_check_is_soft() -> None:
    pytest.importorskip("pydantic_ai")
    from xstate_statemachine.contrib.agents import pydantic_ai as pa

    assert pa.check_pydantic_ai_version("2.51.0") is True
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        assert pa.check_pydantic_ai_version("3.0.0") is False
        assert pa.check_pydantic_ai_version("0.7") is False
        assert pa.check_pydantic_ai_version("") is False
    assert len(w) == 3 and "tested with" in str(w[0].message)


def test_stream_payload_shape_matches_guide() -> None:
    pytest.importorskip("pydantic_ai")
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    from xstate_statemachine import Interpreter, MachineLogic, create_machine
    from xstate_statemachine.contrib.agents.pydantic_ai import (
        pydantic_ai_service,
    )

    seen = []
    svc = pydantic_ai_service(
        Agent(TestModel(custom_output_text="hi")),
        prompt_from=lambda c, e: "q",
        stream=True,
    )
    chart = {
        "id": "h",
        "initial": "a",
        "states": {
            "a": {
                "invoke": {"src": "s", "onDone": "d"},
                "on": {"STREAM": {"actions": "ch"}},
            },
            "d": {"type": "final"},
        },
    }
    logic = MachineLogic(
        services={"s": svc},
        actions={"ch": lambda i, c, e, a: seen.append(e.data)},
    )

    async def main() -> None:
        i = await Interpreter(create_machine(chart, logic=logic)).start()
        for _ in range(200):
            if "h.d" in i.current_state_ids:
                break
            await asyncio.sleep(0.01)

    asyncio.run(main())
    assert seen[0] == {"delta": "hi"}
    assert set(seen[-1]) == {"output", "usage"}
    assert '`event.data == {"delta": "..."}`' in GUIDE


def test_support_bot_readme_structured_intake_runs() -> None:
    readme = (
        ROOT / "examples/integrations/agents_support_bot/README.md"
    ).read_text("utf-8")
    section = readme.split("## Structured intake", 1)[1]
    code = section.split("```python\n", 1)[1].split("```", 1)[0]
    import sys
    import types

    mod = types.ModuleType("_readme_intake")
    sys.modules[mod.__name__] = mod
    try:
        exec(compile(code, "README.md", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(mod.__name__, None)
        sys.modules.pop("intake", None)
