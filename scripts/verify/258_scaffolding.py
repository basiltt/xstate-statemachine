"""Verification for #258 (A1 scaffolding). Runs on any OS: `python scripts/verify/258_scaffolding.py`.

Checks the acceptance criteria end to end against the *installed* package
(not `src.` imports), so it also proves the editable install is wired.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tomllib  # noqa: F401  -- 3.11+; falls back below
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    step("1. `import xstate_statemachine` touches no third-party module")
    code = (
        "import sys, xstate_statemachine as x\n"
        "third = sorted(m for m in sys.modules if m.split('.')[0] in "
        "{'pydantic','fastapi','django','sqlalchemy','celery','redis','flask','starlette'})\n"
        "contrib = [m for m in sys.modules if m.startswith('xstate_statemachine.contrib')]\n"
        "print(json.dumps({'third': third, 'contrib': contrib, 'v': x.__version__}))"
    )
    out = subprocess.run(
        [sys.executable, "-I", "-c", "import json\n" + code],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    rep = json.loads(out.strip().splitlines()[-1])
    assert rep["third"] == [] and rep["contrib"] == [], rep
    print("   OK", rep["v"])

    step("2. MissingExtraError names the pip command and is an ImportError")
    from xstate_statemachine import MissingExtraError
    from xstate_statemachine.contrib._compat import require_extra

    try:
        require_extra("fastapi", "definitely_not_installed_module_xyz")
    except ImportError as e:
        assert isinstance(e, MissingExtraError)
        assert 'pip install "xstate-statemachine[fastapi]"' in str(e), str(e)
        print("   OK:", e)
    else:
        raise SystemExit("expected MissingExtraError")

    step("3. persistence is a package with the old names re-exported")
    p = importlib.import_module("xstate_statemachine.persistence")
    for n in ("SNAPSHOT_VERSION", "structure_hash", "check_version", "upcast"):
        assert hasattr(p, n), n
    print("   OK  SNAPSHOT_VERSION =", p.SNAPSHOT_VERSION)

    step("4. every registry extra is declared in pyproject (and vice versa)")
    from xstate_statemachine.contrib._registry import EXTRAS

    try:
        import tomllib as toml
    except ImportError:  # pragma: no cover -- 3.9/3.10
        import tomli as toml  # type: ignore[no-redef]
    declared = set(
        toml.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]["optional-dependencies"]
    )
    assert set(EXTRAS) <= declared, sorted(set(EXTRAS) - declared)
    assert declared - set(EXTRAS) <= {"format"}, sorted(declared - set(EXTRAS))
    print(f"   OK  {len(EXTRAS)} extras")

    step("5. the guard tests pass")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_zero_dependency.py",
            "tests/contrib",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        check=True,
    )

    step("6. lint + types")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "black",
            "--check",
            "src",
            "tests",
            "--line-length=79",
            "-q",
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run([sys.executable, "-m", "mypy"], cwd=ROOT, check=True)

    step("7. battle tests (post-RC programme) + mojibake scan")
    # 🛡️ The battle file runs its environment-sensitive checks in a bare
    #    child interpreter (`.venvmin` or XSM_BARE_PYTHON) when available,
    #    and skips network checks under --disable-socket.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_battle_258_scaffolding.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:asyncio",
        ],
        cwd=ROOT,
        check=True,
    )
    # 📝 Agents work in worktrees whose scan only sees THEIR tracked files;
    #    a cherry-pick can carry mojibake across. Scan at integration.
    subprocess.run(
        [sys.executable, "scripts/verify/_mojibake_scan.py"],
        cwd=ROOT,
        check=True,
    )
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
