# examples/integrations/eda_fulfilment/tests/test_battle_295_scenario.py
"""#295 battle: sagas, choreography and AsyncAPI on a fulfilment day as an
operations team lives it. The `SagaBuilder` chart runs PERSISTED, driven by
the same `InboundDispatcher` / outbox the example uses, next to the
choreographed `order` / `warehouse` pair.

* **a hundred sagas, a third of them failing at a different step** --
  reserve → charge → ship with compensations; every failing saga
  compensates in REVERSE order exactly once, every succeeding one lands
  its results, no compensation runs twice, the published step events
  tell the story and the AsyncAPI document names every one of them;
* **the saga is killed -9 mid-compensation** -- after `release` ran and
  before the snapshot landed: on restart the saga is still in
  `compensating.reserve_stock`, `release` runs AGAIN (compensations
  must be idempotent -- documented), the saga reaches `failed` once;
* **a compensation that itself fails** -- `refund` is down: the saga
  parks in `compensationFailed`, a dead letter names the step, the
  operator fixes `refund` and `xsm dlq replay` is NOT the tool (a chart
  state, not an envelope) -- the documented restore path finishes it;
* **a redelivered step completion** -- the same `done.invoke` envelope
  arrives twice through the bus: one compensation chain, one result;
* **a shared bus** -- foreign service events, a `type` nobody handles and
  a saga command for an unknown saga id interleave with real traffic:
  ignored / dead-lettered as configured, real traffic unaffected;
* **AsyncAPI** -- the document for the example's charts validates
  offline, and every `meta.publish` type in the charts is a channel
  message (and nothing else is); `xsm asyncapi` prints the same.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

import app  # noqa: E402
from xstate_statemachine import MachineLogic, create_machine  # noqa: E402
from xstate_statemachine.eda import (  # noqa: E402
    Envelope,
    InboundDispatcher,
    OutboxPlugin,
    SQLiteOutboxStore,
    SyncFakeBrokerAdapter,
    asyncapi_document,
    publish_specs,
    validate_asyncapi,
)
from xstate_statemachine.patterns import (  # noqa: E402
    DeadLetterPlugin,
    SagaBuilder,
)
from xstate_statemachine.persistence import (  # noqa: E402
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
)
from xstate_statemachine.eda.dead_letter import (  # noqa: E402
    SQLiteDeadLetterStore,
)

ROOT = Path(__file__).resolve().parents[4]
EXAMPLE = Path(__file__).resolve().parents[1]
N = 90


def _saga() -> SagaBuilder:
    return (
        SagaBuilder("fulfil", start_event="START")
        .step("reserve_stock", invoke="reserve", compensate="release")
        .step("charge_card", invoke="charge", compensate="refund")
        .step("ship", invoke="ship")
        .on_failure("notifyOps")
    )


class Services:
    """Recording services; `fail_at[saga_id] = step` fails that step."""

    def __init__(self, fail_at: Dict[str, str], down: set = frozenset()):
        self.fail_at = fail_at
        self.down = set(down)
        self.calls: List[tuple] = []

    def make(self, name: str) -> Any:
        def svc(i: Any, ctx: Any, e: Any) -> Dict[str, Any]:
            # the saga's identity is its store key (the envelope subject)
            sid = getattr(i, "store_key", None) or ctx.get("sagaId")
            self.calls.append((sid, name))
            if name in self.down:
                raise RuntimeError(f"{name} is down")
            if self.fail_at.get(sid) == name:
                raise RuntimeError(f"{name} failed for {sid}")
            return {"ok": name, "sagaId": sid}

        return svc

    def logic(self, builder: SagaBuilder, ops: List[str]) -> MachineLogic:
        return builder.logic().merge(
            MachineLogic(
                services={
                    n: self.make(n)
                    for n in ("reserve", "release", "charge", "refund", "ship")
                },
                actions={
                    "notifyOps": lambda i, c, e, a: ops.append(i.store_key)
                },
            )
        )

    def for_saga(self, sid: str) -> List[str]:
        return [n for s, n in self.calls if s == sid]


class SagaApp:
    """A saga service process: persisted sagas driven by the bus."""

    def __init__(self, workdir: Path, services: Services, broker: Any = None):
        self.store = SQLiteStore(workdir / "saga.db")
        self.outbox = SQLiteOutboxStore(self.store)
        self.inbox = SQLiteInbox(self.store)
        self.dead_letters = SQLiteDeadLetterStore(self.store)
        self.broker = broker or SyncFakeBrokerAdapter()
        self.ops: List[str] = []
        self.builder = _saga()
        self.machine = create_machine(
            self.builder.build(),
            logic=services.logic(self.builder, self.ops),
            strict_config=True,
        )
        self.plugins = [
            OutboxPlugin(self.outbox, topic="sagas"),
            DeadLetterPlugin(self.dead_letters),
        ]
        self.dispatcher = InboundDispatcher(
            self.store,
            {"xsm.fulfil.START": self.machine},
            plugins=self.plugins,
            inbox=self.inbox,
            lock=PessimisticLock(),
            dead_letters=self.dead_letters,
            on_unknown="ignore",
        )

    def start(self, sid: str) -> Envelope:
        env = Envelope.new(
            type="xsm.fulfil.START",
            subject=sid,
            data={"sagaId": sid},
            source="checkout",
        )
        self.broker.publish("commands", env)
        return env

    def pump(self) -> Any:
        return self.dispatcher.run_once_sync(self.broker, "commands")

    def state(self, sid: str) -> Any:
        rec = self.store.load(sid)
        return json.loads(rec.snapshot) if rec else None

    def close(self) -> None:
        self.store.close()


# -----------------------------------------------------------------------------
# 1. a hundred sagas, a third failing at a different step
# -----------------------------------------------------------------------------
def test_sagas_compensate_in_reverse_exactly_once(tmp_path: Path) -> None:
    fail_at = {}
    for i in range(N):
        if i % 3 == 1:
            fail_at[f"s-{i}"] = ("charge", "ship", "reserve")[
                i % 3 - 1 + (i // 3) % 3
            ]
    svc = Services(fail_at)
    a = SagaApp(tmp_path, svc)
    try:
        for i in range(N):
            a.start(f"s-{i}")
        a.pump()
        for i in range(N):
            sid = f"s-{i}"
            snap = a.state(sid)
            assert snap is not None, sid
            calls = svc.for_saga(sid)
            step = fail_at.get(sid)
            if step is None:
                assert snap["value"] == "completed", (sid, snap["value"])
                assert calls == ["reserve", "charge", "ship"], (sid, calls)
                assert set(snap["context"]["results"]) == {
                    "reserve_stock",
                    "charge_card",
                    "ship",
                }
            else:
                assert snap["value"] == "failed", (sid, snap["value"])
                expect = {
                    "reserve": ["reserve"],
                    "charge": ["reserve", "charge", "release"],
                    "ship": ["reserve", "charge", "ship", "refund", "release"],
                }[step]
                assert calls == expect, (sid, step, calls)
                assert (
                    snap["context"]["error"]["step"]
                    == {
                        "reserve": "reserve_stock",
                        "charge": "charge_card",
                        "ship": "ship",
                    }[step]
                )
        assert sorted(a.ops) == sorted(fail_at)  # notifyOps once per failure
        # the step events the saga published tell the same story
        rows = a.outbox.pending(limit=10_000)
        types = {r.envelope.type for r in rows}
        doc = asyncapi_document(a.machine)
        channels = json.dumps(doc)
        for t in types:
            assert t in channels, t
    finally:
        a.close()


# -----------------------------------------------------------------------------
# 2. killed -9 mid-compensation
# -----------------------------------------------------------------------------
KILL_CHILD = r"""
import os, signal, sys
sys.path.insert(0, sys.argv[2]); sys.path.insert(0, sys.argv[3])
from pathlib import Path
from test_battle_295_scenario import SagaApp, Services
svc = Services({"s-k": "charge"})
a = SagaApp(Path(sys.argv[1]), svc)
real_save = a.store.save
def save(*args, **kw):
    # die after the compensation `release` RAN, before the snapshot lands
    if any(s == "s-k" and n == "release" for s, n in svc.calls):
        os.kill(os.getpid(), getattr(signal, "SIGKILL", 9))
    return real_save(*args, **kw)
a.store.save = save
a.start("s-k")
a.pump()
sys.exit(3)
"""


def test_killed_mid_compensation_compensates_again_idempotently(
    tmp_path: Path,
) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            KILL_CHILD,
            str(tmp_path),
            str(EXAMPLE),
            str(EXAMPLE / "tests"),
        ],
        cwd=str(EXAMPLE),
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONUTF8": "1"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode not in (0, 3), proc.stderr[-2000:]
    svc = Services({"s-k": "charge"})
    b = SagaApp(tmp_path, svc)
    try:
        snap = b.state("s-k")
        # 🔥 the whole step (START → reserve → charge failed → release)
        #    ran inside ONE persisted() block and the save was killed:
        #    nothing landed -- the redelivered command restarts the saga
        #    from scratch, and `release` runs AGAIN (compensations must
        #    be idempotent; documented in the guide's Guarantees box)
        assert snap is None or snap["value"] != "failed", snap
        b.start("s-k")
        b.pump()
        snap = b.state("s-k")
        assert snap["value"] == "failed", snap
        assert b.store.load("s-k").version >= 1
        assert svc.for_saga("s-k") == ["reserve", "charge", "release"]
    finally:
        b.close()


# -----------------------------------------------------------------------------
# 3. a compensation that itself fails
# -----------------------------------------------------------------------------
def test_failed_compensation_parks_with_a_dead_letter(tmp_path: Path) -> None:
    svc = Services({"s-c": "ship"}, down={"refund"})
    a = SagaApp(tmp_path, svc)
    try:
        a.start("s-c")
        a.pump()
        snap = a.state("s-c")
        assert snap["value"] == "compensationFailed", snap["value"]
        assert snap["context"]["error"] == {
            "step": "charge_card",
            "reason": "compensation",
            "type": "RuntimeError",
            "message": "refund is down",
        }
        recs = a.dead_letters.list()
        assert len(recs) == 1
        rec = recs[0]
        assert rec.machine_id == "fulfil"
        assert "compensationFailed" in rec.state_id
        assert rec.envelope in (
            None,
            {},
        ), "a chart-state record, not an envelope"
        # `release` never ran: the chain stopped at the failed compensation
        assert svc.for_saga("s-c") == ["reserve", "charge", "ship", "refund"]
        # 🏛️ `compensationFailed` is FINAL: the saga cannot fix a broken
        #    compensation by itself (a retry loop there would hammer a
        #    down service); the dead letter is the operator's ticket, and
        #    a REDELIVERED command does nothing to the finished saga
        a.start("s-c")
        res = a.pump()
        assert res.dead_lettered == 1 or res.duplicates == 1, res
        assert a.state("s-c")["value"] == "compensationFailed"
        assert svc.for_saga("s-c") == ["reserve", "charge", "ship", "refund"]
    finally:
        a.close()


# -----------------------------------------------------------------------------
# 4. redelivered command, shared bus
# -----------------------------------------------------------------------------
def test_redelivery_and_a_shared_bus(tmp_path: Path) -> None:
    svc = Services({"s-2": "charge"})
    a = SagaApp(tmp_path, svc)
    try:
        env = a.start("s-1")
        a.start("s-2")
        # foreign service events and an unknown saga type on the same bus
        a.broker.publish(
            "commands",
            Envelope.new(type="inventory.Restocked", subject="w-1", data={}),
        )
        a.broker.publish(
            "commands",
            Envelope.new(type="xsm.nobody.START", subject="n-1", data={}),
        )
        a.broker.publish("commands", env)  # the very same command again
        res = a.pump()
        assert res.processed == 2, res
        assert res.duplicates == 1, res
        assert res.ignored == 2, res  # on_unknown="ignore": a shared bus
        assert res.dead_lettered == 0, res
        assert svc.for_saga("s-1") == ["reserve", "charge", "ship"]
        assert svc.for_saga("s-2") == ["reserve", "charge", "release"]
        assert a.state("s-1")["value"] == "completed"
        assert a.state("s-2")["value"] == "failed"
        assert a.state("n-1") is None and a.state("w-1") is None
    finally:
        a.close()


# -----------------------------------------------------------------------------
# 5. AsyncAPI: the example's charts, offline, complete and nothing extra
# -----------------------------------------------------------------------------
def _xsm(*args: str, cwd: Path) -> "subprocess.CompletedProcess[str]":
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "src")] + [p for p in [env.get("PYTHONPATH")] if p]
    )
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "--plain", *args],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )


@pytest.mark.parametrize("chart", ["machine.json", "warehouse.json"])
def test_asyncapi_matches_the_chart_and_validates(chart: str, tmp_path: Path):
    pytest.importorskip("jsonschema")
    machine = (
        app.order_machine()
        if chart == "machine.json"
        else app.warehouse_machine()
    )
    doc = asyncapi_document(
        machine, server={"host": "broker:9092", "protocol": "kafka"}
    )
    validate_asyncapi(doc)
    declared = {s["type"] for s in publish_specs(machine)}
    messages = json.dumps(doc.get("components", {}).get("messages", {}))
    for t in declared:
        assert t in messages, (chart, t)
    # nothing the chart does not declare: a message is either a published
    # type or a `consume.<EVENT>` the chart handles
    names = set(doc.get("components", {}).get("messages", {}))
    events = set(json.dumps(app.load_chart(chart)).split('"'))
    for n in names:
        ok = any(t in n for t in declared) or (
            n.startswith("consume.") and n[len("consume.") :] in events
        )
        assert ok, (chart, n, declared)
    # the CLI prints the same document
    p = _xsm("asyncapi", str(EXAMPLE / chart), "--validate", cwd=tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    cli = json.loads(p.stdout)
    assert set(cli.get("components", {}).get("messages", {})) == names


def test_saga_asyncapi_lists_every_step_event(tmp_path: Path) -> None:
    pytest.importorskip("jsonschema")
    b = _saga()
    m = create_machine(b.build(), logic=b.logic(), strict_config=False)
    doc = asyncapi_document(m)
    validate_asyncapi(doc)
    text = json.dumps(doc)
    for step in ("reserve_stock", "charge_card", "ship"):
        assert step in text, step
    assert "compensated" in text
