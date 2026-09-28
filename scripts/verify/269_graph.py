"""Verification for #269 (B2, graph core). Runs on any OS:
`python scripts/verify/269_graph.py`. Prints `ALL OK`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import (
        SimulatedClock,
        SyncInterpreter,
        create_machine,
        reachable_states,
        shortest_paths,
        simple_paths,
        stub_logic,
        transition_coverage_targets,
    )

    step("1. shortest_paths on AdvancePayment reaches every state")
    cfg = json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
    m = create_machine(cfg, logic=stub_logic(cfg))
    paths = shortest_paths(m, guards="both")
    finals = {s for p in paths.values() for s in p.final_states}
    for st in ("editing", "challenge", "failure", "success"):
        assert f"Advance payment flow.{st}" in finals, (st, finals)
    print(f"   OK ({len(paths)} configurations)")

    step("2. every path replays to exactly its final_states")
    for cfg_key, p in paths.items():
        clock = SimulatedClock()
        i = SyncInterpreter(m, clock=clock)
        p.replay(i, clock)
        assert i.current_state_ids == set(p.final_states), (
            p.event_string(),
            i.current_state_ids,
        )
    print("   OK")

    step("3. simple_paths terminates and honours caps")
    sp = simple_paths(m, guards="both", max_paths=3, max_depth=4)
    assert 1 <= len(sp) <= 3, len(sp)
    print(f"   OK ({len(sp)} paths)")

    step("4. reachable_states / transition_coverage_targets")
    reach = reachable_states(m, guards="both")
    assert "Advance payment flow.challenge" in reach
    targets = transition_coverage_targets(m)
    assert any(t[0].endswith("editing") for t in targets), targets
    print(f"   OK ({len(reach)} reachable, {len(targets)} transitions)")

    step("5. xsm paths --json and --plain; xsm inspect still works")
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "paths",
            str(CORPUS / "AdvancePayment.json"),
            "--json",
            "--guards",
            "both",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    data = json.loads(out.lstrip("﻿"))
    assert data["mode"] == "shortest" and len(data["paths"]) == 4, data
    plain = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "xstate_statemachine",
            "paths",
            str(CORPUS / "AdvancePayment.json"),
            "--plain",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    assert "Configuration" in plain and "(initial)" in plain, plain
    ins = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            "-m",
            "xstate_statemachine",
            "inspect",
            str(CORPUS / "userModeration.json"),
            "--plain",
            "--no-events",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert ins.returncode == 0, ins.stdout + ins.stderr
    print("   OK")

    step("6. tests")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_graph.py",
            "tests/tests_cli/test_paths_command.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "--no-header",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(proc.stdout.strip().splitlines()[-1])
    assert proc.returncode == 0, proc.stdout + proc.stderr

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
