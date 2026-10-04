# tests/contrib/redis/test_battle_306_inbox_log.py
"""Battle #306 (agent B): `RedisInbox` and `RedisLog` under attack.

Every test here failed on the shipped 0.11.0 layout; each names the
failure it pins. Runs on fakeredis by default and on a live server with
``XSM_REDIS_URL`` (both are part of the definition of done)."""

from __future__ import annotations

import os
import threading
import time
import uuid
from typing import Any, List

import pytest

from tests.persistence.test_idempotency import machine, plugin
from tests.persistence.test_log import rec

from ..conftest import requires_extra

pytestmark = requires_extra("redis")


def _inbox(r: Any, prefix: str) -> Any:
    from src.xstate_statemachine.contrib.redis import RedisInbox

    return RedisInbox(r, prefix=prefix)


def _log(r: Any, prefix: str, **kw: Any) -> Any:
    from src.xstate_statemachine.contrib.redis import RedisLog

    return RedisLog(r, prefix=prefix, **kw)


# =============================================================================
# 1. RedisInbox
# =============================================================================
class TestInboxClaim:
    def test_64_threads_one_claim(self, r: Any, prefix: str) -> None:
        ib = _inbox(r, prefix)
        wins: List[bool] = []
        go = threading.Barrier(64)

        def one() -> None:
            go.wait()
            wins.append(ib.claim("s", "k", "fp", ttl_s=60))

        ts = [threading.Thread(target=one) for _ in range(64)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        assert sum(wins) == 1

    def test_dead_claimer_is_readmitted_after_its_ttl(
        self, r: Any, prefix: str
    ) -> None:
        """X0.3: claimed, never marked (process died) -> the in-flight
        claim carries the plugin's TTL and then admits the retry, exactly
        like `SQLiteInbox` / `MemoryInbox`."""
        ib = _inbox(r, prefix)
        assert ib.claim("s", "k", "fp", ttl_s=0.2)
        assert ib.claim("s", "k", "fp", ttl_s=0.2) is False  # in flight
        assert ib.get("s", "k").receipt_json is None
        time.sleep(0.4)
        assert ib.get("s", "k") is None
        assert ib.claim("s", "k", "fp2", ttl_s=60) is True

    def test_skewed_client_clock_cannot_readmit_a_live_key(
        self, r: Any, prefix: str, monkeypatch: Any
    ) -> None:
        """🐛 Expiry used the CALLER's `time.time()`: a host five minutes
        slow wrote an expiry already in the past for everyone else, and
        the next host re-claimed the key -- a second charge. Expiry is
        now. Expiry is the Redis server clock."""
        from src.xstate_statemachine.contrib.redis import inbox as mod

        # 📝 No client clock is read at all (holds on any backend) ...
        assert not hasattr(mod, "time")
        if not os.environ.get("XSM_REDIS_URL"):
            return  # ... fakeredis' TIME *is* time.time(): live-only below
        ib = _inbox(r, prefix)
        real = time.time
        monkeypatch.setattr(time, "time", lambda: real() - 300)
        assert ib.claim("s", "k", "fp", ttl_s=60)
        monkeypatch.setattr(time, "time", lambda: real() + 300)
        assert ib.claim("s", "k", "fp", ttl_s=60) is False
        assert ib.get("s", "k") is not None
        assert ib.purge_expired() == 0

    def test_permanent_mark_survives_purge(self, r: Any, prefix: str) -> None:
        """🐛 claim(ttl) then mark(ttl_s=None) left the claim's expiry in
        the TTL index: `purge_expired` deleted a receipt meant to live
        forever and the redelivery ran the actions again."""
        ib = _inbox(r, prefix)
        ib.claim("s", "k", "fp", ttl_s=0.05)
        ib.mark("s", "k", "{}", ttl_s=None)
        time.sleep(0.1)
        assert ib.purge_expired() == 0
        e = ib.get("s", "k")
        assert e is not None and e.receipt_json == "{}"
        assert e.expires_at is None

    def test_purge_with_pipe_in_scope(self, r: Any, prefix: str) -> None:
        """🐛 The TTL-index member was ``scope|key`` split at the first
        ``|``: a scope holding ``|`` purged the wrong field, the entry
        lived forever and the index kept a dead member."""
        ib = _inbox(r, prefix)
        ib.claim("a|b", "c", "fp", ttl_s=0.01)
        ib.claim("a", "b|c", "fp", ttl_s=1000)
        time.sleep(0.05)
        assert ib.purge_expired() == 1
        assert r.hlen(ib.k.inbox("a|b")) == 0
        assert ib.get("a", "b|c") is not None
        assert r.zcard(ib.k.inbox_exp) == 1

    def test_purge_now_argument(self, r: Any, prefix: str) -> None:
        ib = _inbox(r, prefix)
        ib.claim("s", "k", "fp", ttl_s=60)
        assert ib.purge_expired(now=time.time()) == 0
        assert ib.purge_expired(now=time.time() + 120) == 1
        assert len(ib) == 0


class TestInboxIsolation:
    def test_forget_glob_scope_spares_lookalike(
        self, r: Any, prefix: str
    ) -> None:
        ib = _inbox(r, prefix)
        for scope in ("x*", "xy", "x?", "x["):
            ib.claim(scope, "k", "fp", ttl_s=60)
        assert ib.forget("x*") == 1
        for scope in ("xy", "x?", "x["):
            assert ib.get(scope, "k") is not None
        assert r.zcard(ib.k.inbox_exp) == 3  # x*'s member is gone too

    def test_other_principal_never_sees_the_receipt(
        self, r: Any, prefix: str
    ) -> None:
        ib = _inbox(r, prefix)
        ib.claim("ann/order/o1", "k", "fp", ttl_s=None)
        ib.mark("ann/order/o1", "k", '{"x": 1}', ttl_s=None)
        assert ib.get("bob/order/o1", "k") is None
        assert ib.claim("bob/order/o1", "k", "fp", ttl_s=None)

    @pytest.mark.parametrize("key", ["a:b", "a\x00b", "k" * 10_000, "é|*"])
    def test_hostile_keys_are_opaque_fields(
        self, r: Any, prefix: str, key: str
    ) -> None:
        ib = _inbox(r, prefix)
        assert ib.claim("s", key, "fp", ttl_s=0.01)
        assert ib.claim("s", key + "x", "fp", ttl_s=None)
        time.sleep(0.05)
        assert ib.purge_expired() == 1
        assert ib.get("s", key + "x") is not None

    def test_inbox_and_store_share_a_prefix_without_collision(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.contrib.redis import RedisStore

        st = RedisStore(r, prefix=prefix)
        ib = _inbox(r, prefix)
        st.save("inbox:s", '{"a": 1}')
        ib.claim("s", "k", "fp", ttl_s=None)
        assert st.load("inbox:s").snapshot == '{"a": 1}'
        assert st.list_keys() == ["inbox:s"]
        assert ib.get("s", "k") is not None and len(ib) == 1

    def test_len_with_glob_prefix(self, r: Any) -> None:
        p = f"t-{uuid.uuid4().hex[:6]}"
        a, b = _inbox(r, p + "*"), _inbox(r, p + "x")
        try:
            b.claim("s", "k", "fp", ttl_s=None)
            assert len(a) == 0 and len(b) == 1
        finally:
            for k in r.scan_iter(match=f"{p}*"):
                r.delete(k)


class TestInboxOutage:
    def test_refuse_never_admits_undeduplicated(
        self, r: Any, prefix: str
    ) -> None:
        import redis

        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.persistence.idempotency import (
            InboxUnavailableError,
        )
        from src.xstate_statemachine.receipts import receipt_to_status

        ib = _inbox(r, prefix)

        def down(*a: Any, **k: Any) -> Any:
            raise redis.ConnectionError("Error 111 connecting")

        i = SyncInterpreter(machine()).use(plugin(ib)).start()
        for name in ("_claim", "_get", "_mark"):
            setattr(ib, name, down)
        res = i.send("CREDIT", wait=True, idempotency_key="e1", amount=1)
        assert isinstance(res.error, InboxUnavailableError)
        assert receipt_to_status(res) == 503
        assert i.context["credits"] == 0
        i.stop()


def test_purge_is_a_range_op_not_a_scan(r: Any, prefix: str) -> None:
    """10 expired among 10k vs 100k live entries: the purge walks the
    expired range only. Bulk-loaded straight into the layout."""
    ib = _inbox(r, prefix)

    def load(n: int) -> None:
        far = time.time() + 10**6
        for lo in range(0, n, 5000):
            fields = {str(i): "{}" for i in range(lo, lo + 5000)}
            r.hset(ib.k.inbox("s"), mapping=fields)
            r.zadd(ib.k.inbox_exp, {f"1:s{i}": far for i in fields})

    def timed() -> float:
        for i in range(10):
            ib.claim("t", f"e{i}", "fp", ttl_s=0.001)
        time.sleep(0.01)
        t0 = time.perf_counter()
        assert ib.purge_expired() == 10
        return time.perf_counter() - t0

    load(10_000)
    small = min(timed() for _ in range(3))
    load(100_000)
    big = min(timed() for _ in range(3))
    assert big < max(small * 5, 0.05), (small, big)


# =============================================================================
# 2. RedisLog
# =============================================================================
class TestLogSeq:
    def test_32_appenders_never_share_a_seq(self, r: Any, prefix: str) -> None:
        """🐛 `next_seq` + auto-id `XADD` were two round trips: 32 workers
        x 20 records minted 640 rows with ~37 distinct seqs. The stream id
        is now the seq, so Redis refuses a duplicate and `append_next`
        retries."""
        from src.xstate_statemachine.persistence.log import (
            TransitionLogPlugin,
        )

        lg = _log(r, prefix)
        p = TransitionLogPlugin(lg)
        go = threading.Barrier(32)

        def w() -> None:
            go.wait()
            for _ in range(20):
                p._write(rec(1))

        ts = [threading.Thread(target=w) for _ in range(32)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        seqs = [x.seq for x in lg.read("m", limit=10_000)]
        assert seqs == list(range(1, 641))

    def test_duplicate_or_backwards_append_is_refused(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine.exceptions import StoreError

        lg = _log(r, prefix)
        lg.append(rec(1))
        lg.append(rec(2))
        for bad in (1, 2):
            with pytest.raises(StoreError):
                lg.append(rec(bad))
        assert [x.seq for x in lg.read("m")] == [1, 2]

    def test_validation_parity(self, r: Any, prefix: str) -> None:
        """🐛 `append("x")` raised AttributeError, `read(limit=-1)` and
        `purge_older_than(nan)` were accepted -- the stdlib logs refuse
        all three (#262 battle)."""
        lg = _log(r, prefix)
        with pytest.raises(TypeError):
            lg.append("x")  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            lg.read("m", limit=-1)
        with pytest.raises(ValueError):
            lg.purge_older_than(float("nan"))
        with pytest.raises(ValueError):
            _log(r, prefix, maxlen=0)

    def test_corrupt_entry_is_log_corrupt(self, r: Any, prefix: str) -> None:
        from src.xstate_statemachine.persistence.log import LogCorruptError

        lg = _log(r, prefix)
        r.xadd(lg.k.log("m"), {"seq": 1, "ts": 1, "record": "{nope"}, id="1-0")
        with pytest.raises(LogCorruptError):
            lg.read("m")
        r.delete(lg.k.log("n"))
        r.xadd(
            lg.k.log("n"),
            {"seq": 1, "ts": 1, "record": '{"x": 1}'},
            id="1-0",
        )
        with pytest.raises(LogCorruptError):
            lg.read("n")

    def test_record_from_another_key_is_corrupt(
        self, r: Any, prefix: str
    ) -> None:
        import json

        from src.xstate_statemachine.persistence.log import LogCorruptError

        lg = _log(r, prefix)
        body = json.dumps(rec(1, mid="other").to_dict())
        r.xadd(lg.k.log("m"), {"seq": 1, "ts": 1, "record": body}, id="1-0")
        with pytest.raises(LogCorruptError):
            lg.read("m")


class TestLogRetention:
    def test_default_is_unbounded(self, r: Any, prefix: str) -> None:
        """🐛 The default was ``maxlen=10_000``: a long-lived instance
        silently lost the head of its audit trail. Unbounded, like
        `SQLiteLog`; retention is opt-in."""
        assert _log(r, prefix).maxlen is None

    def test_trimmed_stream_replay_fails_loudly(
        self, r: Any, prefix: str
    ) -> None:
        from src.xstate_statemachine import SyncInterpreter
        from src.xstate_statemachine.persistence.log import (
            ReplayDivergenceError,
            TransitionLogPlugin,
            replay,
        )
        from tests.persistence.test_log import machine as log_machine

        lg = _log(r, prefix, maxlen=5)
        i = SyncInterpreter(log_machine()).use(TransitionLogPlugin(lg))
        i.start()
        for _ in range(200):
            i.send("WHATEVER")
        i.stop()
        rows = lg.read("appr", limit=10_000)
        assert rows and rows[0].seq > 1  # the head was trimmed
        with pytest.raises(ReplayDivergenceError):
            replay(log_machine(), rows)

    def test_purge_and_forget_restart_at_one(
        self, r: Any, prefix: str
    ) -> None:
        lg = _log(r, prefix)
        for s in range(1, 2501):
            lg.append(rec(s, ts=float(s)))
        assert lg.purge_older_than(2000) == 1999
        assert [x.seq for x in lg.read("m", limit=10)][:2] == [2000, 2001]
        assert lg.purge_older_than(10**9) == 501
        assert lg.next_seq("m") == 1  # an emptied stream starts over
        lg.append(rec(1))
        assert lg.forget("m") == 1 and lg.read("m") == []

    def test_unicode_and_large_payload(self, r: Any, prefix: str) -> None:
        lg = _log(r, prefix)
        big = {"txt": "日本語 🚀 \x00 ünï", "blob": "x" * 500_000}
        lg.append(rec(1, event_payload=big))
        assert lg.read("m")[0].event_payload == big


def test_read_paging_is_ranged(r: Any, prefix: str) -> None:
    """`read(after_seq=)` on a 100k stream is an XRANGE from that seq,
    not a scan from the head (the old code walked the whole stream).
    Live server only: fakeredis' own XRANGE is linear."""
    import json

    if not os.environ.get("XSM_REDIS_URL"):
        pytest.skip("complexity claim is about a real Redis")
    lg = _log(r, prefix)
    name = lg.k.log("m")
    for lo in range(1, 100_001, 5000):
        pipe = r.pipeline(transaction=False)
        for s in range(lo, lo + 5000):
            body = json.dumps(rec(s).to_dict())
            pipe.xadd(name, {"seq": s, "ts": 1, "record": body}, id=f"{s}-0")
        pipe.execute()

    def timed(mid: str, after: int) -> float:
        t0 = time.perf_counter()
        rows = lg.read(mid, after_seq=after, limit=100)
        assert rows[0].seq == after + 1 and len(rows) == 100
        return time.perf_counter() - t0

    for s in range(1, 1001):
        lg.append(rec(s, mid="small"))
    small = min(timed("small", 500) for _ in range(3))
    head = min(timed("m", 0) for _ in range(3))
    tail = min(timed("m", 99_800) for _ in range(3))
    assert max(head, tail) < max(small * 5, 0.05), (small, head, tail)
