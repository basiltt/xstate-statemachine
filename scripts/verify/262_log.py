"""Verification for #262 (A5 transition log). `python scripts/verify/262_log.py`.

Runs against the installed package. AuditPlugin on the AdvancePayment
corpus machine (stub logic) records SUBMIT (actor/reason), the engine's
`done.invoke` completion and RESET; replay() reconstructs the state; a
tampered record raises ReplayDivergenceError; JSONLinesLog round-trips.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import SyncInterpreter, create_machine, stub_logic
    from xstate_statemachine.persistence import (
        AuditPlugin,
        JSONLinesLog,
        MemoryLog,
        ReplayDivergenceError,
        TransitionRecord,
        replay,
    )

    cfg = json.loads(
        (
            ROOT / "tests/tests_cli/stately_machines/AdvancePayment.json"
        ).read_text(encoding="utf-8")
    )
    # Review amendment: the corpus machine declares logic -> stub it.
    m = create_machine(cfg, logic=stub_logic(cfg))

    step("AuditPlugin records actor/reason and the engine completion")
    log = MemoryLog()
    i = SyncInterpreter(m).use(AuditPlugin(log)).start()
    i.send("SUBMIT", actor="basil", reason="customer confirmed")
    i.send(
        "RESET", actor="ops"
    )  # handled from `challenge`, reached via done.invoke
    recs = log.read(m.id)
    for r in recs:
        print(
            f"  {r.seq} {r.event_type:<35} {r.disposition:<11} actor={r.actor!s:<6} "
            f"reason={r.reason!s:<20} -> {r.to_states[-1].rsplit('.', 1)[-1]}"
        )
    assert [r.event_type for r in recs] == [
        "SUBMIT",
        "done.invoke.authenticate-payment",
        "RESET",
    ]
    assert recs[0].actor == "basil" and recs[2].actor == "ops"
    assert recs[1].engine and recs[1].event_payload["kind"] == "done"

    step("replay() reconstructs the live state")
    r = replay(m, recs)
    print(
        "  live:",
        sorted(i.current_state_ids),
        "replayed:",
        sorted(r.current_state_ids),
    )
    assert r.current_state_ids == i.current_state_ids
    r.stop()

    step("tampered record -> ReplayDivergenceError(seq)")
    bad = list(recs)
    bad[2] = TransitionRecord(
        **{**recs[2].to_dict(), "to_states": ["Advance payment flow.failure"]}
    )
    try:
        replay(m, bad)
        raise SystemExit("expected divergence")
    except ReplayDivergenceError as exc:
        print(f"  diverged at seq {exc.seq}: {exc}")
        assert exc.seq == 3

    step("JSONLinesLog round-trip")
    jl = JSONLinesLog(Path(tempfile.mkdtemp()) / "audit.jsonl")
    for rec in recs:
        jl.append(rec)
    back = jl.read(m.id)
    assert back == recs
    print("  ", len(back), "records identical after JSON round-trip")
    i.stop()

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
