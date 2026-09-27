"""Every integration must fail loudly and helpfully without its extra.

🏛️ Programme invariant #2 (epic #257, #258): importing
``xstate_statemachine.contrib.<name>`` when the extra is not installed
raises `MissingExtraError` naming the exact pip command -- never a bare
``ModuleNotFoundError`` from deep inside the package.

The registry (`contrib/_registry.py`) is the single list of extras; this
test blocks each entry's third-party modules with a meta-path finder and
imports the subpackage in a subprocess (so the block cannot leak into the
rest of the session). Subpackages that do not exist yet are placeholders
and are skipped -- they become real assertions the moment the owning issue
adds the directory.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import unittest

from src.xstate_statemachine.contrib._registry import EXTRAS

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
CONTRIB = SRC / "xstate_statemachine" / "contrib"

CHILD = r"""
import importlib, importlib.abc, json, sys
blocked = set(%(modules)r)
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in blocked:
            raise ImportError("blocked: " + name)
        return None
sys.meta_path.insert(0, Block())
sys.path.insert(0, %(src)r)
try:
    importlib.import_module("xstate_statemachine.contrib." + %(sub)r)
except Exception as e:  # noqa: BLE001
    from xstate_statemachine.exceptions import MissingExtraError
    print(json.dumps({"type": type(e).__name__, "is_missing_extra": isinstance(e, MissingExtraError),
                      "is_import_error": isinstance(e, ImportError), "msg": str(e)}))
else:
    print(json.dumps({"type": None}))
"""


def _pyproject_extras() -> set:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("[project.optional-dependencies]", 1)[1].split(
        "\n[", 1
    )[0]
    return set(re.findall(r"^([a-z]+)\s*=", block, re.M))


class TestExtrasRegistry(unittest.TestCase):
    def test_every_registry_extra_is_declared_in_pyproject(self) -> None:
        declared = _pyproject_extras()
        missing = sorted(set(EXTRAS) - declared)
        self.assertEqual(
            missing, [], f"extras missing from pyproject: {missing}"
        )

    def test_every_pyproject_extra_is_in_the_registry_or_format(self) -> None:
        unknown = sorted(_pyproject_extras() - set(EXTRAS) - {"format"})
        self.assertEqual(
            unknown, [], f"pyproject extras not in registry: {unknown}"
        )


class TestMissingExtraContract(unittest.TestCase):
    def _existing_subpackages(self):
        for name, extra in EXTRAS.items():
            if not extra.subpackage:
                continue
            path = CONTRIB.joinpath(*extra.subpackage.split("."))
            if path.is_dir() or path.with_suffix(".py").is_file():
                yield name, extra

    def test_blocked_dependency_raises_missing_extra_error(self) -> None:
        seen = 0
        for name, extra in self._existing_subpackages():
            with self.subTest(extra=name):
                code = CHILD % {
                    "modules": list(extra.modules),
                    "src": str(SRC),
                    "sub": extra.subpackage,
                }
                proc = subprocess.run(
                    [sys.executable, "-I", "-c", code],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=str(ROOT),
                )
                self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
                report = json.loads(proc.stdout.strip().splitlines()[-1])
                self.assertTrue(
                    report["is_missing_extra"],
                    f"[{name}] raised {report['type']}: {report.get('msg')}",
                )
                self.assertTrue(report["is_import_error"])
                self.assertIn(
                    f'pip install "xstate-statemachine[{name}]"', report["msg"]
                )
                seen += 1
        if seen == 0:
            self.skipTest(
                "no contrib subpackages exist yet (placeholders only)"
            )

    def test_installed_extras_import_cleanly(self) -> None:
        """When the dependency IS present, the subpackage must import."""
        seen = 0
        for name, extra in self._existing_subpackages():
            if all(importlib.util.find_spec(m) for m in extra.modules):
                importlib.import_module(
                    f"src.xstate_statemachine.contrib.{extra.subpackage}"
                )
                seen += 1
        if seen == 0:
            self.skipTest("no installed extras to import")


if __name__ == "__main__":
    unittest.main()
