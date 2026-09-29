"""Verification for G8 part 2: #288 E2, #289 E3, #291 E5.

`python scripts/verify/G8_agents_2.py`.

Windows-safe (no heredocs, no /tmp). Runs the new test files, the #288
LangGraph one-liner through `MemorySaver`, a pydantic-ai `TestModel`
round trip, structured output invalid → valid, the support bot offline
via `run.py --fake`, and the launch-kit / comparison checks. Paths whose
soft dependency is missing print SKIP and do not fail. Prints ``ALL OK``.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Any, Dict

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 💡 Verify THIS checkout even when an editable install points elsewhere.
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")


def step(name: str) -> None:
    print(f"\n== {name}")


def importable(mod: str) -> bool:
    try:
        if importlib.util.find_spec(mod.split(".")[0]) is None:
            return False
        importlib.import_module(mod)
    except Exception as exc:  # noqa: BLE001 -- blocked DLLs, version skew
        print(f"   SKIP ({mod}: {type(exc).__name__}: {str(exc)[:80]})")
        return False
    return True


def run_tests() -> None:
    step("pytest: agents folder, comparisons, docs, readme, examples")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/contrib/agents",
            "tests/test_comparisons.py",
            "tests/test_docs_site.py",
            "tests/test_readme.py",
            "tests/test_examples_integrations.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, "tests failed"


def langgraph_round_trip() -> None:
    step("#288: statechart_node + route_by_statechart through MemorySaver")
    if not importable("langgraph.graph"):
        return
    from typing import TypedDict

    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.graph import END, StateGraph

    from xstate_statemachine import create_machine
    from xstate_statemachine.contrib.agents.langgraph import (
        route_by_statechart,
        statechart_node,
    )

    m = create_machine(
        {
            "id": "g",
            "initial": "draft",
            "states": {
                "draft": {"on": {"SUBMIT": "review"}},
                "review": {"on": {"OK": "done"}},
                "done": {"type": "final"},
            },
        }
    )

    class S(TypedDict, total=False):
        xsm: Dict[str, Any]
        event: str

    g = StateGraph(S)
    g.add_node(
        "gate", statechart_node(m, None, event_from_state=lambda s: s["event"])
    )
    g.set_entry_point("gate")
    g.add_conditional_edges(
        "gate",
        route_by_statechart(
            m, {"g.review": END, "g.done": END, "g.draft": END}
        ),
    )
    app = g.compile(checkpointer=MemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}
    out = app.invoke({"event": "SUBMIT"}, cfg)
    print("  ", out["xsm"]["state_ids"])
    out = app.invoke({"event": "OK"}, cfg)
    print("  ", out["xsm"]["state_ids"])
    assert out["xsm"]["state_ids"] == ["g.done"]


def pydantic_ai_round_trip() -> None:
    step("#289: pydantic_ai_service with TestModel")
    if not importable("pydantic_ai"):
        return
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    from xstate_statemachine.contrib.agents.pydantic_ai import (
        pydantic_ai_service,
    )

    svc = pydantic_ai_service(
        Agent(TestModel(custom_output_text="ok")),
        prompt_from=lambda c, e: "hi",
    )
    out = asyncio.run(svc(None, {}, None))
    print("  ", out)
    assert out["output"] == "ok" and out["usage"]["output_tokens"] > 0


def structured_retry() -> None:
    step("#289: structured_output invalid -> valid")
    from pydantic import BaseModel

    from xstate_statemachine.contrib.agents import (
        FakeModel,
        run_agent_sync,
        structured_output,
    )

    class W(BaseModel):
        city: str

    res = run_agent_sync(
        model=FakeModel(
            [{"text": "nope"}, {"text": '{"city": "Kochi"}'}], is_async=False
        ),
        prompt="w",
        **structured_output(W, retries=2),
    )
    print("  ", res.final_state, res.output, res.context["output_retries"])
    assert res.output == {"city": "Kochi"}
    assert res.context["output_retries"] == 1


def support_bot() -> None:
    step("#291: agents_support_bot run.py --fake")
    ex = ROOT / "examples" / "integrations" / "agents_support_bot"
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
        proc = subprocess.run(
            [
                sys.executable,
                str(ex / "run.py"),
                "--fake",
                "--prompt",
                "refund order 42",
            ],
            cwd=tmp,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        print("\n".join("   " + ln for ln in proc.stdout.splitlines()[-5:]))
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert "state=supportBot.done" in proc.stdout


def launch_and_comparisons() -> None:
    step("#291: launch drafts + comparison data")
    for p in sorted((ROOT / "docs" / "research" / "launch").glob("*.md")):
        first = p.read_text("utf-8").splitlines()[0]
        assert "DRAFT — do not post without maintainer approval" in first, p
        print("   draft ok:", p.name)
    data = json.loads(
        (ROOT / "docs" / "_data" / "comparisons.json").read_text("utf-8")
    )
    print("   comparison rows:", len(data["rows"]))
    assert len(data["rows"]) >= 11


def main() -> None:
    run_tests()
    langgraph_round_trip()
    pydantic_ai_round_trip()
    structured_retry()
    support_bot()
    launch_and_comparisons()
    print("\nALL OK")


if __name__ == "__main__":
    main()
