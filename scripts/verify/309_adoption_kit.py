"""Verification for #309 (C7, adoption kit).

`python scripts/verify/309_adoption_kit.py`

Windows-safe (no heredocs, no /tmp; `tempfile.mkdtemp`). Checks:
the committed editor schema is current and accepts the corpus; the
pre-commit hook commands pass/fail on the example; `xsm gt --check`
detects drift; `xsm new` scaffolds a project whose tests pass; the
journey page's code blocks run; the PyPI classifiers are valid trove
classifiers. Prints ``ALL OK``.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "integrations" / "fastapi_orders"
ENV = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1"}


def step(name: str) -> None:
    print(f"\n== {name}", flush=True)


def run(args, cwd=None, expect=0) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    if proc.returncode != expect:
        print(proc.stdout[-3000:], proc.stderr[-3000:])
        raise SystemExit(
            f"FAILED: {args} exited {proc.returncode}, expected {expect}"
        )
    return proc


def xsm(*args, expect=0) -> subprocess.CompletedProcess:
    return run(
        ["-m", "xstate_statemachine.cli", "--plain", *args], expect=expect
    )


def main() -> int:
    step("schema is current")
    run([str(ROOT / "scripts" / "gen_machine_schema.py"), "--check"])

    step("schema accepts the corpus")
    try:
        import jsonschema
    except ImportError:
        print("   (jsonschema not installed -- skipped)")
    else:
        schema = json.loads(
            (ROOT / "schemas" / "xstate-machine.schema.json").read_text(
                "utf-8"
            )
        )
        v = jsonschema.Draft202012Validator(schema)
        files = sorted(
            (ROOT / "tests/tests_cli/stately_machines").rglob("*.json")
        )
        bad = [
            f.name
            for f in files
            if list(v.iter_errors(json.loads(f.read_text("utf-8"))))
        ]
        assert not bad, bad
        print(f"   {len(files)} machines valid")

    work = pathlib.Path(tempfile.mkdtemp(prefix="xsm309_"))

    step("pre-commit xsm-validate: example passes, broken file fails")
    xsm("validate", str(EXAMPLE / "machine.json"))
    bad = work / "bad.machine.json"
    bad.write_text(
        '{"id": "m", "initial": "nope", "states": {"a": {}}}', "utf-8"
    )
    xsm("validate", str(bad), expect=1)

    step("xsm gt --check detects drift")
    gen = [
        str(EXAMPLE / "machine.json"),
        "-o",
        str(work / "gen"),
        "-t",
        "pythonic-class",
    ]
    xsm("gt", *gen, "-f")
    xsm("gt", "--check", *gen)
    victim = sorted((work / "gen").glob("*.py"))[0]
    victim.write_text(victim.read_text("utf-8") + "# drift\n", "utf-8")
    xsm("gt", "--check", *gen, expect=1)

    step("xsm new --template fastapi; scaffolded tests pass")
    xsm("new", "--list")
    target = work / "svc"
    xsm("new", str(target), "--name", "shop_orders")
    xsm("new", str(target), expect=2)  # non-empty without --force
    xsm("new", str(work / "dj"), "-t", "django", expect=2)
    try:
        import fastapi  # noqa: F401
        import httpx  # noqa: F401
    except ImportError:
        print("   (fastapi/httpx not installed -- scaffold tests skipped)")
    else:
        out = run(
            [
                "-m",
                "pytest",
                "tests",
                "-q",
                "-p",
                "no:cacheprovider",
                "-o",
                "addopts=",
            ],
            cwd=target,
        )
        print("   " + out.stdout.strip().splitlines()[-1])

    step("journey + stately page code blocks run")
    for page in ("integrations.md", "stately-export.md"):
        md = (ROOT / "docs" / "_guide" / page).read_text("utf-8")
        n = 0
        for m in re.finditer(r"```python\n(.*?)```", md, re.S):
            if md[: m.start()].rstrip().endswith("<!-- doc-fragment -->"):
                continue
            f = work / f"block_{page}_{n}.py"
            f.write_text(m.group(1), "utf-8")
            run([str(f)], cwd=work)
            n += 1
        print(f"   {page}: {n} blocks ran")

    step("PyPI classifiers are valid")
    text = (ROOT / "pyproject.toml").read_text("utf-8")
    ours = re.findall(r'"((?:Framework|Topic|Typing) :: [^"]+)"', text)
    try:
        from trove_classifiers import classifiers
    except ImportError:
        print("   (trove-classifiers not installed -- skipped)")
    else:
        unknown = [c for c in ours if c not in classifiers]
        assert not unknown, unknown
    for c in (
        "Framework :: FastAPI",
        "Framework :: AsyncIO",
        "Framework :: Pytest",
    ):
        assert c in ours, c
    assert (
        "Framework :: Django" not in text and "Framework :: Flask" not in text
    )

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
