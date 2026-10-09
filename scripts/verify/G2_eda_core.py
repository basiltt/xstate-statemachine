"""Verification for G2: #272 B5 (broker protocol + fake), #293 F2 (EDA core,
`[cloudevents]`, outbox, DLQ, AsyncAPI) and #295 F4 (sagas, choreography,
`xsm asyncapi`).

`python scripts/verify/G2_eda_core.py`.

Windows-safe (no heredocs, no /tmp: every file lives in a
``tempfile.mkdtemp()`` directory; the CLI runs through
``subprocess.run([sys.executable, ...])``). Runs the EDA test folders,
then end-to-end checks straight from the issues:

* #272: `FakeBrokerAdapter` from the `[testing]` path; an inbound →
  machine → outbound round trip with causation ids and no real broker.
* #293: the issue's snippet; 1,000 envelopes across 10 subjects (order
  kept, duplicates dropped, none lost); poison → DLQ + ack; SQLite outbox
  rolled back with its snapshot; CloudEvents binary + structured round
  trip; `xsm dlq` dry-run default, guarded replay, id reuse, audit;
  two relays on one outbox (a killed relay's lease expires, no row
  published twice); bad operator input is exit 2 with one line.
* #295: `SagaBuilder` compensates in reverse exactly once; Order + Payment
  choreography from ONE envelope with the causation chain; `xsm asyncapi`
  output validates against the vendored AsyncAPI 3.0.0 schema.

Prints ``ALL OK``.
"""

import asyncio
import json
import os
import pathlib
import random
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

ROOT = pathlib.Path(__file__).resolve().parents[2]
# 💡 Verify THIS checkout even when an editable install points elsewhere
#    (git worktrees share one environment).
sys.path.insert(0, str(ROOT / "src"))
TMP = pathlib.Path(tempfile.mkdtemp(prefix="xsm-g2-"))
ENV = dict(os.environ, PYTHONPATH=str(ROOT / "src"))


def step(name: str) -> None:
    print(f"\n== {name}")


def run_tests() -> None:
    step("pytest eda + patterns + contrib/cloudevents + CLI")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/eda",
            "tests/patterns",
            "tests/contrib/cloudevents",
            "tests/contrib/sqlalchemy/test_sqlalchemy_outbox.py",
            "tests/contrib/testing/test_fake_broker.py",
            "tests/tests_cli/test_eda_cli.py",
            "tests/tests_cli/test_battle_293_b_dlq.py",
            "tests/contrib/test_extras_matrix.py",
            "-q",
            "-p",
            "no:cacheprovider",
            # 📝 git worktrees share one environment: the `pytest11` entry
            #    point may point at ANOTHER checkout's package. Disable it;
            #    these folders do not use the xsm_* fixtures.
            "-p",
            "no:xstate_statemachine",
        ],
        cwd=str(ROOT),
        env=ENV,
    )
    assert proc.returncode == 0, "tests failed"


def xsm(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "--plain", *args],
        cwd=str(TMP),
        env=ENV,
        capture_output=True,
        text=True,
        timeout=120,
    )


# -----------------------------------------------------------------------------
# #272
# -----------------------------------------------------------------------------
def b5_fake_broker() -> None:
    step("#272 FakeBrokerAdapter round trip (no real broker)")
    from xstate_statemachine import PluginBase, SyncInterpreter, create_machine
    from xstate_statemachine.eda import Envelope, SyncFakeBrokerAdapter

    try:
        from xstate_statemachine.contrib.testing import FakeBrokerAdapter
        from xstate_statemachine.eda import FakeBrokerAdapter as Core

        assert FakeBrokerAdapter is Core
        print("  [testing] path re-exports the core fake")
    except ImportError:
        print("  (pytest not installed: [testing] path skipped)")

    broker = SyncFakeBrokerAdapter()
    m = create_machine(
        {
            "id": "o",
            "initial": "a",
            "states": {"a": {"on": {"GO": "b"}}, "b": {}},
        }
    )

    class Pub(PluginBase):
        cause: Any = None

        def on_transition(self, i: Any, f: Any, t: Any, tr: Any) -> None:
            if getattr(tr, "event", None) != "GO":
                return  # the initial entry is not an integration event
            broker.publish(
                "out",
                Envelope.from_transition(i, type="o.moved", cause=self.cause),
            )

    pub = Pub()
    i = SyncInterpreter(m).use(pub).start()

    def inbound(env: Envelope) -> None:
        pub.cause = env
        i.send(env.to_event())

    broker.on("in", inbound)
    cmd = Envelope.new(type="xsm.o.GO", subject="o-1")
    broker.deliver("in", cmd)
    broker.drain()
    [out] = broker.published_on("out")
    assert out.causationid == cmd.id and out.subject == "o-1"
    i.stop()
    print("  inbound -> send -> outbound, causationid ok")


# -----------------------------------------------------------------------------
# #293
# -----------------------------------------------------------------------------
def f2_issue_snippet() -> None:
    step("#293 the issue's verification snippet")
    from xstate_statemachine import create_machine
    from xstate_statemachine.eda import (
        Envelope,
        FakeBrokerAdapter,
        InboundDispatcher,
        OutboxPlugin,
    )
    from xstate_statemachine.persistence import MemoryStore

    cfg = {
        "id": "o",
        "initial": "a",
        "states": {
            "a": {
                "on": {
                    "GO": {
                        "target": "b",
                        "meta": {"publish": {"type": "order.moved"}},
                    }
                }
            },
            "b": {},
        },
    }
    m = create_machine(cfg)
    broker, store = FakeBrokerAdapter(), MemoryStore()
    disp = InboundDispatcher(
        store, lambda t: m, plugins=[OutboxPlugin(broker)]
    )

    async def main() -> List[Any]:
        await broker.deliver(
            "orders", Envelope.new(type="xsm.o.GO", subject="o-1", data={})
        )
        await disp.run_once(broker, "orders")
        return [
            (e.type, e.subject, e.causationid is not None)
            for e in broker.published
        ]

    got = asyncio.run(main())
    print(" ", got)
    assert got == [("order.moved", "o-1", True)]


def f2_thousand() -> None:
    step("#293 1,000 envelopes / 10 subjects: order kept, dups dropped")
    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.eda import (
        Envelope,
        FakeBrokerAdapter,
        InboundDispatcher,
    )
    from xstate_statemachine.persistence import MemoryInbox, MemoryStore

    m = create_machine(
        {
            "id": "c",
            "initial": "on",
            "context": {"seen": []},
            "states": {"on": {"on": {"ADD": {"actions": "rec"}}}},
        },
        logic=MachineLogic(
            actions={
                "rec": lambda i, c, e, a: c.__setitem__(
                    "seen", c["seen"] + [e.payload["n"]]
                )
            }
        ),
    )
    store, broker = MemoryStore(), FakeBrokerAdapter()
    disp = InboundDispatcher(
        store, lambda t: m, inbox=MemoryInbox(), max_in_flight=4
    )
    rng = random.Random(1)
    per: Dict[str, int] = {f"s{k}": 0 for k in range(10)}
    sent = []
    for _ in range(900):
        s = f"s{rng.randrange(10)}"
        sent.append(
            Envelope.new(type="xsm.c.ADD", subject=s, data={"n": per[s]})
        )
        per[s] += 1
    dups = [sent[rng.randrange(900)] for _ in range(100)]

    async def go() -> Any:
        for e in sent + dups:
            await broker.deliver("in", e)
        return await disp.run_once(broker, "in")

    res = asyncio.run(go())
    assert (res.processed, res.duplicates) == (900, 100), res
    for s, n in per.items():
        seen = json.loads(store.load(s).snapshot)["context"]["seen"]
        assert seen == list(range(n)), s
    print(f"  processed={res.processed} duplicates={res.duplicates} lost=0")


def f2_poison_and_outbox() -> None:
    step("#293 poison -> DLQ + ack; SQLite outbox rolls back with snapshot")
    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.eda import (
        Envelope,
        InboundDispatcher,
        MemoryDeadLetterStore,
        OutboxPlugin,
        SQLiteOutboxStore,
        SyncFakeBrokerAdapter,
    )
    from xstate_statemachine.persistence import (
        MemoryStore,
        PessimisticLock,
        SQLiteStore,
        persisted,
    )

    bad = create_machine(
        {
            "id": "p",
            "initial": "a",
            "actionErrorPolicy": "fail",
            "states": {"a": {"on": {"E": {"actions": "boom"}}}},
        },
        logic=MachineLogic(actions={"boom": lambda i, c, e, a: 1 / 0}),
    )
    dlq = MemoryDeadLetterStore()
    disp = InboundDispatcher(
        MemoryStore(), lambda t: bad, max_attempts=3, dead_letters=dlq
    )
    broker = SyncFakeBrokerAdapter()
    broker.deliver("in", Envelope.new(type="xsm.p.E", subject="k"))
    for _ in range(5):
        disp.run_once_sync(broker, "in")
    assert len(dlq) == 1 and broker.pending("in") == 0
    assert dlq.list()[0].reason == "max_attempts"
    print("  poison dead-lettered after 3 attempts and acked")

    store = SQLiteStore(TMP / "outbox.db")
    outbox = SQLiteOutboxStore(store)
    cfg = {
        "id": "o",
        "initial": "a",
        "states": {
            "a": {"on": {"GO": {"target": "b", "meta": {"publish": "o.go"}}}},
            "b": {},
        },
    }
    real = outbox.add

    def add_then_crash(topic: str, env: Any) -> None:
        real(topic, env)
        raise RuntimeError("crash after the outbox write")

    outbox.add = add_then_crash  # type: ignore[method-assign]
    try:
        with persisted(
            store,
            "o-1",
            create_machine(cfg),
            lock=PessimisticLock(),
            plugins=[OutboxPlugin(outbox)],
        ) as i:
            i.send("GO")
    except RuntimeError:
        pass
    assert outbox.count() == 0 and store.load("o-1") is None
    store.close()
    print("  forced failure after the write: no outbox row, no snapshot")


def f2_cloudevents() -> None:
    step("#293 [cloudevents] binary + structured round trip")
    try:
        from xstate_statemachine.contrib.cloudevents import (
            from_http,
            to_binary,
            to_structured,
        )
    except ImportError:
        print("  (cloudevents not installed: skipped)")
        return
    from xstate_statemachine.eda import Envelope

    e = Envelope.new(
        type="order.paid", subject="o-1", data={"t": 1}, correlationid="c"
    )
    for fn in (to_binary, to_structured):
        headers, body = fn(e)
        headers["Authorization"] = "Bearer secret"
        assert from_http(headers, body) == e
    print("  both HTTP modes round-trip; Authorization never copied")


def f2_dlq_cli() -> None:
    step("#293 xsm dlq: dry run default, guarded replay, id reuse, audit")
    from xstate_statemachine import MachineLogic, create_machine
    from xstate_statemachine.eda import (
        Envelope,
        InboundDispatcher,
        SQLiteDeadLetterStore,
    )
    from xstate_statemachine.persistence import SQLiteStore

    cfg = {
        "id": "counter",
        "version": "1",
        "initial": "on",
        "context": {"n": 0},
        "states": {"on": {"on": {"ADD": {"actions": "add"}}}},
    }
    (TMP / "counter.json").write_text(json.dumps(cfg), encoding="utf-8")
    (TMP / "g2_counter_logic.py").write_text(
        "def add(i, ctx, e, a):\n    ctx['n'] += 1\n", encoding="utf-8"
    )
    broken = create_machine(
        dict(cfg, actionErrorPolicy="fail"),
        logic=MachineLogic(actions={"add": lambda i, c, e, a: 1 / 0}),
    )
    dlq = SQLiteDeadLetterStore(TMP / "dlq.db")
    state = SQLiteStore(TMP / "state.db")
    env = Envelope.new(type="xsm.counter.ADD", subject="c-1")
    InboundDispatcher(
        state, lambda t: broken, max_attempts=1, dead_letters=dlq
    ).handle(env, topic="in")
    state.close()
    dlq_url = f"sqlite:///{(TMP / 'dlq.db').as_posix()}"
    st_url = f"sqlite:///{(TMP / 'state.db').as_posix()}"
    base = ["dlq", "--dlq", dlq_url]
    r = xsm(*base, "list")
    assert r.returncode == 0 and env.id in r.stdout, r.stdout + r.stderr
    rp = [
        *base,
        "replay",
        env.id,
        "--store",
        st_url,
        "--machine",
        "counter.json",
        "--logic",
        "g2_counter_logic",
    ]
    ENV["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(TMP)])
    r = xsm(*rp, "--reason", "fixed")
    assert r.returncode == 0 and "dry run" in r.stdout, r.stdout + r.stderr
    assert xsm(*rp, "--no-dry-run", "--reason", "x").returncode != 0
    r = xsm(*rp, "--no-dry-run", "--yes", "--reason", "fixed in 1.2")
    assert r.returncode == 0 and "processed" in r.stdout, r.stdout + r.stderr
    r = xsm(*rp, "--no-dry-run", "--yes", "--reason", "again", "--json")
    assert json.loads(r.stdout)["outcome"] == "duplicate", r.stdout
    audit = dlq.audit_log()
    assert [a["reason"] for a in audit] == ["fixed in 1.2", "again"]
    dlq.close()
    print("  dry run by default; --yes/--reason enforced; replay audited;")
    print("  double replay deduplicated by the reused envelope id")


def f2_relay_leases() -> None:
    step("#293 battle: two relays on one SQLite outbox -- leases")
    from xstate_statemachine.eda import (
        Envelope,
        OutboxRelay,
        SQLiteOutboxStore,
        SyncFakeBrokerAdapter,
    )

    outbox = SQLiteOutboxStore(TMP / "outbox.db")
    broker = SyncFakeBrokerAdapter()
    for n in range(50):
        outbox.add("orders", Envelope.new(type="t", subject=f"s-{n}"))
    # relay A claims a batch and "dies" (kill -9: no release)
    dead = outbox.claim(limit=20, owner="relay-a", lease_s=0.2)
    relay_b = OutboxRelay(outbox, broker, owner="relay-b", lease_s=30)
    assert relay_b.relay_once_sync() == 30  # skips A's live lease
    assert relay_b.relay_once_sync() == 0
    import time

    time.sleep(0.3)  # A's lease expires
    assert relay_b.relay_once_sync() == 20
    ids = [e.id for e in broker.published_on("orders")]
    assert len(ids) == len(set(ids)) == 50, "a row was published twice"
    assert {r.envelope.id for r in dead} <= set(ids)
    assert outbox.count(pending_only=True) == 0
    outbox.close()
    print("  50 rows, relay A killed holding 20: B published 30, then the")
    print("  20 after the lease expired -- none twice, none lost")


def f2_dlq_operator_input() -> None:
    step("#293 battle: xsm dlq / asyncapi refuse bad input with exit 2")
    ghost = (TMP / "typo.db").as_posix()
    junk = TMP / "junk.db"
    junk.write_text("not sqlite", encoding="utf-8")
    cases = [
        ["dlq", "--dlq", f"sqlite:///{ghost}", "list"],
        ["dlq", "--dlq", "redis://x", "list"],
        ["dlq", "--dlq", str(junk), "list"],
        ["dlq", "--dlq", str(TMP / "dlq.db"), "show", "nope"],
        [
            "dlq",
            "--dlq",
            str(TMP / "dlq.db"),
            "purge",
            "--older-than",
            "7w",
            "--yes",
            "--reason",
            "r",
        ],
        ["asyncapi", str(TMP / "none.json")],
    ]
    for argv in cases:
        r = xsm(*argv)
        out = r.stdout + r.stderr
        assert r.returncode == 2 and "Traceback" not in out, (argv, out)
    assert not (TMP / "typo.db").exists(), "a typo created a store"
    print(f"  {len(cases)} bad inputs: one line each, exit 2, no file created")


# -----------------------------------------------------------------------------
# #295
# -----------------------------------------------------------------------------
def f4_saga() -> None:
    step("#295 SagaBuilder: reverse compensation exactly once")
    from xstate_statemachine import (
        MachineLogic,
        SimulatedClock,
        SyncInterpreter,
        create_machine,
    )
    from xstate_statemachine.patterns import SagaBuilder

    calls: List[str] = []

    def svc(name: str, fail: bool = False) -> Any:
        def run(i: Any, c: Any, e: Any) -> str:
            calls.append(name)
            if fail:
                raise RuntimeError(name)
            return name

        return run

    saga = (
        SagaBuilder("demo")
        .step("a", invoke="doA", compensate="undoA")
        .step("b", invoke="doB", compensate="undoB")
        .step("c", invoke="doC")
    )
    cfg = saga.build()
    (TMP / "saga.json").write_text(json.dumps(cfg), encoding="utf-8")
    logic = saga.logic().merge(
        MachineLogic(
            services={
                "doA": svc("a"),
                "doB": svc("b"),
                "doC": svc("c", True),
                "undoA": svc("undoA"),
                "undoB": svc("undoB"),
            }
        )
    )
    m = create_machine(cfg, logic=logic, strict_config=True)
    i = SyncInterpreter(m, clock=SimulatedClock()).start()
    assert calls == ["a", "b", "c", "undoB", "undoA"], calls
    assert i.current_state_ids == {"demo.failed"}
    i.stop()
    print("  ", calls)
    r = xsm("inspect", "saga.json", "--no-events")
    assert r.returncode == 0, r.stderr
    print("  xsm inspect renders the generated chart")


def f4_choreography() -> None:
    step("#295 Order + Payment choreography from ONE envelope")
    from xstate_statemachine import create_machine
    from xstate_statemachine.eda import (
        Envelope,
        FakeBrokerAdapter,
        OutboxPlugin,
    )
    from xstate_statemachine.patterns import ChoreographyRouter
    from xstate_statemachine.persistence import MemoryInbox, MemoryStore

    order = create_machine(
        {
            "id": "order",
            "initial": "new",
            "states": {
                "new": {
                    "on": {
                        "PLACE": {
                            "target": "awaiting",
                            "meta": {"publish": "order.placed"},
                        }
                    }
                },
                "awaiting": {"on": {"PAID": "completed"}},
                "completed": {"type": "final"},
            },
        }
    )
    payment = create_machine(
        {
            "id": "payment",
            "initial": "idle",
            "states": {
                "idle": {
                    "on": {
                        "CHARGE": {
                            "target": "paid",
                            "meta": {"publish": "payment.captured"},
                        }
                    }
                },
                "paid": {"type": "final"},
            },
        }
    )
    bus, store = FakeBrokerAdapter(), MemoryStore()
    router = ChoreographyRouter(
        store,
        {
            "xsm.order.PLACE": order,
            "order.placed": (payment, "CHARGE"),
            "payment.captured": (order, "PAID"),
        },
        plugins=[OutboxPlugin(bus, topic="events")],
        inbox=MemoryInbox(),
    )
    cmd = Envelope.new(type="xsm.order.PLACE", subject="o-9")

    async def go() -> None:
        await bus.deliver("events", cmd)
        await router.run_until_quiet(bus)

    asyncio.run(go())
    o = json.loads(store.load("order:o-9").snapshot)["state_ids"]
    p = json.loads(store.load("payment:o-9").snapshot)["state_ids"]
    assert (o, p) == (["order.completed"], ["payment.paid"]), (o, p)
    chain = {e.type: e for e in bus.published}
    assert chain["order.placed"].causationid == cmd.id
    assert chain["payment.captured"].causationid == chain["order.placed"].id
    print("  order.completed + payment.paid; causation chain intact")


def f4_asyncapi() -> None:
    step("#295 xsm asyncapi validates against the vendored schema")
    r = xsm("asyncapi", "saga.json", "-o", "asyncapi.json")
    assert r.returncode == 0, r.stderr
    doc = json.loads((TMP / "asyncapi.json").read_text(encoding="utf-8"))
    assert doc["asyncapi"] == "3.0.0"
    try:
        import jsonschema  # noqa: F401
    except ImportError:
        print("  (jsonschema not installed: validation skipped)")
        return
    from xstate_statemachine.eda import validate_asyncapi

    validate_asyncapi(doc)
    print(
        f"  valid AsyncAPI 3.0.0 with "
        f"{len(doc['components']['messages'])} messages"
    )


def main() -> None:
    run_tests()
    b5_fake_broker()
    f2_issue_snippet()
    f2_thousand()
    f2_poison_and_outbox()
    f2_cloudevents()
    f2_dlq_cli()
    f2_relay_leases()
    f2_dlq_operator_input()
    f4_saga()
    f4_choreography()
    f4_asyncapi()
    print("\nALL OK")


if __name__ == "__main__":
    main()
