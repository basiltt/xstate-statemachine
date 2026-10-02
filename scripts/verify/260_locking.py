"""Verification for #260 (A3 locking). `python scripts/verify/260_locking.py`.

Runs against the installed package. 16 threads x 200 increments on ONE key
under OptimisticLock and PessimisticLock on SQLiteStore -> exactly 3200;
exception in a block writes nothing; the block raises ConflictError on the
first conflict (the review-amended semantics; retrying is `persisted_retry`).
"""

from __future__ import annotations

import tempfile
import threading
import time
from pathlib import Path


def step(name: str) -> None:
    print(f"\n== {name}")


def main() -> int:
    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.persistence import (
        ConflictError,
        NoLock,
        OptimisticLock,
        PessimisticLock,
        SQLiteStore,
        persisted,
        persisted_retry,
    )

    tmp = Path(tempfile.mkdtemp())
    cfg = {
        "id": "c",
        "initial": "s",
        "context": {"n": 0},
        "states": {"s": {"on": {"T": {"actions": "inc"}}}},
    }
    m = create_machine(
        cfg,
        logic=MachineLogic(
            actions={"inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1)}
        ),
    )

    for lock in (OptimisticLock(retries=1000), PessimisticLock(timeout=60)):
        step(f"{type(lock).__name__}: 16 threads x 200 on one key")
        store = SQLiteStore(tmp / f"{type(lock).__name__}.db")
        t0 = time.perf_counter()

        def w() -> None:
            for _ in range(200):
                persisted_retry(
                    store, "k", m, lambda i: i.send("T"), lock=lock
                )

        ts = [threading.Thread(target=w) for _ in range(16)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        with persisted(store, "k", m, lock=NoLock()) as i:
            n = i.context["n"]
        print(f"  n = {n} in {time.perf_counter() - t0:.2f}s")
        assert n == 3200, n
        store.close()

    step("exception inside the block writes nothing")
    store = SQLiteStore(tmp / "tx.db")
    with persisted(store, "k", m) as i:
        i.send("T")
    before = store.load("k")
    try:
        with persisted(store, "k", m) as i:
            i.send("T")
            raise RuntimeError("user code failed")
    except RuntimeError:
        pass
    after = store.load("k")
    assert (
        after.version == before.version and after.snapshot == before.snapshot
    )
    print("  version unchanged:", after.version)

    step("block raises ConflictError on the first conflict; caller retries")
    try:
        with persisted(store, "k", m) as i:
            persisted_retry(store, "k", m, lambda x: x.send("T"))  # sneak
            i.send("T")
        raise SystemExit("expected ConflictError")
    except ConflictError as exc:
        print(f"  conflict: expected v{exc.expected}, found v{exc.actual}")
    with persisted(store, "k", m) as i:
        assert i.context["n"] == 2  # create-send(1) + sneak(1); block lost
    store.close()

    print(
        "\n== battle tests (post-RC programme): semantics / after_commit / "
        "failure injection / leaks + mojibake scan"
    )
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    for cmd in (
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/persistence/test_battle_260_locking_semantics.py",
            "tests/persistence/test_battle_260_locking_failures.py",
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
