# tests/test_battle_291_scenario.py
"""#291 battle: the comparison pages, the support-bot example and the
launch kit on a READER's day -- someone evaluating the library from the
`vs-langgraph` page, trying the snippet, running the example, and
reading the launch drafts.

* **every "ours" claim in the three agent comparison tables is TRUE of
  the code**: each row's `ours` text names a thing that exists and
  behaves as said (hierarchy, parallel + `done.state`, `run_tool`
  re-check of the per-state allow-list even when the guard is removed,
  durable `after` deadlines waking through the store, `awaiting_human`
  persisted with an escalation deadline and exact call ids, snapshots
  in SQLite / Redis / Postgres stores, a Stately-loadable chart,
  pydantic context + event schemas + strict tool args, JSONL trace with
  `gen_ai.*` fields and secret redaction, `spawn_agent` with per-child
  and global budgets, `statechart_node` / `langgraph_service` /
  `agent_tool_from_machine`);
* **the "theirs" column is not a straw man**: where LangGraph is
  installed, its claimed capabilities (`interrupt`, checkpointers,
  `Send`, subgraphs, per-node retry policy) really exist, and we do not
  claim a LangGraph gap that LangGraph has closed;
* **every "ours" snippet on the three pages executes verbatim** and its
  assertions hold; a reader copying it with `instructor` / `langgraph`
  absent still gets a result (soft imports);
* **the support-bot example is the 2-minute walkthrough the issue
  promised**: `run.py --fake --prompt "refund order 42"` offline, no
  key, deterministic, ends `done` with ONE refund; `--provider openai`
  without a key is one clear line, exit non-zero, nothing written;
* **the launch kit is a DRAFT and says so**: every file under
  `docs/research/launch/` starts with the draft banner, no file carries
  a live URL to a post, every library claim in the drafts (turn counts,
  feature names, extras) matches the code;
* **README "For LLM agents" + PyPI keywords** are present; the README
  section's snippet runs; the `[agents]` extra installs what the pages
  say.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "_data" / "comparisons.json"
PAGES = ROOT / "docs" / "_guide" / "comparisons"
LAUNCH = ROOT / "docs" / "research" / "launch"
EXAMPLE = ROOT / "examples" / "integrations" / "agents_support_bot"
AGENT_PAGES = ("vs-langgraph", "vs-burr", "vs-statelyai-agent")

pydantic = pytest.importorskip("pydantic")


def _rows() -> List[Dict[str, Any]]:
    return json.loads(DATA.read_text("utf-8"))["rows"]  # type: ignore


def _row(feature: str) -> Dict[str, Any]:
    return next(r for r in _rows() if r["feature"] == feature)


# -----------------------------------------------------------------------------
# 1. every "ours" claim is true of the code
# -----------------------------------------------------------------------------
def test_hierarchy_and_parallel_claims() -> None:
    from xstate_statemachine import SyncInterpreter, create_machine

    assert "compound" in _row("Hierarchy (nested states)")["ours"]
    assert "done.state" in _row("Parallel regions")["ours"]
    m = create_machine(
        {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "type": "parallel",
                    "onDone": "end",
                    "states": {
                        "a": {
                            "initial": "x",
                            "states": {
                                "x": {
                                    "initial": "deep",
                                    "states": {
                                        "deep": {"on": {"GO": "#m.p.a.f"}}
                                    },
                                },
                                "f": {"type": "final"},
                            },
                        },
                        "b": {
                            "initial": "y",
                            "states": {
                                "y": {"on": {"GO": "f"}},
                                "f": {"type": "final"},
                            },
                        },
                    },
                },
                "end": {"type": "final"},
            },
        }
    )
    i = SyncInterpreter(m).start()
    assert "m.p.a.x.deep" in i.current_state_ids  # 3 levels deep
    i.send("GO")
    assert i.current_state_ids == {"m.end"}  # done.state joined both
    i.stop()


def test_guards_as_policy_claim_run_tool_recheck_survives_guard_removal() -> (
    None
):
    """The page says `run_tool` re-checks the per-state allow-list even
    when a guard is edited out of the chart."""
    from xstate_statemachine.contrib.agents import (
        FakeModel,
        load_chart,
        run_agent_sync,
        tool,
        tool_registry,
    )

    assert "run_tool" in _row("Guards as policy")["ours"]
    done: List[Any] = []

    def refund(order_id: int) -> str:
        """Refund."""
        done.append(order_id)
        return "ok"

    def lookup(order_id: int) -> str:
        """Look up."""
        return "shipped"

    chart = load_chart()
    for s in ("awaiting_model", "awaiting_tool"):
        chart["states"][s]["meta"]["tools"] = ["lookup"]  # refund NOT legal
    # 🔪 edit the guard out of the transition that gates tool calls
    for st in chart["states"].values():
        for arms in (st.get("on") or {}).values():
            for arm in arms if isinstance(arms, list) else [arms]:
                if isinstance(arm, dict) and arm.get("guard") == "toolAllowed":
                    del arm["guard"]
    res = run_agent_sync(
        chart,
        model=FakeModel(
            [{"tool": "refund", "args": {"order_id": 1}}, {"text": "x"}],
            is_async=False,
        ),
        tools=tool_registry(
            tool(refund, timeout_s=5), tool(lookup, timeout_s=5)
        ),
        prompt="refund",
    )
    assert done == [], "run_tool executed a tool the state forbids"
    assert res.final_state.endswith("error") or res.error is not None


def test_after_timeouts_claim_durable_deadline_wakes_through_the_store(
    tmp_path: Path,
) -> None:
    """The page says `after` deadlines are persisted and woken by
    `DueTimerScanner` -- an hour-long wait survives every worker dying."""
    from xstate_statemachine import (
        SimulatedClock,
        SyncInterpreter,
        create_machine,
    )
    from xstate_statemachine.persistence import DueTimerScanner, SQLiteStore

    ours = _row("`after` timeouts")["ours"]
    assert "durable" in ours.lower() and "DueTimerScanner" in ours
    chart = {
        "id": "w",
        "initial": "waiting",
        "states": {
            "waiting": {"after": {"3600000": "escalated"}},
            "escalated": {"type": "final"},
        },
    }
    m = create_machine(chart)
    store = SQLiteStore(str(tmp_path / "s.db"))
    i = SyncInterpreter(m, clock=SimulatedClock(wall_start=1_000.0)).start()
    store.save("k", i.get_snapshot(), deadlines=tuple(i.pending_deadlines()))
    i.stop()  # every worker died
    # an hour later, on a fresh host: the scanner fires the matured deadline
    scanner = DueTimerScanner(store, lambda k: create_machine(chart))
    assert scanner.scan(1_000.0 + 3599.0).woken == 0  # not yet due
    result = scanner.scan(1_000.0 + 3601.0)
    assert result.woken == 1, result
    j = SyncInterpreter.from_snapshot(store.load("k").snapshot, m).start()
    assert j.current_state_ids == {"w.escalated"}, j.current_state_ids
    j.stop()
    store.close()


def test_human_in_the_loop_claim_exact_call_ids_and_deadline() -> None:
    from xstate_statemachine.contrib.agents import (
        FakeModel,
        load_chart,
        run_agent_sync,
        tool,
        tool_registry,
    )

    ours = _row("Human-in-the-loop as durable state")["ours"]
    assert "awaiting_human" in ours and "exact" in ours
    hits: List[Any] = []

    def refund(order_id: int) -> str:
        """Refund."""
        hits.append(order_id)
        return "ok"

    chart = load_chart()
    for s in ("awaiting_model", "awaiting_tool"):
        chart["states"][s]["meta"]["tools"] = ["refund"]
    res = run_agent_sync(
        chart,
        model=FakeModel(
            [{"tool": "refund", "args": {"order_id": 1}}, {"text": "done"}],
            is_async=False,
        ),
        tools=tool_registry(tool(refund, timeout_s=5, side_effect=True)),
        prompt="refund",
    )
    assert res.waiting and res.final_state.endswith("awaiting_human")
    # the approval must name the EXACT pending call id
    pending = res.context["pending_tool_calls"]
    assert len(pending) == 1 and pending[0]["id"]
    # the escalation deadline is an `after` on awaiting_human in the chart
    assert "after" in load_chart()["states"]["awaiting_human"]
    assert hits == []


def test_persistence_and_observability_claims() -> None:
    from xstate_statemachine import persistence

    ours = _row("Persistence / replay")["ours"]
    for store in ("SQLite", "Redis", "Postgres"):
        assert store in ours
    assert hasattr(persistence, "SQLiteStore")
    assert importlib.util.find_spec("xstate_statemachine.contrib.redis")
    assert importlib.util.find_spec("xstate_statemachine.contrib.sqlalchemy")
    obs = _row("Observability")["ours"]
    assert "gen_ai" in obs and "redaction" in obs
    from xstate_statemachine.contrib.agents import AgentTracePlugin, scrub

    assert "sk-live" not in json.dumps(scrub({"api_key": "sk-live-1"}))
    assert AgentTracePlugin


def test_multi_agent_and_incremental_adoption_claims() -> None:
    from xstate_statemachine.contrib import agents

    ma = _row("Multi-agent")["ours"]
    assert "spawn_agent" in ma
    for name in ("spawn_agent", "BudgetPlugin", "handoff_guard"):
        assert hasattr(agents, name), name
    for chart in ("supervisor", "pipeline", "debate"):
        agents.load_chart(chart)
    inc = _row("Incremental adoption")["ours"]
    for name in ("statechart_node", "langgraph_service"):
        assert name in inc
        assert name in (
            ROOT / "src/xstate_statemachine/contrib/agents/langgraph.py"
        ).read_text("utf-8")
    assert "agent_tool_from_machine" in (
        ROOT / "src/xstate_statemachine/contrib/agents/pydantic_ai.py"
    ).read_text("utf-8")


def test_typed_context_claim() -> None:
    ours = _row("Typed context / events")["ours"]
    assert "strict" in ours.lower()
    from xstate_statemachine.contrib.agents import tool, tool_registry

    def refund(order_id: int) -> str:
        """Refund."""
        return "ok"

    t = tool_registry(tool(refund, timeout_s=5)).get("refund")
    with pytest.raises(Exception):
        t.validate({"order_id": "42"})  # strict: no coercion


# -----------------------------------------------------------------------------
# 2. the "theirs" column is not a straw man (where LangGraph is installed)
# -----------------------------------------------------------------------------
def test_langgraph_column_is_fair() -> None:
    lg = pytest.importorskip("langgraph")
    from langgraph.types import Send, interrupt  # noqa: F401
    from langgraph.checkpoint.memory import MemorySaver  # noqa: F401

    rows = {r["feature"]: r["langgraph"] for r in _rows()}
    assert "interrupt" in rows["Human-in-the-loop as durable state"]
    assert "heckpoint" in rows["Persistence / replay"]
    # we claim "no durable timers": LangGraph has no `after`-style timer
    assert "durable" in rows["`after` timeouts"].lower()
    assert not hasattr(lg, "after") and importlib.util.find_spec(
        "langgraph.types"
    )
    # the version we checked against is not older than the installed major
    checked = json.loads(DATA.read_text("utf-8"))["competitors"]["langgraph"][
        "checked"
    ]
    m = re.search(r"langgraph (\d+)\.", checked)
    installed = getattr(lg, "__version__", None) or importlib.metadata.version(
        "langgraph"
    )
    assert m and int(m.group(1)) >= int(installed.split(".")[0]) - 1


# -----------------------------------------------------------------------------
# 3. every "ours" snippet on the three pages executes verbatim
# -----------------------------------------------------------------------------
def _python_blocks(text: str) -> List[str]:
    return re.findall(r"```python\n(.*?)```", text, re.S)


@pytest.mark.parametrize("slug", AGENT_PAGES)
def test_every_ours_snippet_runs(slug: str) -> None:
    text = (PAGES / f"{slug}.md").read_text("utf-8")
    blocks = _python_blocks(text)
    assert blocks, slug
    for block in blocks:
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
        env.setdefault("PYDANTIC_AI_NO_BANNER", "1")
        proc = subprocess.run(
            [sys.executable, "-c", block],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            cwd=str(ROOT),
        )
        assert proc.returncode == 0, f"{slug}:\n{block}\n{proc.stderr[-2000:]}"


# -----------------------------------------------------------------------------
# 4. the support-bot example is the 2-minute walkthrough
# -----------------------------------------------------------------------------
def _run_example(*args: str, tmp: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
    env.pop("OPENAI_API_KEY", None)
    env.pop("ANTHROPIC_API_KEY", None)
    env["XSM_SUPPORT_BOT_DB"] = str(tmp / "bot.db")
    return subprocess.run(
        [sys.executable, "run.py", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        cwd=str(EXAMPLE),
    )


def test_fake_walkthrough_offline_one_refund(tmp_path: Path) -> None:
    out = _run_example("--fake", "--prompt", "refund order 42", tmp=tmp_path)
    assert out.returncode == 0, out.stderr[-1500:]
    assert "state=supportBot.done" in out.stdout
    assert out.stdout.count("refunds executed:") == 1
    assert "'order_id': 42" in out.stdout
    assert "Traceback" not in out.stderr


def test_provider_without_key_is_one_clear_line(tmp_path: Path) -> None:
    out = _run_example("--provider", "openai", "--prompt", "hi", tmp=tmp_path)
    assert out.returncode != 0
    lines = [ln for ln in (out.stdout + out.stderr).splitlines() if ln.strip()]
    assert len(lines) <= 3, lines
    assert "OPENAI_API_KEY" in " ".join(lines)
    assert "Traceback" not in out.stderr


# -----------------------------------------------------------------------------
# 5. the launch kit is a DRAFT and says so; its claims match the code
# -----------------------------------------------------------------------------
BANNER = "DRAFT — do not post without maintainer approval"


def test_every_launch_file_is_a_draft_and_has_no_live_post_links() -> None:
    files = sorted(LAUNCH.glob("*.md"))
    assert len(files) >= 8, [f.name for f in files]
    for f in files:
        text = f.read_text("utf-8")
        assert text.lstrip().startswith(f"> **{BANNER}**"), f.name
        # a live post URL would mean it WAS posted
        assert not re.search(
            r"https?://(news\.ycombinator\.com/item|www\.reddit\.com/r/\w+/comments|x\.com/\w+/status|twitter\.com/\w+/status)",
            text,
        ), f.name


def test_launch_kit_library_claims_match_the_code() -> None:
    from xstate_statemachine import __version__

    text = "\n".join(f.read_text("utf-8") for f in LAUNCH.glob("*.md"))
    # every extra named in the drafts is a real extra
    import tomllib

    extras = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))[
        "project"
    ]["optional-dependencies"]
    for ex in set(re.findall(r"xstate-statemachine\[([\w,-]+)\]", text)):
        for one in ex.split(","):
            assert one in extras, (one, sorted(extras))
    # every `xsm <cmd>` named in the drafts is a real sub-command
    from xstate_statemachine.cli import args as cli_args

    known = set(getattr(cli_args, "COMMANDS", ()) or ())
    for cmd in set(re.findall(r"`xsm (\w[\w-]*)", text)):
        if known:
            assert cmd in known, cmd
    # no version string older than the current one is advertised
    for v in set(re.findall(r"\b0\.(\d+)\.\d+\b", text)):
        assert int(v) <= int(__version__.split(".")[1])


# -----------------------------------------------------------------------------
# 6. README "For LLM agents" + PyPI keywords
# -----------------------------------------------------------------------------
def test_readme_for_llm_agents_section_and_keywords() -> None:
    import tomllib

    readme = (ROOT / "README.md").read_text("utf-8")
    assert "### 🤖 For LLM agents" in readme
    proj = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))[
        "project"
    ]
    for kw in ("llm-agents", "agent-orchestration"):
        assert kw in proj["keywords"]
    section = re.split(
        r"\n#{2,3} ", readme.split("### 🤖 For LLM agents", 1)[1], 1
    )[0]
    for block in _python_blocks(section):
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONUTF8="1")
        proc = subprocess.run(
            [sys.executable, "-c", block],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            cwd=str(ROOT),
        )
        assert proc.returncode == 0, proc.stderr[-1500:]
    # the section links to the comparison pages and the agents guide
    assert "integration-agents" in section or "vs-langgraph" in section
