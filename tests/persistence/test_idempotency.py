# tests/persistence/test_idempotency.py
"""#261: `IdempotencyPlugin` + inbox backends -- dedup before the machine
sees the event, scoped by principal, fingerprinted, crash-consistent."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from typing import Any, Dict, Iterator, List

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.persistence import (
    DEFAULT_TTL_S,
    IdempotencyInFlightError,
    IdempotencyMismatchError,
    IdempotencyPlugin,
    InboxStore,
    MemoryInbox,
    MemoryStore,
    PessimisticLock,
    SQLiteInbox,
    SQLiteStore,
    default_key,
    fingerprint,
    persisted,
)
from src.xstate_statemachine.persistence.idempotency import (
    PROCESSED_RING_SIZE,
    validate_idempotency_key,
)

INBOX_FACTORIES = {
    "memory": lambda tmp: MemoryInbox(),
    "sqlite": lambda tmp: SQLiteInbox(tmp / "inbox.db"),
}


@pytest.fixture(params=sorted(INBOX_FACTORIES))
def inbox(request: Any, tmp_path: Any) -> Iterator[Any]:
    ib = INBOX_FACTORIES[request.param](tmp_path)
    yield ib
    if hasattr(ib, "close"):
        ib.close()


CFG = {
    "id": "wallet",
    "initial": "open",
    "context": {"credits": 0},
    "states": {
        "open": {
            "on": {
                "CREDIT": {"actions": "add"},
                "CLOSE": "closed",
                "BOOM": {"actions": "boom"},
            }
        },
        "closed": {"type": "final"},
    },
}


def _add(i: Any, c: Any, e: Any, a: Any) -> None:
    c["credits"] += e.payload["amount"]


def _boom(i: Any, c: Any, e: Any, a: Any) -> None:
    raise RuntimeError("boom")


def machine():
    return create_machine(
        CFG, logic=MachineLogic(actions={"add": _add, "boom": _boom})
    )


def plugin(inbox: Any, **kw: Any) -> IdempotencyPlugin:
    kw.setdefault("principal", lambda e: "acct_1")
    return IdempotencyPlugin(inbox, **kw)


# -----------------------------------------------------------------------------
# inbox contract
# -----------------------------------------------------------------------------
class TestInboxContract:
    def test_protocol(self, inbox: Any) -> None:
        assert isinstance(inbox, InboxStore)

    def test_claim_mark_get(self, inbox: Any) -> None:
        assert inbox.get("s", "k") is None
        assert inbox.claim("s", "k", "fp", ttl_s=None) is True
        assert inbox.claim("s", "k", "fp", ttl_s=None) is False  # in flight
        e = inbox.get("s", "k")
        assert e.fingerprint == "fp" and e.receipt_json is None
        inbox.mark("s", "k", '{"x":1}', ttl_s=None)
        e = inbox.get("s", "k")
        assert e.receipt_json == '{"x":1}' and e.expires_at is None

    def test_release_only_drops_in_flight(self, inbox: Any) -> None:
        inbox.claim("s", "k", "fp", ttl_s=None)
        inbox.release("s", "k")
        assert inbox.get("s", "k") is None
        inbox.claim("s", "k", "fp", ttl_s=None)
        inbox.mark("s", "k", "{}", ttl_s=None)
        inbox.release("s", "k")  # marked: no-op
        assert inbox.get("s", "k") is not None

    def test_ttl_expiry_and_purge(self, inbox: Any) -> None:
        inbox.claim("s", "old", "fp", ttl_s=0.01)
        inbox.mark("s", "old", "{}", ttl_s=0.01)
        inbox.claim("s", "new", "fp", ttl_s=1000)
        inbox.mark("s", "new", "{}", ttl_s=1000)
        time.sleep(0.03)
        assert inbox.get("s", "old") is None  # expired reads as unseen
        assert inbox.claim("s", "old", "fp2", ttl_s=None) is True  # re-admit
        inbox.mark("s", "old", "{}", ttl_s=0.01)
        time.sleep(0.03)
        assert inbox.purge_expired() == 1
        assert inbox.purge_expired() == 0
        assert inbox.get("s", "new") is not None

    def test_scopes_isolate_and_forget(self, inbox: Any) -> None:
        for scope in ("a/m/1", "a/m/2", "b/m/1"):
            inbox.claim(scope, "k", "fp", ttl_s=None)
            inbox.mark(scope, "k", "{}", ttl_s=None)
        assert inbox.forget("a/m/1") == 1
        assert inbox.get("a/m/1", "k") is None
        assert inbox.get("a/m/2", "k") is not None
        assert inbox.get("b/m/1", "k") is not None

    def test_claim_is_atomic_across_threads(self, inbox: Any) -> None:
        winners: List[int] = []
        barrier = threading.Barrier(8)

        def w(n: int) -> None:
            barrier.wait()
            if inbox.claim("s", "race", "fp", ttl_s=None):
                winners.append(n)

        ts = [threading.Thread(target=w, args=(n,)) for n in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert len(winners) == 1


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------
class TestHelpers:
    def test_default_key(self) -> None:
        from src.xstate_statemachine import Event

        assert default_key(Event("X", {"idempotency_key": "a"})) == "a"
        assert default_key(Event("X", {"id": 7})) == "7"
        assert (
            default_key(Event("X", {"idempotency_key": "a", "id": 7})) == "a"
        )
        assert default_key(Event("X")) is None

    def test_fingerprint_ignores_key_and_order(self) -> None:
        from src.xstate_statemachine import Event

        a = fingerprint(Event("X", {"idempotency_key": "k1", "b": 1, "a": 2}))
        b = fingerprint(Event("X", {"a": 2, "b": 1, "idempotency_key": "k2"}))
        c = fingerprint(Event("X", {"a": 2, "b": 99}))
        d = fingerprint(Event("Y", {"a": 2, "b": 1}))
        assert a == b and a != c and a != d

    def test_validate_key(self) -> None:
        assert validate_idempotency_key("evt_1") == "evt_1"
        for bad in ("", "x" * 256, "tab\there", "ünïcode", 5):
            with pytest.raises(ValueError):
                validate_idempotency_key(bad)


# -----------------------------------------------------------------------------
# plugin behaviour, both engines
# -----------------------------------------------------------------------------
class TestPluginSync:
    def test_duplicate_returns_original_receipt(self, inbox: Any) -> None:
        i = SyncInterpreter(machine()).use(plugin(inbox)).start()
        r1 = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=10)
        r2 = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=10)
        assert i.context["credits"] == 10  # exactly once
        assert not r1.duplicate and r1.changed
        assert r2.duplicate and r2.changed  # ORIGINAL outcome, flagged
        assert r2.state_ids == r1.state_ids
        # a different key is a new delivery
        i.send("CREDIT", idempotency_key="evt_2", amount=5)
        assert i.context["credits"] == 15
        i.stop()

    def test_no_key_is_not_deduplicated(self, inbox: Any) -> None:
        i = SyncInterpreter(machine()).use(plugin(inbox)).start()
        i.send("CREDIT", amount=1)
        i.send("CREDIT", amount=1)
        assert i.context["credits"] == 2
        i.stop()

    def test_mismatch_is_422_refusal_receipt(self, inbox: Any) -> None:
        from src.xstate_statemachine import receipt_to_status

        i = SyncInterpreter(machine()).use(plugin(inbox)).start()
        i.send("CREDIT", idempotency_key="evt_1", amount=10)
        r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=99)
        assert isinstance(r.error, IdempotencyMismatchError)
        assert r.error.key == "evt_1" and r.duplicate and not r.changed
        assert receipt_to_status(r) == 422
        assert i.context["credits"] == 10  # the machine never saw it
        i.stop()

    def test_in_flight_is_409_refusal_receipt(self, inbox: Any) -> None:
        from src.xstate_statemachine import Event, receipt_to_status

        i = SyncInterpreter(machine()).use(plugin(inbox)).start()
        scope = "acct_1/wallet/wallet"
        fp = fingerprint(
            Event("CREDIT", {"idempotency_key": "evt_1", "amount": 1})
        )
        inbox.claim(scope, "evt_1", fp, ttl_s=None)  # another worker holds it
        r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=1)
        assert isinstance(r.error, IdempotencyInFlightError)
        assert receipt_to_status(r) == 409
        assert i.context["credits"] == 0
        i.stop()

    def test_refusal_survives_json_codec(self, inbox: Any) -> None:
        from src.xstate_statemachine import (
            receipt_from_json,
            receipt_to_json,
            receipt_to_status,
        )

        i = SyncInterpreter(machine()).use(plugin(inbox)).start()
        i.send("CREDIT", idempotency_key="evt_1", amount=10)
        r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=99)
        back = receipt_from_json(json.loads(json.dumps(receipt_to_json(r))))
        assert receipt_to_status(back) == 422  # matched by class NAME
        i.stop()

    def test_principal_scopes_keys(self, inbox: Any) -> None:
        p = IdempotencyPlugin(inbox, principal=lambda e: e.payload["tenant"])
        i = SyncInterpreter(machine()).use(p).start()
        i.send("CREDIT", idempotency_key="evt_1", amount=1, tenant="A")
        i.send("CREDIT", idempotency_key="evt_1", amount=1, tenant="B")
        r = i.send(
            "CREDIT", wait=True, idempotency_key="evt_1", amount=1, tenant="A"
        )
        assert i.context["credits"] == 2 and r.duplicate
        i.stop()

    def test_invalid_key_is_refused(self, inbox: Any) -> None:
        i = SyncInterpreter(machine()).use(plugin(inbox)).start()
        r = i.send("CREDIT", wait=True, idempotency_key="x" * 300, amount=1)
        assert isinstance(r.error, ValueError) and r.duplicate
        assert i.context["credits"] == 0
        i.stop()

    def test_failed_delivery_releases_claim(self, inbox: Any) -> None:
        cfg = dict(CFG, actionErrorPolicy="rollback")
        m = create_machine(
            cfg, logic=MachineLogic(actions={"add": _add, "boom": _boom})
        )
        i = SyncInterpreter(m).use(plugin(inbox)).start()
        r = i.send("BOOM", wait=True, idempotency_key="evt_1")
        assert r.error is not None and not r.changed
        # released: a retry is admitted, not answered from the inbox
        r2 = i.send("BOOM", wait=True, idempotency_key="evt_1")
        assert r2.error is not None and not r2.duplicate
        i.stop()

    def test_ttl_expiry_readmits(self, inbox: Any) -> None:
        i = SyncInterpreter(machine()).use(plugin(inbox, ttl_s=0.02)).start()
        i.send("CREDIT", idempotency_key="evt_1", amount=1)
        time.sleep(0.05)
        r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=1)
        assert not r.duplicate and i.context["credits"] == 2
        i.stop()

    def test_stop_releases_pending(self, inbox: Any) -> None:
        # A claim whose event never finished must not wedge the key.
        p = plugin(inbox)
        i = SyncInterpreter(machine()).use(p).start()
        p._pending[123] = ("acct_1/wallet/wallet", "orphan")
        inbox.claim("acct_1/wallet/wallet", "orphan", "fp", ttl_s=None)
        i.stop()
        assert inbox.get("acct_1/wallet/wallet", "orphan") is None

    def test_default_ttl_is_seven_days(self) -> None:
        assert DEFAULT_TTL_S == 7 * 86_400


class TestPluginAsync:
    def test_parity(self, inbox: Any) -> None:
        async def go() -> Dict[str, Any]:
            i = await Interpreter(machine()).use(plugin(inbox)).start()
            r1 = await i.send(
                "CREDIT", wait=True, idempotency_key="evt_1", amount=10
            )
            r2 = await i.send(
                "CREDIT", wait=True, idempotency_key="evt_1", amount=10
            )
            r3 = await i.send(
                "CREDIT", wait=True, idempotency_key="evt_1", amount=1
            )
            credits = i.context["credits"]
            await i.stop()
            return {
                "c": credits,
                "d1": r1.duplicate,
                "d2": r2.duplicate,
                "ch2": r2.changed,
                "mismatch": isinstance(r3.error, IdempotencyMismatchError),
            }

        assert asyncio.run(go()) == {
            "c": 10,
            "d1": False,
            "d2": True,
            "ch2": True,
            "mismatch": True,
        }


# -----------------------------------------------------------------------------
# inside persisted(): crash-consistency
# -----------------------------------------------------------------------------
class TestWithPersisted:
    def test_dedup_across_hydrations(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        inbox = SQLiteInbox(store)  # shared backend
        m = machine()
        p = plugin(inbox)
        with persisted(store, "w1", m, plugins=[p]) as i:
            i.send("CREDIT", idempotency_key="evt_1", amount=10)
        with persisted(store, "w1", m, plugins=[p]) as i:
            r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=10)
            assert r.duplicate and i.context["credits"] == 10
        # the ring travelled inside the snapshot
        snap = json.loads(store.load("w1").snapshot)
        assert snap["context"]["__xsm_processed_ids__"] == [
            "acct_1/wallet/w1|evt_1"
        ]
        store.close()

    def test_crash_before_save_leaves_no_mark(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        inbox = SQLiteInbox(store)
        m = machine()
        p = plugin(inbox)
        with pytest.raises(RuntimeError):
            with persisted(store, "w1", m, plugins=[p]) as i:
                i.send("CREDIT", idempotency_key="evt_1", amount=10)
                raise RuntimeError("crash before save")
        assert store.load("w1") is None
        assert inbox.get("acct_1/wallet/w1", "evt_1") is None  # claim released
        # the retry is a first delivery
        with persisted(store, "w1", m, plugins=[p]) as i:
            r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=10)
            assert not r.duplicate
        store.close()

    def test_crash_between_save_and_mark_caught_by_ring(self, tmp_path: Any):
        store = SQLiteStore(tmp_path / "s.db")
        inbox = MemoryInbox()  # NOT shared: save-then-mark path
        m = machine()
        p = plugin(inbox)
        # Simulate: snapshot saved, process died before the mark.
        flushed = {"n": 0}
        real_flush = p.flush_marks

        def dying_flush() -> int:
            flushed["n"] += 1
            p._buffered.clear()  # marks lost; the claim stays in flight
            return 0

        p.flush_marks = dying_flush  # type: ignore[method-assign]
        with persisted(store, "w1", m, plugins=[p]) as i:
            i.send("CREDIT", idempotency_key="evt_1", amount=10)
        assert flushed["n"] == 1
        # The process "died" with the claim still in flight (no receipt).
        entry = inbox.get("acct_1/wallet/w1", "evt_1")
        assert entry is not None and entry.receipt_json is None
        p.flush_marks = real_flush  # type: ignore[method-assign]
        # Redelivery: in-flight per the inbox, PROCESSED per the snapshot's
        # ring -> the crash window; answered as a duplicate and repaired.
        with persisted(store, "w1", m, plugins=[p]) as i:
            r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=10)
            assert r.duplicate and i.context["credits"] == 10
        assert inbox.get("acct_1/wallet/w1", "evt_1").receipt_json is not None
        store.close()

    def test_crash_after_mark_is_plain_duplicate(self, tmp_path: Any) -> None:
        store = SQLiteStore(tmp_path / "s.db")
        inbox = SQLiteInbox(store)
        m = machine()
        p = plugin(inbox)
        with persisted(store, "w1", m, plugins=[p]) as i:
            i.send("CREDIT", idempotency_key="evt_1", amount=10)
        # "crash after mark": nothing to recover; a redelivery is a dup.
        with persisted(store, "w1", m, plugins=[p]) as i:
            r = i.send("CREDIT", wait=True, idempotency_key="evt_1", amount=10)
            assert r.duplicate and r.changed
        store.close()

    def test_shared_backend_commits_mark_in_lock_transaction(self, tmp_path):
        """With PessimisticLock on SQLite the lock IS the transaction: a
        save failure (simulated by a conflict) must leave no mark."""
        store = SQLiteStore(tmp_path / "s.db")
        inbox = SQLiteInbox(store)
        m = machine()
        p = plugin(inbox)
        with persisted(store, "w1", m, plugins=[p]):
            pass
        from src.xstate_statemachine.persistence import ConflictError

        with pytest.raises(ConflictError):
            with persisted(
                store, "w1", m, plugins=[p], lock=PessimisticLock()
            ) as i:
                i.send("CREDIT", idempotency_key="evt_1", amount=10)
                # a writer that bypassed the lock -> fenced save fails
                store.save("w1", store.load("w1").snapshot)
        assert inbox.get("acct_1/wallet/w1", "evt_1") is None
        store.close()

    def test_ring_is_bounded(self, tmp_path: Any) -> None:
        store = MemoryStore()
        inbox = MemoryInbox()
        m = machine()
        p = plugin(inbox)
        with persisted(store, "w1", m, plugins=[p]) as i:
            for n in range(PROCESSED_RING_SIZE + 10):
                i.send("CREDIT", idempotency_key=f"evt_{n}", amount=1)
        ring = json.loads(store.load("w1").snapshot)["context"][
            "__xsm_processed_ids__"
        ]
        assert len(ring) == PROCESSED_RING_SIZE
        assert ring[-1].endswith(f"|evt_{PROCESSED_RING_SIZE + 9}")
