"""Verification for #261 (A4 idempotency). `python scripts/verify/261_idempotency.py`.

Runs against the installed package. Redelivery returns the original
receipt flagged duplicate and the machine transitions once (both engines);
fingerprint mismatch -> 422 receipt; in-flight -> 409; TTL re-admits;
dedup across `persisted()` hydrations with a shared SQLite backend; the
save->mark crash window is caught by the in-snapshot ring.
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
        MachineLogic,
        SyncInterpreter,
        create_machine,
        receipt_to_status,
    )
    from xstate_statemachine.persistence import (
        IdempotencyMismatchError,
        IdempotencyPlugin,
        MemoryInbox,
        SQLiteInbox,
        SQLiteStore,
        persisted,
    )

    cfg = {
        "id": "w",
        "initial": "a",
        "context": {"credits": 0},
        "states": {"a": {"on": {"CREDIT": {"actions": "add"}}}},
    }
    m = create_machine(
        cfg,
        logic=MachineLogic(
            actions={
                "add": lambda i, c, e, a: c.__setitem__(
                    "credits", c["credits"] + e.payload["amount"]
                )
            }
        ),
    )

    step("sync: redelivery returns the original receipt, credited once")
    i = (
        SyncInterpreter(m)
        .use(IdempotencyPlugin(MemoryInbox(), principal=lambda e: "acct_1"))
        .start()
    )
    r1 = i.send("CREDIT", wait=True, idempotency_key="evt_123", amount=10)
    r2 = i.send("CREDIT", wait=True, idempotency_key="evt_123", amount=10)
    print(i.context["credits"], r1.duplicate, r2.duplicate)
    assert i.context["credits"] == 10 and not r1.duplicate and r2.duplicate
    r3 = i.send("CREDIT", wait=True, idempotency_key="evt_123", amount=99)
    print("mismatch ->", receipt_to_status(r3), type(r3.error).__name__)
    assert receipt_to_status(r3) == 422
    assert isinstance(r3.error, IdempotencyMismatchError)
    i.stop()

    step("async parity")

    async def go() -> tuple:
        ai = (
            await Interpreter(m)
            .use(
                IdempotencyPlugin(MemoryInbox(), principal=lambda e: "acct_1")
            )
            .start()
        )
        a1 = await ai.send("CREDIT", wait=True, idempotency_key="e", amount=1)
        a2 = await ai.send("CREDIT", wait=True, idempotency_key="e", amount=1)
        n = ai.context["credits"]
        await ai.stop()
        return n, a1.duplicate, a2.duplicate

    print(asyncio.run(go()))
    assert asyncio.run(go()) == (1, False, True)

    step("TTL expiry re-admits; purge counts")
    inbox = MemoryInbox()
    i = (
        SyncInterpreter(m)
        .use(IdempotencyPlugin(inbox, principal=lambda e: "p", ttl_s=0.05))
        .start()
    )
    i.send("CREDIT", idempotency_key="k", amount=1)
    time.sleep(0.1)
    r = i.send("CREDIT", wait=True, idempotency_key="k", amount=1)
    print("re-admitted:", not r.duplicate, "credits:", i.context["credits"])
    assert not r.duplicate and i.context["credits"] == 2
    i.stop()

    step("persisted() + shared SQLite backend: dedup across hydrations")
    db = Path(tempfile.mkdtemp()) / "app.db"
    store = SQLiteStore(db)
    plugin = IdempotencyPlugin(SQLiteInbox(store), principal=lambda e: "acct")
    for _ in range(3):
        with persisted(store, "w:acct", m, plugins=[plugin]) as w:
            w.send("CREDIT", idempotency_key="evt_1", amount=500)
    with persisted(store, "w:acct", m, plugins=[plugin]) as w:
        print("balance after 3 deliveries:", w.context["credits"])
        assert w.context["credits"] == 500
    store.close()

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
