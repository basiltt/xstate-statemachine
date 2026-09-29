"""Verification for #308 (B9 recipes pack).

`python scripts/verify/308_recipes.py`

Windows-safe (no heredocs, no /tmp; scratch space via `tempfile.mkdtemp`).
Runs the recipe tests and the docs/comparison/site tests, replays every
recipe page's `xsm simulate` line, validates every chart, and drives the
Stripe recipe end to end: forged and stale signatures rejected, replay
applied once. Recipes whose soft dependency is missing print SKIP and do
not fail. Prints ``ALL OK``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 💡 Verify THIS checkout even when an editable install points elsewhere.
sys.path.insert(0, str(ROOT / "src"))
ENV = {
    **os.environ,
    "PYTHONPATH": str(ROOT / "src"),
    "PYTHONIOENCODING": "utf-8",
}
PAGES = ROOT / "docs" / "_guide" / "recipes"
SIMULATE = re.compile(r"^xsm simulate (\S+)((?: [^\n#]+?)?)\n# -> (\S+)", re.M)


def step(name: str) -> None:
    print(f"\n== {name}")


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")
    print(f"   ok  {msg}")


def run_tests() -> None:
    step("pytest: recipes, comparisons, docs site, readme, examples")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/recipes",
            "tests/test_comparisons.py",
            "tests/test_docs_site.py",
            "tests/test_readme.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "-rs",
        ],
        cwd=str(ROOT),
        env=ENV,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = proc.stdout.strip().splitlines()
    for line in tail:
        if line.startswith("SKIPPED"):
            print(f"   SKIP {line[8:120]}")
    print("   " + (tail[-1] if tail else "?"))
    check(proc.returncode == 0, "recipe + docs tests pass")


def simulate_lines() -> None:
    step("every recipe page's `xsm simulate` line reproduces its flow")
    n = 0
    for page in sorted(PAGES.glob("*.md")):
        for path, args, expected in SIMULATE.findall(page.read_text("utf-8")):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "xstate_statemachine",
                    "simulate",
                    str(ROOT / path),
                    *shlex.split(args),
                    "--json",
                ],
                cwd=str(ROOT),
                env=ENV,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            active = json.loads(proc.stdout)["active"] if proc.stdout else []
            check(
                expected in active,
                f"{page.stem}: {args.strip()} -> {expected}",
            )
            n += 1
    check(n >= 8, f"{n} simulate lines replayed")


def validate_charts() -> None:
    step("every recipe chart passes `xsm validate --plain`")
    charts = sorted((ROOT / "examples" / "recipes").glob("*/machine.json"))
    check(len(charts) == 8, "eight recipe charts")
    for chart in charts:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "xstate_statemachine",
                "validate",
                str(chart),
                "--plain",
            ],
            env=ENV,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        check(proc.returncode == 0, f"validate {chart.parent.name}")


def stripe_end_to_end() -> None:
    step("Stripe: forged / stale rejected, replay applied once (SQLite)")
    sys.path.insert(0, str(ROOT / "examples" / "recipes" / "stripe_webhooks"))
    import stripe_webhooks as sw  # noqa: E402

    from xstate_statemachine.persistence import SQLiteInbox, SQLiteStore

    tmp = tempfile.mkdtemp(prefix="xsm308-")
    store = SQLiteStore(os.path.join(tmp, "stripe.db"))
    try:
        env = {
            "secret": "whsec_verify",
            "store": store,
            "inbox": SQLiteInbox(store),
            "machine": sw.build_machine(),
            "now": 1_735_700_000.0,
        }
        fx = ROOT / "examples" / "recipes" / "stripe_webhooks" / "fixtures"
        paid = (fx / "invoice_paid.json").read_bytes().strip()
        failed = (fx / "invoice_payment_failed.json").read_bytes().strip()

        def deliver(body: bytes, ts: float, secret: str = "whsec_verify"):
            return sw.handle_webhook(
                body, sw.sign(body, secret, int(ts)), **env
            )

        check(
            deliver(paid, env["now"], "whsec_evil")[0] == 400, "forged -> 400"
        )
        check(deliver(paid, env["now"] - 301)[0] == 400, "stale -> 400")
        check(
            deliver(paid, env["now"])[1]["state"] == "active", "paid -> active"
        )
        s1, b1 = deliver(failed, env["now"])
        s2, b2 = deliver(failed, env["now"] + 3)
        check(
            (s1, b1["state"]) == (200, "past_due") and b2["duplicate"],
            "replayed event.id answered from the inbox",
        )
        ctx = json.loads(store.load("subscription.sub_123").snapshot)[
            "context"
        ]
        check(ctx["failures"] == 1, "the replay was applied exactly once")
    finally:
        store.close()
        shutil.rmtree(tmp, ignore_errors=True)


def soft_deps() -> None:
    step("soft dependencies (informational)")
    for mod in (
        "fastapi",
        "flask",
        "apscheduler",
        "streamlit",
        "gradio",
        "rq",
        "arq",
        "dramatiq",
        "stripe",
    ):
        found = importlib.util.find_spec(mod) is not None
        print(f"   {'present' if found else 'SKIP   '} {mod}")


def main() -> None:
    run_tests()
    simulate_lines()
    validate_charts()
    stripe_end_to_end()
    soft_deps()
    print("\nALL OK")


if __name__ == "__main__":
    main()
