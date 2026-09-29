"""Verification for #296 (G1 -- 1.0 hardening).

`python scripts/verify/296_hardening.py`

Windows-safe (no heredocs, no /tmp; scratch space via `tempfile`). Checks:

1. discovery: the fixture third-party package, laid out as an installed
   distribution, is found by `discover()`, listed by `xsm plugins --json`,
   attached by `attach_discovered()`; the broken loader is skipped, and
   `strict=True` raises; XSM_DISABLE_PLUGIN_DISCOVERY=1 returns [];
   importing the library calls no entry-point API;
2. compatibility: docs/_guide/compatibility.md regenerates byte-identical;
3. deprecations: once per call site; the policy page lists the registry;
4. `[all]` smoke script runs against this environment;
5. the 1.0 checklist tests and the related suites pass.

Prints ``ALL OK``.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import warnings

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 💡 Verify THIS checkout even when an editable install points elsewhere.
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
ENV = {
    **os.environ,
    "PYTHONPATH": str(ROOT / "src"),
    "PYTHONIOENCODING": "utf-8",
}
ENV.pop("XSM_DISABLE_PLUGIN_DISCOVERY", None)


def step(name: str) -> None:
    print(f"\n== {name}")


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
    print(f"   ok  {msg}")


def run(*args: str, env: dict = ENV) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def discovery() -> None:
    step("1. entry-point discovery (fixture third-party package)")
    from tests.test_plugin_discovery import install_fixture
    from xstate_statemachine import SyncInterpreter, create_machine
    from xstate_statemachine.plugins import (
        STORES_GROUP,
        attach_discovered,
        discover,
    )

    os.environ.pop("XSM_DISABLE_PLUGIN_DISCOVERY", None)
    with tempfile.TemporaryDirectory() as tmp:
        install_fixture(pathlib.Path(tmp))
        sys.path.insert(0, tmp)
        try:
            found = {p.name: p for p in discover()}
            check("thirdparty_audit" in found, "discover() finds the fixture")
            p = found["thirdparty_audit"]
            check(
                (p.distribution, p.version)
                == ("xsm-thirdparty-plugin", "1.2.3"),
                "distribution + version reported",
            )
            check(
                p.hooks == ("on_interpreter_start", "on_transition"),
                "hooks implemented reported",
            )
            check("thirdparty_broken" not in found, "broken loader skipped")
            try:
                discover(strict=True)
                check(False, "strict=True re-raises")
            except RuntimeError:
                check(True, "strict=True re-raises")
            stores = [x.name for x in discover(group=STORES_GROUP)]
            check(stores == ["thirdparty_memory"], "stores group discovered")
            m = create_machine(
                {"id": "v", "initial": "a", "states": {"a": {}}}
            )
            it = SyncInterpreter(m)
            got = attach_discovered(it, allow=["xsm-thirdparty-plugin"])
            it.start().stop()
            check(
                len(got) == 1 and got[0].started == ["v"],
                "attach_discovered() attaches and the plugin fires",
            )
            os.environ["XSM_DISABLE_PLUGIN_DISCOVERY"] = "1"
            check(discover() == [], "XSM_DISABLE_PLUGIN_DISCOVERY=1 -> []")
            os.environ.pop("XSM_DISABLE_PLUGIN_DISCOVERY")

            env = dict(ENV)
            env["PYTHONPATH"] = os.pathsep.join([tmp, str(ROOT / "src")])
            cli = run(
                "-m", "xstate_statemachine", "plugins", "--json", env=env
            )
            check(cli.returncode == 0, "xsm plugins --json exits 0")
            rows = json.loads(cli.stdout)["plugins"]
            check(
                any(r["name"] == "thirdparty_audit" for r in rows),
                "xsm plugins lists the fixture",
            )
        finally:
            sys.path.remove(tmp)
            for mod in [m for m in sys.modules if "xsm_thirdparty" in m]:
                del sys.modules[mod]

    probe = (
        "import importlib.metadata as md\n"
        "calls = []\n"
        "orig = md.entry_points\n"
        "md.entry_points = lambda *a, **k: calls.append(1) or orig(*a, **k)\n"
        "import xstate_statemachine, xstate_statemachine.plugins\n"
        "print(len(calls))\n"
    )
    out = run("-c", probe)
    check(out.stdout.strip() == "0", "importing the library discovers nothing")


def compatibility() -> None:
    step("2. compatibility table is generated from the matrix")
    out = run("scripts/gen_compatibility.py", "--check")
    check(out.returncode == 0, out.stdout.strip() or out.stderr.strip())


def deprecations() -> None:
    step("3. deprecation helper")
    from xstate_statemachine import deprecations as dep

    dep.reset_deprecation_warnings()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(3):
            dep.deprecated("v", since="0", removal="1", alternative="w")
    check(len(caught) == 1, "one warning per call site")
    page = (ROOT / "docs" / "_guide" / "deprecation-policy.md").read_text(
        encoding="utf-8"
    )
    real = [d for d in dep.deprecations() if d.what != "v"]
    check(all(d.what in page for d in real), "policy page lists the registry")


def all_smoke() -> None:
    step("4. [all] smoke (this environment)")
    out = run("scripts/verify/all_smoke.py")
    print(out.stdout.rstrip())
    check(out.returncode == 0, "all_smoke.py -> ALL OK")


def tests() -> None:
    step("5. suites")
    out = run(
        "-m",
        "pytest",
        "tests/test_plugin_discovery.py",
        "tests/test_deprecations.py",
        "tests/test_compat_matrix.py",
        "tests/test_public_api_surface.py",
        "tests/test_one_point_oh.py",
        "tests/test_docs_executable.py",
        "tests/test_readme.py",
        "tests/test_docs_site.py",
        "tests/test_zero_dependency.py",
        "tests/test_import_surface.py",
        "tests/test_security_baseline.py",
        "-q",
        "-p",
        "no:cacheprovider",
    )
    tail = (out.stdout.strip().splitlines() or ["?"])[-1]
    print(f"   {tail}")
    check(out.returncode == 0, "pytest green")


def main() -> None:
    discovery()
    compatibility()
    deprecations()
    all_smoke()
    tests()
    print("\nALL OK")


if __name__ == "__main__":
    main()
