# tests/test_battle_290_docs.py
"""#290 battle (B): docs truth for multi-agent.

Every multi-agent snippet in the guide runs verbatim; the acceptance
criteria (`xsm inspect` / `xsm simulate` / `xsm replay`) are exercised
through the real CLI; every Guarantees promise and Troubleshooting row
has a test that provokes it; the API index describes every public name.
"""

from __future__ import annotations

import copy
import importlib
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

pytest.importorskip("pydantic")

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine import (  # noqa: E402
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.contrib.agents import (  # noqa: E402
    TOOL_LOOP,
    AgentConfigError,
    AgentTracePlugin,
    BudgetPlugin,
    FakeModel,
    handoff_guard,
    load_chart,
    spawn_agent,
    tool_registry,
)
from xstate_statemachine.models import MachineNode  # noqa: E402
from xstate_statemachine.inspect import (  # noqa: E402
    InspectorPlugin,
    JsonLinesSink,
)

ROOT = Path(__file__).resolve().parents[1]
GUIDE = (ROOT / "docs/_guide/integration-agents.md").read_text("utf-8")
API = (ROOT / "docs/api/index.md").read_text("utf-8")
CHARTS = ROOT / "src/xstate_statemachine/contrib/agents/charts"
MULTI = GUIDE.split("### Multi-agent", 1)[1].split("\n### ", 1)[0]


def _xsm(*args: str) -> "subprocess.CompletedProcess[str]":
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )


# -------------------------------------------------------------------------
# 📖 Snippets run verbatim
# -------------------------------------------------------------------------
def _multi_blocks() -> List[str]:
    blocks = re.findall(
        r"<!-- doc-requires: pydantic -->\n```python\n(.*?)```", MULTI, re.S
    )
    assert blocks, "no runnable block in §Multi-agent"
    return blocks


@pytest.mark.parametrize("idx", range(len(_multi_blocks())))
def test_multi_agent_snippet_runs_verbatim(idx: int, capsys: Any) -> None:
    # 📝 includes `total_usage["turns"] == 4` after the send-time rollup
    exec(compile(_multi_blocks()[idx], "integration-agents.md", "exec"), {})
    assert "supervisor.reporting" in capsys.readouterr().out


# -------------------------------------------------------------------------
# 🖥️ Acceptance: inspect / simulate / replay
# -------------------------------------------------------------------------
@pytest.mark.parametrize(
    "chart, regions",
    [
        ("supervisor", ["running", "planner", "workers"]),
        ("pipeline", ["researching", "writing", "reviewing"]),
        ("debate", ["arguing", "pro", "con", "judging"]),
    ],
)
def test_xsm_inspect_renders_the_chart(chart: str, regions: List[str]):
    path = str(CHARTS / f"{chart}.json")
    r = _xsm("inspect", path, "--plain", "--no-events")
    assert r.returncode == 0, r.stderr
    for name in regions:
        assert name in r.stdout
    if chart != "pipeline":
        assert "parallel 1" in r.stdout  # the parallel region is shown


@pytest.mark.parametrize(
    "chart, events, final",
    [
        ("supervisor", "PLAN,HANDOFF,AGENT_DONE", "reporting"),
        ("pipeline", "AGENT_DONE,AGENT_DONE,AGENT_DONE", "published"),
        ("debate", "AGENT_DONE,AGENT_DONE", "decided"),
    ],
)
def test_xsm_simulate_walks_the_chart_offline(
    chart: str, events: str, final: str
) -> None:
    r = _xsm("simulate", str(CHARTS / f"{chart}.json"), "-e", events, "--json")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["value"] == final
    # 📝 the guide: actions are stubs -- no sub-agent, no context change
    assert out["context"]["total_usage"] == {}


def test_simulate_guards_false_holds_the_worker_region() -> None:
    r = _xsm(
        "simulate",
        str(CHARTS / "supervisor.json"),
        "-e",
        "PLAN,HANDOFF",
        "--guards-false",
        "allWorkersReported",
        "--json",
    )
    out = json.loads(r.stdout)
    assert out["value"]["running"]["workers"] == "working"


def search(q: str) -> str:
    """Search the web."""
    return f"results for {q}"


def _supervisor(
    budget: BudgetPlugin,
    model: FakeModel,
    *,
    tracer: Any = None,
    chart: Any = None,
    child: Any = None,
) -> SyncInterpreter:
    def store(i: Any, c: Dict[str, Any], e: Any, a: Any) -> None:
        c["tasks"] = list(e.payload["tasks"])
        c["outstanding"] = len(c["tasks"])

    def hand_off(i: Any, c: Dict[str, Any], e: Any, a: Any) -> None:
        for t in c["tasks"]:
            i.send(
                {
                    "type": "HANDOFF",
                    "from": "planner",
                    "to": "worker",
                    "task": t,
                }
            )

    def col(key: str, field: str) -> Any:
        return lambda i, c, e, a: c[key].append(e.payload.get(field))

    def reported(c: Dict[str, Any], e: Any) -> bool:
        done = len(c["results"]) + len(c["failures"])
        return 0 < c["outstanding"] <= done

    logic = MachineLogic(
        actions={
            "storePlan": store,
            "handOffTasks": hand_off,
            "collectResult": col("results", "result"),
            "collectFailure": col("failures", "error"),
        },
        guards={"allWorkersReported": reported},
    ).merge(
        spawn_agent(
            child,
            model,
            tool_registry(search),
            budget={"max_turns": 2},
            parent_tools=["search", "fetch"],
            name="worker",
            tracer=tracer,
        ),
        handoff_guard({"planner": ["worker"]}),
        budget.guards(),
    )
    machine = create_machine(chart or load_chart("supervisor"), logic=logic)
    return SyncInterpreter(machine).use(budget)


def _paid(cost: float = 0.01) -> FakeModel:
    return FakeModel(
        [{"text": "A"}] * 20,
        is_async=False,
        default_usage={
            "input_tokens": 10,
            "output_tokens": 2,
            "cost_usd": cost,
        },
    )


def test_inspector_recording_of_a_tree_replays(tmp_path: Path) -> None:
    rec = tmp_path / "run.jsonl"
    sink = JsonLinesSink(rec)
    plugin = InspectorPlugin(sink).install()
    try:
        sup = _supervisor(BudgetPlugin(max_total_usd=1), _paid()).start()
        sup.send("PLAN", tasks=["a", "b"])
    finally:
        plugin.uninstall()
        sink.close()
    r = _xsm("replay", str(rec))
    assert r.returncode == 0, r.stderr
    # ✅ each child is its own session in the replay
    assert "supervisor:worker-1" in r.stdout
    assert "supervisor:worker-2" in r.stdout


def test_replay_refuses_an_agent_trace(tmp_path: Path) -> None:
    path = tmp_path / "trace.jsonl"
    trace = AgentTracePlugin(str(path))
    sup = _supervisor(BudgetPlugin(max_total_usd=1), _paid(), tracer=trace)
    sup.use(trace).start()
    sup.send("PLAN", tasks=["a"])
    assert path.stat().st_size > 0
    for extra in ([], ["--live", "--port", "0", "--duration", "0"]):
        r = _xsm("replay", str(path), *extra)
        assert r.returncode == 1
        assert "not a recording" in r.stdout + r.stderr


# -------------------------------------------------------------------------
# 🛡️ Guarantees anchors (the rest live in test_battle_290_scenario.py)
# -------------------------------------------------------------------------
def test_guide_budget_trip_collects_the_tripping_result() -> None:
    budget = BudgetPlugin(max_total_usd=0.02)
    sup = _supervisor(budget, _paid()).start()
    sup.send("PLAN", tasks=["a", "b", "c", "d"])
    ctx = sup.context
    assert ctx["budget_exceeded"] is True
    assert ctx["results"] == ["A", "A"]  # 2nd report tripped, collected
    assert sorted(ctx["usage_by_agent"]) == [
        "supervisor:worker-1",
        "supervisor:worker-2",
    ]  # c and d never spawned, though their HANDOFFs were queued
    assert sup.current_state_ids == {"supervisor.reporting"}


def test_guarantees_anchors_exist() -> None:
    scenario = (
        ROOT
        / "examples/integrations/agents_support_bot/tests"
        / "test_battle_290_scenario.py"
    ).read_text("utf-8")
    here = Path(__file__).read_text("utf-8")
    section = GUIDE.split("**Multi-agent (`spawn_agent`", 1)[1]
    section = section.split("## Threat model", 1)[0]
    anchors = re.findall(r"`(test_\w+)`", section)
    assert len(anchors) >= 7
    for name in anchors:
        assert f"def {name}(" in scenario + here, name


# -------------------------------------------------------------------------
# 🧯 Troubleshooting rows are what the code says
# -------------------------------------------------------------------------
def _row(fragment: str) -> None:
    rows = GUIDE.split("## Troubleshooting", 1)[1]
    assert fragment in rows, f"no troubleshooting row for {fragment!r}"


def test_trouble_budget_required() -> None:
    with pytest.raises(AgentConfigError) as exc:
        spawn_agent(None, _paid(), budget=None)
    assert "spawn_agent requires an explicit budget=" in str(exc.value)
    _row("spawn_agent requires an explicit budget=")


def test_trouble_child_tools_exceed_parent() -> None:
    with pytest.raises(AgentConfigError) as exc:
        spawn_agent(
            None,
            _paid(),
            tool_registry(search),
            budget={"max_turns": 1},
            parent_tools=["fetch"],
        )
    assert "are not in the parent's allow-list" in str(exc.value)
    _row("sub-agent tools [...] are not in the parent's allow-list")


def test_trouble_built_machine_refused() -> None:
    with pytest.raises(AgentConfigError) as exc:
        spawn_agent(
            MachineNode.__new__(MachineNode),
            _paid(),
            budget={"max_turns": 1},
        )
    assert "pass the child chart as a dict" in str(exc.value)
    _row("pass the child chart as a dict")


def test_trouble_missing_task_stops_the_machine(caplog: Any) -> None:
    sup = _supervisor(BudgetPlugin(max_total_usd=1), _paid()).start()
    with caplog.at_level(logging.ERROR):
        sup.send({"type": "HANDOFF", "from": "planner", "to": "worker"})
    assert sup.status == "stopped"  # the WHOLE supervisor, loudly
    assert "no task (event.task or context['task'])" in caplog.text
    _row("no task (event.task or context['task'])")
    _row("kills the **whole** supervisor")


def test_trouble_unhandled_budget_exceeded_stays_running() -> None:
    chart = load_chart("supervisor")
    working = chart["states"]["running"]["states"]["workers"]["states"]
    del working["working"]["on"]["BUDGET_EXCEEDED"]
    sup = _supervisor(BudgetPlugin(max_total_usd=0.005), _paid(), chart=chart)
    sup.start().send("PLAN", tasks=["a", "b", "c"])
    assert sup.status == "running" and sup.context["budget_exceeded"]
    assert len(sup.context["usage_by_agent"]) == 1  # nothing more spawned
    _row("the active state has no `BUDGET_EXCEEDED` transition")


def test_trouble_child_without_notify_parent_never_reports() -> None:
    child = copy.deepcopy(TOOL_LOOP)
    for state in child["states"].values():
        if state.get("entry") == "notifyParent":
            del state["entry"]
    sup = _supervisor(BudgetPlugin(max_total_usd=1), _paid(), child=child)
    sup.start().send("PLAN", tasks=["a"])
    assert "supervisor.running.workers.working" in sup.current_state_ids
    assert sup.context["usage_by_agent"] == {}  # BudgetPlugin saw nothing
    _row("no `notifyParent` entry action")


# -------------------------------------------------------------------------
# 📊 Operations: who spent the budget
# -------------------------------------------------------------------------
def test_operations_totals_name_the_spender() -> None:
    trace = AgentTracePlugin()
    cheap = _paid(0.001)
    sup = _supervisor(BudgetPlugin(max_total_usd=1), cheap, tracer=trace)
    sup.use(trace).start()
    sup.send("PLAN", tasks=["a", "b"])
    totals = trace.totals()
    assert set(totals["agents"]) == {
        "supervisor:worker-1",
        "supervisor:worker-2",
    }
    assert totals["total"]["turns"] == 2
    parents = {
        r["agent_id"]: r["parent_id"]
        for r in trace.records
        if r["agent_id"] != "supervisor"
    }
    assert set(parents.values()) == {"supervisor"}
    by_agent = sup.context["usage_by_agent"]
    top = max(by_agent.items(), key=lambda kv: kv[1].get("cost_usd", 0))
    assert top[0].startswith("supervisor:worker-")
    assert "who spent the budget" in GUIDE.lower()


# -------------------------------------------------------------------------
# 📚 API index + chart descriptions
# -------------------------------------------------------------------------
def test_every_multi_agent_name_has_a_described_row() -> None:
    mod = importlib.import_module("xstate_statemachine.contrib.agents.multi")
    for name in [*mod.__all__, "AgentTracePlugin.totals"]:
        pat = rf"^\| `{re.escape(name)}.*\| \S"
        assert re.search(pat, API, re.M), name
        assert name.split(".")[0] in GUIDE


def test_chart_descriptions_match_behaviour() -> None:
    sup = load_chart("supervisor")["description"]
    assert "PLACEHOLDERS" in sup and "sendTo" not in sup
    deb = load_chart("debate")["description"]
    assert "FAILS" in deb and "never stalled" in deb
    assert "bounded" in load_chart("pipeline")["description"]
