"""Verification for #306 (A12 redis). `python scripts/verify/306_redis.py [--real URL]`.

Runs against fakeredis by default; `--real redis://host:6379/15` uses a live
server. Exercises optimistic conflict, lock fencing, atomic forget,
list_keys glob escaping, the async twin, and the scanner's zset index.
"""

from __future__ import annotations

import asyncio
import sys
import time
import uuid


def step(name: str) -> None:
    print(f"\n== {name}")


def main(argv: list) -> int:
    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.contrib.redis import (
        AsyncRedisStore,
        RedisInbox,
        RedisLog,
        RedisStore,
    )
    from xstate_statemachine.persistence import (
        AuditPlugin,
        ConflictError,
        DueTimerScanner,
        IdempotencyPlugin,
        PessimisticLock,
        apersisted,
        persisted,
    )

    if "--real" in argv:
        import redis

        url = argv[argv.index("--real") + 1]
        r = redis.Redis.from_url(url)
        import redis.asyncio as aredis

        ar = aredis.Redis.from_url(url)
        print("live Redis:", url)
    else:
        import fakeredis

        srv = fakeredis.FakeServer()
        r = fakeredis.FakeRedis(server=srv)
        ar = fakeredis.FakeAsyncRedis(server=srv)
        print("fakeredis")
    prefix = f"verify-{uuid.uuid4().hex[:6]}"

    cfg = {
        "id": "c",
        "initial": "s",
        "context": {"n": 0},
        "states": {
            "s": {"on": {"T": {"actions": "inc"}}, "after": {"3600000": "d"}},
            "d": {"type": "final"},
        },
    }
    m = create_machine(
        cfg,
        logic=MachineLogic(
            actions={"inc": lambda i, c, e, a: c.__setitem__("n", c["n"] + 1)}
        ),
    )
    store = RedisStore(r, prefix=prefix, lock_ttl_ms=50)
    inbox, log = RedisInbox(r, prefix=prefix), RedisLog(r, prefix=prefix)
    plugins = [
        IdempotencyPlugin(inbox, principal=lambda e: "p"),
        AuditPlugin(log),
    ]

    step("round-trip with inbox + log; optimistic conflict")
    with persisted(store, "k", m, plugins=plugins) as i:
        i.send("T", idempotency_key="e1", actor="a")
    with persisted(store, "k", m, plugins=plugins) as i:
        rc = i.send("T", wait=True, idempotency_key="e1")
        assert rc.duplicate and i.context["n"] == 1
    rec = store.load("k")
    try:
        store.save("k", rec.snapshot, expected_version=0)
        raise SystemExit("conflict not raised")
    except ConflictError as e:
        print("  conflict ->", e.actual)
    print("  log:", [(x.seq, x.event_type) for x in log.read("k")])

    step(
        "fencing: lock expires under a slow holder -> ConflictError, first writer wins"
    )
    try:
        with persisted(store, "k", m, lock=PessimisticLock(timeout=1)) as slow:
            slow.send("T")
            time.sleep(0.08)
            with persisted(
                store, "k", m, lock=PessimisticLock(timeout=1)
            ) as fast:
                fast.send("T")
                fast.send("T")
        raise SystemExit("expected ConflictError")
    except ConflictError:
        with persisted(store, "k", m) as i:
            print(
                "  n =", i.context["n"], "(fast's 2 writes, slow's discarded)"
            )
            assert i.context["n"] == 3

    step("list_keys escapes glob metacharacters")
    for k in ("order*1", "orderX1", "order?1"):
        store.save(k, rec.snapshot)
    print("  order* ->", store.list_keys(prefix="order*"))
    assert store.list_keys(prefix="order*") == ["order*1"]

    step("scanner reads the deadline index")
    sc = DueTimerScanner(store, lambda key: m)
    now = time.time()
    print(
        "  due at +30min:",
        sc.run_once(now=now + 1800),
        " due at +61min:",
        sc.run_once(now=now + 3660),
    )

    step("async twin")

    async def go() -> int:
        astore = AsyncRedisStore(ar, prefix=prefix)
        async with apersisted(astore, "ak", m) as i:
            await i.send("T", wait=True)
        return (await astore.load("ak")).version

    print("  async version:", asyncio.run(go()))

    step("forget leaves nothing behind")
    counts = store.forget("k")
    left = [k for k in r.scan_iter(match=f"{prefix}:*:k")]
    print("  ", counts, "left:", left)
    assert left == []
    for k in r.scan_iter(match=f"{prefix}:*"):
        r.delete(k)

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
