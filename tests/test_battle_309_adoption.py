# tests/test_battle_309_adoption.py
"""#309 battle: the first fifteen minutes, as a newcomer actually has them.

The adoption kit's claims are only true if they hold for someone who did
NOT clone this repository: a fresh virtual environment, the built wheel
installed from PyPI-shaped artefacts, the journey page's commands typed
in order, the scaffold's own tests run, the GitHub Action's and the
pre-commit hooks' command lines executed. So this module does exactly
that -- it builds the wheel, makes a venv, installs
``wheel[fastapi,redis,testing] httpx "fakeredis[lua]"`` and then:

* **the journey page** -- every ```python block of
  `docs/_guide/integrations.md` runs in the fresh interpreter, in order,
  in one working directory, against the INSTALLED package (not `src`);
  a block whose `doc-requires` extra is absent is skipped, never failed;
  the error a newcomer gets with PLAIN `fakeredis` (no Lua) names the
  cure instead of a raw `evalsha` ResponseError;
* **`xsm new --template fastapi`** -- scaffolds into a temp dir, its
  `requirements.txt` pins the installed version, its tests pass in the
  fresh venv;
* **the decision tree** -- every leaf link of the journey page resolves
  to an existing guide page;
* **`action.yml` / `.pre-commit-hooks.yaml`** -- the exact command lines
  they run (`xsm validate --plain`, `xsm gt --check --plain ...`) pass
  on the example chart in the fresh venv and FAIL on drift / a broken
  chart with exit code 1 and a one-line message;
* **the schema** -- `schemas/xstate-machine.schema.json` validates the
  journey's exported chart and rejects a broken one;
* **PyPI metadata** -- the wheel's classifiers and keywords are the ones
  the issue promised.

Slow (~2 min: a venv + pip). Runs when ``XSM_ADOPTION_VENV=1`` or on the
battle gates; CI's `fastapi` cell sets it. Skipped otherwise.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import textwrap
from typing import Dict, List, Optional, Tuple

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
JOURNEY = ROOT / "docs" / "_guide" / "integrations.md"
EXAMPLE = ROOT / "examples" / "integrations" / "fastapi_orders"

needs_venv = pytest.mark.skipif(
    os.environ.get("XSM_ADOPTION_VENV") != "1",
    reason="set XSM_ADOPTION_VENV=1: builds a wheel and a venv (~2 min)",
)

REQUIRES_MARK = re.compile(
    r"(<!--\s*doc-requires:\s*([^\n]*?)\s*-->\s*\n)?```python\n(.*?)```", re.S
)


def _run(
    argv: List[str], *, cwd: Optional[pathlib.Path] = None, env=None
) -> subprocess.CompletedProcess:
    base = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    base.pop("PYTHONPATH", None)  # the INSTALLED package, never src/
    if env:
        base.update(env)
    return subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=base,
        capture_output=True,
        text=True,
        timeout=900,
    )


@pytest.fixture(scope="module")
def venv(tmp_path_factory) -> Dict[str, pathlib.Path]:
    """A fresh venv with the wheel built from THIS checkout installed.

    Under pytest's own temp root so the venvs are reclaimed (review M5:
    `mkdtemp` left a few hundred MB behind per run)."""
    work = tmp_path_factory.mktemp("xsm-adoption")
    dist = work / "dist"
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
    [wheel] = list(dist.glob("*.whl"))
    r = _run([sys.executable, "-m", "venv", str(work / "venv")])
    assert r.returncode == 0, r.stderr[-2000:]
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    py = (
        work
        / "venv"
        / scripts
        / ("python.exe" if sys.platform == "win32" else "python")
    )
    r = _run(
        [
            str(py),
            "-m",
            "pip",
            "install",
            "-q",
            "--disable-pip-version-check",
            f"{wheel}[fastapi,redis,testing]",
            "httpx",
            "fakeredis[lua]",
        ]
    )
    assert r.returncode == 0, r.stderr[-3000:]
    return {"py": py, "wheel": wheel, "work": work}


def _blocks(md: str) -> List[Tuple[List[str], str]]:
    out = []
    for m in REQUIRES_MARK.finditer(md):
        reqs = [r.strip() for r in (m.group(2) or "").split(",") if r.strip()]
        out.append((reqs, m.group(3)))
    return out


# -----------------------------------------------------------------------------
# 1. the journey page, block by block, in a fresh interpreter
# -----------------------------------------------------------------------------
@needs_venv
def test_journey_page_runs_in_a_fresh_venv(venv) -> None:
    py = str(venv["py"])
    home = venv["work"] / "journey"
    home.mkdir()
    blocks = _blocks(JOURNEY.read_text("utf-8"))
    assert len(blocks) >= 4
    ran = 0
    for i, (reqs, code) in enumerate(blocks, 1):
        if reqs:
            probe = _run([py, "-c", "import " + ",".join(reqs)])
            if probe.returncode != 0:
                continue  # the page says: skipped where the extra is absent
        # the page chdir()s into a fresh mkdtemp in step 2; later steps
        # assume that directory persists -- pin it for the whole journey
        src = code.replace(
            "os.chdir(tempfile.mkdtemp())", f"os.chdir({str(home)!r})"
        )
        r = _run([py, "-c", src], cwd=home)
        assert r.returncode == 0, f"block {i}:\n" + textwrap.indent(
            (r.stderr or r.stdout)[-3000:], "    "
        )
        ran += 1
    assert ran >= 4, ran
    # step 2 generated the companions into the journey directory
    assert (home / "generated" / "order_api.py").is_file()


@needs_venv
def test_plain_fakeredis_error_names_the_cure(venv) -> None:
    """Without the `[lua]` extra the Redis step used to die with a raw
    `unknown command 'evalsha'`; the error must say what to install."""
    py = str(venv["py"])
    code = textwrap.dedent("""
        import sys
        # plain `fakeredis` == no `lupa`: make the import fail like it does
        # for a newcomer who skipped the [lua] extra
        sys.modules["lupa"] = None
        import fakeredis
        from xstate_statemachine.contrib.redis import RedisStore
        try:
            # the constructor runs the schema script -- the first EVALSHA
            store = RedisStore(fakeredis.FakeRedis(), prefix="x")
            store.save("k", "{}")
        except Exception as exc:
            msg = str(exc)
            assert "Lua" in msg and "fakeredis[lua]" in msg, msg
            assert exc.__cause__ is not None, "cause dropped"
            sys.exit(0)
        print("no error: this fakeredis has Lua", file=sys.stderr)
        sys.exit(3)
        """)
    r = _run([py, "-c", code])
    # 📝 review M3: exit 3 means the store did not touch Lua at
    #    construction (or `lua_modules=None` does not disable it) -- the
    #    cure message was never exercised; that is a failure, not a pass
    assert r.returncode == 0, r.stderr[-2000:]


def test_typed_names_the_lua_cure_and_keeps_the_cause() -> None:
    """In-process: the mapping itself, incl. that unrelated unknown
    commands are NOT given the Lua cure (review L8)."""
    redis = pytest.importorskip("redis")
    from src.xstate_statemachine.contrib.redis._errors import typed

    exc = redis.ResponseError(
        "unknown command 'evalsha', with args beginning with: 'abc'"
    )
    msg = str(typed(exc))
    assert "Lua" in msg and "fakeredis[lua]" in msg and "evalsha" in msg
    other = typed(redis.ResponseError("unknown command 'FOO', 'evaluate'"))
    assert "Lua" not in str(other)
    assert "FOO" in str(other)


# -----------------------------------------------------------------------------
# 2. xsm new
# -----------------------------------------------------------------------------
@needs_venv
def test_xsm_new_fastapi_scaffold_tests_pass_in_the_fresh_venv(venv) -> None:
    py = str(venv["py"])
    target = venv["work"] / "my_service"
    r = _run(
        [
            py,
            "-m",
            "xstate_statemachine",
            "new",
            "--template",
            "fastapi",
            str(target),
            "--plain",
        ]
    )
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    req = (target / "requirements.txt").read_text("utf-8")
    ver = _run(
        [py, "-c", "import xstate_statemachine as x; print(x.__version__)"]
    ).stdout.strip()
    assert f"xstate-statemachine[fastapi]>={ver}" in req, req
    r = _run(
        [py, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
        cwd=target,
    )
    assert r.returncode == 0, r.stdout[-3000:]
    assert "passed" in r.stdout


# -----------------------------------------------------------------------------
# 3. the decision tree's leaves
# -----------------------------------------------------------------------------
def test_decision_tree_leaves_link_to_existing_pages() -> None:
    md = JOURNEY.read_text("utf-8")
    guide = ROOT / "docs" / "_guide"
    # a page's URL slug is its filename, or its `permalink:` when it lives
    # in a sub-folder (comparisons/, recipes/)
    pages = set()
    for p in guide.rglob("*.md"):
        pages.add(p.stem)
        m = re.search(
            r"^permalink:\s*/guide/([a-z0-9-]+)/", p.read_text("utf-8"), re.M
        )
        if m:
            pages.add(m.group(1))
    links = re.findall(r"\]\(\.\./([a-z0-9-]+)/", md)
    assert links, "no guide links on the journey page"
    missing = sorted({slug for slug in links if slug not in pages})
    assert missing == [], missing


# -----------------------------------------------------------------------------
# 4. action.yml / pre-commit hooks: the command lines, for real
# -----------------------------------------------------------------------------
@needs_venv
def test_action_and_hook_command_lines(venv) -> None:
    scripts = venv["py"].parent
    xsm = scripts / ("xsm.exe" if sys.platform == "win32" else "xsm")
    assert xsm.exists(), "the wheel must install the `xsm` entry point"
    chart = EXAMPLE / "machine.json"
    out = venv["work"] / "generated"
    # action step 1: xsm validate --plain <files>
    r = _run([str(xsm), "validate", "--plain", str(chart)])
    assert r.returncode == 0, r.stdout + r.stderr
    # action step 2 (after a generate): xsm gt --check --plain <files> -o <dir> <gt-args>
    r = _run(
        [
            str(xsm),
            "gt",
            str(chart),
            "-o",
            str(out),
            "-t",
            "pythonic-class",
            "-f",
            "--plain",
        ]
    )
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    r = _run(
        [
            str(xsm),
            "gt",
            "--check",
            "--plain",
            str(chart),
            "-o",
            str(out),
            "-t",
            "pythonic-class",
        ]
    )
    assert r.returncode == 0, r.stdout[-2000:]
    # drift → exit 1 and the stale file named, nothing rewritten
    stale = out / "order_logic.py"
    before = stale.read_bytes()
    stale.write_bytes(before + b"\n# drift\n")
    r = _run(
        [
            str(xsm),
            "gt",
            "--check",
            "--plain",
            str(chart),
            "-o",
            str(out),
            "-t",
            "pythonic-class",
        ]
    )
    assert r.returncode == 1 and "out of date" in r.stdout, r.stdout[-1500:]
    assert stale.read_bytes() == before + b"\n# drift\n"
    # a broken chart → validate exits non-zero with a one-line reason
    bad = venv["work"] / "bad.machine.json"
    bad.write_text(
        json.dumps({"id": "b", "initial": "nowhere", "states": {"a": {}}}),
        encoding="utf-8",
    )
    r = _run([str(xsm), "validate", "--plain", str(bad)])
    assert r.returncode != 0
    assert "Traceback" not in r.stderr
    # the hooks file declares exactly these entries
    hooks = (ROOT / ".pre-commit-hooks.yaml").read_text("utf-8")
    assert "entry: xsm validate --plain" in hooks
    assert "entry: xsm gt --check --plain" in hooks
    action = (ROOT / "action.yml").read_text("utf-8")
    assert (
        "xsm validate --plain" in action and "xsm gt --check --plain" in action
    )


# -----------------------------------------------------------------------------
# 5. the schema
# -----------------------------------------------------------------------------
def test_schema_validates_the_journey_chart_and_rejects_a_broken_one() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(
        (ROOT / "schemas" / "xstate-machine.schema.json").read_text("utf-8")
    )
    md = JOURNEY.read_text("utf-8")
    m = re.search(r"chart = (\{.*?\n\})\n", md, re.S)
    assert m, "the journey page's exported chart literal"
    chart = eval(
        m.group(1), {}
    )  # noqa: S307 -- a dict literal from our own docs
    jsonschema.validate(chart, schema)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({"id": "x", "states": "not-an-object"}, schema)


# -----------------------------------------------------------------------------
# 6. PyPI metadata
# -----------------------------------------------------------------------------
@needs_venv
def test_wheel_metadata_has_the_promised_classifiers_and_keywords(
    venv,
) -> None:
    import zipfile

    with zipfile.ZipFile(venv["wheel"]) as z:
        meta = next(n for n in z.namelist() if n.endswith("METADATA"))
        text = z.read(meta).decode("utf-8")
    for cls in (
        "Framework :: AsyncIO",
        "Framework :: Django",
        "Framework :: FastAPI",
        "Framework :: Flask",
        "Framework :: Pytest",
    ):
        assert f"Classifier: {cls}" in text, cls
    kw = next(ln for ln in text.splitlines() if ln.startswith("Keywords:"))
    for word in (
        "statechart",
        "xstate",
        "fsm",
        "workflow-engine",
        "saga",
        "event-driven",
        "llm-agents",
    ):
        assert word in kw, (word, kw)
    # battle #309-a: PyPI showed only Homepage + Bug Tracker
    urls = dict(
        ln[len("Project-URL: ") :].split(", ", 1)
        for ln in text.splitlines()
        if ln.startswith("Project-URL: ")
    )
    for key in ("Documentation", "Changelog", "Source", "Bug Tracker"):
        assert urls.get(key, "").startswith("https://"), (key, urls)


def test_vscode_file_match_covers_the_journey_and_corpus_charts() -> None:
    """The documented `json.schemas` fileMatch must match the file the
    journey writes, and the schema must accept the shipped examples."""
    import fnmatch

    jsonschema = pytest.importorskip("jsonschema")
    page = (ROOT / "docs" / "_guide" / "stately-export.md").read_text("utf-8")
    [pattern] = re.findall(r'"fileMatch":\s*\["([^"]+)"\]', page)
    assert fnmatch.fnmatch("order.machine.json", pattern)
    assert "order.machine.json" in JOURNEY.read_text("utf-8")
    schema = json.loads(
        (ROOT / "schemas" / "xstate-machine.schema.json").read_text("utf-8")
    )
    assert schema.get("$id") and schema.get("title")
    for name in ("fastapi_orders", "flask_wizard", "django_approvals"):
        chart = json.loads(
            (
                ROOT / "examples" / "integrations" / name / "machine.json"
            ).read_text("utf-8")
        )
        jsonschema.validate(chart, schema)


# -----------------------------------------------------------------------------
# 7. battle #309-a: the oldest interpreter, and a core-only install
# -----------------------------------------------------------------------------
def _py39() -> Optional[pathlib.Path]:
    env = os.environ.get("XSM_PY39")
    cand = pathlib.Path(env) if env else ROOT.parents[2] / ".venv39"
    if not env and not cand.is_dir():
        cand = ROOT / ".venv39"
    exe = cand / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    if cand.is_file():
        return cand
    return exe if exe.is_file() else None


def _child_venv(base: str, work: pathlib.Path, name: str) -> pathlib.Path:
    r = _run([base, "-m", "venv", str(work / name)])
    assert r.returncode == 0, r.stderr[-2000:]
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    exe = "python.exe" if sys.platform == "win32" else "python"
    return work / name / scripts / exe


@needs_venv
def test_journey_and_scaffolds_on_python_3_9(venv) -> None:
    base = _py39()
    if base is None:
        pytest.skip("no 3.9 interpreter (.venv39 or XSM_PY39)")
    py = _child_venv(str(base), venv["work"], "venv39")
    r = _run(
        [str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check"]
        + [f"{venv['wheel']}[fastapi,redis,flask,testing]", "httpx"]
        + ["fakeredis[lua]"]
    )
    assert r.returncode == 0, r.stderr[-3000:]
    home = venv["work"] / "journey39"
    home.mkdir()
    for i, (reqs, code) in enumerate(_blocks(JOURNEY.read_text("utf-8")), 1):
        src = code.replace(
            "os.chdir(tempfile.mkdtemp())", f"os.chdir({str(home)!r})"
        )
        r = _run([str(py), "-c", src], cwd=home)
        assert r.returncode == 0, f"3.9 block {i}:\n{r.stderr[-3000:]}"
    for template in ("fastapi", "flask"):
        target = venv["work"] / f"{template} 39 é"
        r = _run(
            [str(py), "-m", "xstate_statemachine", "--plain", "new"]
            + ["--template", template, str(target)]
        )
        assert r.returncode == 0, r.stdout + r.stderr
        r = _run(
            [str(py), "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
            cwd=target,
        )
        assert r.returncode == 0 and "passed" in r.stdout, r.stdout[-3000:]


@needs_venv
def test_core_only_install_degrades_with_notes_not_tracebacks(venv) -> None:
    """No extras, cp1252 stdout (the Windows console default): every
    journey command still works; --with-api/--with-models say what was
    skipped and how to get the full check."""
    py = _child_venv(sys.executable, venv["work"], "core")
    r = _run([str(py), "-m", "pip", "install", "-q", str(venv["wheel"])])
    assert r.returncode == 0, r.stderr[-3000:]
    chart = str(EXAMPLE / "machine.json")
    out = venv["work"] / "core_out"
    env = {"PYTHONUTF8": "0", "PYTHONIOENCODING": "cp1252"}
    for argv in (
        ["validate", chart],
        ["inspect", chart],
        ["gt", chart, "--with-api", "--with-models", "-o", str(out)],
        [
            "gt",
            "--check",
            chart,
            "--with-api",
            "--with-models",
            "-o",
            str(out),
        ],
        ["new", "--list"],
    ):
        base = {**os.environ, **env}
        base.pop("PYTHONPATH", None)
        r = subprocess.run(
            [str(py), "-m", "xstate_statemachine", *argv],
            env=base,
            capture_output=True,
            encoding="cp1252",  # what the console would have to render
            timeout=300,
        )
        both = r.stdout + r.stderr
        assert r.returncode == 0, (argv, both[-2000:])
        assert "Traceback" not in both, (argv, both[-2000:])
        if argv[0] == "gt" and "--check" not in argv:
            assert "xstate-statemachine[fastapi]" in both, both
    assert (out / "order_api.py").is_file()
