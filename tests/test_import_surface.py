"""Import-time guard: core must not eagerly load contrib or third parties."""

from __future__ import annotations

import importlib.machinery
import os
import pathlib
import subprocess
import sys
import unittest
from typing import Set

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MARKER = "XSM_IMPORT_START"
PLATFORM_STDLIB = {
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
    "_posixsubprocess",
    "nt",
    "posix",
}


def _is_stdlib(root: str) -> bool:
    """Match the 3.9-compatible origin check in test_zero_dependency.py."""
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return root in names
    if root in sys.builtin_module_names or root in PLATFORM_STDLIB:
        return True
    spec = importlib.machinery.PathFinder.find_spec(root, None)
    if spec is None:
        return False
    if spec.origin in ("built-in", "frozen"):
        return True
    locations = (
        [spec.origin]
        if spec.origin is not None
        else list(spec.submodule_search_locations or ())
    )
    base = os.path.realpath(sys.base_prefix)
    return bool(locations) and all(
        os.path.realpath(location).startswith(base)
        and not any(
            marker in os.path.realpath(location)
            for marker in (
                os.sep + "site-packages" + os.sep,
                os.sep + "dist-packages" + os.sep,
            )
        )
        for location in locations
    )


def _parse_importtime(stderr: str) -> Set[str]:
    if MARKER not in stderr:
        raise AssertionError("importtime subprocess did not print its marker")
    imported = set()
    for line in stderr.partition(MARKER)[2].splitlines():
        if line.startswith("import time:") and "|" in line:
            imported.add(line.rpartition("|")[2].strip())
    return imported


class TestImportSurface(unittest.TestCase):
    def test_importtime_parser_sees_nested_modules(self) -> None:
        imported = _parse_importtime(
            "import time: 1 | 1 | site\n"
            f"{MARKER}\n"
            "import time: 5 | 5 |   xstate_statemachine.events\n"
            "import time: 6 | 6 |     pydantic.core\n"
        )
        self.assertEqual(
            imported, {"xstate_statemachine.events", "pydantic.core"}
        )

    def test_importing_core_only_loads_stdlib(self) -> None:
        code = (
            "import sys\n"
            f"sys.path.insert(0, {str(SRC)!r})\n"
            f"sys.stderr.write({MARKER!r} + '\\n')\n"
            "import xstate_statemachine\n"
        )
        proc = subprocess.run(
            [sys.executable, "-I", "-X", "importtime", "-c", code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr[-4000:])
        imported = _parse_importtime(proc.stderr)
        self.assertIn("xstate_statemachine", imported)
        leaked = sorted(
            name
            for name in imported
            if name.startswith("xstate_statemachine.contrib")
        )
        third_party = sorted(
            name
            for name in imported
            if not name.startswith("xstate_statemachine")
            and not _is_stdlib(name.split(".", 1)[0])
        )
        self.assertEqual(leaked, [], f"contrib imported eagerly: {leaked}")
        self.assertEqual(
            third_party, [], f"third-party modules imported: {third_party}"
        )


if __name__ == "__main__":
    unittest.main()
