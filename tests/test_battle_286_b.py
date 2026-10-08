# tests/test_battle_286_b.py
"""#286 battle (adversary B): every comparison row against the competitor's
pinned release.

The version each page was checked against lives in
``docs/_data/comparisons.json`` (`checked`). The probes below install THAT
release in a throwaway venv and exercise the rows, so when the pin moves
(``test_battle_286_scenario`` fails on PyPI drift) re-running this file
says which claims still hold. ``@statelyai/agent`` is TypeScript: its npm
metadata is checked. AWS Step Functions is a service: the documentation
pages the rows cite are fetched and the quoted facts searched for.

Network + venvs: runs when ``XSM_ADOPTION_VENV=1``. The data checks
(pins agree with the benchmark, README links) always run.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = json.loads(
    (ROOT / "docs" / "_data" / "comparisons.json").read_text("utf-8")
)
needs_net = pytest.mark.skipif(
    os.environ.get("XSM_ADOPTION_VENV") != "1",
    reason="set XSM_ADOPTION_VENV=1: network + venvs (slow)",
)


def _entry(key: str) -> dict:
    for group in ("competitors", "workflow_competitors"):
        if key in DATA.get(group, {}):
            return DATA[group][key]
    return DATA[key]


def _pinned(key: str) -> str:
    return re.search(r"(\d+\.\d+\.\d+)", _entry(key)["checked"]).group(1)


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "xsm-battle"})
    with urllib.request.urlopen(req, timeout=30) as f:
        return f.read().decode("utf-8", "replace")


# -----------------------------------------------------------------------------
# Python competitors: one probe script per package, run in its own venv
# -----------------------------------------------------------------------------
TRANSITIONS = r"""
import inspect, transitions
from transitions import Machine
from transitions.extensions import (
    AsyncMachine, GraphMachine, HierarchicalMachine, LockedMachine)
from transitions.extensions.states import Timeout
from transitions.extensions.markup import MarkupMachine
import transitions.extensions.locking as locking
# Hierarchy: the core Machine rejects nested states; the HSM extension
# accepts them, and parallel ones
try:
    Machine(states=["a", {"name": "p", "children": ["x"]}], initial="a")
    raise SystemExit("core Machine accepted nested states")
except TypeError:
    pass
h = HierarchicalMachine(states=["a", {"name": "p", "parallel": ["x", "y"]}],
                        transitions=[["go", "a", "p"]], initial="a")
h.go(); assert h.state == ["p_x", "p_y"], h.state
# Timers: Timeout arms a threading.Timer per entry
assert "Timer(" in inspect.getsource(Timeout)
# Locking: threading.Lock, in-process only
assert "from threading import Lock" in inspect.getsource(locking)
# Diagrams: Mermaid needs no Graphviz
g = GraphMachine(states=["a", "b"], transitions=[["go", "a", "b"]],
                 initial="a", graph_engine="mermaid")
assert "stateDiagram" in g.get_graph().draw(None)
# No history states, no XState JSON, MarkupMachine has its own format
src = inspect.getsource(transitions)
for mod in ("core", "extensions.nesting", "extensions.markup"):
    m = __import__("transitions." + mod, fromlist=["x"])
    assert "history" not in inspect.getsource(m).lower(), mod
    assert "xstate" not in inspect.getsource(m).lower(), mod
assert "transitions" in MarkupMachine(states=["a"], initial="a").markup
print("OK", transitions.__version__)
"""

PSM = r"""
import importlib.util as u, inspect, statemachine
from statemachine import State, StateMachine
from statemachine.statemachine import StateChart
assert hasattr(State, "Compound") and hasattr(State, "Parallel")
assert "delay" in inspect.signature(StateMachine.send).parameters
for mod in ("statemachine.contrib.timeout", "statemachine.invoke",
            "statemachine.engines", "statemachine.mixins",
            "statemachine.io.json", "statemachine.io.yaml",
            "statemachine.io.scxml", "statemachine.contrib.diagram",
            "statemachine.contrib.diagram.sphinx_ext",
            "statemachine.contrib.diagram.renderers.mermaid"):
    assert u.find_spec(mod), mod
from statemachine.mixins import MachineMixin
# no actor/spawn system; no XState JSON reader
assert not [n for n in dir(StateChart) if "spawn" in n.lower()]
import pathlib
pkg = pathlib.Path(statemachine.__file__).parent
assert not any("xstate" in p.read_text("utf-8", "replace").lower()
               for p in pkg.rglob("*.py")), "mentions xstate"
print("OK", statemachine.__version__)
"""

DJANGO_FSM = r"""
import django, inspect, pathlib
from django.conf import settings
settings.configure(INSTALLED_APPS=["django_fsm"])
django.setup()
import django_fsm
from django_fsm import (ConcurrentTransition, ConcurrentTransitionMixin,
    FSMField, FSMIntegerField, transition)
from django_fsm.admin import FSMAdminMixin
from django_fsm.signals import pre_transition, post_transition
pkg = pathlib.Path(django_fsm.__file__).parent
assert (pkg / "management/commands/graph_transitions.py").is_file()
src = "".join(p.read_text("utf-8") for p in pkg.rglob("*.py"))
# no timers, no async, no import/export format, no nesting
for word in ("async def", "Timer(", "xstate", "parallel", "children"):
    assert word not in src, word
# the old admin import path is a deprecated shim
import fsm_admin.mixins as old
assert "deprecated" in inspect.getsource(old)
print("OK", django.VERSION)
"""

LANGGRAPH = r"""
import inspect
from typing import TypedDict
from langgraph.graph import END, START, StateGraph
from langgraph.types import (Command, RetryPolicy, Send, TimeoutPolicy,
                             interrupt)
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.func import entrypoint, task

class S(TypedDict):
    x: int

sub = StateGraph(S)
sub.add_node("inc", lambda s: {"x": s["x"] + 1})
sub.add_edge(START, "inc"); sub.add_edge("inc", END)
g = StateGraph(S)
g.add_node("sub", sub.compile())  # a subgraph is a node ...
g.add_edge(START, "sub"); g.add_edge("sub", END)
assert g.compile().invoke({"x": 1}) == {"x": 2}
# ... and there is no compound / parallel / after state type
params = inspect.signature(StateGraph.add_node).parameters
assert {"timeout", "retry_policy"} <= set(params), list(params)
for word in ("after", "parallel", "initial", "history"):
    assert word not in params, word
assert "Timer(" not in inspect.getsource(TimeoutPolicy)
print("OK")
"""

BURR = r"""
import importlib.util as u, inspect, pathlib, burr
from burr.core import ApplicationBuilder, State, action, default, expr, when
from burr.core.application import Application
from burr.core.persistence import SQLLitePersister
assert "halt_before" in inspect.signature(Application.run).parameters
root = pathlib.Path(burr.__file__).parent
# optional extras: present as modules even when their deps are not installed
for rel in ("integrations/opentelemetry.py", "integrations/pydantic.py",
            "integrations/persisters/b_redis.py",
            "integrations/persisters/postgresql.py", "tracking/__init__.py"):
    assert (root / rel).is_file(), rel
core = root / "core"
# MapStates / MapActions / RunnableGraph (importing it needs burr[tracking])
par = (core / "parallelism.py").read_text("utf-8")
for cls in ("MapStates", "MapActions", "RunnableGraph"):
    assert f"class {cls}" in par, cls
src = "".join(p.read_text("utf-8") for p in core.glob("*.py"))
for word in ("Timer(", "call_later", "def after("):
    assert word not in src, word
print("OK")
"""

PROBES = {
    "transitions": ("transitions", TRANSITIONS, []),
    "python_statemachine": ("python-statemachine", PSM, []),
    "django_fsm": ("django-fsm-2", DJANGO_FSM, []),
    "langgraph": ("langgraph", LANGGRAPH, []),
    "burr": ("burr", BURR, []),
}


@needs_net
@pytest.mark.parametrize("key", sorted(PROBES))
def test_competitor_rows_hold_on_the_pinned_release(
    key: str, tmp_path: pathlib.Path
) -> None:
    pkg, code, extra = PROBES[key]
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    bindir = "Scripts" if os.name == "nt" else "bin"
    py = str(venv / bindir / "python")
    r = subprocess.run(
        [py, "-m", "pip", "install", "-q", "--disable-pip-version-check"]
        + [f"{pkg}=={_pinned(key)}", *extra],
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert r.returncode == 0, r.stderr[-2000:]
    r = subprocess.run(
        [py, "-c", code], capture_output=True, text=True, timeout=300
    )
    assert r.returncode == 0 and "OK" in r.stdout, (key, r.stderr[-2000:])


@needs_net
def test_statelyai_agent_npm_metadata_matches_the_rows() -> None:
    pinned = _pinned("statelyai_agent")
    meta = json.loads(_get("https://registry.npmjs.org/@statelyai/agent"))
    assert meta["dist-tags"]["latest"] == pinned, (
        f"@statelyai/agent latest is {meta['dist-tags']['latest']}; "
        f"comparisons.json pins {pinned}: re-check its rows"
    )
    deps = meta["versions"][pinned]["dependencies"]
    # XState v5 (hierarchy, parallel, after, guards) + the Vercel AI SDK
    assert deps["xstate"].lstrip("^~").startswith("5."), deps
    assert "ai" in deps, deps


SFN = "https://docs.aws.amazon.com/step-functions/latest/dg/"
SFN_FACTS = {
    "service-quotas.html": "Maximum execution time 1 year",
    "sfn-local.html": "Step Functions Local is unsupported",
    "concepts-standard-vs-express.html": "up to one year",
    "test-state-isolation.html": "TestState",
    "state-wait.html": "Wait",
}


@needs_net
@pytest.mark.parametrize("page", sorted(SFN_FACTS))
def test_step_functions_docs_still_say_what_the_rows_cite(page: str) -> None:
    text = re.sub(r"<[^>]+>", " ", _get(SFN + page))
    text = re.sub(r"\s+", " ", text)
    assert SFN_FACTS[page] in text, page


# -----------------------------------------------------------------------------
# always-on data checks
# -----------------------------------------------------------------------------
def test_benchmark_ran_against_the_pinned_competitor_versions() -> None:
    bench = json.loads(
        (ROOT / "benchmarks" / "competitors" / "results.json").read_text(
            "utf-8"
        )
    )["libs"]
    assert bench["transitions"] == _pinned("transitions")
    assert bench["python-statemachine"] == _pinned("python_statemachine")
    readme = (ROOT / "benchmarks" / "competitors" / "README.md").read_text(
        "utf-8"
    )
    for lib, key in (
        ("transitions", "transitions"),
        ("python-statemachine", "python_statemachine"),
    ):
        assert f"{lib} {_pinned(key)}" in readme, lib


def test_readme_links_every_comparison_page() -> None:
    readme = (ROOT / "README.md").read_text("utf-8")
    pages = sorted((ROOT / "docs" / "_guide" / "comparisons").glob("vs-*.md"))
    assert len(pages) == 7
    integrations = (ROOT / "docs" / "_guide" / "integrations.md").read_text(
        "utf-8"
    )
    for page in pages:
        assert f"/guide/{page.stem}/" in readme, page.stem
        assert integrations.count(f"](../{page.stem}/)") == 1, page.stem
    assert (
        "coming soon" not in readme.lower().split("how it compares")[1][:4000]
    )
