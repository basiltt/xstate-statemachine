# tests/test_battle_291_b.py
"""Battle #291 (adversary B): the launch kit and reader's path tell the truth.

Every intra-repo path, ``/guide/<slug>/`` permalink, ``xsm`` command and
code snippet named in ``docs/research/launch`` must exist / run today.
(DRAFT banners, live links and extras live in test_battle_291_scenario.)
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Set

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "docs" / "research" / "launch"
GUIDE = ROOT / "docs" / "_guide"
KIT = sorted(LAUNCH.glob("*.md"))


def _kit_text() -> str:
    return "\n".join(p.read_text("utf-8") for p in KIT)


def _slugs() -> Set[str]:
    out = set()
    for p in GUIDE.rglob("*.md"):
        m = re.search(
            r"^permalink:\s*/guide/([^/]+)/", p.read_text("utf-8"), re.M
        )
        out.add(m.group(1) if m else p.stem)
    return out


def _env() -> dict:
    return dict(
        os.environ,
        PYTHONPATH=str(ROOT / "src"),
        PYTHONUTF8="1",
        PYDANTIC_AI_NO_BANNER="1",
    )


def test_kit_is_present() -> None:
    assert len(KIT) >= 7


def test_every_repo_path_in_the_kit_exists() -> None:
    paths = re.findall(r"`((?:examples|docs|src|tests)/[^`\s]+)`", _kit_text())
    assert paths
    for p in paths:
        assert (ROOT / p).exists(), p


def test_every_guide_permalink_in_the_kit_exists() -> None:
    named = set(re.findall(r"/guide/([a-z0-9-]+)/", _kit_text()))
    assert {"vs-langgraph", "vs-burr", "vs-statelyai-agent"} <= named
    assert named <= _slugs(), named - _slugs()


def test_every_xsm_command_in_the_kit_is_real() -> None:
    cmds = set(re.findall(r"\bxsm ([a-z][a-z-]+)", _kit_text()))
    for cmd in cmds:
        proc = subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", cmd, "--help"],
            capture_output=True,
            env=_env(),
            timeout=60,
        )
        assert proc.returncode == 0, cmd


def test_kit_names_only_real_chart_states() -> None:
    from xstate_statemachine.contrib.agents import load_chart

    states = set(load_chart()["states"])
    named = re.findall(r"`(idle|[a-z]+_[a-z_]+)`", _kit_text())
    for s in named:
        if s.startswith(("awaiting_", "checking_", "timed_")):
            assert s in states, s
    # 📝 RETRY_OUTPUT is a transition, never a state.
    assert "`RETRY_OUTPUT` state" not in _kit_text()


def test_no_kit_snippet_imports_a_missing_module() -> None:
    mods = re.findall(
        r"^\s*(?:from|import) (xstate_statemachine[\w.]*)",
        _kit_text(),
        re.M,
    )
    for mod in mods:
        __import__(mod)


def _blocks() -> List[str]:
    return re.findall(r"```python\n(.*?)```", _kit_text(), re.S)


@pytest.mark.parametrize("block", _blocks() or ["pass"])
def test_every_kit_python_snippet_runs(block: str) -> None:
    pytest.importorskip("pydantic")
    proc = subprocess.run(
        [sys.executable, "-c", block],
        capture_output=True,
        text=True,
        env=_env(),
        timeout=120,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "Error" not in proc.stderr, proc.stderr[-2000:]


def test_show_hn_snippet_reaches_done() -> None:
    pytest.importorskip("pydantic")
    block = re.findall(
        r"```python\n(.*?)```",
        (LAUNCH / "show_hn.md").read_text("utf-8"),
        re.S,
    )[0]
    proc = subprocess.run(
        [sys.executable, "-c", block],
        capture_output=True,
        text=True,
        env=_env(),
        timeout=120,
    )
    assert "toolLoop.done" in proc.stdout, proc.stdout + proc.stderr


# -------------------------------------------------------------------------
# 🗺️ Reader's path
# -------------------------------------------------------------------------
def test_readme_find_your_way_has_an_agents_row() -> None:
    readme = (ROOT / "README.md").read_text("utf-8")
    table = readme.split("Find your way", 1)[1].split("---", 1)[0]
    assert "(#-for-llm-agents)" in table
    assert "### 🤖 For LLM agents" in readme


def test_agents_guide_links_comparisons_and_checked_versions() -> None:
    text = (GUIDE / "integration-agents.md").read_text("utf-8")
    compat = text.split("## Compatibility", 1)[1].split("\n## ", 1)[0]
    assert "site.data.comparisons.competitors[key]" in compat
    assert "c.checked" in compat
    assert '"langgraph,burr,statelyai_agent"' in compat


def test_pyproject_classifies_as_ai() -> None:
    text = (ROOT / "pyproject.toml").read_text("utf-8")
    topic = "Topic :: Scientific/Engineering :: Artificial Intelligence"
    assert topic in text
    for url in ("Documentation", "Changelog", '"Bug Tracker"'):
        assert f"\n{url} = " in text, url


def test_example_readme_says_what_it_writes_and_how_long() -> None:
    ex = ROOT / "examples" / "integrations" / "agents_support_bot"
    readme = (ex / "README.md").read_text("utf-8")
    ignored = (ex / ".gitignore").read_text("utf-8").split()
    for name in ("support.db", "support-trace.jsonl"):
        assert name in ignored and f"`{name}`" in readme
    assert "clean up" in readme and "seconds" in readme
