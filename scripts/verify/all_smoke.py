#!/usr/bin/env python
# scripts/verify/all_smoke.py
# -----------------------------------------------------------------------------
# 🚬 `[all]` smoke (#296)
# -----------------------------------------------------------------------------
# Run against an environment that installed the WHEEL with `[all]` (the CI
# `all-smoke` job, on Linux / macOS / Windows):
#
#   1. `import xstate_statemachine` alone loads no third-party module
#      (checked in a fresh interpreter, before anything else is imported);
#   2. every `xstate_statemachine.contrib.*` subpackage on disk imports
#      (found with pkgutil, so a new extra is covered without editing this);
#   3. each shipped extra's docs **Quick start** snippet -- the first
#      ```python block under `## Quick start` of its guide page -- runs in
#      its own subprocess and exits 0.
#
# 🪟 Windows-safe: no shell, no heredocs, temp files written with "\n" and
#    UTF-8, `sys.executable` for every child.
# -----------------------------------------------------------------------------
"""Smoke-test an `[all]` install: core stays clean, contrib imports, docs run."""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs" / "_guide"
TIMEOUT_S = 120

#: Shipped extra -> guide page whose Quick start is the verification
#: snippet. `quart` rides on the [flask] page and has no Quick start.
QUICKSTARTS: Dict[str, str] = {
    "pydantic": "integration-pydantic.md",
    "redis": "integration-redis.md",
    "sqlalchemy": "integration-sqlalchemy.md",
    "flask": "integration-flask.md",
    "starlette": "integration-starlette.md",
    "fastapi": "integration-fastapi.md",
    "litestar": "integration-litestar.md",
    "agents": "integration-agents.md",
}

#: Top-level modules that are NOT stdlib but must never be pulled in by a
#: bare `import xstate_statemachine` (every shipped extra's dependency).
THIRD_PARTY = (
    "pydantic fastapi starlette litestar sqlalchemy redis flask quart "
    "django celery werkzeug httpx anyio greenlet"
).split()

CORE_CHECK = (
    "import sys\n"
    "import xstate_statemachine\n"
    "bad = sorted({m.split('.')[0] for m in sys.modules} & set(%r))\n"
    "assert not bad, 'core import pulled third-party modules: %%s' %% bad\n"
    "print('core import clean')\n"
)

CONTRIB_CHECK = (
    "import importlib, pkgutil\n"
    "import xstate_statemachine.contrib as c\n"
    "from xstate_statemachine.contrib._registry import EXTRAS\n"
    "from xstate_statemachine.exceptions import MissingExtraError\n"
    "shipped = {e.subpackage.split('.')[0] for e in EXTRAS.values()}\n"
    "names = [m.name for m in pkgutil.iter_modules(c.__path__)\n"
    "         if not m.name.startswith('_')]\n"
    "assert names, 'no contrib subpackages found'\n"
    "for n in names:\n"
    "    try:\n"
    "        importlib.import_module('xstate_statemachine.contrib.' + n)\n"
    "    except MissingExtraError as exc:\n"
    "        # A shim that is not an extra of its own (contrib.quart rides\n"
    "        # on [flask] + a soft `pip install quart`) may name its missing\n"
    "        # dependency. Anything backed by an extra must import cleanly.\n"
    "        if n in shipped:\n"
    "            raise\n"
    "        print('soft-dep skip', n, '-', exc.module)\n"
    "        continue\n"
    "    print('import ok', n)\n"
)


def quickstart(page: str) -> str:
    """The first python fence under `## Quick start` of *page*."""
    text = (GUIDE / page).read_text(encoding="utf-8").replace("\r\n", "\n")
    section = text.split("\n## Quick start", 1)[1].split("\n## ", 1)[0]
    m = re.search(r"```python\n(.*?)```", section, re.S)
    if not m:
        raise SystemExit(f"{page}: no python block under '## Quick start'")
    return m.group(1)


def run_code(label: str, code: str, cwd: str) -> bool:
    fd, path = tempfile.mkstemp(suffix=".py", dir=cwd)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(code)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    # 🧹 Never let the checkout's `src/` shadow the installed wheel.
    env.pop("PYTHONPATH", None)
    try:
        r = subprocess.run(
            [sys.executable, path],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        print(f"FAIL {label}: timed out after {TIMEOUT_S}s")
        return False
    if r.returncode != 0:
        print(f"FAIL {label} (exit {r.returncode})")
        print(r.stdout[-2000:])
        print(r.stderr[-4000:])
        return False
    print(f"ok   {label}")
    return True


def main(argv: List[str]) -> int:
    only = set(argv)
    failures: List[str] = []
    # 📂 Run from an empty directory so `import xstate_statemachine`
    #    resolves to the INSTALLED package, never ./src.
    with tempfile.TemporaryDirectory() as cwd:
        checks = [
            ("core import is third-party-free", CORE_CHECK % (THIRD_PARTY,)),
            ("every contrib subpackage imports", CONTRIB_CHECK),
        ]
        for extra, page in QUICKSTARTS.items():
            if only and extra not in only:
                continue
            checks.append((f"[{extra}] quick start", quickstart(page)))
        for label, code in checks:
            if not run_code(label, code, cwd):
                failures.append(label)
    if failures:
        print(f"{len(failures)} check(s) failed: {failures}")
        return 1
    print("ALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
