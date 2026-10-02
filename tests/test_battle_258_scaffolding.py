"""Battle test for #258: contrib/persistence scaffolding, extras, guards.

📝 Every check that must control the import environment runs in a child
interpreter (the #258 review amendment: an in-process ``sys.modules`` /
``sys.meta_path`` sweep re-creates exception classes and poisons the rest of
the session). Checks that need a *bare* interpreter use ``XSM_BARE_PYTHON``
(or the repository's ``.venvmin``) when present, or the running interpreter
when it has no extras installed; otherwise they skip with the reason.

Network checks (PyPI floors, ``pip --dry-run``) skip under
``--disable-socket`` -- which every test job uses (X0.16), so in CI they
run ONLY in the ``audit`` job (`-k TestExtrasResolveOnPyPI`), the one job
that already talks to PyPI. Locally they run whenever sockets are open.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from typing import Dict, List, Optional, Set

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PKG = SRC / "xstate_statemachine"
CONTRIB = PKG / "contrib"
CI = ROOT / ".github" / "workflows" / "ci.yml"
PYPROJECT = ROOT / "pyproject.toml"
EXTRAS_PAGE = ROOT / "docs" / "_guide" / "integrations-extras.md"
API_INDEX = ROOT / "docs" / "api" / "index.md"

# 📝 loaded by path: putting tests/ on sys.path would let tests/inspect
#    shadow the stdlib `inspect` for every later test (seen on 3.9).
_spec = importlib.util.spec_from_file_location(
    "_battle258_zd", str(ROOT / "tests" / "test_zero_dependency.py")
)
assert _spec and _spec.loader
zd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(zd)

from src.xstate_statemachine.contrib._registry import EXTRAS  # noqa: E402

UMBRELLAS = {"web", "eda", "all"}
NOT_INTEGRATION = {"format"}  # the CLI's black/isort formatting extra


# -----------------------------------------------------------------------------
# 🧰 helpers
# -----------------------------------------------------------------------------
def _bare_python() -> Optional[str]:
    """An interpreter with NO extras installed, or ``None``."""
    env = os.environ.get("XSM_BARE_PYTHON")
    if env and pathlib.Path(env).exists():
        return env
    if importlib.util.find_spec("pydantic") is None and (
        importlib.util.find_spec("django") is None
    ):
        return sys.executable
    for base in (ROOT, *ROOT.parents):
        for cand in (
            base / ".venvmin" / "Scripts" / "python.exe",
            base / ".venvmin" / "bin" / "python",
        ):
            if cand.exists():
                return str(cand)
    return None


BARE = _bare_python()
needs_bare = unittest.skipUnless(BARE, "no bare (extras-free) interpreter")


def _child(code: str, python: Optional[str] = None) -> dict:
    proc = subprocess.run(
        [python or sys.executable, "-I", "-c", code],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _network_ok() -> bool:
    try:
        socket.create_connection(("pypi.org", 443), timeout=5).close()
        return True
    except Exception:  # noqa: BLE001 -- pytest-socket raises RuntimeError
        return False


def _pyproject_extras() -> Dict[str, List[str]]:
    """``{extra: [requirement, ...]}`` -- comment-stripped, 3.9-safe."""
    text = PYPROJECT.read_text(encoding="utf-8")
    block = text.split("[project.optional-dependencies]", 1)[1]
    block = block.split("\n[", 1)[0]
    lines = [ln.split("#", 1)[0] for ln in block.splitlines()]
    body = "\n".join(lines)
    out: Dict[str, List[str]] = {}
    for m in re.finditer(r"^([a-z]+)\s*=\s*\[(.*?)\]\s*$", body, re.M | re.S):
        out[m.group(1)] = re.findall(r'"([^"]+)"', m.group(2))
    return out


def _raw_extra_lines() -> Dict[str, str]:
    """``{extra: its raw pyproject line(s) incl. comments}``."""
    text = PYPROJECT.read_text(encoding="utf-8")
    block = text.split("[project.optional-dependencies]", 1)[1]
    block = block.split("\n[project.", 1)[0]
    out: Dict[str, str] = {}
    cur = None
    for ln in block.splitlines():
        m = re.match(r"^([a-z]+)\s*=", ln)
        if m:
            cur = m.group(1)
            out[cur] = ""
        if cur:
            out[cur] += ln + "\n"
    return out


def _dist(req: str) -> str:
    return re.split(r"[<>=!~\[ ;]", req, maxsplit=1)[0].lower()


def _floor(req: str) -> Optional[str]:
    m = re.search(r">=([\d.]+)", req)
    return m.group(1) if m else None


def _contrib_job() -> str:
    text = CI.read_text(encoding="utf-8")
    start = text.index("\n  contrib:")
    end = re.search(r"\n  [a-z][a-z0-9-]*:\n", text[start + 5 :])
    return text[start : start + 5 + end.start()] if end else text[start:]


def _matrix_extras() -> List[str]:
    job = _contrib_job()
    block = job.split("extra:", 1)[1].split("os:", 1)[0]
    return re.findall(r"^\s+- ([a-z]+)\s*$", block, re.M)


def _count_tests(folder: pathlib.Path) -> int:
    n = 0
    for f in folder.rglob("test_*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef)
            ) and node.name.startswith("test"):
                n += 1
    return n


# -----------------------------------------------------------------------------
# 1. zero-dependency guard is not vacuous
# -----------------------------------------------------------------------------
class TestZeroDepGuardBites(unittest.TestCase):
    def _guard_on(self, src: pathlib.Path) -> dict:
        code = zd.CHILD % {
            "src": str(src),
            "optional": sorted(zd.OPTIONAL_THIRD_PARTY),
        }
        return _child(code)

    def _poisoned_copy(self, tmp: str) -> pathlib.Path:
        dst = pathlib.Path(tmp) / "src"
        shutil.copytree(
            str(PKG),
            str(dst / "xstate_statemachine"),
            ignore=shutil.ignore_patterns("__pycache__", "contrib"),
        )
        # contrib must exist as a package for the leak variant
        shutil.copytree(
            str(CONTRIB),
            str(dst / "xstate_statemachine" / "contrib"),
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        return dst

    def test_a_core_module_importing_a_third_party_fails_the_guard(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = self._poisoned_copy(tmp)
            (dst / "xstate_statemachine" / "_poison.py").write_text(
                "import requests_battle_258_poison  # noqa\n", "utf-8"
            )
            rep = self._guard_on(dst)
        self.assertIn("requests_battle_258_poison", rep["violations"])
        self.assertIn("xstate_statemachine._poison", rep["failed"])

    def test_a_real_installed_third_party_is_still_caught(self) -> None:
        # json-tolerant: `pip` is always installed next to the interpreter
        with tempfile.TemporaryDirectory() as tmp:
            dst = self._poisoned_copy(tmp)
            (dst / "xstate_statemachine" / "_poison.py").write_text(
                "import pip  # noqa\n", "utf-8"
            )
            rep = self._guard_on(dst)
        self.assertIn("pip", rep["violations"])

    def test_core_importing_contrib_is_reported_as_a_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dst = self._poisoned_copy(tmp)
            init = dst / "xstate_statemachine" / "__init__.py"
            init.write_text(
                init.read_text("utf-8")
                + "\nfrom .contrib import _compat as _leak  # noqa\n",
                "utf-8",
            )
            rep = self._guard_on(dst)
        self.assertIn(
            "xstate_statemachine.contrib._compat", rep["leaked_contrib"]
        )

    def test_every_stdlib_name_core_uses_passes_the_39_origin_probe(
        self,
    ) -> None:
        """The 3.9 branch of the guard (no ``stdlib_module_names``) must
        accept every stdlib module core imports -- else 3.9 CI goes red on
        a false positive, or worse, the probe is too loose."""
        used: Set[str] = set()
        for f in PKG.rglob("*.py"):
            if "contrib" in f.relative_to(PKG).parts:
                continue
            for node in ast.walk(ast.parse(f.read_text("utf-8-sig"))):
                if isinstance(node, ast.Import):
                    used |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    used.add((node.module or "").split(".")[0])
        names = getattr(sys, "stdlib_module_names", None)
        if names is None:
            self.skipTest("needs 3.10+ for the reference name set")
        stdlib_used = sorted(
            (used & set(names))
            - {"__future__"}
            - set(sys.builtin_module_names)
        )
        code = (
            zd.CHILD.split("ALLOWED_ROOTS", 1)[0].replace(
                'STDLIB = set(getattr(sys, "stdlib_module_names", ()))',
                "STDLIB = set()",
            )
            + "PLATFORM = %r\n"
            "print(json.dumps({'bad': [n for n in %r if n not in PLATFORM"
            " and not is_stdlib(n)]}))\n"
        ) % (
            {
                "msvcrt",
                "winreg",
                "_winapi",
                "termios",
                "tty",
                "fcntl",
                "pwd",
                "grp",
                "resource",
                "readline",
            },
            stdlib_used,
        )
        rep = _child(code)
        self.assertEqual(rep["bad"], [], "3.9 probe rejects real stdlib")
        # ...and it is not trivially permissive
        rep2 = _child(
            code.replace(repr(stdlib_used), repr(["pip", "setuptools"]))
        )
        self.assertEqual(sorted(rep2["bad"]), ["pip", "setuptools"])


# -----------------------------------------------------------------------------
# 1./5. bare interpreter: import surface
# -----------------------------------------------------------------------------
BARE_SURFACE = r"""
import json, sys, time
sys.path.insert(0, %(src)r)
t = time.perf_counter()
import xstate_statemachine as x
ms = (time.perf_counter() - t) * 1000
std = set(getattr(sys, "stdlib_module_names", ()))
# 📝 Loaded by site-packages `.pth` hooks at interpreter start on some
#    runners (setuptools' distutils shim on 3.10/3.11 CI cells), never by
#    the library. Not stdlib, not ours, not a leak.
PTH = {"_distutils_hack", "_virtualenv", "sitecustomize", "usercustomize"}
tops = sorted({m.split(".")[0] for m in sys.modules})
third = [t for t in tops if std and t not in std
         and t not in ("xstate_statemachine", "__main__") and t not in PTH]
bad_all = []
contrib_syms = []
for n in x.__all__:
    try:
        o = getattr(x, n)
    except AttributeError:
        bad_all.append(n); continue
    if "contrib" in (getattr(o, "__module__", "") or ""):
        contrib_syms.append(n)
import importlib
subs = {}
for s in ("persistence", "patterns", "eda", "graph", "receipts",
          "testing_utils", "coverage", "inspect"):
    try:
        importlib.import_module("xstate_statemachine." + s); subs[s] = "ok"
    except Exception as e:
        subs[s] = repr(e)
import xstate_statemachine.exceptions as ex
after = sorted({m.split(".")[0] for m in sys.modules})
third_after = [t for t in after if std and t not in std
               and t not in ("xstate_statemachine", "__main__")
               and t not in PTH]
print(json.dumps({"ms": ms, "third": third, "third_after": third_after,
  "pytest": "pytest" in sys.modules, "bad_all": bad_all,
  "contrib_syms": contrib_syms, "subs": subs,
  "mee_top": "MissingExtraError" in x.__all__,
  "mee_exc": "MissingExtraError" in getattr(ex, "__all__", []),
  "contrib_loaded": [m for m in sys.modules if ".contrib" in m]}))
"""


@needs_bare
class TestBareInterpreterSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rep = _child(BARE_SURFACE % {"src": str(SRC)}, BARE)

    def test_core_import_loads_no_third_party_and_never_pytest(self) -> None:
        self.assertEqual(self.rep["third"], [])
        self.assertFalse(self.rep["pytest"])

    def test_core_subpackages_all_import_clean(self) -> None:
        self.assertEqual(
            {k: v for k, v in self.rep["subs"].items() if v != "ok"}, {}
        )
        # ...and still pull in nothing third-party, nor any contrib
        self.assertEqual(self.rep["third_after"], [])
        self.assertEqual(self.rep["contrib_loaded"], [])

    def test_every_all_name_resolves_and_none_is_contrib(self) -> None:
        self.assertEqual(self.rep["bad_all"], [])
        self.assertEqual(self.rep["contrib_syms"], [])

    def test_missing_extra_error_is_exported_both_places(self) -> None:
        self.assertTrue(self.rep["mee_top"])
        self.assertTrue(self.rep["mee_exc"])

    def test_exceptions_all_lists_every_exception_class(self) -> None:
        from src.xstate_statemachine import exceptions as ex

        classes = {
            n
            for n, o in vars(ex).items()
            if isinstance(o, type)
            and issubclass(o, BaseException)
            and o.__module__ == ex.__name__
        }
        self.assertEqual(set(ex.__all__), classes)

    def test_import_wall_time_is_reported(self) -> None:
        # 📝 report, not a perf gate (tests/test_perf_budgets.py owns that;
        #    ~65 ms on Linux CI). The ceiling only catches a pathological
        #    regression such as an accidental heavy import.
        ms = self.rep["ms"]
        print(f"\n[258] bare `import xstate_statemachine`: {ms:.0f} ms")
        self.assertLess(ms, 2000)


# -----------------------------------------------------------------------------
# 2. MissingExtraError at every lazy site
# -----------------------------------------------------------------------------
PROBE_CONTRIB = r"""
import importlib, json, sys
sys.path.insert(0, %(src)r)
from xstate_statemachine.exceptions import MissingExtraError
out = {}
for sub in %(subs)r:
    try:
        importlib.import_module("xstate_statemachine.contrib." + sub)
        out[sub] = None
    except ImportError as e:  # MissingExtraError must be caught HERE
        out[sub] = {"mee": isinstance(e, MissingExtraError),
                    "extra": getattr(e, "extra", None),
                    "module": getattr(e, "module", None), "msg": str(e)}
print(json.dumps(out))
"""

#: subpackage -> (extra, module named first in a bare env)
EXPECTED_BARE = {
    "agents": ("agents", "pydantic"),
    "celery": ("celery", "celery"),
    "channels": ("channels", "channels"),
    "cloudevents": ("cloudevents", "cloudevents"),
    "django": ("django", "django"),
    "drf": ("drf", "rest_framework"),
    "fastapi": ("fastapi", "fastapi"),
    "flask": ("flask", "flask"),
    "litestar": ("litestar", "litestar"),
    "observability": ("observability", "opentelemetry"),
    "observability.otel": ("observability", "opentelemetry"),
    "observability.prometheus": ("observability", "opentelemetry"),
    "pydantic": ("pydantic", "pydantic"),
    "quart": ("flask", "flask"),
    "flask.quart": ("flask", "flask"),
    "redis": ("redis", "redis"),
    "sqlalchemy": ("sqlalchemy", "sqlalchemy"),
    "starlette": ("starlette", "starlette"),
    "brokers.kafka": ("kafka", "aiokafka"),
    "brokers.rabbitmq": ("rabbitmq", "aio_pika"),
    "brokers.nats": ("nats", "nats"),
    "brokers.sqs": ("sqs", "boto3"),
    "brokers.redis_streams": ("redis", "redis"),
}
#: import fine in a bare env by design (documented)
IMPORT_CLEAN_BARE = {"brokers"}


def _pinned(module: str, extra: str) -> str:
    return (
        f"`{module}` is not installed. Install the extra: "
        f'pip install "xstate-statemachine[{extra}]"'
    )


@needs_bare
class TestMissingExtraBare(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subs = sorted(EXPECTED_BARE) + sorted(IMPORT_CLEAN_BARE)
        cls.rep = _child(PROBE_CONTRIB % {"src": str(SRC), "subs": subs}, BARE)

    def test_every_top_level_subpackage_is_enumerated(self) -> None:
        on_disk = {
            p.name
            for p in CONTRIB.iterdir()
            if p.is_dir() and not p.name.startswith("_")
        }
        # `testing` needs only pytest -- present wherever tests run
        self.assertEqual(
            on_disk - set(EXPECTED_BARE) - IMPORT_CLEAN_BARE, {"testing"}
        )

    def test_each_site_raises_missing_extra_with_the_pinned_message(
        self,
    ) -> None:
        for sub, (extra, module) in EXPECTED_BARE.items():
            with self.subTest(sub=sub):
                r = self.rep[sub]
                self.assertIsNotNone(r, f"{sub} imported without its extra")
                self.assertTrue(r["mee"], r)
                self.assertEqual((r["extra"], r["module"]), (extra, module))
                self.assertTrue(
                    r["msg"].startswith(_pinned(module, extra)), r["msg"]
                )

    def test_brokers_package_itself_imports_clean(self) -> None:
        for sub in IMPORT_CLEAN_BARE:
            self.assertIsNone(self.rep[sub])


BLOCKED = r"""
import importlib, importlib.abc, json, sys
blocked = set(%(blocked)r)
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in blocked:
            raise ImportError("blocked: " + name)
        return None
sys.meta_path.insert(0, Block())
sys.path.insert(0, %(src)r)
from xstate_statemachine.exceptions import MissingExtraError
try:
%(body)s
    print(json.dumps({"raised": None}))
except ImportError as e:
    print(json.dumps({"raised": type(e).__name__,
        "mee": isinstance(e, MissingExtraError),
        "extra": getattr(e, "extra", None),
        "module": getattr(e, "module", None), "msg": str(e)}))
"""


def _blocked(blocked: List[str], body: str) -> dict:
    body = "\n".join("    " + ln for ln in body.strip().splitlines())
    return _child(
        BLOCKED % {"blocked": blocked, "src": str(SRC), "body": body}
    )


def _have(*mods: str):
    missing = [m for m in mods if importlib.util.find_spec(m) is None]
    return unittest.skipIf(missing, f"needs {missing} installed")


class TestMissingExtraTransitiveAndLazy(unittest.TestCase):
    """Attack the sites a bare env cannot reach: a dependency that is
    present but whose sibling is not, and first-use (lazy) soft deps."""

    @_have("channels")
    def test_channels_with_django_blocked_names_django_under_channels(
        self,
    ) -> None:
        r = _blocked(
            ["django"],
            "import xstate_statemachine.contrib.channels",
        )
        self.assertTrue(r["mee"], r)
        self.assertEqual(r["extra"], "channels")
        self.assertEqual(r["module"], "django")

    @_have("rest_framework")
    def test_drf_with_django_blocked_names_drf_not_django(self) -> None:
        r = _blocked(["django"], "import xstate_statemachine.contrib.drf")
        self.assertTrue(r["mee"], r)
        # 📝 `rest_framework` is installed, but importing it imports django:
        #    the extra must still be the one the user tried to use.
        self.assertEqual(r["extra"], "drf")

    @_have("litestar")
    def test_litestar_with_starlette_blocked_names_litestar(self) -> None:
        r = _blocked(
            ["starlette"], "import xstate_statemachine.contrib.litestar"
        )
        self.assertTrue(r["mee"], r)
        self.assertEqual(r["extra"], "litestar")

    @_have("fastapi")
    def test_fastapi_with_pydantic_blocked_names_fastapi(self) -> None:
        r = _blocked(
            ["pydantic"], "import xstate_statemachine.contrib.fastapi"
        )
        self.assertTrue(r["mee"], r)
        self.assertEqual(r["extra"], "fastapi")

    @_have("opentelemetry", "prometheus_client")
    def test_structlog_is_lazy_first_use_with_the_soft_hint(self) -> None:
        r = _blocked(
            ["structlog"],
            "from xstate_statemachine.contrib.observability import logs\n"
            "logs.StructlogPlugin()",
        )
        self.assertTrue(r["mee"], r)
        self.assertEqual(
            (r["extra"], r["module"]), ("observability", "structlog")
        )
        self.assertIn("pip install structlog", r["msg"])

    @_have("opentelemetry", "prometheus_client")
    def test_sentry_is_lazy_first_use(self) -> None:
        r = _blocked(
            ["sentry_sdk"],
            "from xstate_statemachine.contrib.observability import sentry\n"
            "sentry.SentryPlugin()",
        )
        self.assertTrue(r["mee"], r)
        self.assertIn("pip install sentry-sdk", r["msg"])

    @_have("pytest")
    def test_hypothesis_is_lazy_in_testing_model(self) -> None:
        r = _blocked(
            ["hypothesis"],
            "from xstate_statemachine.contrib.testing import model\n"
            "model.payload_strategy({'type': 'object'})",
        )
        self.assertTrue(r["mee"], r)
        self.assertEqual((r["extra"], r["module"]), ("testing", "hypothesis"))

    @_have("flask")
    def test_quart_shim_names_flask_and_carries_the_quart_hint(self) -> None:
        r = _blocked(["quart"], "import xstate_statemachine.contrib.quart")
        self.assertTrue(r["mee"], r)
        self.assertEqual((r["extra"], r["module"]), ("flask", "quart"))
        # 📝 [flask] does not install quart: the hint is what tells them so
        self.assertIn("pip install quart", r["msg"])

    @_have("pydantic")
    def test_langgraph_submodule_is_import_time_with_hint(self) -> None:
        r = _blocked(
            ["langgraph"],
            "import xstate_statemachine.contrib.agents.langgraph",
        )
        self.assertTrue(r["mee"], r)
        self.assertEqual(r["extra"], "agents")
        self.assertIn("pip install langgraph", r["msg"])

    def test_require_extra_names_the_first_missing_not_the_first_arg(
        self,
    ) -> None:
        from src.xstate_statemachine.contrib._compat import require_extra
        from src.xstate_statemachine.exceptions import MissingExtraError

        with self.assertRaises(ImportError) as cm:
            require_extra("x", "json", "battle_258_absent_mod")
        self.assertIsInstance(cm.exception, MissingExtraError)
        self.assertEqual(cm.exception.module, "battle_258_absent_mod")
        self.assertEqual(
            str(cm.exception), _pinned("battle_258_absent_mod", "x")
        )

    def test_a_broken_installed_module_is_a_missing_extra_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pathlib.Path(tmp, "battle258broken.py").write_text(
                "import battle_258_absent_inner\n", "utf-8"
            )
            r = _child(
                "import json, sys\n"
                f"sys.path[:0] = [{tmp!r}, {str(SRC)!r}]\n"
                "from xstate_statemachine.contrib._compat import "
                "require_extra\n"
                "from xstate_statemachine.exceptions import "
                "MissingExtraError\n"
                "try:\n    require_extra('e', 'battle258broken')\n"
                "except MissingExtraError as e:\n"
                "    print(json.dumps({'m': e.module, 's': str(e)}))\n"
            )
        self.assertEqual(r["m"], "battle258broken")
        self.assertIn("import failed", r["s"])

    def test_registry_modules_match_each_require_extra_call(self) -> None:
        """`contrib/_registry.py` drives the extras-matrix blocking test and
        `requires_extra()` skips: it must list every module the subpackage
        actually gates on, or the matrix test blocks too little."""
        for name, extra in EXTRAS.items():
            if not extra.subpackage:
                continue
            path = CONTRIB.joinpath(*extra.subpackage.split("."))
            src = (
                path / "__init__.py"
                if path.is_dir()
                else path.with_suffix(".py")
            ).read_text("utf-8")
            m = re.search(r"^require_extra\(([^)]*)\)", src, re.M)
            self.assertTrue(m, name)
            args = re.findall(r'"([^"]+)"', m.group(1))
            with self.subTest(extra=name):
                self.assertEqual(args[0], name)
                # 📝 a subset: [testing] gates on pytest at import and on
                #    hypothesis lazily (contrib/testing/model.py)
                self.assertLessEqual(set(args[1:]), set(extra.modules))
                self.assertTrue(args[1:], name)


# -----------------------------------------------------------------------------
# 3. extras resolve
# -----------------------------------------------------------------------------
class TestExtrasDeclaration(unittest.TestCase):
    def setUp(self) -> None:
        self.ex = _pyproject_extras()

    def test_all_is_exactly_the_union_of_every_integration_extra(
        self,
    ) -> None:
        union: Dict[str, str] = {}
        for k, reqs in self.ex.items():
            if k in UMBRELLAS | NOT_INTEGRATION:
                continue
            for r in reqs:
                union[_dist(r)] = r
        alls = {_dist(r): r for r in self.ex["all"]}
        self.assertEqual(alls, union)

    def test_umbrellas_equal_the_union_of_their_named_members(self) -> None:
        raw = _raw_extra_lines()
        for umb in ("web", "eda"):
            with self.subTest(umbrella=umb):
                m = re.search(r"#\s*\[([a-z, ]+)\]", raw[umb])
                self.assertTrue(m, f"{umb} must name its members")
                members = [s.strip() for s in m.group(1).split(",")]
                want = {_dist(r): r for mem in members for r in self.ex[mem]}
                got = {_dist(r): r for r in self.ex[umb]}
                self.assertEqual(got, want)

    def test_every_pin_has_a_floor_and_no_unexplained_upper_bound(
        self,
    ) -> None:
        raw = _raw_extra_lines()
        for k, reqs in self.ex.items():
            for r in reqs:
                with self.subTest(req=r):
                    self.assertIsNotNone(_floor(r), r)
                    if "<" in r:
                        line = next(
                            ln for ln in raw[k].splitlines() if r in ln
                        )
                        self.assertIn("#", line, f"{r}: say why")


class TestExtrasResolveOnPyPI(unittest.TestCase):
    _cache: Dict[str, dict] = {}

    @classmethod
    def setUpClass(cls) -> None:
        # 📝 probed here, not at import: pytest-socket only blocks once
        #    tests run, so an import-time probe always says "online".
        if not _network_ok():
            raise unittest.SkipTest("network disabled (--disable-socket)")

    def _meta(self, dist: str) -> dict:
        if dist not in self._cache:
            import urllib.request

            with urllib.request.urlopen(
                f"https://pypi.org/pypi/{dist}/json", timeout=30
            ) as resp:
                self._cache[dist] = json.load(resp)
        return self._cache[dist]

    def test_every_floor_exists_and_installs_on_39(self) -> None:
        reqs = {r for v in _pyproject_extras().values() for r in v}
        for r in sorted(reqs):
            with self.subTest(req=r):
                dist, floor = _dist(r), _floor(r)
                rel = self._meta(dist)["releases"]
                hit = next(
                    (
                        v
                        for v in (floor, f"{floor}.0", f"{floor}.0.0")
                        if rel.get(v)
                    ),
                    None,
                )
                self.assertIsNotNone(hit, f"{r}: floor not on PyPI")
                files = rel[hit]
                ok = any(
                    f["filename"].endswith(".tar.gz")
                    or re.search(r"-(py3|py2\.py3|cp39)-", f["filename"])
                    for f in files
                )
                self.assertTrue(ok, f"{r}: no 3.9-installable file")
                rp = files[0].get("requires_python") or ""
                m = re.search(r">=\s*3\.(\d+)", rp)
                self.assertTrue(not m or int(m.group(1)) <= 9, (r, rp))

    def _dry_run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--dry-run",
                "--ignore-installed",
                "-q",
                "--disable-pip-version-check",
                *args,
            ],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(ROOT),
        )

    def test_floor_pairings_the_compat_job_does_not_pin_together(
        self,
    ) -> None:
        pairs = [
            ("litestar==2.0.0", "starlette==0.27.0"),
            ("djangorestframework==3.14.0", "django==4.2"),
            ("channels==4.0.0", "django==4.2"),
        ]
        for pair in pairs:
            with self.subTest(pair=pair):
                p = self._dry_run(*pair)
                self.assertEqual(p.returncode, 0, p.stderr[-2000:])

    def test_all_resolves_as_one_set(self) -> None:
        p = self._dry_run("-e", ".[all]")
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])


# -----------------------------------------------------------------------------
# 4. CI matrix honesty
# -----------------------------------------------------------------------------
#: test-import name -> pip distribution
IMPORT_TO_DIST = {
    "rest_framework": "djangorestframework",
    "drf_spectacular": "drf-spectacular",
    "django_fsm": "django-fsm-2",
    "pydantic_ai": "pydantic-ai-slim",
    "langchain_core": "langchain-core",
    "flask_wtf": "flask-wtf",
    "aio_pika": "aio-pika",
    "nats": "nats-py",
    "prometheus_client": "prometheus-client",
    "opentelemetry": "opentelemetry-api",
    "yaml": "pyyaml",
}
#: local test-project packages, not distributions
LOCAL = {
    "src",
    "tests",
    "shop",
    "legacy",
    "project",
    "conftest",
    "xstate_statemachine",
}


def _module_level_imports(folder: pathlib.Path) -> Set[str]:
    """Third-party roots imported at module level (unconditionally) by the
    folder's test and conftest files -- the ones that error collection."""
    std = set(getattr(sys, "stdlib_module_names", ()))
    out: Set[str] = set()
    for f in folder.glob("*.py"):
        tree = ast.parse(f.read_text("utf-8-sig"))
        for node in tree.body:
            names: List[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level:
                names = [node.module or ""]
            for n in names:
                root = n.split(".")[0]
                if root and root not in std and root not in LOCAL:
                    out.add(root)
    return out - {"pytest"}


def _cell_install_text(extra: str) -> str:
    job = _contrib_job()
    deps = " ".join(_pyproject_extras().get(extra, []))
    m = re.search(rf"^\s+{extra}\) (.*?);;", job, re.M)
    return (deps + " " + (m.group(1) if m else "")).lower()


class TestCIMatrix(unittest.TestCase):
    def test_every_integration_extra_has_a_cell(self) -> None:
        cells = set(_matrix_extras())
        want = set(EXTRAS) - UMBRELLAS
        self.assertEqual(want - cells, set())
        self.assertEqual(cells - set(EXTRAS), set())

    def test_every_cell_folder_collects_real_tests(self) -> None:
        for extra in _matrix_extras():
            folder = ROOT / "tests" / "contrib" / extra
            with self.subTest(extra=extra):
                self.assertTrue(folder.is_dir(), "placeholder cell left")
                self.assertGreater(_count_tests(folder), 0)

    def test_no_exit_5_mask_in_the_contrib_job(self) -> None:
        # 📝 every extra now ships tests; "no tests collected" must be red
        self.assertNotIn("$? -eq 5", _contrib_job())

    def test_every_run_step_uses_bash_for_windows_cells(self) -> None:
        job = _contrib_job()
        if "windows" not in job:
            self.skipTest("no windows cell")
        steps = re.split(r"\n\s+- (?:name|uses):", job)
        for st in steps:
            if "run:" in st:
                self.assertIn("shell: bash", st, st[:120])

    @unittest.skipIf(
        sys.version_info < (3, 10), "needs sys.stdlib_module_names"
    )
    def test_each_cell_installs_its_folders_unconditional_imports(
        self,
    ) -> None:
        gaps: Dict[str, List[str]] = {}
        for extra in _matrix_extras():
            folder = ROOT / "tests" / "contrib" / extra
            text = _cell_install_text(extra)
            for mod in sorted(_module_level_imports(folder)):
                dist = IMPORT_TO_DIST.get(mod, mod).lower()
                if dist.replace("_", "-") not in text.replace("_", "-"):
                    gaps.setdefault(extra, []).append(f"{mod}->{dist}")
        self.assertEqual(gaps, {})


# -----------------------------------------------------------------------------
# 6. docs
# -----------------------------------------------------------------------------
class TestDocs(unittest.TestCase):
    def test_extras_page_table_lists_every_extra(self) -> None:
        text = EXTRAS_PAGE.read_text(encoding="utf-8")
        table = "\n".join(
            ln for ln in text.splitlines() if ln.startswith("| `")
        )
        for extra in set(_pyproject_extras()) - NOT_INTEGRATION:
            self.assertIn(f"`{extra}`", table, extra)

    def test_every_install_one_liner_names_a_real_extra(self) -> None:
        real = set(_pyproject_extras())
        files = list((ROOT / "docs" / "_guide").glob("*.md")) + [
            API_INDEX,
            ROOT / "README.md",
        ]
        bad = []
        for f in files:
            if f.name == "changelog.md":
                continue
            for m in re.finditer(
                r"xstate-statemachine\[([a-z, ]+)\]", f.read_text("utf-8")
            ):
                for e in m.group(1).split(","):
                    if e.strip() not in real:
                        bad.append(f"{f.name}: [{e.strip()}]")
        self.assertEqual(bad, [])

    def test_api_index_documents_missing_extra_error_and_require_extra(
        self,
    ) -> None:
        text = API_INDEX.read_text(encoding="utf-8")
        self.assertIn("MissingExtraError", text)
        self.assertIn("require_extra", text)

    def test_api_contrib_table_has_one_row_per_extra(self) -> None:
        text = API_INDEX.read_text(encoding="utf-8")
        rows = re.findall(r"^\| `\[([a-z]+)\]` \|", text, re.M)
        dupes = sorted({r for r in rows if rows.count(r) > 1})
        self.assertEqual(dupes, [])

    def test_integrations_page_does_not_call_shipped_brokers_planned(
        self,
    ) -> None:
        text = (ROOT / "docs" / "_guide" / "integrations.md").read_text(
            "utf-8"
        )
        self.assertNotIn("planned #294", text)
        self.assertNotIn("broker adapters planned", text)
        desc = EXTRAS_PAGE.read_text("utf-8").split("\n---", 1)[0]
        self.assertNotIn("planned", desc)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
