# tests/persistence/test_log.py
"""#262: transition log stores (contract), `TransitionLogPlugin` /
`AuditPlugin` on both engines, and `replay()` incl. divergence."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Iterator, List

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
    stub_logic,
)
from src.xstate_statemachine.persistence import (
    AuditPlugin,
    IdempotencyPlugin,
    JSONLinesLog,
    MemoryInbox,
    MemoryLog,
    ReplayDivergenceError,
    SQLiteLog,
    SQLiteStore,
    TransitionLogPlugin,
    TransitionLogStore,
    TransitionRecord,
    correlation_id_var,
    persisted,
    replay,
)

ROOT = Path(__file__).resolve().parents[2]
CORPUS = (
    ROOT / "tests" / "tests_cli" / "stately_machines" / "AdvancePayment.json"
)

LOG_FACTORIES = {
    "memory": lambda tmp: MemoryLog(),
    "jsonl": lambda tmp: JSONLinesLog(tmp / "log.jsonl"),
    "sqlite": lambda tmp: SQLiteLog(tmp / "log.db"),
}


@pytest.fixture(params=sorted(LOG_FACTORIES))
def log(request: Any, tmp_path: Any) -> Iterator[Any]:
    lg = LOG_FACTORIES[request.param](tmp_path)
    yield lg
    if hasattr(lg, "close"):
        lg.close()


def rec(
    seq: int, mid: str = "m", ts: float = 100.0, **kw: Any
) -> TransitionRecord:
    base = dict(
        machine_id=mid,
        seq=seq,
        ts=ts,
        event_type="GO",
        event_payload={"k": seq},
        from_states=("m.a",),
        to_states=("m.b",),
        actions=("act",),
    )
    base.update(kw)
    return TransitionRecord(**base)


# -----------------------------------------------------------------------------
# store contract
# -----------------------------------------------------------------------------
class TestLogContract:
    def test_protocol(self, log: Any) -> None:
        assert isinstance(log, TransitionLogStore)

    def test_append_read_seq(self, log: Any) -> None:
        assert log.next_seq("m") == 1
        log.append(rec(1))
        log.append(rec(2, event_payload={"n": [1, 2], "nested": {"a": None}}))
        log.append(rec(1, mid="other"))
        assert log.next_seq("m") == 3
        rows = log.read("m")
        assert [r.seq for r in rows] == [1, 2]
        assert rows[1].event_payload == {"n": [1, 2], "nested": {"a": None}}
        assert rows[0] == rec(1)  # full round-trip equality
        assert [r.seq for r in log.read("m", after_seq=1)] == [2]
        assert [r.seq for r in log.read("m", limit=1)] == [1]
        assert log.read("nobody") == []

    def test_purge_and_forget(self, log: Any) -> None:
        log.append(rec(1, ts=10))
        log.append(rec(2, ts=20))
        log.append(rec(1, mid="o", ts=30))
        assert log.purge_older_than(15) == 1
        assert [r.seq for r in log.read("m")] == [2]
        assert log.forget("o") == 1
        assert log.read("o") == []
        assert log.forget("o") == 0

    def test_record_json_round_trip(self) -> None:
        r = rec(
            7,
            actor="basil",
            reason="ok",
            correlation_id="c-1",
            disposition="denied",
            engine=True,
            error={"type": "X", "message": "y"},
        )
        back = TransitionRecord.from_dict(json.loads(json.dumps(r.to_dict())))
        assert back == r


# -----------------------------------------------------------------------------
# plugin
# -----------------------------------------------------------------------------
CFG = {
    "id": "appr",
    "initial": "draft",
    "context": {"n": 0, "password": "x"},
    "states": {
        "draft": {
            "on": {
                "SUBMIT": {"target": "review", "actions": "bump"},
                "NOPE": {"target": "review", "guard": "never"},
                "BOOM": {"actions": "boom"},
            }
        },
        "review": {
            "on": {"APPROVE": "approved", "REJECT": "draft"},
            "after": {"1000": "expired"},
        },
        "approved": {"type": "final"},
        "expired": {"type": "final"},
    },
}


def _bump(i: Any, c: Any, e: Any, a: Any) -> None:
    c["n"] += 1


def _boom(i: Any, c: Any, e: Any, a: Any) -> None:
    raise RuntimeError("boom")


def machine():
    return create_machine(
        CFG,
        logic=MachineLogic(
            actions={"bump": _bump, "boom": _boom},
            guards={"never": lambda c, e: False},
        ),
    )


class TestPluginSync:
    def test_records_transitions_and_non_transitions(self, log: Any) -> None:
        i = SyncInterpreter(machine()).use(TransitionLogPlugin(log)).start()
        i.send("NOPE")  # denied: declared in draft, guard says no
        i.send("SUBMIT", token="s3cret", note="hi")
        i.send("WHATEVER")  # unhandled (not declared; default onUnhandled)
        i.send("REJECT")
        i.send("BOOM", wait=True)
        i.stop()
        rows = log.read("appr")
        by_type = {r.event_type: r for r in rows}
        assert [r.seq for r in rows] == list(
            range(1, len(rows) + 1)
        )  # gap-free
        s = by_type["SUBMIT"]
        assert s.disposition == "transition"
        assert s.from_states == ("appr.draft",) and s.to_states == (
            "appr.review",
        )
        assert s.actions == ("bump",)
        assert s.event_payload == {"token": "***", "note": "hi"}  # redacted
        assert s.machine_version == "" and s.engine is False
        assert by_type["NOPE"].disposition == "denied"
        assert by_type["NOPE"].to_states == by_type["NOPE"].from_states
        assert by_type["WHATEVER"].disposition == "unhandled"
        assert by_type["REJECT"].disposition == "transition"
        b = by_type["BOOM"]
        assert b.disposition == "error" and b.error["type"] == "RuntimeError"

    def test_include_non_transitions_false(self, log: Any) -> None:
        i = (
            SyncInterpreter(machine())
            .use(TransitionLogPlugin(log, include_non_transitions=False))
            .start()
        )
        i.send("NOPE")
        i.send("SUBMIT")
        i.stop()
        assert [r.event_type for r in log.read("appr")] == ["SUBMIT"]

    def test_engine_events_after_timer(self, log: Any) -> None:
        clk = SimulatedClock()
        i = (
            SyncInterpreter(machine(), clock=clk)
            .use(TransitionLogPlugin(log))
            .start()
        )
        i.send("SUBMIT")
        clk.increment(1001)
        i.stop()
        rows = log.read("appr")
        assert rows[-1].engine is True
        assert rows[-1].event_type.startswith("after.")
        assert rows[-1].event_payload == {"kind": "after"}
        assert rows[-1].to_states == ("appr.expired",)

    def test_audit_fields_and_correlation(self, log: Any) -> None:
        i = SyncInterpreter(machine()).use(AuditPlugin(log)).start()
        i.send(
            "SUBMIT",
            actor="basil",
            reason="customer confirmed",
            correlation_id="req-1",
        )
        tok = correlation_id_var.set("req-2")
        try:
            i.send("REJECT", actor="ops")
        finally:
            correlation_id_var.reset(tok)
        i.send("SUBMIT")
        i.stop()
        a, b, c = log.read("appr")
        assert (a.actor, a.reason, a.correlation_id) == (
            "basil",
            "customer confirmed",
            "req-1",
        )
        assert (b.actor, b.reason, b.correlation_id) == ("ops", None, "req-2")
        assert (c.actor, c.reason, c.correlation_id) == (None, None, None)

    def test_custom_audit_keys(self, log: Any) -> None:
        i = (
            SyncInterpreter(machine())
            .use(AuditPlugin(log, actor_key="user", reason_key="why"))
            .start()
        )
        i.send("SUBMIT", user="u1", why="because")
        i.stop()
        r = log.read("appr")[0]
        assert (r.actor, r.reason) == ("u1", "because")

    def test_duplicate_disposition_with_idempotency(self, log: Any) -> None:
        i = (
            SyncInterpreter(machine())
            .use(IdempotencyPlugin(MemoryInbox(), principal=lambda e: "p"))
            .use(TransitionLogPlugin(log))
            .start()
        )
        i.send("SUBMIT", idempotency_key="e1")
        i.send("SUBMIT", idempotency_key="e1")  # short-circuited: never enters
        i.stop()
        rows = log.read("appr")
        # A short-circuited send fires no on_event_processed -> one row.
        assert [r.disposition for r in rows] == ["transition"]


class TestPluginAsync:
    def test_parity(self, log: Any) -> None:
        async def go() -> List[TransitionRecord]:
            i = await Interpreter(machine()).use(AuditPlugin(log)).start()
            await i.send("NOPE", wait=True)
            await i.send("SUBMIT", wait=True, actor="a")
            await i.send("APPROVE", wait=True, actor="b", reason="ok")
            await i.stop()
            return log.read("appr")

        rows = asyncio.run(go())
        assert [(r.event_type, r.disposition, r.actor) for r in rows] == [
            ("NOPE", "denied", None),
            ("SUBMIT", "transition", "a"),
            ("APPROVE", "transition", "b"),
        ]
        assert rows[-1].to_states == ("appr.approved",)


# -----------------------------------------------------------------------------
# replay
# -----------------------------------------------------------------------------
class TestReplay:
    def test_replay_reconstructs_state_and_context(self, log: Any) -> None:
        m = machine()
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        i.send("SUBMIT")
        i.send("REJECT")
        i.send("SUBMIT")
        i.send("NOPE")
        i.send("APPROVE")
        i.stop()
        r = replay(m, log.read("appr"))
        assert r.current_state_ids == {"appr.approved"}
        # context reconstructed by the *stubbed* actions? No -- stubs do not
        # mutate. Pass the real (idempotent) logic to rebuild context too.
        r2 = replay(m, log.read("appr"), logic=m.logic)
        assert r2.context["n"] == 2
        r.stop()
        r2.stop()

    def test_replay_keeps_real_guards_by_default(self, log: Any) -> None:
        """A denied event in the log must replay as denied: the real guard
        is kept even though actions/services are stubbed."""
        m = machine()
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        i.send("NOPE")  # denied by the real `never` guard
        i.send("SUBMIT")
        i.stop()
        r = replay(m, log.read("appr"))  # no logic= -> would diverge at 1
        assert r.current_state_ids == {"appr.review"}
        r.stop()

    def test_replay_upto(self, log: Any) -> None:
        m = machine()
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        i.send("SUBMIT")
        i.send("APPROVE")
        i.stop()
        r = replay(m, log.read("appr"), upto=1)
        assert r.current_state_ids == {"appr.review"}
        r.stop()

    def test_tampered_record_raises_divergence(self, log: Any) -> None:
        m = machine()
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        i.send("SUBMIT")
        i.send("APPROVE")
        i.stop()
        rows = log.read("appr")
        tampered = [
            rows[0],
            TransitionRecord(
                **{**rows[1].to_dict(), "to_states": ["appr.draft"]}
            ),
        ]
        with pytest.raises(ReplayDivergenceError) as ei:
            replay(m, tampered)
        assert ei.value.seq == 2
        assert ei.value.expected == ("appr.draft",)
        assert ei.value.actual == ("appr.approved",)
        # verify=False just rebuilds
        r = replay(m, tampered, verify=False)
        assert r.current_state_ids == {"appr.approved"}
        r.stop()

    def test_replay_after_timer(self, log: Any) -> None:
        m = machine()
        clk = SimulatedClock()
        i = SyncInterpreter(m, clock=clk).use(TransitionLogPlugin(log)).start()
        i.send("SUBMIT")
        clk.increment(1001)
        i.stop()
        r = replay(m, log.read("appr"))
        assert r.current_state_ids == {"appr.expired"}
        r.stop()

    def test_replay_corpus_with_service_completion(self, log: Any) -> None:
        """AdvancePayment: SUBMIT invokes a service whose recorded done
        event is replayed via a stub service, then RESET."""
        cfg = json.loads(CORPUS.read_text(encoding="utf-8"))
        m = create_machine(cfg, logic=stub_logic(cfg))
        i = SyncInterpreter(m).use(AuditPlugin(log)).start()
        i.send("SUBMIT", actor="basil", reason="customer confirmed")
        i.send("RESET", actor="ops")
        rows = log.read(i.id)
        assert [r.event_type for r in rows] == [
            "SUBMIT",
            "done.invoke.authenticate-payment",
            "RESET",
        ]
        assert rows[1].engine and rows[1].event_payload["kind"] == "done"
        r = replay(m, rows)
        assert r.current_state_ids == i.current_state_ids
        i.stop()
        r.stop()

    def test_replay_does_not_run_real_actions(self, log: Any) -> None:
        calls = {"n": 0}

        def side_effect(i: Any, c: Any, e: Any, a: Any) -> None:
            calls["n"] += 1

        m = create_machine(
            CFG,
            logic=MachineLogic(
                actions={"bump": side_effect, "boom": _boom},
                guards={"never": lambda c, e: False},
            ),
        )
        i = SyncInterpreter(m).use(TransitionLogPlugin(log)).start()
        i.send("SUBMIT")
        i.stop()
        assert calls["n"] == 1
        replay(m, log.read("appr")).stop()
        assert calls["n"] == 1  # stubbed: the side effect did not repeat
        assert (
            m.logic.actions["bump"] is side_effect
        )  # caller's machine untouched


class TestWithPersisted:
    def test_log_key_is_store_key_and_shares_sqlite(
        self, tmp_path: Any
    ) -> None:
        store = SQLiteStore(tmp_path / "app.db")
        log = SQLiteLog(store)
        m = machine()
        plugin = AuditPlugin(log)
        with persisted(store, "appr:42", m, plugins=[plugin]) as i:
            i.send("SUBMIT", actor="basil")
        with persisted(store, "appr:42", m, plugins=[plugin]) as i:
            i.send("APPROVE", actor="ops", reason="lgtm")
        rows = log.read("appr:42")
        assert [(r.seq, r.event_type, r.actor) for r in rows] == [
            (1, "SUBMIT", "basil"),
            (2, "APPROVE", "ops"),
        ]
        assert log.read("appr") == []
        store.close()
