# tests/test_battle_296_scenario.py
"""#296 battle: 1.0 hardening on a plugin author's -- and an operator's --
day.

* **a marketplace of plugins, some hostile** -- five third-party
  distributions laid out as installed `.dist-info`s: a good audit
  plugin; one whose loader raises; one whose entry point names a
  non-PluginBase class; one whose constructor raises; one whose MODULE
  IMPORT has side effects (writes a file) -- discovery never happens on
  `import xstate_statemachine` (the side effect file does not appear);
  `discover()` lists the loadable ones and logs the rest; `strict=True`
  raises on the first failure; `allow=` by name or distribution never
  imports the others (the side-effect file still does not appear);
  `XSM_DISABLE_PLUGIN_DISCOVERY=1` returns `[]` with the import never
  done; `attach_discovered()` attaches only real plugins and the
  interpreter keeps running when a discovered plugin raises in EVERY
  hook (fail-open plugins);
* **two distributions, one entry-point name** -- both are listed, each
  with its own distribution, and `allow=` by distribution picks one;
* **`xsm plugins`** -- `--plain` and `--json` list name, distribution,
  version, group and hooks; exit 0 with ZERO plugins installed; exit 0
  with the broken ones (listed as skipped), `--strict` exits non-zero;
* **the 3.9 shim** -- `_entry_points()` on a dict-shaped
  `entry_points()` return selects by key;
* **deprecations** -- `deprecated()` emits ONCE per call site across 16
  threads hammering the same site, emits again from a different site,
  `reset_deprecation_warnings()` re-arms, the registry names every
  deprecation with its removal version, and every deprecation named in
  the policy page exists in the registry;
* **the 1.0 checklist, mechanically** -- every `__all__` name of every
  `contrib.*` module appears in `docs/api/index.md`; no TODO/FIXME in
  `src/`; README states SemVer + the Python range and that range equals
  `requires-python` AND the CI matrix; `[all]` lists every contrib extra;
  `python -c "import xstate_statemachine"` in a subprocess pulls no
  third-party module and does not touch `importlib.metadata.entry_points`.
"""

from __future__ import annotations

import configparser
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import warnings
from typing import Any, Dict, List

import pytest

from xstate_statemachine import SyncInterpreter, create_machine
from xstate_statemachine import plugin_discovery as pd
from xstate_statemachine.deprecations import (
    deprecated,
    deprecations,
    reset_deprecation_warnings,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# -----------------------------------------------------------------------------
# a marketplace of distributions, built as installed .dist-info on sys.path
# -----------------------------------------------------------------------------
GOOD = """
from xstate_statemachine import PluginBase
class Good(PluginBase):
    def __init__(self): self.seen = []
    def on_transition(self, i, f, t, tr): self.seen.append(1)
"""
RAISES_EVERYWHERE = """
from xstate_statemachine import PluginBase
class Loud(PluginBase):
    def __getattribute__(self, name):
        if name.startswith("on_"):
            def boom(*a, **k): raise RuntimeError("plugin bug: " + name)
            return boom
        return object.__getattribute__(self, name)
"""
BAD_CTOR = """
from xstate_statemachine import PluginBase
class NeedsArgs(PluginBase):
    def __init__(self, required): pass
"""
SIDE_EFFECT = """
import os, pathlib
pathlib.Path(os.environ["XSM_296_MARKER"]).write_text("imported")
from xstate_statemachine import PluginBase
class Spy(PluginBase): pass
"""
NOT_A_PLUGIN = "class Nope:\n    pass\n"
BROKEN = "raise ImportError('vendor sdk missing')\n"

DISTS: Dict[str, Dict[str, Any]] = {
    "good-audit": {
        "module": "good_audit",
        "code": GOOD,
        "ep": "good_audit:Good",
    },
    "loud-plugin": {
        "module": "loud_plugin",
        "code": RAISES_EVERYWHERE,
        "ep": "loud_plugin:Loud",
    },
    "needs-args": {
        "module": "needs_args",
        "code": BAD_CTOR,
        "ep": "needs_args:NeedsArgs",
    },
    "spy-plugin": {
        "module": "spy_plugin",
        "code": SIDE_EFFECT,
        "ep": "spy_plugin:Spy",
    },
    "not-a-plugin": {
        "module": "not_a_plugin",
        "code": NOT_A_PLUGIN,
        "ep": "not_a_plugin:Nope",
    },
    "broken-loader": {
        "module": "broken_loader",
        "code": BROKEN,
        "ep": "broken_loader:Whatever",
    },
}


def _dist(
    root: pathlib.Path,
    name: str,
    version: str,
    module: str,
    code: str,
    eps: Dict[str, str],
) -> None:
    (root / f"{module}.py").write_text(code, encoding="utf-8")
    info = root / f"{module}-{version}.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        encoding="utf-8",
    )
    cp = configparser.ConfigParser(delimiters=("=",))
    cp.optionxform = str  # type: ignore[assignment,method-assign]
    cp[pd.PLUGINS_GROUP] = eps
    with open(info / "entry_points.txt", "w", encoding="utf-8") as fh:
        cp.write(fh)


@pytest.fixture
def marketplace(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> pathlib.Path:
    for name, d in DISTS.items():
        _dist(
            tmp_path,
            name,
            "0.1.0",
            d["module"],
            d["code"],
            {d["module"]: d["ep"]},
        )
    # two distributions, ONE entry-point name
    _dist(
        tmp_path,
        "vendor-a",
        "1.0.0",
        "vendor_a",
        GOOD,
        {"audit": "vendor_a:Good"},
    )
    _dist(
        tmp_path,
        "vendor-b",
        "2.0.0",
        "vendor_b",
        GOOD,
        {"audit": "vendor_b:Good"},
    )
    marker = tmp_path / "side-effect.marker"
    monkeypatch.setenv("XSM_296_MARKER", str(marker))
    monkeypatch.delenv(pd.DISABLE_ENV, raising=False)
    monkeypatch.syspath_prepend(str(tmp_path))
    # importlib.metadata caches nothing across calls, but drop modules
    yield tmp_path
    for mod in [
        m
        for m in sys.modules
        if m
        in {d["module"] for d in DISTS.values()} | {"vendor_a", "vendor_b"}
    ]:
        del sys.modules[mod]


def _marker(root: pathlib.Path) -> bool:
    return (root / "side-effect.marker").exists()


def _machine() -> Any:
    return create_machine(
        {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
    )


# -----------------------------------------------------------------------------
# 1. the marketplace
# -----------------------------------------------------------------------------
def test_discovery_is_never_implicit(marketplace: pathlib.Path) -> None:
    # importing the library (fresh process, marketplace on the path) must
    # not import any plugin module
    env = dict(
        os.environ, PYTHONPATH=os.pathsep.join([str(marketplace), str(SRC)])
    )
    code = (
        "import sys, xstate_statemachine, xstate_statemachine.plugins\n"
        "import xstate_statemachine.plugin_discovery\n"
        "from xstate_statemachine import SyncInterpreter, create_machine\n"
        "m = create_machine({'id':'m','initial':'a','states':{'a':{}}})\n"
        "SyncInterpreter(m).start().stop()\n"
        "bad = [k for k in sys.modules if k in ('spy_plugin','good_audit','vendor_a')]\n"
        "print('MODS', bad)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    assert "MODS []" in out.stdout, out.stdout
    assert not _marker(marketplace)


def test_discover_lists_loadable_logs_the_rest(
    marketplace: pathlib.Path, caplog: Any
) -> None:
    with caplog.at_level("WARNING", logger="xstate_statemachine"):
        found = pd.discover()
    names = {p.name for p in found}
    assert {
        "good_audit",
        "loud_plugin",
        "needs_args",
        "spy_plugin",
        "not_a_plugin",
        "audit",
    } <= names
    assert "broken_loader" not in names
    assert (
        "broken_loader" in caplog.text and "vendor sdk missing" in caplog.text
    )
    # a non-PluginBase entry is listed with NO hooks (so `xsm plugins` shows it)
    assert next(p for p in found if p.name == "not_a_plugin").hooks == ()
    assert next(p for p in found if p.name == "good_audit").hooks == (
        "on_transition",
    )
    assert _marker(marketplace)  # a full discover() does import spy_plugin


def test_strict_raises_on_the_first_failure(marketplace: pathlib.Path) -> None:
    with pytest.raises(ImportError, match="vendor sdk missing"):
        pd.discover(strict=True)


def test_allow_never_imports_the_others(marketplace: pathlib.Path) -> None:
    found = pd.discover(allow=["good_audit"])
    assert [p.name for p in found] == ["good_audit"]
    assert not _marker(marketplace)  # spy_plugin never imported
    # by DISTRIBUTION name, picking one of two same-named entry points
    found = pd.discover(allow=["vendor-b"])
    assert [(p.name, p.distribution, p.version) for p in found] == [
        ("audit", "vendor-b", "2.0.0")
    ]
    assert not _marker(marketplace)


def test_two_distributions_one_name_both_listed(
    marketplace: pathlib.Path,
) -> None:
    found = [
        p
        for p in pd.discover(allow=["vendor-a", "vendor-b"])
        if p.name == "audit"
    ]
    assert sorted((p.distribution, p.version) for p in found) == [
        ("vendor-a", "1.0.0"),
        ("vendor-b", "2.0.0"),
    ]


def test_env_switch_returns_nothing_and_imports_nothing(
    marketplace: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(pd.DISABLE_ENV, "1")
    assert pd.discover() == []
    assert pd.attach_discovered(SyncInterpreter(_machine())) == []
    assert not _marker(marketplace)


def test_attach_attaches_real_plugins_and_survives_a_loud_one(
    marketplace: pathlib.Path, caplog: Any
) -> None:
    i = SyncInterpreter(_machine())
    with caplog.at_level("WARNING", logger="xstate_statemachine"):
        attached = pd.attach_discovered(
            i,
            allow=["good_audit", "loud_plugin", "needs_args", "not_a_plugin"],
        )
    kinds = sorted(type(p).__name__ for p in attached)
    # 🔥 a non-PluginBase object must not be attached as a plugin; a
    #    constructor needing args is skipped and logged
    assert "NeedsArgs" not in kinds and "needs_args" in caplog.text
    assert "Good" in kinds and "Loud" in kinds
    assert "Nope" not in kinds, kinds
    i.start()
    r = i.send("GO", wait=True)
    assert r.state_ids == frozenset({"m.b"}) and i.status == "running"
    good = next(p for p in attached if type(p).__name__ == "Good")
    assert good.seen  # the good plugin still saw the transition
    i.stop()


# -----------------------------------------------------------------------------
# 2. xsm plugins
# -----------------------------------------------------------------------------
def _xsm(
    args: List[str], path: pathlib.Path, **env_extra: str
) -> subprocess.CompletedProcess:
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([str(path), str(SRC)]),
        PYTHONUTF8="1",
        **env_extra,
    )
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "plugins", *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def test_xsm_plugins_lists_everything_and_exits_zero(
    marketplace: pathlib.Path,
) -> None:
    out = _xsm(["--json"], marketplace)
    assert out.returncode == 0, out.stderr[-1500:]
    data = json.loads(out.stdout)
    rows = (
        data
        if isinstance(data, list)
        else data.get("plugins") or data.get("found") or []
    )
    by = {(r.get("name"), r.get("distribution")): r for r in rows}
    assert ("good_audit", "good-audit") in by
    assert by[("good_audit", "good-audit")]["version"] == "0.1.0"
    assert by[("good_audit", "good-audit")]["hooks"] == ["on_transition"]
    assert ("audit", "vendor-a") in by and ("audit", "vendor-b") in by
    text = json.dumps(data)
    assert "broken_loader" in text  # skipped ones are reported, not hidden
    plain = _xsm(["--plain"], marketplace)
    assert (
        plain.returncode == 0
        and "good-audit" in plain.stdout
        and "0.1.0" in plain.stdout
    )


def test_xsm_plugins_strict_exits_nonzero_on_a_broken_loader(
    marketplace: pathlib.Path,
) -> None:
    out = _xsm(["--plain", "--strict"], marketplace)
    assert out.returncode == 1, out.returncode
    assert "broken_loader" in out.stderr and "broken-loader" in out.stderr
    assert "vendor sdk missing" in out.stderr
    assert "Traceback" not in out.stderr


def test_xsm_plugins_with_nothing_installed_exits_zero(
    tmp_path: pathlib.Path,
) -> None:
    out = _xsm(["--plain"], tmp_path, XSM_DISABLE_PLUGIN_DISCOVERY="1")
    assert out.returncode == 0, out.stderr[-800:]
    assert "Traceback" not in out.stderr


# -----------------------------------------------------------------------------
# 3. the 3.9 shim
# -----------------------------------------------------------------------------
def test_py39_dict_shaped_entry_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EP:
        def __init__(self, name: str) -> None:
            self.name, self.group, self.value = name, pd.PLUGINS_GROUP, "x:y"

    fake = {pd.PLUGINS_GROUP: [EP("a"), EP("b")], "other": [EP("c")]}
    import importlib.metadata as md

    monkeypatch.setattr(md, "entry_points", lambda: fake)
    assert [e.name for e in pd._entry_points(pd.PLUGINS_GROUP)] == ["a", "b"]
    assert pd._entry_points("missing") == []


# -----------------------------------------------------------------------------
# 4. deprecations
# -----------------------------------------------------------------------------
def test_deprecated_emits_once_per_site_across_threads() -> None:
    from xstate_statemachine import deprecations as dmod

    reset_deprecation_warnings()
    kw = dict(since="0.11.0", removal="2.0", alternative="use_other()")
    caught: List[Any] = []
    lock = threading.Lock()
    # 📝 `catch_warnings(record=True)` is process-global and not
    #    thread-safe; count through `showwarning` under a lock instead.
    orig = warnings.showwarning

    def record(message: Any, *a: Any, **k: Any) -> None:
        with lock:
            caught.append(message)

    warnings.showwarning = record  # type: ignore[assignment]
    warnings.simplefilter("always")

    def site_one() -> None:
        deprecated("battle296_thing", **kw)

    threads = []
    for _ in range(16):
        t = threading.Thread(target=lambda: [site_one() for _ in range(4)])
        threads.append(t)
        t.start()
    for t in threads:
        t.join(30)
    warnings.showwarning = orig  # type: ignore[assignment]
    warnings.resetwarnings()
    assert len(caught) == 1, len(caught)  # 64 calls, one site, one warning
    # a different call site warns again (and the loop below is ONE site)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        for _ in range(3):
            deprecated("battle296_thing", **kw)
    assert len(w) == 1, len(w)
    msg = str(w[0].message)
    assert "use_other()" in msg and "2.0" in msg and "0.11.0" in msg
    reset_deprecation_warnings()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        deprecated("battle296_thing", **kw)
    assert len(w) == 1  # re-armed
    # leave the registry as found (the policy page is synced against it)
    with dmod._LOCK:
        dmod._REGISTRY.pop("battle296_thing", None)


def test_registry_and_policy_page_agree() -> None:
    entries = {d.what: d for d in deprecations()}
    assert entries, "no deprecations registered"
    for d in entries.values():
        ver = r"(\d+\.\d+(?:\.\d+)?)"
        s_m, r_m = re.match(ver, d.since), re.match(ver, d.removal)
        assert s_m and r_m, d  # both START with a version

        def key(v: str) -> tuple:
            return tuple(int(x) for x in v.split("."))

        assert key(r_m.group(1)) > key(s_m.group(1)), d
    page = next(ROOT.glob("docs/_guide/**/deprecation*.md"), None)
    assert page is not None, "no deprecation policy page"
    text = page.read_text("utf-8")
    assert "DeprecationWarning" in text and "major" in text.lower()
    changelog = (ROOT / "CHANGELOG.md").read_text("utf-8")
    head = changelog.split("## [", 1)[0]
    assert (
        "deprecation" in head.lower()
    )  # the policy is linked from the header
    for d in entries.values():
        if d.what.startswith("battle296"):
            continue
        token = d.what.split("(")[0].split(" ")[0]
        assert token in text, f"{d.what!r} not on the policy page"


# -----------------------------------------------------------------------------
# 5. the 1.0 checklist, mechanically
# -----------------------------------------------------------------------------
def test_every_contrib_public_name_is_in_the_api_reference() -> None:
    # 📝 the existing checklist test IMPORTS each subpackage and skips the
    #    ones whose extra is absent locally; this reads `__init__.py`
    #    statically so a name added behind a missing extra is caught here.
    api = (ROOT / "docs/api/index.md").read_text("utf-8")
    missing: List[str] = []
    for init in sorted(
        (SRC / "xstate_statemachine/contrib").glob("*/__init__.py")
    ):
        text = init.read_text("utf-8")
        m = re.search(r"__all__\s*(?::[^=]+)?=\s*\[(.*?)\]", text, re.S)
        if not m:
            continue
        for name in re.findall(r"\"([A-Za-z_][A-Za-z0-9_]*)\"", m.group(1)):
            if f"`{name}" not in api:
                missing.append(f"{init.relative_to(SRC)}:{name}")
    assert not missing, missing


def test_no_todo_fixme_in_src_or_docs_or_examples() -> None:
    """Comment tokens only (generators WRITE `# TODO` into scaffolds as
    string literals); widened past the checklist's `src/` to the shipped
    examples and guide pages."""
    import io
    import tokenize

    marker = re.compile(r"\b(TODO|FIXME|XXX)\b")
    hits: List[str] = []
    for root in (
        SRC,
        ROOT / "examples" / "recipes",
        ROOT / "examples" / "integrations",
    ):
        for path in sorted(root.rglob("*.py")):
            for tok in tokenize.tokenize(
                io.BytesIO(path.read_bytes()).readline
            ):
                if tok.type == tokenize.COMMENT and marker.search(tok.string):
                    hits.append(f"{path.relative_to(ROOT)}:{tok.start[0]}")
    # 📝 guide pages that SHOW generated scaffolds legitimately contain
    #    `# TODO: implement` inside fenced code; prose must not.
    for page in sorted((ROOT / "docs" / "_guide").rglob("*.md")):
        prose = re.sub(r"```.*?```", "", page.read_text("utf-8"), flags=re.S)
        for line in prose.splitlines():
            # describing the generated `# TODO` stubs is fine; an open one
            # in the prose is not
            if marker.search(line) and not re.search(
                r"stub|marker|fill in|implement", line, re.I
            ):
                hits.append(f"{page.relative_to(ROOT)}: {line.strip()[:60]}")
    assert not hits, hits


def test_python_range_is_one_truth() -> None:
    tomllib = pytest.importorskip("tomllib")
    proj = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))[
        "project"
    ]
    lo = re.search(r">=\s*3\.(\d+)", proj["requires-python"]).group(1)
    classifiers = sorted(
        int(m)
        for m in re.findall(
            r"Programming Language :: Python :: 3\.(\d+)",
            "\n".join(proj["classifiers"]),
        )
    )
    assert classifiers and classifiers[0] == int(lo)
    ci = (ROOT / ".github/workflows/ci.yml").read_text("utf-8")
    ci_versions = sorted({int(m) for m in re.findall(r'"3\.(\d+)"', ci)})
    assert ci_versions[0] == int(lo) and ci_versions[-1] == classifiers[-1], (
        ci_versions,
        classifiers,
    )
    readme = (ROOT / "README.md").read_text("utf-8")
    assert f"3.{lo}" in readme and f"3.{classifiers[-1]}" in readme
    assert re.search(r"[Ss]em(antic )?[Vv]er", readme)


def test_all_extra_covers_every_contrib_extra() -> None:
    tomllib = pytest.importorskip("tomllib")
    extras = tomllib.loads((ROOT / "pyproject.toml").read_text("utf-8"))[
        "project"
    ]["optional-dependencies"]
    all_deps = set(extras["all"])
    for name, deps in extras.items():
        if name in ("all", "dev", "lint", "test", "format", "docs", "testing"):
            continue
        for dep in deps:
            assert dep in all_deps, (name, dep)


def test_core_import_is_third_party_free_and_discovers_nothing() -> None:
    code = (
        "import sys, importlib.metadata as md\n"
        "calls = []\n"
        "orig = md.entry_points\n"
        "md.entry_points = lambda *a, **k: (calls.append(1), orig(*a, **k))[1]\n"
        "import xstate_statemachine\n"
        "from xstate_statemachine import *\n"
        "import xstate_statemachine.persistence, xstate_statemachine.patterns, xstate_statemachine.plugins\n"
        "third = sorted(m.split('.')[0] for m in sys.modules if m.split('.')[0] in "
        "{'pydantic','fastapi','django','sqlalchemy','celery','redis','flask','starlette','litestar','langgraph','pydantic_ai','opentelemetry','prometheus_client','aiokafka','nats','aio_pika'})\n"
        "print('THIRD', third)\nprint('EPCALLS', len(calls))\n"
    )
    env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONUTF8="1")
    out = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert out.returncode == 0, out.stderr[-1500:]
    assert "THIRD []" in out.stdout, out.stdout
    assert "EPCALLS 0" in out.stdout, out.stdout
