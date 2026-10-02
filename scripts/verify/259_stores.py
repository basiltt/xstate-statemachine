"""Verification for #259 (A2 stores). `python scripts/verify/259_stores.py`.

Runs against the installed package. Contract behaviours on all three
backends, FileStore atomicity under a fault hook, and the full 8-thread
x 200 optimistic retry loop on SQLiteStore (n == 1600, no lost updates).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import (
        MachineLogic,
        SyncInterpreter,
        create_machine,
    )
    from xstate_statemachine.persistence import (
        ConflictError,
        FileStore,
        LockTimeoutError,
        MemoryStore,
        SQLiteStore,
        load_interpreter,
        save_interpreter,
    )

    tmp = Path(tempfile.mkdtemp())
    cfg = {
        "id": "o",
        "initial": "a",
        "context": {"n": 0},
        "states": {
            "a": {"on": {"GO": {"target": "b", "actions": "inc"}}},
            "b": {"on": {"GO": {"target": "a", "actions": "inc"}}},
        },
    }
    m = create_machine(
        cfg,
        logic=MachineLogic(
            actions={"inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1)}
        ),
    )

    step("contract: round-trip + conflict on every backend")
    for store in (
        MemoryStore(),
        FileStore(tmp / "fs"),
        SQLiteStore(tmp / "s.db"),
    ):
        i = SyncInterpreter(m).start()
        i.send("GO")
        v = store.save(
            "k", i.get_snapshot(), expected_version=0, machine_version="1"
        )
        i.stop()
        rec = store.load("k")
        assert v == 1 and rec.version == 1 and rec.machine_version == "1"
        try:
            store.save("k", rec.snapshot, expected_version=0)
            raise SystemExit("conflict not raised")
        except ConflictError as exc:
            assert exc.actual == 1
        r = SyncInterpreter.from_snapshot(rec.snapshot, m).start()
        assert r.context["n"] == 1 and r.matches("o.b")
        r.stop()
        assert store.list_keys(prefix="k") == ["k"]
        with store.lock("k", timeout=1):
            pass
        print(f"  {store.backend}: ok  health={store.health()['ok']}")

    step("FileStore: crash between fsync and rename leaves previous intact")
    fs = FileStore(tmp / "fs2")
    fs.save(
        "k",
        json.dumps(
            {
                "version": 4,
                "status": "running",
                "context": {},
                "state_ids": ["o.a"],
            }
        ),
    )
    before = fs.load("k")

    def crash(_tmp: str) -> None:
        raise OSError("simulated crash")

    fs._before_replace_hook = crash
    try:
        fs.save("k", "{}")
    except OSError:
        pass
    fs._before_replace_hook = None
    assert fs.load("k") == before
    print("  previous record intact, version", before.version)

    step("SQLiteStore: 8 threads x 200 optimistic saves on one key")
    store = SQLiteStore(tmp / "stress.db")
    conflicts = [0]
    t0 = time.perf_counter()

    def worker() -> None:
        for _ in range(200):
            while True:
                interp, ver = load_interpreter(store, "order-1", m)
                try:
                    interp.send("GO")
                    save_interpreter(
                        store, "order-1", interp, expected_version=ver
                    )
                    break
                except (ConflictError, LockTimeoutError):
                    conflicts[0] += 1
                finally:
                    interp.stop()

    ts = [threading.Thread(target=worker) for _ in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    interp, ver = load_interpreter(store, "order-1", m)
    print(
        f"  n = {interp.context['n']} version = {ver} conflicts = {conflicts[0]} "
        f"in {time.perf_counter() - t0:.2f}s"
    )
    assert interp.context["n"] == 1600 and ver == 1600
    interp.stop()
    store.close()

    print(
        "\n== battle tests (post-RC programme): crash / concurrency / "
        "corruption / contracts + mojibake scan"
    )
    # 🛡️ Real kill -9 of a writer child at every save step, ENOSPC at
    #    every syscall, two processes on one lock, every byte of a record
    #    mutated, the backend contract matrix across all three stores.
    root = Path(__file__).resolve().parents[2]
    for cmd in (
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/persistence/test_battle_259_stores_crash_concurrency.py",
            "tests/persistence/test_battle_259_stores_corruption_scaling.py",
            "-q",
            "-p",
            "no:cacheprovider",
            "-p",
            "no:asyncio",
        ],
        [sys.executable, "scripts/verify/_mojibake_scan.py"],
    ):
        subprocess.run(cmd, cwd=root, check=True)

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
