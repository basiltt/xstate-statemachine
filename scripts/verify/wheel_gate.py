# scripts/verify/wheel_gate.py
"""RC gate: run every ``scripts/verify`` script against the BUILT WHEEL
installed with ``[all]`` in a fresh virtualenv -- the exact artefact a
user would install, not this checkout's editable source.

Usage: ``python scripts/verify/wheel_gate.py [--venv PATH] [--only NAME ...]``

Prints one line per script (OK / FAIL / SKIP with the reason) and a final
``ALL OK`` or the list of failures; exit status 1 on any failure.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[2]
VERIFY = ROOT / "scripts" / "verify"
# Test-only requirements the verify scripts need beyond the extras.
TEST_REQUIREMENTS = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-socket>=0.7",
    "pytest-django",
    "hypothesis>=6",
    "fakeredis[lua]>=2.20",
    "moto[sqs]>=5",
    "httpx>=0.24",
    "openapi-spec-validator>=0.7",
    "aiosqlite>=0.19",
    "alembic>=1.12",
    "quart>=0.19",
    "flask-wtf>=1.2",
    "jsonschema>=4",
    "django-fsm-2",
    "drf-spectacular",
    "daphne",
    "build",
    # 258_scaffolding / 304_core_hooks run the lint + type gate inside the
    # venv; the pins mirror ci.yml's lint job.
    "black==26.1.0",
    "flake8==7.3.0",
    "flake8-isort==7.0.0",
    "mypy>=1.14",
    "trove-classifiers",
]
SKIP = {"wheel_gate.py", "all_smoke.py", "django_fsm_migration.py"}


def sh(*cmd: str, **kw: object) -> subprocess.CompletedProcess:
    # 📝 Child output is UTF-8 (emoji in the scripts); never let the
    #    console code page (cp1252 on Windows) turn a passing script into
    #    a UnicodeDecodeError in the gate.
    return subprocess.run(  # type: ignore[call-overload]
        list(cmd), text=True, encoding="utf-8", errors="replace", **kw
    )


def build_wheel() -> pathlib.Path:
    dist = ROOT / "dist"
    for old in dist.glob("*.whl"):
        old.unlink()
    sh(
        sys.executable,
        "-m",
        "build",
        "--wheel",
        "-q",
        cwd=str(ROOT),
        check=True,
    )
    return next(dist.glob("*.whl"))


def make_venv(path: pathlib.Path, wheel: pathlib.Path) -> pathlib.Path:
    sh(sys.executable, "-m", "venv", str(path), check=True)
    py = path / ("Scripts" if os.name == "nt" else "bin") / "python"
    sh(str(py), "-m", "pip", "install", "-q", "--upgrade", "pip", check=True)
    sh(
        str(py),
        "-m",
        "pip",
        "install",
        "-q",
        f"{wheel}[all]",
        *TEST_REQUIREMENTS,
        check=True,
    )
    return py


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--venv")
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()
    wheel = build_wheel()
    print(f"wheel: {wheel.name}")
    venv = pathlib.Path(args.venv or tempfile.mkdtemp(prefix="xsm-gate-"))
    py = make_venv(venv, wheel)
    print(f"venv:  {venv}")
    # 📝 Run from OUTSIDE the checkout so `import xstate_statemachine`
    #    resolves to the installed wheel; scripts locate the repo via
    #    __file__ and prepend src/ themselves only where they need tests.
    env = dict(
        os.environ,
        XSM_WHEEL_GATE="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
    )
    env.pop("PYTHONPATH", None)
    results: List[Tuple[str, str, float]] = []
    scripts = sorted(p for p in VERIFY.glob("*.py") if p.name not in SKIP)
    if args.only:
        scripts = [p for p in scripts if p.stem in set(args.only)]
    for script in scripts:
        t0 = time.perf_counter()
        proc = sh(
            str(py),
            str(script),
            cwd=str(venv),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        dt = time.perf_counter() - t0
        out = proc.stdout or ""
        ok = proc.returncode == 0 and "ALL OK" in out
        status = "OK" if ok else "FAIL"
        results.append((script.name, status, dt))
        print(f"{status:4} {script.name:32} {dt:6.1f}s", flush=True)
        if not ok:
            tail = "\n".join(out.strip().splitlines()[-25:])
            print("     " + tail.replace("\n", "\n     "))
    failed = [n for n, s, _ in results if s != "OK"]
    print()
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    print(f"ALL OK ({len(results)} verify scripts against {wheel.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
