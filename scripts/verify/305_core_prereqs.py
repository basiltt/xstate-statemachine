"""Verification for #305 part 1 (A0b core prerequisites).
`python scripts/verify/305_core_prereqs.py`.

Runs against the installed package. Exercises snapshot layout v4 on BOTH
engines, v3 -> v4 upcast and restore, `check_version` refusing v5,
`MachineNode.version`, `wall_now()` with `SimulatedClock(wall_start=)`,
`Deadline` round-trip, the receipt codec and `xsm inspect` showing the
version.
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
        SimulatedClock,
        SyncInterpreter,
        create_machine,
        receipt_from_json,
        receipt_to_json,
        receipt_to_status,
        stub_logic,
    )
    from xstate_statemachine.exceptions import SnapshotVersionError
    from xstate_statemachine.persistence import (
        SNAPSHOT_VERSION,
        Deadline,
        check_version,
        upcast,
    )

    cfg = json.loads(
        (
            ROOT / "tests/tests_cli/stately_machines/AdvancePayment.json"
        ).read_text(encoding="utf-8")
    )
    cfg["version"] = "7"
    m = create_machine(cfg, logic=stub_logic(cfg))

    step("MachineNode.version")
    print("machine.version:", m.version)
    assert m.version == "7"

    step("sync engine writes layout v4")
    i = SyncInterpreter(m).start()
    blob = json.loads(i.get_snapshot())
    print(
        "snapshot v",
        blob["version"],
        blob["machine_version"],
        blob["deadlines"],
    )
    assert SNAPSHOT_VERSION == 4
    assert blob["version"] == 4 and blob["machine_version"] == "7"
    assert blob["deadlines"] == []
    i.stop()

    step("async engine writes layout v4")

    async def go() -> dict:
        ai = await Interpreter(m).start()
        try:
            return json.loads(ai.get_snapshot())
        finally:
            await ai.stop()

    ablob = asyncio.run(go())
    assert ablob["version"] == 4 and ablob["machine_version"] == "7"
    print("async ok")

    step("v3 blob upcasts and restores")
    v3 = dict(blob, version=3)
    v3.pop("machine_version")
    v3.pop("deadlines")
    up = upcast(dict(v3), 3)
    assert up["machine_version"] is None and up["deadlines"] == []
    r = SyncInterpreter.from_snapshot(json.dumps(v3), m).start()
    re_blob = json.loads(r.get_snapshot())
    r.stop()
    print("re-persisted as v", re_blob["version"], re_blob["machine_version"])
    assert re_blob["version"] == 4 and re_blob["machine_version"] == "7"

    step("check_version refuses v5")
    try:
        check_version(dict(blob, version=5))
    except SnapshotVersionError as exc:
        print("refused:", exc)
    else:
        raise AssertionError("v5 accepted")

    step("wall_now() with SimulatedClock(wall_start=)")
    clk = SimulatedClock(wall_start=1_000_000.0)
    si = SyncInterpreter(m, clock=clk).start()
    assert si.wall_now() == 1_000_000.0
    clk.increment(3_600_000)
    print("an hour later:", si.wall_now(), "monotonic:", clk.now())
    assert si.wall_now() == 1_003_600.0 and clk.now() == 3600.0
    si.stop()

    step("Deadline round-trip")
    d = Deadline("m.a", 2, 1_003_600.0 + 30, 30_000, "after.30000.m.a")
    d2 = Deadline.from_dict(json.loads(json.dumps(d.to_dict())))
    assert d2 == d and d.remaining_ms(1_003_600.0) == 30_000
    print("deadline:", d2)

    step("receipt codec")
    si = SyncInterpreter(m).start()
    rc = si.send("SUBMIT", wait=True)
    si.stop()
    wire = receipt_to_json(rc)
    print("status:", receipt_to_status(rc), "json:", json.dumps(wire))
    assert receipt_from_json(json.loads(json.dumps(wire))) == rc

    step("xsm inspect shows the version")
    tmp = ROOT / "scripts" / "verify" / "_305_tmp.json"
    tmp.write_text(json.dumps(cfg), encoding="utf-8")
    try:
        out = subprocess.run(
            [
                sys.executable,
                "-m",
                "xstate_statemachine",
                "inspect",
                str(tmp),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        data = json.loads(out.stdout)
        print("inspect --json version:", data.get("version"))
        assert data.get("version") == "7"
    finally:
        tmp.unlink(missing_ok=True)

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
