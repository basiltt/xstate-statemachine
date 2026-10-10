# tests/recipes/test_battle_308_a.py
"""#308 battle (A): correctness / security / concurrency of the recipes
as a user would copy them. "Fixed:" tests were 500s / wrong behaviour
before; "Held:" tests pin behaviour that is correct or documented."""

from __future__ import annotations

import json
import threading
import time
import warnings
from collections import Counter
from typing import Any, List

import pytest

from .conftest import load_recipe

sw = load_recipe("stripe_webhooks", "stripe_webhooks")
sf = load_recipe("slot_filling", "slot_filling")
ro = load_recipe("feature_flag_rollout", "rollout")
ws = load_recipe("websocket_reconnect", "ws_reconnect")
qw = load_recipe("task_queue_workers", "queue_workers")

SECRET = "whsec_battle_a"
NOW = 1_700_000_000


def _body(eid: str = "evt_1", kind: str = "invoice.paid", **obj: Any) -> bytes:
    o = {"id": "in_1", "subscription": "sub_1", **obj}
    event = {"id": eid, "type": kind, "data": {"object": o}}
    return json.dumps(event).encode()


def _deliver(store: Any, inbox: Any, body: bytes, header: Any = None) -> Any:
    return sw.handle_webhook(
        body,
        header if header is not None else sw.sign(body, SECRET, NOW),
        secret=SECRET,
        store=store,
        inbox=inbox,
        machine=sw.build_machine(),
        now=NOW,
    )


@pytest.fixture
def mem() -> Any:
    from xstate_statemachine.persistence import MemoryInbox, MemoryStore

    return MemoryStore(), MemoryInbox()


# ---------------------------------------------------------------- Stripe --
class TestStripeSignature:
    @pytest.mark.parametrize(
        "header",
        [
            "t=1700000000,v1=éé",  # Fixed: TypeError -> 500
            "t=" + "9" * 400 + ",v1=aa",  # Fixed: OverflowError -> 500
            "t=-1700000000,v1=aa",
            "t=1e9,v1=aa",
            "t=nan,v1=aa",
            "t= 1700000000 ,v1=" + "0" * 64,
            "t=1700000000,v1=",
            "t=1700000000,v1=zz",
            "t=1700000000,v1=" + "a" * 10_000,
        ],
    )
    def test_hostile_header_is_400_never_500(self, mem: Any, header: str):
        status, payload = _deliver(*mem, _body(), header)
        assert status == 400
        assert payload["error"] == "invalid_signature"

    def test_leading_plus_and_spaces_still_verify(self) -> None:
        # Held: int() accepts "+N"; the HMAC is over the CANONICAL int,
        # so "+N" verifies only with the MAC Stripe made for "N" -- the
        # attacker gains nothing they did not already have.
        body = _body()
        good = sw.sign(body, SECRET, NOW)
        v1 = good.split("v1=")[1]
        sw.verify_signature(body, f"t=+{NOW},v1={v1}", SECRET, now=NOW)
        # whitespace around the item is stripped by design
        sw.verify_signature(body, f" t={NOW} , v1={v1} ", SECRET, now=NOW)

    def test_duplicate_t_uses_the_first(self) -> None:
        body = _body()
        v1 = sw.sign(body, SECRET, NOW).split("v1=")[1]
        sw.verify_signature(body, f"t={NOW},t=1,v1={v1}", SECRET, now=NOW)
        with pytest.raises(sw.SignatureError):
            sw.verify_signature(
                body, f"t=1,t={NOW},v1={v1}", SECRET, now=NOW
            )

    @pytest.mark.parametrize("tol", [0, -1])
    def test_zero_or_negative_tolerance(self, tol: int) -> None:
        body = _body()
        h = sw.sign(body, SECRET, NOW)
        if tol == 0:
            assert sw.verify_signature(body, h, SECRET, now=NOW, tolerance_s=0)
        else:  # Held: negative tolerance rejects everything (fail closed)
            with pytest.raises(sw.SignatureError):
                sw.verify_signature(body, h, SECRET, now=NOW, tolerance_s=tol)

    def test_every_v1_candidate_is_compared(self, monkeypatch: Any) -> None:
        # The compare is per candidate and never short-circuits on length.
        seen: List[Any] = []
        real = sw.hmac.compare_digest

        def spy(a: Any, b: Any) -> bool:
            seen.append((len(a), len(b)))
            return bool(real(a, b))

        monkeypatch.setattr(sw.hmac, "compare_digest", spy)
        body = _body()
        with pytest.raises(sw.SignatureError):
            sw.verify_signature(
                body, f"t={NOW},v1=ab,v1={'c' * 64},v1=", SECRET, now=NOW
            )
        assert [b for _, b in seen] == [2, 64, 0]

    def test_nul_bytes_in_body(self, mem: Any) -> None:
        body = b'{"id":"evt\\u0000","type":"x"}\x00'
        assert _deliver(*mem, body)[0] == 400  # not JSON -> 400


class TestStripeEventShape:
    @pytest.mark.parametrize("kind", [7, ["invoice.paid"], {"a": 1}, None])
    def test_non_str_type_is_ignored_200(self, mem: Any, kind: Any) -> None:
        body = json.dumps({"id": "e", "type": kind}).encode()
        assert _deliver(*mem, body)[0] == 200

    def test_expanded_subscription_object_uses_its_id(self, mem: Any):
        # Fixed: key was "subscription.{'id': 'sub_9', ...}".
        store, inbox = mem
        body = _body(subscription={"id": "sub_9", "object": "subscription"})
        assert _deliver(store, inbox, body)[0] == 200
        m = sw.build_machine()
        with sw.persisted(store, "subscription.sub_9", m) as s:
            assert s.value == "active"

    @pytest.mark.parametrize("sub", [7, ["sub_1"], {"no": "id"}])
    def test_junk_subscription_is_400_or_falls_back(self, mem: Any, sub):
        status, _ = _deliver(*mem, _body(subscription=sub))
        assert status in (200, 400) and status != 500
        if isinstance(sub, (int, list)):
            assert status == 400

    @pytest.mark.parametrize("eid", ["e" * 256, "e" * 10_000, "evt_é"])
    def test_inbox_refused_event_id_is_400(self, mem: Any, eid: str):
        # Fixed: a REJECTED receipt -> 500 -> Stripe retries for days.
        status, payload = _deliver(*mem, _body(eid=eid))
        assert status == 400 and payload["error"] == "invalid_event"

    def test_255_char_event_id_is_accepted(self, mem: Any) -> None:
        assert _deliver(*mem, _body(eid="e" * 255))[0] == 200

    def test_same_event_id_two_subscriptions(self, mem: Any) -> None:
        # Held (for the integrator): the inbox scope includes the store
        # key, so a re-signed evt_1 aimed at another subscription is a
        # NEW delivery there. Only a leaked secret can produce it.
        store, inbox = mem
        assert _deliver(store, inbox, _body(subscription="sub_A"))[1][
            "duplicate"
        ] is False
        r = _deliver(store, inbox, _body(subscription="sub_B"))[1]
        assert r["duplicate"] is False and r["state"] == "active"

    def test_tampered_subscription_breaks_signature(self, mem: Any) -> None:
        good = _body(subscription="sub_A")
        header = sw.sign(good, SECRET, NOW)
        evil = _body(subscription="sub_B")
        assert _deliver(*mem, evil, header)[0] == 400


class TestStripeConcurrency:
    def test_default_busy_timeout_never_500(self, tmp_path: Any) -> None:
        # 16 threads x 5 rounds, DEFAULT SQLiteStore settings: every
        # outcome is 200 or 409 -- no "database is locked" 500.
        from xstate_statemachine.persistence import MemoryInbox, SQLiteStore

        store, inbox = SQLiteStore(str(tmp_path / "s.db")), MemoryInbox()
        out: List[Any] = []

        def go(n: int) -> None:
            body = _body(f"evt_{n}", "invoice.payment_failed")
            try:
                out.append(_deliver(store, inbox, body)[0])
            except Exception as exc:  # pragma: no cover - the defect
                out.append(repr(exc))

        for r in range(5):
            ts = [
                threading.Thread(target=go, args=(r * 16 + k,))
                for k in range(16)
            ]
            [t.start() for t in ts]
            [t.join() for t in ts]
        assert set(Counter(out)) <= {200, 409}, Counter(out)
        assert out.count(200) >= 5


# ----------------------------------------------------------- Slot filling --
class TestSlots:
    @pytest.mark.parametrize(
        "value, ok",
        [
            (float("inf"), False),
            (float("nan"), False),
            (10**8, True),
            (10**9, False),
            (" " * 200 + "x", True),  # Held: length is measured stripped
            ("Ann‮gro", False),  # Fixed: bidi override
            ("A​nn", False),  # Fixed: zero-width space
            ("A\x00nn", False),  # Fixed: NUL
            ("Zoë", True),
            ("שרה", True),  # plain RTL text is fine
        ],
    )
    def test_valid_slot_value(self, value: Any, ok: bool) -> None:
        assert sf.valid_slot_value(value) is ok

    def test_minus_zero_is_held(self) -> None:
        # Held: -0.0 is a number < 10**9; range checks are the app's job.
        assert sf.valid_slot_value(-0.0)

    def _bot(self) -> Any:
        from xstate_statemachine import SimulatedClock, SyncInterpreter

        out: List[str] = []
        c = SimulatedClock()
        i = SyncInterpreter(sf.build_machine(out.append), clock=c).start()
        return i, c, out

    def test_injected_name_never_reaches_the_prompt(self) -> None:
        i, _, out = self._bot()
        i.send("USER_SAID", date="fri", party_size=2, name="‮evil")
        assert i.value == "collecting"
        assert not any("‮" in line for line in out)
        i.stop()

    def test_slots_key_and_yes_while_collecting(self) -> None:
        i, _, _ = self._bot()
        i.send("USER_SAID", slots={"date": "x"}, nudges=-99)
        assert i.context["slots"]["date"] is None
        assert i.context["nudges"] == 0
        r = i.send("YES", wait=True)
        assert not r.changed and i.value == "collecting"
        i.stop()

    def test_empty_turns_reset_the_silence_timer(self) -> None:
        # Held (documented: "each USER_SAID restarts the 30 s timer"): a
        # user who keeps sending empty turns is never nudged.
        i, c, out = self._bot()
        for _ in range(10):
            c.increment(29_000)
            i.send("USER_SAID")
        assert i.value == "collecting"
        assert not any(o.startswith("Still there") for o in out)
        i.stop()

    def test_max_nudges_boundary(self) -> None:
        i, c, out = self._bot()
        for _ in range(sf.MAX_NUDGES):
            c.increment(30_000)
            assert i.value == "collecting"
        c.increment(30_000)
        assert i.value == "abandoned"
        assert sum(o.startswith("Still there") for o in out) == sf.MAX_NUDGES
        i.stop()

    def test_10k_turns_context_stays_small(self) -> None:
        i, _, _ = self._bot()
        for n in range(10_000):
            i.send("USER_SAID", date=f"d{n}", junk="x" * 100)
        assert len(json.dumps(i.context)) < 300
        i.stop()


# ----------------------------------------------------------- Feature flag --
def _rollout(apply: Any = None, metrics: Any = None) -> Any:
    from xstate_statemachine import SimulatedClock, SyncInterpreter

    c = SimulatedClock()
    m = ro.build_machine(
        metrics or (lambda: {"error_rate": 0.0, "p99_ms": 1.0}),
        apply or (lambda f, p: None),
    )
    return SyncInterpreter(m, clock=c).start(), c, m


class TestRollout:
    def test_apply_failure_does_not_record_exposure(self) -> None:
        # Fixed: ctx["percent"] said 0.1 although apply_percent raised.
        def boom(flag: str, pct: float) -> None:
            if pct:
                raise RuntimeError("flag API down")

        i, _, _ = _rollout(boom)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            i.send("START")
        assert i.value == {"exposed": "internal"}
        assert i.context["percent"] == 0.0  # the truth: nothing applied
        assert i.context["history"] == [0.0]
        i.stop()

    def test_metrics_extra_keys_ignored(self) -> None:
        big = {"error_rate": 0.0, "p99_ms": 1.0, "x" * 1000: 1.0}
        assert ro.healthy(big)
        assert not ro.healthy({"junk": 0.0})  # missing -> unhealthy

    @pytest.mark.parametrize("state", ["disabled", "rolled_back"])
    def test_metrics_bad_outside_exposed_is_no_op(self, state: str) -> None:
        i, _, _ = _rollout()
        if state == "rolled_back":
            i.send("START")
            i.send("ROLLBACK")
        r = i.send("METRICS_BAD", wait=True)
        assert not r.changed and i.value == state
        i.stop()

    def test_history_grows_per_cycle(self) -> None:
        # Held (for the integrator): `history` is unbounded -- 3 entries
        # per START/ROLLBACK/RETRY cycle. Bound it if you loop forever.
        i, _, _ = _rollout()
        for _ in range(100):
            i.send("START")
            i.send("ROLLBACK")
            i.send("RETRY")
        assert len(i.context["history"]) == 1 + 300
        i.stop()

    def test_restart_mid_bake_keeps_the_deadline(self) -> None:
        # Held: a restored interpreter does NOT re-arm the bake timer by
        # itself; the absolute deadline is in the snapshot for
        # `DueTimerScanner` (the recipe says: persist + scanner).
        i, c, m = _rollout()
        i.send("START")
        c.increment(1_800_000)
        snap = json.loads(i.get_snapshot())
        i.stop()
        (d,) = snap["deadlines"]
        assert d["delay_ms"] == 3_600_000
        assert d["event_type"].startswith("after.3600000.")


# -------------------------------------------------------------- WebSocket --
class _Client:
    def __init__(self, fail_close: bool = False) -> None:
        self.fail_close = fail_close
        self.on_message: Any = None
        self.closed = 0

    def connect(self) -> None:
        pass

    def close(self) -> None:
        self.closed += 1
        if self.fail_close:
            raise OSError("close failed")


class TestWebSocket:
    def _sock(self, **kw: Any) -> Any:
        from xstate_statemachine import SyncInterpreter

        made: List[_Client] = []
        fail = kw.pop("fail_close", False)

        def factory() -> _Client:
            made.append(_Client(fail))
            return made[-1]

        i = SyncInterpreter(ws.build_machine(factory, **kw)).start()
        i.send("CONNECT")
        deadline = time.monotonic() + 5
        while i.value != "connected" and time.monotonic() < deadline:
            time.sleep(0.01)
        return i, made

    def test_raising_on_message_still_counts(self) -> None:
        i, made = self._sock(on_message=lambda m: 1 / 0)
        made[0].on_message("hi")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            i.send("NOOP")  # send_back is a mailbox: drained on send()
        assert i.context["received"] == 1 and i.value == "connected"
        i.stop()

    def test_raising_close_still_leaves_connected(self) -> None:
        i, made = self._sock(fail_close=True)
        i.send("DISCONNECT")
        assert i.value == "disconnected" and made[0].closed == 1
        i.stop()

    def test_message_after_disconnect_is_dropped(self) -> None:
        got: List[Any] = []
        i, made = self._sock(on_message=got.append)
        i.send("DISCONNECT")
        made[0].on_message("late")
        i.send("NOOP")
        assert got == [] and i.context["received"] == 0
        i.stop()

    def test_full_jitter_zero_delay_is_allowed(self) -> None:
        from xstate_statemachine.patterns import RetryPolicy

        p = RetryPolicy(
            max_attempts=3, base_ms=100, jitter="full", rng=lambda: 0.0
        )
        assert p.delay_ms(1) == 0


# ------------------------------------------------------------ Queue loop --
class TestQueueRetry:
    def test_permanent_conflict_is_bounded(self, monkeypatch: Any) -> None:
        calls = []

        class Always:
            def __enter__(self) -> Any:
                calls.append(1)
                raise qw.ConflictError("k", 1, 2)

            def __exit__(self, *a: Any) -> None:
                return None

        monkeypatch.setattr(qw, "persisted", lambda *a, **k: Always())
        with pytest.raises(qw.ConflictError):
            qw.apply_event("k", "E")
        assert len(calls) == qw.RETRIES + 1
