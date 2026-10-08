# tests/test_battle_286_a.py
"""#286 battle, adversary A: the six example apps as a newcomer meets them.

Always on (cheap, no network):

* every ``xstate_statemachine.contrib.X`` and third-party module an
  example's *runtime* code imports is covered by its README's
  ``pip install`` line (an extra that pins it, or the package itself);
* README truth: every file a README names exists; no relative link
  leaves the folder (it breaks on GitHub/PyPI/a copied folder);
* no 3.10+ syntax in the examples (they run on the library's 3.9 floor);
* the three order charts (fastapi / sqlalchemy / eda) agree on the
  shared lifecycle: ``PAY`` leads to ``paid`` and ``CANCEL`` exists;
* ``docker compose config`` validates the fastapi Compose file (no
  daemon needed; skipped without the ``docker`` CLI).

``XSM_ADOPTION_VENV=1``: each app from a fresh **Python 3.9** venv on its
README's install lines (``XSM_PY39`` names the interpreter; skipped
without one).
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "integrations"
APPS = sorted(p.name for p in EXAMPLES.iterdir() if (p / "README.md").exists())
PYPROJECT = (ROOT / "pyproject.toml").read_text("utf-8")

#: import name -> pip distribution, where they differ
DIST = {
    "flask_wtf": "flask-wtf",
    "prometheus_client": "prometheus-client",
    "opentelemetry": "opentelemetry-api",
    "rest_framework": "djangorestframework",
    "drf_spectacular": "drf-spectacular",
    "yaml": "pyyaml",
}
#: imports a README may leave to a sentence instead of the install line
#: (opt-in paths the README documents separately, each checked below)
OPT_IN = {
    "openai",  # agents: "Real model (opt-in)" install line
    "anthropic",
    "boto3",  # eda: real-broker switch, faked by default
    "moto",
    "psycopg",
    "celery",  # in [celery]
}
#: app -> extras an opt-in mode needs, which the README must name there
OPT_IN_EXTRAS = {"flask_wizard": ("sqlalchemy",)}


def _stdlib_names() -> Set[str]:
    """`sys.stdlib_module_names` is 3.10+; on 3.9 fall back to "importable
    from the interpreter's own lib dir" (CI py3.9 cells, review #286)."""
    names = set(getattr(sys, "stdlib_module_names", ()))
    if not names:
        import sysconfig

        stdlib = Path(sysconfig.get_paths()["stdlib"])
        names = {p.stem for p in stdlib.iterdir() if p.suffix == ".py"}
        names |= {p.name for p in stdlib.iterdir() if p.is_dir()}
        names |= set(sys.builtin_module_names)
    return names | {"__future__"}


STDLIB = _stdlib_names()


def _extras() -> Dict[str, Set[str]]:
    """extra -> distribution names, from pyproject (3.9 has no tomllib)."""
    block = PYPROJECT.split("[project.optional-dependencies]", 1)[1]
    block = block.split("\n[", 1)[0]
    out: Dict[str, Set[str]] = {}
    name = ""
    for line in block.splitlines():
        line = line.split("#", 1)[0]
        m = re.match(r"^(\w+)\s*=", line)
        if m:
            name = m.group(1)
            out[name] = set()
        for dep in re.findall(r'"([^"]+)"', line):
            out[name].add(re.split(r"[\[<>=]", dep)[0].lower())
    return out


def _install_lines(app: str) -> List[str]:
    text = (EXAMPLES / app / "README.md").read_text("utf-8")
    return [
        ln.split("#", 1)[0]
        for ln in re.findall(r"^pip install (.+)$", text, re.M)
    ]


def _covered(app: str) -> Set[str]:
    extras = _extras()
    names: Set[str] = set()
    for line in _install_lines(app):
        for tok in line.split():
            tok = tok.strip("\"'")
            m = re.match(r"xstate-statemachine\[([\w,]+)\]", tok)
            if m:
                names |= {f"extra:{e}" for e in m.group(1).split(",")}
                for e in m.group(1).split(","):
                    names |= extras.get(e, set())
            else:
                names.add(re.split(r"[\[<>=]", tok)[0].lower())
    return names


def _soft(tree: ast.AST) -> Set[int]:
    """ids of import nodes guarded by ``except ImportError`` (optional)."""
    out: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Try) and any(
            "ImportError" in ast.dump(h.type or ast.Name(""))
            for h in node.handlers
        ):
            for stmt in node.body:
                out |= {id(n) for n in ast.walk(stmt)}
    return out


def _runtime_imports(app: str) -> Set[str]:
    """Top-level modules the app's non-test code imports unconditionally
    (``try: ... except ImportError`` imports are optional features)."""
    found: Set[str] = set()
    optional: Set[str] = set()
    for py in (EXAMPLES / app).rglob("*.py"):
        if "tests" in py.relative_to(EXAMPLES / app).parts or "tools" in (
            py.relative_to(EXAMPLES / app).parts
        ):
            continue
        tree = ast.parse(py.read_text("utf-8-sig"))
        soft = _soft(tree)
        for node in ast.walk(tree):
            bucket = optional if id(node) in soft else found
            if isinstance(node, ast.Import):
                bucket |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                bucket.add(node.module or "")
    # a module imported optionally once is optional everywhere (a route
    # body that only exists when the guarded import succeeded)
    tops = {m.split(".")[0] for m in optional}
    return {m for m in found if m.split(".")[0] not in tops}


@pytest.mark.parametrize("app", APPS)
def test_readme_install_line_covers_every_import(app: str) -> None:
    local = {p.stem for p in (EXAMPLES / app).rglob("*.py")} | {
        p.name for p in (EXAMPLES / app).iterdir() if p.is_dir()
    }
    have = _covered(app)
    readme = (EXAMPLES / app / "README.md").read_text("utf-8")
    for extra in OPT_IN_EXTRAS.get(app, ()):
        assert f"[{extra}]" in readme, (app, extra)
    extras = _extras()
    # an extra counts when every pin it brings is already installed (the
    # [fastapi] extra brings [pydantic]/[starlette]'s pins), or when the
    # the README documents it for a named opt-in mode (OPT_IN_EXTRAS)
    for name, pins in extras.items():
        if (pins and pins <= have) or name in OPT_IN_EXTRAS.get(app, ()):
            have |= {f"extra:{name}"} | pins
    if app == "agents_support_bot":
        local |= {"app"}  # the sibling fastapi example, imported lazily
    missing = []
    for mod in sorted(_runtime_imports(app)):
        top = mod.split(".")[0]
        if mod.startswith("xstate_statemachine.contrib."):
            sub = mod.split(".")[2]
            if sub == "brokers":  # one extra per broker; README's table
                continue
            # contrib.X is shipped by extra X (agents/django/... )
            if f"extra:{sub}" not in have:
                missing.append(f"[{sub}] for {mod}")
        elif (
            top in STDLIB
            or top in local
            or top
            in (
                "xstate_statemachine",
                app,
            )
        ):
            continue
        elif top in OPT_IN:
            continue
        else:
            dist = DIST.get(top, top).lower().replace("_", "-")
            if dist not in have and top not in have:
                missing.append(f"{dist} for {mod}")
    assert not missing, f"{app}: README `pip install` lacks {missing}"


def test_opt_in_imports_are_documented() -> None:
    agents = (EXAMPLES / "agents_support_bot" / "README.md").read_text("utf-8")
    assert "pip install openai" in agents and "anthropic" in agents
    eda = (EXAMPLES / "eda_fulfilment" / "README.md").read_text("utf-8")
    assert "moto" in eda and "boto3" in eda or "sqs" in eda


@pytest.mark.parametrize("app", APPS)
def test_readme_links_stay_inside_the_folder(app: str) -> None:
    text = (EXAMPLES / app / "README.md").read_text("utf-8")
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"https?://|#|mailto:", target):
            continue
        path = target.split("#", 1)[0]
        assert not path.startswith(".."), f"{app}: {target} leaves folder"
        assert (EXAMPLES / app / path).exists(), f"{app}: {target}"


@pytest.mark.parametrize("app", APPS)
def test_every_file_a_readme_names_exists(app: str) -> None:
    folder = EXAMPLES / app
    text = (folder / "README.md").read_text("utf-8")
    names = set(
        re.findall(r"`([\w./-]+\.(?:py|json|yml|yaml|ini|html|txt))`", text)
    )
    have = {p.name for p in folder.rglob("*")} | {
        str(p.relative_to(folder)).replace(os.sep, "/")
        for p in folder.rglob("*")
    }
    # a few mention the repository's own tests, not files in the folder
    names = {n for n in names if not n.startswith("tests/test_examples")}
    absent = sorted(
        n for n in names if n not in have and Path(n).name not in have
    )
    assert not absent, f"{app}/README.md names missing files: {absent}"


_310 = re.compile(
    r"^\s*match\s+\S.*:\s*$|^\s*case\s+\S.*:\s*$|\bzoneinfo\b", re.M
)


@pytest.mark.parametrize("app", APPS)
def test_examples_parse_on_python_39(app: str) -> None:
    for py in (EXAMPLES / app).rglob("*.py"):
        src = py.read_text("utf-8-sig")
        ast.parse(src, feature_version=(3, 9))
        assert not _310.search(src), py
        # `X | Y` in a runtime-evaluated annotation needs __future__
        if re.search(r"(->|:)\s*\w+(\[[^\]]*\])?\s*\|\s*\w", src):
            assert "from __future__ import annotations" in src, py


def _chart(app: str) -> Dict:
    return json.loads((EXAMPLES / app / "machine.json").read_text("utf-8"))


def _edges(node: Dict, out: Dict[str, Set[str]]) -> None:
    for ev, t in (node.get("on") or {}).items():
        for tr in t if isinstance(t, list) else [t]:
            tgt = tr if isinstance(tr, str) else (tr or {}).get("target")
            out.setdefault(ev, set()).add(str(tgt))
    for child in (node.get("states") or {}).values():
        _edges(child, out)


@pytest.mark.parametrize(
    "app", ["fastapi_orders", "sqlalchemy_orders", "eda_fulfilment"]
)
def test_the_order_charts_agree_on_the_shared_lifecycle(app: str) -> None:
    chart = _chart(app)
    assert chart["id"] == "order"
    states = set(chart["states"])
    assert {"paid", "shipped", "cancelled"} <= states
    edges: Dict[str, Set[str]] = {}
    _edges(chart, edges)
    assert {"PAY", "CANCEL"} <= set(edges)
    assert any("cancelled" in t for t in edges["CANCEL"])


@pytest.mark.parametrize(
    "app", ["fastapi_orders", "sqlalchemy_orders", "eda_fulfilment"]
)
def test_the_order_charts_reach_paid_with_stub_logic(app: str) -> None:
    events = {
        "eda_fulfilment": "PAY",
    }.get(app, "ADD_ITEM,CHECKOUT,PAY")
    env = {**os.environ, "PYTHONUTF8": "1"}
    env["PYTHONPATH"] = os.pathsep.join(
        p for p in (str(ROOT / "src"), env.get("PYTHONPATH", "")) if p
    )
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "simulate",
            str(EXAMPLES / app / "machine.json"),
            "--events",
            events,
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert re.findall(r'"value":\s*"(\w+)"', proc.stdout)[-1] == "paid"


def test_fastapi_compose_file_validates() -> None:
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("docker CLI not installed")
    proc = subprocess.run(
        [docker, "compose", "config", "-q"],
        cwd=EXAMPLES / "fastapi_orders",
        capture_output=True,
        text=True,
        timeout=120,
    )
    if "unknown command" in proc.stderr or "is not a docker" in proc.stderr:
        pytest.skip("docker compose plugin unavailable")
    assert proc.returncode == 0, proc.stderr


def test_agents_gitignore_covers_its_run_outputs() -> None:
    ignore = (EXAMPLES / "agents_support_bot" / ".gitignore").read_text(
        "utf-8"
    )
    assert "support.db" in ignore and "support-trace.jsonl" in ignore


# -----------------------------------------------------------------------------
# Python 3.9 fresh venvs (slow)
# -----------------------------------------------------------------------------
PY39 = os.environ.get("XSM_PY39") or str(
    ROOT.parents[2] / ".venv39" / "Scripts" / "python.exe"
    if sys.platform == "win32"
    else ROOT / ".venv39" / "bin" / "python"
)
needs_39 = pytest.mark.skipif(
    os.environ.get("XSM_ADOPTION_VENV") != "1" or not Path(PY39).exists(),
    reason="XSM_ADOPTION_VENV=1 and a Python 3.9 (XSM_PY39) needed",
)


@pytest.fixture(scope="module")
def wheel39(tmp_path_factory) -> Path:
    """One wheel for every app (``build`` must be importable)."""
    pytest.importorskip("build")
    from tests import test_battle_286_scenario as sc

    dist = tmp_path_factory.mktemp("xsm-286a-dist")
    r = sc._run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)]
        + [str(ROOT)]
    )
    assert r.returncode == 0, r.stderr[-2000:]
    [wheel] = dist.glob("*.whl")
    return wheel


@needs_39
@pytest.mark.parametrize("name", APPS)
def test_example_runs_on_python_39(
    name: str, tmp_path: Path, wheel39: Path
) -> None:
    from tests import test_battle_286_scenario as sc

    wheel = wheel39
    r = sc._run([PY39, "-m", "venv", str(tmp_path / "v")])
    assert r.returncode == 0, r.stderr
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    py = str(next((tmp_path / "v" / scripts).glob("python*")))
    for args in sc._readme_installs(EXAMPLES / name, wheel):
        # 📝 3.9/Windows: the newest greenlet has no cp39 wheel (README)
        r = sc._run(
            [
                py,
                "-m",
                "pip",
                "install",
                "-q",
                "pytest",
                "--only-binary",
                "greenlet",
                *args,
            ]
        )
        assert r.returncode == 0, (args, r.stderr[-3000:])
    if name == "eda_fulfilment":
        shutil.copytree(EXAMPLES / name, tmp_path / "pkg" / name)
        cwd, target = tmp_path / "pkg", f"{name}/tests"
    else:
        shutil.copytree(
            EXAMPLES / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("*.db", "*.sqlite3*"),
        )
        cwd, target = tmp_path / name, "tests"
    r = sc._run(
        [
            py,
            "-m",
            "pytest",
            target,
            "-q",
            "-p",
            "no:cacheprovider",
            "-o",
            "addopts=",
        ],
        cwd=cwd,
        timeout=2400,
    )
    assert r.returncode == 0, (name, r.stdout[-3000:], r.stderr[-1500:])
