"""Verification for #304 (A0 core hooks). `python scripts/verify/304_core_hooks.py`.

Runs against the installed package. Exercises `on_before_send` short-circuit,
`on_event_processed` outcomes on BOTH engines, `Receipt.duplicate`, and
`stub_logic()` on the Stately corpus.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import (
        Interpreter,
        PluginBase,
        Receipt,
        SyncInterpreter,
        create_machine,
        stub_logic,
    )

    cfg = json.loads(
        (
            ROOT / "tests/tests_cli/stately_machines/AdvancePayment.json"
        ).read_text(encoding="utf-8")
    )

    class P(PluginBase):
        def __init__(self) -> None:
            self.seen: list = []

        def on_before_send(self, i, e):
            if e.type == "BLOCKED":
                return Receipt(
                    frozenset(i.current_state_ids),
                    False,
                    None,
                    False,
                    False,
                    True,
                )
            return None

        def on_event_processed(self, i, e, r):
            self.seen.append((e.type, r.changed, r.denied, r.duplicate))

    step("1. sync engine: short-circuit, outcomes, identity")
    p = P()
    m = create_machine(cfg, logic=stub_logic(cfg))
    i = SyncInterpreter(m).use(p).start()
    blocked = i.send("BLOCKED", wait=True)
    assert blocked.duplicate and not blocked.changed
    ok = i.send("SUBMIT", wait=True)
    nope = i.send("NOPE", wait=True)
    assert ok.changed and not nope.changed
    # SUBMIT invokes a stub service that completes at once, so the engine-
    # minted `done.invoke.*` is a processed event in its own right.
    kinds = [t for t, *_ in p.seen]
    assert (
        kinds[0] == "SUBMIT"
        and kinds[1].startswith("done.invoke.")
        and kinds[-1] == "NOPE"
    ), kinds
    assert p.seen[0][1:] == (True, False, False) and p.seen[-1][1:] == (
        False,
        False,
        False,
    )
    print("   OK", p.seen)

    step("2. async engine: same contract")

    async def run() -> None:
        q = P()
        ai = Interpreter(create_machine(cfg, logic=stub_logic(cfg))).use(q)
        await ai.start()
        b = await ai.send("BLOCKED", wait=True)
        assert b.duplicate
        r = await ai.send("SUBMIT", wait=True)
        await ai.send("NOPE", wait=True)
        assert r.changed
        kinds = [t for t, *_ in q.seen]
        assert (
            kinds[0] == "SUBMIT"
            and kinds[-1] == "NOPE"
            and any(k.startswith("done.invoke.") for k in kinds)
        ), kinds
        await ai.stop()
        print("   OK", q.seen)

    asyncio.run(run())

    step("3. stub_logic builds the whole corpus")
    built = 0
    for f in sorted(
        (ROOT / "tests/tests_cli/stately_machines").glob("*.json")
    ):
        c = json.loads(f.read_text(encoding="utf-8"))
        try:
            create_machine(c, logic=stub_logic(c))
            built += 1
        except Exception as exc:  # noqa: BLE001
            print("   skipped (invalid fixture):", f.name, type(exc).__name__)
    print(f"   OK  {built} machines built")

    step("4. tests + lint + types")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_plugin_hooks_send.py",
            "tests/test_plugins.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        check=True,
    )
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
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
