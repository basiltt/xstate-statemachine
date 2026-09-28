"""Verification for #264 (A7 durable timers). `python scripts/verify/264_timers.py`.

Runs against the installed package. The issue's end-to-end scenario on
SQLiteStore AND FileStore: a persisted() block arms a 1 h `after`; a new
store handle ("another process") runs the scanner: not early, fires once
due, idempotent; the machine is in `reminded`. Plus the resume timing
check (5000 ms, snapshot at 2000, +2999 no, +1 yes) on both engines.
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import (
        Interpreter,
        SimulatedClock,
        SyncInterpreter,
        create_machine,
    )
    from xstate_statemachine.persistence import (
        DueTimerScanner,
        FileStore,
        SQLiteStore,
        persisted,
    )

    cfg = {
        "id": "r",
        "initial": "waiting",
        "states": {
            "waiting": {"after": {"3600000": "reminded"}},
            "reminded": {"type": "final"},
        },
    }
    m = create_machine(cfg)
    tmp = Path(tempfile.mkdtemp())

    for name, make in (
        ("SQLiteStore", lambda: SQLiteStore(tmp / "s.db")),
        ("FileStore", lambda: FileStore(tmp / "fs")),
    ):
        step(f"{name}: arm 1h timer, restart, scan")
        with persisted(make(), "u1", m):
            pass
        now = time.time()
        (d,) = make().load("u1").deadlines
        print(
            f"  persisted deadline in {d.due_at_wall - now:.0f}s (entry_seq={d.entry_seq})"
        )
        sc = DueTimerScanner(make(), lambda k: m)
        early = sc.run_once(now=now + 1800)
        due = sc.run_once(now=now + 3601)
        again = sc.run_once(now=now + 3601)
        print(
            f"  early={early} due={due} again={again} lag={sc.last_result.max_lag_s:.1f}s"
        )
        assert early == 0, "must not fire early"
        assert due == 1, "must fire once due"
        assert again == 0, "must be idempotent"
        with persisted(make(), "u1", m) as i:
            print("  state:", i.current_state_ids)
            assert "r.reminded" in i.current_state_ids

    step("resume: 5000 ms timer, snapshot at 2000 -> +2999 no, +1 yes (sync)")
    cfg5 = {
        **cfg,
        "states": {
            **cfg["states"],
            "waiting": {"after": {"5000": "reminded"}},
        },
    }
    m5 = create_machine(cfg5)
    clk = SimulatedClock(wall_start=1000.0)
    i = SyncInterpreter(m5, clock=clk).start()
    clk.increment(2000)
    blob = i.get_snapshot()
    i.stop()
    clk2 = SimulatedClock(wall_start=1002.0)
    r = SyncInterpreter.from_snapshot(
        blob, m5, clock=clk2, restart_timers="resume"
    ).start()
    clk2.increment(2999)
    a = set(r.current_state_ids)
    clk2.increment(1)
    b = set(r.current_state_ids)
    print(f"  +2999: {a}  +1: {b}")
    assert a == {"r.waiting"} and b == {"r.reminded"}

    step("resume / fire_due on the async engine")

    async def go() -> tuple:
        c3 = SimulatedClock(wall_start=1002.0)
        x = Interpreter.from_snapshot(
            blob, m5, clock=c3, restart_timers="resume"
        )
        await x.start()
        await c3.increment(2999)
        a = set(x.current_state_ids)
        await c3.increment(1)
        b = set(x.current_state_ids)
        await x.stop()
        c4 = SimulatedClock(wall_start=99999.0)
        y = Interpreter.from_snapshot(
            blob, m5, clock=c4, restart_timers="fire_due"
        )
        await y.start()
        c = set(y.current_state_ids)
        await y.stop()
        return a, b, c

    a, b, c = asyncio.run(go())
    print(f"  resume +2999: {a}  +1: {b}   fire_due at start: {c}")
    assert a == {"r.waiting"} and b == {"r.reminded"} and c == {"r.reminded"}

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
