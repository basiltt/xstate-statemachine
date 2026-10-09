# tests/test_battle_291_a.py
"""#291 battle, adversary A: claims vs reality, both columns.

Covers what `test_battle_291_scenario.py` does not:

* the pages cannot rot -- every agent competitor's ``checked`` date is
  at most 180 days old, and the installed LangGraph's major equals the
  checked major (exact, not "within one");
* the softened "ours" cells: snapshots of an AGENT run land in Redis and
  SQLAlchemy stores (not only SQLite), "replay" is the transition-log
  `replay()`, the chart opens in Stately (only XState keys plus
  ``actionErrorPolicy``), the exact ``gen_ai.*`` names, the OTel span
  exporter, no prompt text by default, the redacted secret keys, the
  versioned snapshot layout;
* the "theirs" column where the competitor is importable (LangGraph
  always here, Burr only if installed);
* the snippets under ``-X dev -W error`` with ``instructor`` and
  ``langgraph`` hidden and a cwd outside the repo, and the LangGraph
  snippet never runs ``refund`` before approval;
* the example: ``XSM_SUPPORT_BOT_DB`` is honoured, an unwritable
  ``--db`` is one line + exit 2, ``--reject`` refunds nothing, a missing
  SDK is one line, the trace holds no prompt text.
"""

from __future__ import annotations

import datetime as dt
import importlib.metadata
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "_data" / "comparisons.json"
PAGES = ROOT / "docs" / "_guide" / "comparisons"
EXAMPLE = ROOT / "examples" / "integrations" / "agents_support_bot"
AGENT_KEYS = ("langgraph", "burr", "statelyai_agent")
MAX_AGE_DAYS = 180
# 📝 #291 review (1/2): the two DRIFT checks below depend on today's date
#    and on the installed competitor release, not on this repo's code --
#    on a pull request they would go red with no change. They run in the
#    nightly `comparisons` CI job (`XSM_COMPARISON_DRIFT=1`), like #286's.
needs_drift = pytest.mark.skipif(
    os.environ.get("XSM_COMPARISON_DRIFT") != "1",
    reason="competitor drift check: nightly comparisons job only",
)

pytest.importorskip("pydantic")


def _data() -> Dict[str, Any]:
    return json.loads(DATA.read_text("utf-8"))  # type: ignore[no-any-return]


def _row(feature: str) -> Dict[str, Any]:
    return next(r for r in _data()["rows"] if r["feature"] == feature)


def _fake(*steps: Dict[str, Any]) -> Any:
    from xstate_statemachine.contrib.agents import FakeModel

    return FakeModel(list(steps), is_async=False)


def _lookup_tools() -> Any:
    from xstate_statemachine.contrib.agents import tool, tool_registry

    def lookup(order_id: int) -> str:
        """Look up."""
        return "shipped"

    return tool_registry(tool(lookup, timeout_s=5))


def _steps() -> Any:
    return _fake({"tool": "lookup", "args": {"order_id": 1}}, {"text": "ok"})


# -----------------------------------------------------------------------------
# 1. the pages cannot silently rot
# -----------------------------------------------------------------------------
@needs_drift
@pytest.mark.parametrize("key", AGENT_KEYS)
def test_checked_date_is_recent(key: str) -> None:
    checked = _data()["competitors"][key]["checked"]
    day = dt.date.fromisoformat(checked.rsplit(", ", 1)[1])
    age = (dt.date.today() - day).days
    assert 0 <= age <= MAX_AGE_DAYS, f"{key}: re-check, {checked!r}"


@needs_drift
def test_installed_langgraph_major_equals_checked_major() -> None:
    pytest.importorskip("langgraph")
    checked = _data()["competitors"]["langgraph"]["checked"]
    m = re.match(r"langgraph (\d+)\.\d+\.\d+", checked)
    assert m, checked
    installed = importlib.metadata.version("langgraph")
    assert int(installed.split(".")[0]) == int(m.group(1)), installed


def test_pages_document_the_staleness_rule() -> None:
    for slug in ("vs-langgraph", "vs-burr", "vs-statelyai-agent"):
        text = (PAGES / f"{slug}.md").read_text("utf-8")
        assert "180 days" in text and "major version" in text, slug


# -----------------------------------------------------------------------------
# 2. "ours" cells the scenario does not pin
# -----------------------------------------------------------------------------
def test_agent_run_persists_in_redis_and_sqlalchemy_stores() -> None:
    fakeredis = pytest.importorskip("fakeredis")
    sa = pytest.importorskip("sqlalchemy")
    from sqlalchemy.orm import sessionmaker

    from xstate_statemachine.contrib.agents import load_chart, run_agent_sync
    from xstate_statemachine.contrib.redis import RedisStore
    from xstate_statemachine.contrib.sqlalchemy import SQLAlchemyStore
    from xstate_statemachine.persistence import SNAPSHOT_VERSION

    ours = _row("Persistence / replay")["ours"]
    assert "Redis" in ours and "SQLAlchemy" in ours
    stores = (
        RedisStore(fakeredis.FakeRedis(), prefix="t:"),
        SQLAlchemyStore(sessionmaker(sa.create_engine("sqlite://"))),
    )
    for store in stores:
        res = run_agent_sync(
            load_chart(),
            model=_steps(),
            tools=_lookup_tools(),
            prompt="hi",
            store=store,
            key="a",
        )
        assert res.final_state == "toolLoop.done"
        snap = json.loads(store.load("a").snapshot)
        # 📝 "versioned layout"
        assert snap["version"] == SNAPSHOT_VERSION


def test_replay_means_transition_log_replay() -> None:
    from xstate_statemachine import create_machine
    from xstate_statemachine.contrib.agents import (
        agent_logic,
        load_chart,
        run_agent_sync,
    )
    from xstate_statemachine.persistence.log import (
        MemoryLog,
        TransitionLogPlugin,
        replay,
    )

    assert "`replay()`" in _row("Persistence / replay")["ours"]
    log = MemoryLog()
    tools = _lookup_tools()
    res = run_agent_sync(
        load_chart(),
        model=_steps(),
        tools=tools,
        prompt="hi",
        plugins=[TransitionLogPlugin(log)],
    )
    assert res.final_state == "toolLoop.done"
    m = create_machine(load_chart(), logic=agent_logic(_steps(), tools))
    i = replay(m, log.read("toolLoop"))
    assert i.current_state_ids == {"toolLoop.done"}


XSTATE_KEYS = {
    "id", "initial", "type", "states", "on", "after", "always", "entry",
    "exit", "invoke", "context", "meta", "tags", "description", "output",
    "history", "target", "version", "onDone", "onError", "src", "input",
    "systemId", "guard", "actions", "reenter",
}  # fmt: skip


@pytest.mark.parametrize("name", ["tool_loop", "supervisor", "pipeline"])
def test_charts_open_in_stately(name: str, tmp_path: Path) -> None:
    """Only XState node keys (plus the one documented engine key) --
    tool policy and output models live under `meta`, which Stately
    keeps verbatim."""
    from xstate_statemachine.contrib.agents import load_chart

    cell = _row("Visual editor")["ours"]
    assert "actionErrorPolicy" in cell and "round-trip" not in cell
    chart = load_chart(name)
    seen: set = set()

    def walk(node: Dict[str, Any]) -> None:
        seen.update(node)
        for child in (node.get("states") or {}).values():
            walk(child)

    walk(chart)
    assert seen - XSTATE_KEYS <= {"actionErrorPolicy"}, seen - XSTATE_KEYS
    # what Stately exports (plain JSON) passes `xsm validate`
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(chart), "utf-8")
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        PYTHONUTF8="1",
        PYTHONWARNINGS="ignore",  # third-party DeprecationWarnings on stderr
    )
    proc = subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "validate", path.name],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_trace_fields_otel_and_no_prompt_by_default() -> None:
    pytest.importorskip("opentelemetry.sdk")
    from xstate_statemachine.contrib.agents import (
        AGENT_REDACT_KEYS,
        AgentTracePlugin,
        load_chart,
        run_agent_sync,
    )

    cell = _row("Observability")["ours"]
    assert '`on_span="otel"`' in cell and "redaction" in cell
    recs: List[Dict[str, Any]] = []
    tracer = AgentTracePlugin(None, on_span=recs.append)
    run_agent_sync(
        load_chart(),
        model=_steps(),
        tools=_lookup_tools(),
        prompt="SECRETPROMPT",
        tracer=tracer,
    )
    names = {k for r in recs for k in r if k.startswith("gen_ai.")}
    assert {
        "gen_ai.operation.name",
        "gen_ai.request.model",
        "gen_ai.usage.input_tokens",
        "gen_ai.usage.output_tokens",
        "gen_ai.tool.name",
    } <= names
    assert "SECRETPROMPT" not in json.dumps(recs)
    assert "gen_ai.prompt" not in names
    # OTel exporter resolves without error
    AgentTracePlugin(None, on_span="otel")
    for k in ("api_key", "authorization", "token", "password", "secret"):
        assert k in AGENT_REDACT_KEYS


# -----------------------------------------------------------------------------
# 3. "theirs" cells against installed packages
# -----------------------------------------------------------------------------
def test_langgraph_cells_name_real_apis() -> None:
    pytest.importorskip("langgraph")
    import inspect

    from langgraph.func import entrypoint, task  # noqa: F401
    from langgraph.graph import StateGraph
    from langgraph.types import (  # noqa: F401
        Command,
        RetryPolicy,
        Send,
        TimeoutPolicy,
        interrupt,
    )

    params = inspect.signature(StateGraph.add_node).parameters
    assert "timeout" in params and "retry_policy" in params
    assert hasattr(StateGraph, "add_conditional_edges")


def test_burr_cells_name_real_apis() -> None:
    pytest.importorskip("burr")
    import inspect

    from burr.core import Application, default, expr, when  # noqa: F401
    from burr.core.persistence import SQLitePersister  # noqa: F401

    params = inspect.signature(Application.run).parameters
    assert "halt_before" in params and "halt_after" in params
    assert importlib.util.find_spec("burr.core.parallelism")


# -----------------------------------------------------------------------------
# 4. snippets: strict warnings, soft deps hidden, cwd outside the repo
# -----------------------------------------------------------------------------
HIDE = (
    "import sys\n"
    "sys.modules['instructor'] = None\n"
    "sys.modules['langgraph'] = None\n"
)


@pytest.mark.parametrize(
    "slug", ["vs-langgraph", "vs-burr", "vs-statelyai-agent"]
)
def test_snippets_strict_and_outside_repo(slug: str, tmp_path: Path) -> None:
    text = (PAGES / f"{slug}.md").read_text("utf-8")
    blocks = re.findall(r"```python\n(.*?)```", text, re.S)
    assert blocks
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        PYTHONUTF8="1",
        PYTHONWARNINGS="ignore",  # third-party DeprecationWarnings on stderr
    )
    env.pop("PYDANTIC_AI_NO_BANNER", None)
    for block in blocks:
        extra = ""
        if slug == "vs-langgraph":
            # refund must NOT have run before the human approves
            extra = (
                "\nassert not any('refunded' in str(m) "
                "for m in res.context['messages'])\n"
            )
        proc = subprocess.run(
            [sys.executable, "-X", "dev", "-W", "error", "-c"]
            + [HIDE + block + extra],
            capture_output=True,
            text=True,
            env=env,
            timeout=120,
            cwd=str(tmp_path),
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        assert list(tmp_path.iterdir()) == [], "snippet wrote into cwd"


# -----------------------------------------------------------------------------
# 5. the example app under hostile conditions
# -----------------------------------------------------------------------------
def _run(tmp: Path, *args: str, pre: str = "", **env_kw: str) -> Any:
    env = dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        PYTHONUTF8="1",
        PYTHONWARNINGS="ignore",  # third-party DeprecationWarnings on stderr
    )
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "XSM_SUPPORT_BOT_DB"):
        env.pop(var, None)
    env.update(env_kw)
    code = (
        pre + "import runpy, sys\n"
        f"sys.argv = ['run.py', *{list(args)!r}]\n"
        f"runpy.run_path({str(EXAMPLE / 'run.py')!r}, run_name='__main__')\n"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        cwd=str(tmp),
    )


def test_example_honours_db_env_and_reject(tmp_path: Path) -> None:
    db = tmp_path / "elsewhere" / "bot.db"
    proc = _run(tmp_path, "--fake", "--reject", XSM_SUPPORT_BOT_DB=str(db))
    assert proc.returncode == 0, proc.stderr
    assert "refunds executed: []" in proc.stdout
    assert db.exists() and not (tmp_path / "support.db").exists()
    trace = (tmp_path / "support-trace.jsonl").read_text("utf-8")
    assert "refund order 42" not in trace


def test_example_unwritable_db_is_one_line(tmp_path: Path) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    proc = _run(tmp_path, "--fake", "--db", str(blocker / "sub" / "x.db"))
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert proc.stderr.strip().startswith("error: cannot open")


def test_example_missing_sdk_is_one_line(tmp_path: Path) -> None:
    proc = _run(
        tmp_path,
        "--provider",
        "anthropic",
        pre="import sys\nsys.modules['anthropic'] = None\n",
        ANTHROPIC_API_KEY="sk-ant-fake",
    )
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert "pip install anthropic" in proc.stderr
    assert "sk-ant-fake" not in proc.stderr + proc.stdout
