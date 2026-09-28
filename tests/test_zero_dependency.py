"""The core library has zero runtime dependencies -- enforced, not promised.

🏛️ Programme invariant #1 (epic #257, #258): ``import xstate_statemachine``
and every module under it *except* ``contrib`` must import with every
non-stdlib import blocked. Framework integrations live in ``contrib/`` and
are only ever imported explicitly by the user.

📝 Why a subprocess: an in-process ``importlib.reload`` sweep re-creates
exception classes, so ``isinstance`` / ``except XStateMachineError`` in the
rest of the test session silently breaks (observed). A child interpreter
starts clean, installs the blocking finder *first*, imports the package the
way a user would, and reports what happened as JSON.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

#: 🧷 Third-party names the CLI *optionally* imports inside ``try/except
#: ImportError`` (code formatting of generated output). The guard must let
#: those attempts FAIL normally (they are optional) rather than count them
#: as violations -- so they are blocked (raise ImportError) but not recorded.
#:
#: ``org`` is not ours at all: CPython's own ``copy.py`` (<= 3.11) probes
#: ``from org.python.core import PyStringMap`` for Jython inside a
#: ``try/except ImportError``. It is stdlib behaviour, not a dependency.
OPTIONAL_THIRD_PARTY = {"black", "isort", "org"}

# The child script. Kept as a string so the whole check is one process with
# no imports from this repository happening before the finder is in place.
CHILD = r"""
import importlib, importlib.abc, importlib.machinery, json, os, pkgutil, sys, sysconfig

STDLIB = set(getattr(sys, "stdlib_module_names", ()))
# Everything that ships WITH the interpreter lives under base_prefix
# (Lib/, DLLs/ on Windows, lib-dynload/ on POSIX); third-party code lives
# in site-packages/dist-packages, so those two subtrees are the exclusion.
BASE = os.path.realpath(sys.base_prefix)
THIRD_PARTY_MARKERS = (os.sep + "site-packages" + os.sep, os.sep + "dist-packages" + os.sep)

def is_stdlib(root):
    # 3.10+: the frozen name set. 3.9: resolve with the DEFAULT path finder
    # and accept built-ins, frozen modules and anything living under the
    # stdlib directory (but not its site-packages).
    if STDLIB:
        return root in STDLIB
    if root in sys.builtin_module_names:
        return True
    spec = importlib.machinery.PathFinder.find_spec(root, None)
    if spec is None:
        return False
    origin = getattr(spec, "origin", None)
    if origin in (None, "built-in", "frozen"):
        return True
    origin = os.path.realpath(origin)
    return origin.startswith(BASE) and not any(m in origin for m in THIRD_PARTY_MARKERS)

ALLOWED_ROOTS = {"xstate_statemachine", "_distutils_hack", "__editable__"}
# Platform-specific stdlib modules do not exist on the other OS, so the
# 3.9 origin probe cannot see them; they are stdlib everywhere they exist.
PLATFORM_STDLIB = {"msvcrt", "winreg", "_winapi", "termios", "tty", "fcntl", "pwd", "grp", "resource", "readline", "_posixsubprocess", "nt", "posix"}
OPTIONAL = %(optional)r
violations = []

class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        root = name.split(".")[0]
        if root in ALLOWED_ROOTS or root in PLATFORM_STDLIB or root.startswith("__editable___") or is_stdlib(root):
            return None
        if root not in OPTIONAL:
            violations.append(name)
        raise ImportError("blocked by zero-dependency guard: " + name)

sys.meta_path.insert(0, Guard())
sys.path.insert(0, %(src)r)

try:
    import xstate_statemachine  # noqa: E402  -- the user's import
except ImportError as e:
    print(json.dumps({"violations": sorted(set(violations)) or [str(e)], "leaked_contrib": [],
                      "imported": 0, "failed": {"xstate_statemachine": str(e)}}))
    raise SystemExit(0)
leaked = sorted(m for m in sys.modules if m.startswith("xstate_statemachine.contrib"))

imported = []
failed = {}
pkg = xstate_statemachine

def _walk(path, prefix):
    # 📝 `pkgutil.walk_packages` IMPORTS every subpackage to recurse into it,
    #    which would execute `contrib/<extra>/__init__.py` (and its
    #    `require_extra` probe) before the name filter could skip it. Walk
    #    one level at a time and never descend into `contrib`.
    for info in pkgutil.iter_modules(path, prefix):
        if info.name.rsplit(".", 1)[-1] == "contrib":
            continue
        yield info
        if info.ispkg:
            sub = importlib.import_module(info.name)
            yield from _walk(sub.__path__, info.name + ".")

for info in _walk(pkg.__path__, pkg.__name__ + "."):
    try:
        importlib.import_module(info.name)
        imported.append(info.name)
    except ImportError as e:
        # optional deps (black/isort) are allowed to be missing; anything
        # else that fails to import under the guard is a violation
        if not any(o in str(e) for o in OPTIONAL):
            failed[info.name] = str(e)

print(json.dumps({"violations": sorted(set(violations)), "leaked_contrib": leaked,
                  "imported": len(imported), "failed": failed}))
"""


def _run_guard() -> dict:
    code = CHILD % {"src": str(SRC), "optional": sorted(OPTIONAL_THIRD_PARTY)}
    proc = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            code,
        ],  # -I: isolated, no site-packages leakage
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(ROOT),
    )
    assert proc.returncode == 0, f"guard child crashed:\n{proc.stderr[-4000:]}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


class TestZeroDependencyCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = _run_guard()

    def test_no_third_party_import_is_attempted_by_core(self) -> None:
        self.assertEqual(
            self.report["violations"],
            [],
            "core attempted third-party imports: "
            f"{self.report['violations']}",
        )

    def test_every_core_module_imports_under_the_guard(self) -> None:
        self.assertEqual(self.report["failed"], {}, self.report["failed"])
        # sanity: the sweep actually walked the package
        self.assertGreater(self.report["imported"], 40)

    def test_importing_the_package_does_not_touch_contrib(self) -> None:
        self.assertEqual(self.report["leaked_contrib"], [])


class TestMissingExtraError(unittest.TestCase):
    def test_message_names_the_pip_command_and_is_an_import_error(
        self,
    ) -> None:
        from src.xstate_statemachine import MissingExtraError
        from src.xstate_statemachine.contrib._compat import (
            extra_available,
            require_extra,
        )

        with self.assertRaises(ImportError) as cm:  # the base-class contract
            require_extra("fastapi", "definitely_not_installed_module_xyz")
        err = cm.exception
        self.assertIsInstance(err, MissingExtraError)
        self.assertEqual(
            str(err),
            "`definitely_not_installed_module_xyz` is not installed. "
            'Install the extra: pip install "xstate-statemachine[fastapi]"',
        )
        self.assertEqual(
            (err.extra, err.module),
            ("fastapi", "definitely_not_installed_module_xyz"),
        )
        # stdlib modules are always available; defaults to (extra,)
        require_extra("json")
        self.assertTrue(extra_available("json", "os"))
        self.assertFalse(
            extra_available("json", "definitely_not_installed_module_xyz")
        )

    def test_hint_is_appended(self) -> None:
        from src.xstate_statemachine.contrib._compat import require_extra

        with self.assertRaises(ImportError) as cm:
            require_extra(
                "observability", "nope_nope", hint="or: pip install structlog"
            )
        self.assertTrue(
            str(cm.exception).endswith("or: pip install structlog")
        )


if __name__ == "__main__":
    unittest.main()
