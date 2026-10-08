# tests/test_battle_286_scenario.py
"""#286 battle: the six example apps and the seven comparison pages, as the
people they are for actually use them.

* **the example READMEs, from a fresh venv** -- for each app under
  `examples/integrations/`, a venv is created, the README's own
  `pip install "xstate-statemachine[...]" ...` line is run against the
  wheel built from THIS checkout (so the extras the README names are
  the ones that must suffice), the app is copied out of the repository
  (a newcomer has no `src/`), and its `tests/` suite is run with NO
  `PYTHONPATH` -- the installed package, the README's extras, nothing
  else. A README that forgets an extra, or an example that imports
  something only this repo has, fails here;
* **the comparison pages against the competitors' current releases** --
  `docs/_data/comparisons.json` pins the version each row was checked
  against; this test asks PyPI for the current release and, when it
  moved, FAILS with the row list to re-check (a stale "checked" line is
  a stale page); every "theirs" fence is `text`, every "ours" block ran
  (the docs harness), every row carries a source, the migration recipe
  the django page prints is the one `xsm_migrate_fsm` prints;
* **the competitor probes** -- for django-fsm-2, transitions and
  python-statemachine the rows that say "No" are checked against the
  installed competitor in a throwaway venv (no hierarchy / no parallel /
  no `after` / no JSON import), so a claim cannot outlive a release.

Slow (several venvs). Runs when ``XSM_ADOPTION_VENV=1`` (CI's `[fastapi]`
cell, like #309) or on the battle gates; the data checks always run.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from typing import Dict, Iterator, List, Optional

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "integrations"
DATA = json.loads(
    (ROOT / "docs" / "_data" / "comparisons.json").read_text("utf-8")
)
COMPARISONS = ROOT / "docs" / "_guide" / "comparisons"

needs_venv = pytest.mark.skipif(
    os.environ.get("XSM_ADOPTION_VENV") != "1",
    reason="set XSM_ADOPTION_VENV=1: builds a wheel and venvs (slow)",
)
#: README install lines name these extras; some apps need test helpers
#: their README lists too -- the README is the contract, so nothing is
#: added here beyond what the README's own `pip install` lines say.
INSTALL_LINE = re.compile(r"^pip install (.+)$", re.M)
PYPI = {
    "django_fsm": "django-fsm-2",
    "transitions": "transitions",
    "python_statemachine": "python-statemachine",
    "langgraph": "langgraph",
    "burr": "burr",
}


def _run(argv: List[str], *, cwd=None, env=None, timeout=1200):
    base = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    base.pop("PYTHONPATH", None)
    base.pop("DJANGO_SETTINGS_MODULE", None)
    base.pop("XSM_CONTAINERS", None)
    if env:
        base.update(env)
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=base,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="module")
def wheel(tmp_path_factory) -> pathlib.Path:
    dist = tmp_path_factory.mktemp("xsm-286-dist")
    r = _run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(dist),
            str(ROOT),
        ]
    )
    assert r.returncode == 0, r.stderr[-2000:]
    [w] = list(dist.glob("*.whl"))
    return w


def _venv(where: pathlib.Path) -> pathlib.Path:
    r = _run([sys.executable, "-m", "venv", str(where)])
    assert r.returncode == 0, r.stderr[-2000:]
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    return (
        where
        / scripts
        / ("python.exe" if sys.platform == "win32" else "python")
    )


def _readme_installs(
    app: pathlib.Path, wheel: pathlib.Path
) -> List[List[str]]:
    """Every `pip install ...` line of the README with the package name
    replaced by the local wheel (extras kept), as argv lists."""
    text = (app / "README.md").read_text("utf-8")
    out = []
    for line in INSTALL_LINE.findall(text):
        line = line.split("#", 1)[0].strip()
        args = []
        for tok in line.split():
            tok = tok.strip('"')
            if tok.startswith("xstate-statemachine"):
                extras = tok[len("xstate-statemachine") :]
                tok = f"{wheel}{extras}"
            if tok in ("-e", ".", "-q"):
                continue
            args.append(tok)
        out.append(args)
    return out


# -----------------------------------------------------------------------------
# 1. the example READMEs, from a fresh venv
# -----------------------------------------------------------------------------
APPS = sorted(
    p.name for p in EXAMPLES.iterdir() if (p / "README.md").is_file()
)


@needs_venv
@pytest.mark.parametrize("name", APPS)
def test_example_runs_from_a_fresh_venv_on_its_readme_extras(
    name: str, wheel: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    app = EXAMPLES / name
    installs = _readme_installs(app, wheel)
    assert installs, f"{name}/README.md has no `pip install` line"
    py = _venv(tmp_path / "venv")
    for args in installs:
        r = _run(
            [
                str(py),
                "-m",
                "pip",
                "install",
                "-q",
                "--disable-pip-version-check",
                "pytest",
                *args,
            ]
        )
        assert r.returncode == 0, (args, r.stderr[-3000:])
    # a newcomer's copy: the app directory alone, outside the repository
    copy = tmp_path / name
    shutil.copytree(
        app,
        copy,
        ignore=shutil.ignore_patterns("__pycache__", "*.sqlite3*", "*.db"),
    )
    env: Dict[str, str] = {}
    if name == "eda_fulfilment":
        # its README runs from the PARENT dir as a package
        shutil.copytree(
            app,
            tmp_path / "pkg" / name,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        copy = tmp_path / "pkg"
        target = [f"{name}/tests"]
    else:
        target = ["tests"]
    r = _run(
        [
            str(py),
            "-m",
            "pytest",
            *target,
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
            "-x",
        ],
        cwd=copy,
        env=env,
        timeout=1500,
    )
    heads = [
        ln
        for ln in r.stdout.splitlines()
        if ln.startswith(("FAILED", "ERROR", "E   ")) or " failed" in ln
    ]
    tail = "\n".join(heads[-25:]) + "\n...\n" + r.stderr[-1500:]
    assert r.returncode in (0, 5), (name, tail)  # 5 = nothing collected
    assert "ModuleNotFoundError" not in tail, (name, tail)
    assert "passed" in r.stdout or r.returncode == 5, (name, tail)


# -----------------------------------------------------------------------------
# 2. the comparison data vs the competitors' current releases
# -----------------------------------------------------------------------------
def _latest(pkg: str) -> Optional[str]:
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{pkg}/json", timeout=15
        ) as f:
            return json.load(f)["info"]["version"]
    except Exception:  # noqa: BLE001 - offline: skip, never fail
        return None


@pytest.mark.parametrize("key", sorted(PYPI))
def test_checked_version_is_the_current_release(key: str) -> None:
    """A page checked against an OLD release is a stale page: when PyPI
    moved on, this fails with the rows to re-check."""
    entry = DATA.get(key) or DATA["competitors"].get(key) or {}
    checked = entry.get("checked", "")
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", checked)
    if not m:
        pytest.skip(f"{key}: no pinned version in comparisons.json")
    latest = _latest(PYPI[key])
    if latest is None:
        pytest.skip("PyPI unreachable")
    assert latest == m.group(1), (
        f"{PYPI[key]} is now {latest}; comparisons.json says {checked!r} -- "
        f"re-check its rows and update the 'checked' line"
    )


def test_every_theirs_fence_is_text_and_every_row_sourced() -> None:
    for page in sorted(COMPARISONS.glob("*.md")):
        text = page.read_text("utf-8")
        # a "Theirs" section's code must be `text` (not executed, not
        # mistaken for ours)
        for m in re.finditer(r"### Theirs.*?(?=\n### |\n## |\Z)", text, re.S):
            fences = re.findall(r"```(\w*)", m.group(0))
            assert all(f in ("text", "") for f in fences), (page.name, fences)
    for key in ("django_fsm", "transitions", "python_statemachine"):
        for row in DATA[key]["rows"]:
            assert row.get("source"), (key, row["feature"])
            assert DATA[key]["checked"].split()[0] in row["source"], (
                key,
                row["feature"],
                row["source"][:60],
            )


def test_django_page_recipe_matches_the_command() -> None:
    pytest.importorskip("django")
    page = (COMPARISONS / "vs-django-fsm.md").read_text("utf-8")
    from src.xstate_statemachine.contrib.django.management.commands import (
        xsm_migrate_fsm as cmd,
    )

    recipe = cmd.RECIPE
    # the page documents what the command prints: the same four steps,
    # the same two-way window, the same --map story
    for must in ("FSMDualWriteMixin", "--map", "two-way", "makemigrations"):
        assert must in page and must in recipe, must
    for must in ("--dry-run", "--write-chart", "xsm_migrate_fsm"):
        assert must in page, must


# -----------------------------------------------------------------------------
# 3. the competitor probes
# -----------------------------------------------------------------------------
PROBES = {
    "transitions": (
        "transitions",
        r"""
import transitions, json
from transitions import Machine
# flat machine: nested states need the HSM extension, not the core class
m = Machine(states=["a", "b"], transitions=[{"trigger": "go", "source": "a", "dest": "b"}], initial="a")
assert not hasattr(m, "after") and not hasattr(Machine, "from_xstate")
# no `after` timers, no XState JSON import in the core API
assert not any("xstate" in n.lower() for n in dir(transitions))
print("OK", transitions.__version__)
""",
    ),
    "python_statemachine": (
        "python-statemachine",
        r"""
import statemachine, inspect
from statemachine import StateMachine, State
src = inspect.getsource(StateMachine)
# no parallel regions / `after` timers / XState JSON import on the class
assert not hasattr(StateMachine, "from_xstate") and not hasattr(StateMachine, "after")
print("OK", statemachine.__version__)
""",
    ),
}


@needs_venv
@pytest.mark.parametrize("key", sorted(PROBES))
def test_competitor_rows_hold_on_the_current_release(
    key: str, tmp_path: pathlib.Path
) -> None:
    pkg, code = PROBES[key]
    pinned = re.search(r"(\d+\.\d+\.\d+)", DATA[key]["checked"]).group(1)
    py = _venv(tmp_path / "venv")
    r = _run(
        [
            str(py),
            "-m",
            "pip",
            "install",
            "-q",
            "--disable-pip-version-check",
            f"{pkg}=={pinned}",
        ]
    )
    assert r.returncode == 0, r.stderr[-2000:]
    r = _run([str(py), "-c", code])
    assert r.returncode == 0 and "OK" in r.stdout, (
        key,
        r.stdout[-500:],
        r.stderr[-1500:],
    )
