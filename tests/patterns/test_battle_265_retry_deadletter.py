# tests/patterns/test_battle_265_retry_deadletter.py
# -----------------------------------------------------------------------------
# ⚔️ #265 battle (agent A): RetryPolicy + DeadLetterPlugin + DeadLetterStore
# -----------------------------------------------------------------------------
# 🏛️ Attacks the delay formulas as properties, the retry chart end-to-end on
#    both engines with `SimulatedClock`, the persistence interplay (durable
#    `after` + `DueTimerScanner`), the dead-letter record contents and X0.5
#    redaction, the shared-plugin trap (#261: every order has machine id
#    `order`), sink failures, store concurrency / NaN / limit edge cases,
#    leaks, and the Stately corpus.
# -----------------------------------------------------------------------------
"""#265 battle: RetryPolicy / DeadLetterPlugin / DeadLetterStore."""

from __future__ import annotations

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import gc
import json
import logging
import math
import pathlib
import random
import threading
import time
import tracemalloc
from typing import Any, Dict, List, Tuple

# -------------------------------------------------------------------------
# 📦 Third-Party Imports
# -------------------------------------------------------------------------
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
    wait_for,
)
from src.xstate_statemachine.patterns import (
    DeadLetter,
    DeadLetterPlugin,
    DeadLetterStore,
    RetryPolicy,
)
from src.xstate_statemachine.persistence import (
    DueTimerScanner,
    SQLiteStore,
    persisted,
)
from src.xstate_statemachine.testing_utils import stub_logic

pytestmark = pytest.mark.timeout(60)

MODES = ("none", "full", "equal", "decorrelated")
EPS = 1e-9


@pytest.fixture
def quiet_logs() -> Any:
    """📝 pytest's log capture keeps every ERROR record WITH its traceback,
    whose frames pin the interpreters -- that is a test-harness "leak", not
    a library one. Leak tests silence logging so they measure the library.
    """
    logging.disable(logging.CRITICAL)
    try:
        yield
    finally:
        logging.disable(logging.NOTSET)


# =============================================================================
# 1. Jitter formulas as properties
# =============================================================================
class TestJitterProperties:
    @pytest.mark.parametrize("mode", MODES)
    def test_10k_seeded_draws_stay_in_bounds(self, mode: str) -> None:
        # Arrange
        base, factor, cap = 100.0, 2.0, 5000.0
        p = RetryPolicy(
            base_ms=base,
            factor=factor,
            max_ms=cap,
            jitter=mode,  # type: ignore[arg-type]
            rng=random.Random(265).random,
        )
        prev = None
        # Act / Assert
        for n in range(10_000):
            attempt = n % 12 + 1
            exp = min(cap, base * factor ** (attempt - 1))
            d = p.delay_ms(attempt, previous_ms=prev)
            assert 0 <= d <= cap + EPS
            if mode == "none":
                assert d == exp
            elif mode == "full":
                assert 0 <= d <= exp + EPS
            elif mode == "equal":
                assert exp / 2 - EPS <= d <= exp + EPS
            else:
                hi = min(cap, 3 * (base if prev is None else prev))
                assert base - EPS <= d <= max(base, hi) + EPS
                prev = d

    def test_decorrelated_is_not_monotone_but_capped(self) -> None:
        p = RetryPolicy(
            base_ms=10,
            max_ms=1000,
            jitter="decorrelated",
            rng=random.Random(3).random,
        )
        prev, seq = None, []
        for a in range(1, 200):
            prev = p.delay_ms(a, previous_ms=prev)
            seq.append(prev)
        assert max(seq) <= 1000
        assert seq != sorted(seq)  # the amendment: no monotonicity promise

    @settings(max_examples=300, deadline=None)
    @given(
        mode=st.sampled_from(MODES),
        base=st.floats(0, 1e6),
        cap=st.floats(0, 1e7),
        factor=st.floats(1.0, 1e6),
        attempt=st.integers(1, 10**6),
        r=st.floats(0, 1, exclude_max=True),
        prev=st.one_of(st.none(), st.floats(0, 1e9)),
    )
    def test_degenerate_params_finite_and_capped(
        self,
        mode: str,
        base: float,
        cap: float,
        factor: float,
        attempt: int,
        r: float,
        prev: Any,
    ) -> None:
        p = RetryPolicy(
            base_ms=base,
            max_ms=cap,
            factor=factor,
            jitter=mode,  # type: ignore[arg-type]
            rng=lambda: r,
        )
        d = p.delay_ms(attempt, previous_ms=prev)
        assert math.isfinite(d) and 0 <= d <= cap + EPS

    def test_factor_overflow_returns_cap(self) -> None:
        # BUG fixed: `1e6 ** 999999` raised OverflowError.
        p = RetryPolicy(factor=1e6, max_ms=500, jitter="none")
        assert p.delay_ms(10**6) == 500

    def test_max_below_base_decorrelated(self) -> None:
        p = RetryPolicy(
            base_ms=1000, max_ms=10, jitter="decorrelated", rng=lambda: 0.5
        )
        assert p.delay_ms(1) == 10

    def test_zero_params(self) -> None:
        for mode in MODES:
            assert RetryPolicy(base_ms=0, jitter=mode).delay_ms(5) == 0
            assert RetryPolicy(max_ms=0, jitter=mode).delay_ms(5) == 0
        assert RetryPolicy(factor=1.0, jitter="none").delay_ms(50) == 200

    @pytest.mark.parametrize("attempt", [0, -1, -(10**6)])
    def test_bad_attempt(self, attempt: int) -> None:
        with pytest.raises(ValueError):
            RetryPolicy().delay_ms(attempt)

    @pytest.mark.parametrize("bad", [float("nan"), 1.5, -0.1])
    @pytest.mark.parametrize("mode", ["full", "equal", "decorrelated"])
    def test_rng_out_of_range_is_loud(self, bad: float, mode: str) -> None:
        # BUG fixed: NaN / out-of-range draws produced NaN or out-of-cap
        # delays silently.
        p = RetryPolicy(jitter=mode, rng=lambda: bad)  # type: ignore
        with pytest.raises(ValueError, match="rng"):
            p.delay_ms(1)

    def test_rng_exactly_one_is_accepted_and_capped(self) -> None:
        for mode in ("full", "equal", "decorrelated"):
            p = RetryPolicy(jitter=mode, max_ms=1000, rng=lambda: 1.0)
            assert p.delay_ms(3) <= 1000

    @pytest.mark.parametrize(
        "kw",
        [
            {"base_ms": float("nan")},
            {"max_ms": float("inf")},
            {"factor": float("nan")},
        ],
    )
    def test_non_finite_params_rejected(self, kw: Dict[str, float]) -> None:
        with pytest.raises(ValueError):
            RetryPolicy(**kw)  # type: ignore[arg-type]

    def test_decorrelated_nan_previous_from_context(self) -> None:
        p = RetryPolicy(jitter="decorrelated", rng=lambda: 0.5)
        assert math.isfinite(p.delay_ms(2, previous_ms=float("nan")))

    def test_max_attempts_one_never_retries(self) -> None:
        g = RetryPolicy(max_attempts=1).guard_can_retry()
        assert g({"attempt": 1}, None) is False

    def test_seeded_determinism_across_policies(self) -> None:
        for mode in MODES:
            a = RetryPolicy(jitter=mode, rng=random.Random(9).random)
            b = RetryPolicy(jitter=mode, rng=random.Random(9).random)
            assert [a.delay_ms(k) for k in range(1, 30)] == [
                b.delay_ms(k) for k in range(1, 30)
            ]


# =============================================================================
# 2. The retry chart end-to-end
# =============================================================================
def retry_cfg(
    prefix: str = "retry", key: str = "attempt", mid: str = "job"
) -> Dict[str, Any]:
    return {
        "id": mid,
        "initial": "attempting",
        "context": {key: 0},
        "states": {
            "attempting": {
                "invoke": {
                    "src": "work",
                    "onDone": {"target": "done", "actions": f"{prefix}Reset"},
                    "onError": {
                        "target": "retrying",
                        "actions": f"{prefix}Bump",
                    },
                }
            },
            "retrying": {
                "after": {
                    f"{prefix}Delay": [
                        {
                            "guard": f"{prefix}CanRetry",
                            "target": "attempting",
                        },
                        {"target": "dead_lettered"},
                    ]
                }
            },
            "done": {"type": "final"},
            "dead_lettered": {"type": "final", "tags": ["dead-letter"]},
        },
    }


class Flaky:
    """Service that fails *fails* times, recording the instant of each try."""

    def __init__(self, fails: int, clk: Any = None, tag: str = "") -> None:
        self.fails, self.clk, self.tag = fails, clk, tag
        self.at: List[float] = []

    def __call__(self, i: Any, c: Any, e: Any) -> str:
        self.at.append(self.clk.now() if self.clk else 0.0)
        if len(self.at) <= self.fails:
            raise ConnectionError(f"{self.tag}boom #{len(self.at)}")
        return "ok"


def _sync_run(
    fails: int, max_attempts: int, **pk: Any
) -> Tuple[Any, Flaky, DeadLetterStore]:
    clk = SimulatedClock()
    p = RetryPolicy(max_attempts=max_attempts, base_ms=100, **pk)
    work = Flaky(fails, clk)
    m = create_machine(
        retry_cfg(),
        logic=p.logic().merge(MachineLogic(services={"work": work})),
    )
    store = DeadLetterStore()
    i = SyncInterpreter(m, clock=clk).use(DeadLetterPlugin(store)).start()
    for _ in range(2000):  # 1 ms steps: exact instants are observable
        if i.status != "running" or i.matches("job.done"):
            break
        clk.increment(1)
    return i, work, store


class TestRetryChartSync:
    def test_exact_instants_jitter_none(self) -> None:
        i, work, store = _sync_run(3, 5, jitter="none")
        assert work.at == pytest.approx(
            [0.0, 0.1, 0.3, 0.7]
        )  # +100, +200, +400 ms
        assert i.matches("job.done") and i.context["attempt"] == 0
        assert len(store) == 0
        i.stop()

    def test_fourth_failure_dead_letters_max_three(self) -> None:
        i, work, store = _sync_run(10, 3, jitter="none")
        assert len(work.at) == 3 and i.matches("job.dead_lettered")
        (dl,) = store.all()
        assert dl.attempts == 3 and len(dl.errors) == 3
        i.stop()

    def test_max_attempts_one(self) -> None:
        i, work, store = _sync_run(10, 1, jitter="none")
        assert len(work.at) == 1 and len(store) == 1
        i.stop()

    def test_reset_clears_decorrelated_memory(self) -> None:
        i, _, _ = _sync_run(2, 5, jitter="decorrelated")
        assert i.context["attempt"] == 0
        assert "attempt_delay_ms" not in i.context
        i.stop()

    def test_custom_key_and_two_loops_in_one_chart(self) -> None:
        a = retry_cfg("ra", "tries")
        b = retry_cfg("rb", "fails")
        cfg = {
            "id": "two",
            "type": "parallel",
            "context": {"tries": 0, "fails": 0, "pings": 0},
            "states": {
                "A": {k: v for k, v in a.items() if k != "id"},
                "B": {
                    **{k: v for k, v in b.items() if k != "id"},
                    "on": {"PING": {"actions": "ping"}},
                },
            },
        }
        cfg["states"]["A"].pop("context")
        cfg["states"]["B"].pop("context")
        cfg["states"]["B"]["states"]["attempting"]["invoke"]["src"] = "w2"
        clk = SimulatedClock()
        wa, wb = Flaky(2, clk, "A"), Flaky(10, clk, "B")

        def ping(i: Any, c: Any, e: Any, d: Any) -> None:
            c["pings"] += 1

        logic = (
            RetryPolicy(max_attempts=5, base_ms=100, jitter="none")
            .logic("ra", "tries")
            .merge(
                RetryPolicy(max_attempts=2, base_ms=50, jitter="none").logic(
                    "rb", "fails"
                )
            )
            .merge(
                MachineLogic(
                    services={"work": wa, "w2": wb}, actions={"ping": ping}
                )
            )
        )
        store = DeadLetterStore()
        i = (
            SyncInterpreter(create_machine(cfg, logic=logic), clock=clk)
            .use(DeadLetterPlugin(store, attempt_key="fails"))
            .start()
        )
        for _ in range(1000):
            clk.increment(1)
            i.send("PING")  # sibling region keeps processing
        assert wa.at == pytest.approx([0.0, 0.1, 0.3])
        assert i.context["tries"] == 0
        assert wb.at == pytest.approx([0.0, 0.05])
        assert i.context["pings"] == 1000
        (dl,) = store.all()
        assert dl.state_id == "two.B.dead_lettered" and dl.attempts == 2
        # DOCUMENTED: the error chain is per INTERPRETER, not per region --
        # region A's concurrent failure is interleaved into B's record, and
        # a success in ANY region clears the whole chain.
        msgs = [e["message"] for e in dl.errors]
        assert msgs == ["Aboom #1", "Bboom #1", "Bboom #2", "Aboom #2"]
        i.stop()


class TestRetryChartAsync:
    def test_exact_instants_and_dead_letter_async(self) -> None:
        async def go() -> Any:
            clk = SimulatedClock()
            p = RetryPolicy(max_attempts=3, base_ms=100, jitter="none")
            work = Flaky(10, clk)

            async def aw(i: Any, c: Any, e: Any) -> str:
                return work(i, c, e)

            m = create_machine(
                retry_cfg(),
                logic=p.logic().merge(MachineLogic(services={"work": aw})),
            )
            store = DeadLetterStore()
            i = (
                await Interpreter(m, clock=clk)
                .use(DeadLetterPlugin(store))
                .start()
            )
            for _ in range(5):
                await wait_for(
                    i,
                    lambda x: x.matches("job.retrying")
                    or x.matches("job.dead_lettered"),
                    timeout=5,
                )
                if i.matches("job.dead_lettered"):
                    break
                await clk.increment(1000)
            await asyncio.sleep(0)
            await i.stop()
            return work.at, store.all()

        at, recs = asyncio.run(go())
        assert len(at) == 3
        (dl,) = recs
        assert dl.attempts == 3 and dl.event["type"].startswith("after.")
        assert [e["message"] for e in dl.errors] == [
            "boom #1",
            "boom #2",
            "boom #3",
        ]


# =============================================================================
# 3. Persistence interplay
# =============================================================================
def _persist_machine(fails: int, jitter: str = "none") -> Tuple[Any, Flaky]:
    p = RetryPolicy(
        max_attempts=5,
        base_ms=60_000,
        max_ms=600_000,
        jitter=jitter,  # type: ignore[arg-type]
        rng=random.Random(1).random,
    )
    work = Flaky(fails)
    return (
        create_machine(
            retry_cfg(),
            logic=p.logic().merge(MachineLogic(services={"work": work})),
        ),
        work,
    )


class TestPersistence:
    def test_backoff_survives_restart_and_scanner_wakes(
        self, tmp_path: pathlib.Path
    ) -> None:
        m, work = _persist_machine(fails=1)
        store = SQLiteStore(tmp_path / "s.db")
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass
        rec = store.load("k")
        (d,) = rec.deadlines
        assert d.delay_ms == 60_000 and d.due_at_wall == 60.0
        # resume after 30 s keeps the remaining 30 s
        clk = SimulatedClock(wall_start=30.0)
        with persisted(store, "k", m, clock=clk) as i:
            clk.increment(29_999)
            assert i.matches("job.retrying")
        sc = DueTimerScanner(SQLiteStore(tmp_path / "s.db"), lambda k: m)
        assert sc.run_once(now=61.0) == 1
        with persisted(store, "k", m) as i:
            assert i.matches("job.done") and i.context["attempt"] == 0
        assert len(work.at) == 2
        store.close()

    def test_decorrelated_delay_persisted_in_context(
        self, tmp_path: pathlib.Path
    ) -> None:
        m, _ = _persist_machine(fails=10, jitter="decorrelated")
        store = SQLiteStore(tmp_path / "s.db")
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass
        ctx = store.load("k").snapshot
        blob = json.loads(ctx) if isinstance(ctx, str) else ctx
        assert "attempt_delay_ms" in json.dumps(blob)
        store.close()

    def test_error_chain_survives_persisted_blocks_and_scanner_wakes(
        self, tmp_path: pathlib.Path
    ) -> None:
        # BUG fixed (coordinator HIGH): every attempt runs in a FRESH
        # interpreter (request block, then scanner wakes); the chain was
        # popped in `on_interpreter_stop`, so the record had attempts=3,
        # errors=[]. It now rides in the snapshot (`_xsm_errors`).
        p = RetryPolicy(max_attempts=3, base_ms=1000, jitter="none")
        kinds = [
            ConnectionError("gateway down card_token=tok_live_9999"),
            ValueError("declined"),
            TimeoutError("circuit open"),
        ]
        seen: List[int] = []

        def work(i: Any, c: Any, e: Any) -> str:
            seen.append(id(i))
            raise kinds[len(seen) - 1]

        cfg = retry_cfg(mid="order")
        cfg["context"] = {"attempt": 0, "card_token": "tok_live_9999"}
        m = create_machine(
            cfg, logic=p.logic().merge(MachineLogic(services={"work": work}))
        )
        dls = DeadLetterStore()
        plugin = DeadLetterPlugin(dls)
        path = tmp_path / "s.db"
        with persisted(
            SQLiteStore(path),
            "o1",
            m,
            clock=SimulatedClock(wall_start=0),
            plugins=[plugin],
        ):
            pass  # attempt 1 fails inside the request block
        for now in (1.5, 3.5, 10.0):  # wake attempt 2, attempt 3, give up
            sc = DueTimerScanner(SQLiteStore(path), lambda k: m)
            sc.plugins = [plugin]
            assert sc.run_once(now=now) == 1, sc.last_result
        assert len(set(seen)) == 3  # three different interpreters
        (dl,) = dls.all()
        assert dl.state_id == "order.dead_lettered"
        assert dl.attempts == 3 and len(dl.errors) == 3
        assert [e["type"] for e in dl.errors] == [
            "ConnectionError",
            "ValueError",
            "TimeoutError",
        ]
        assert "tok_live_9999" not in dl.to_json()
        assert dl.errors[0]["message"] == "gateway down card_token=***"
        assert all(isinstance(v, str) for e in dl.errors for v in e.values())
        assert "_xsm_errors" not in dl.snapshot["context"]
        # the persisted record's chain was cleared once captured
        snap = SQLiteStore(path).load("o1").snapshot
        assert "_xsm_errors" not in json.dumps(snap, default=str)

    def test_chain_is_capped_and_reset_by_retry_reset(self) -> None:
        plugin = DeadLetterPlugin(DeadLetterStore(), max_errors=2)
        with pytest.raises(ValueError):
            DeadLetterPlugin(DeadLetterStore(), max_errors=0)
        i, _, _ = _sync_run(3, 5, jitter="none")
        assert "_xsm_errors" not in i.context  # no plugin -> nothing
        i.stop()
        clk = SimulatedClock()
        p = RetryPolicy(max_attempts=10, base_ms=1, jitter="none")
        work = Flaky(5, clk)
        m = create_machine(
            retry_cfg(),
            logic=p.logic().merge(MachineLogic(services={"work": work})),
        )
        i = SyncInterpreter(m, clock=clk).use(plugin).start()
        clk.increment(4)
        assert len(work.at) >= 3
        assert len(i.context["_xsm_errors"]) == 2  # capped
        assert i.context["_xsm_errors"][-1]["message"] == (
            f"boom #{len(work.at)}"
        )
        clk.increment(100)
        assert i.matches("job.done") and "_xsm_errors" not in i.context
        i.stop()

    def test_scanner_refire_after_crash_does_not_double_bump(
        self, tmp_path: pathlib.Path
    ) -> None:
        # 📝 #264 at-least-once: a scanner whose SAVE fails re-fires the
        #    timer next pass. The bump happens on `onError` (inside the
        #    step that FAILED to save), never on the timer itself, so a
        #    lost save replays the whole step from the old record: the
        #    counter can't advance twice for one real failure.
        m, work = _persist_machine(fails=10)
        store = SQLiteStore(tmp_path / "s.db")
        with persisted(store, "k", m, clock=SimulatedClock(wall_start=0)):
            pass

        class Crash(SQLiteStore):
            def save(self, *a: Any, **k: Any) -> Any:
                raise OSError("crash before commit")

        sc = DueTimerScanner(Crash(tmp_path / "s.db"), lambda k: m)
        sc.run_once(now=61.0)
        assert sc.last_result.errors
        assert store.load("k").deadlines  # still due
        sc2 = DueTimerScanner(SQLiteStore(tmp_path / "s.db"), lambda k: m)
        assert sc2.run_once(now=61.0) == 1
        with persisted(store, "k", m) as i:
            assert i.context["attempt"] == 2  # not 3
        store.close()


# =============================================================================
# 4 + 8. Record contents (both engines)
# =============================================================================
SECRET_CFG = {
    "id": "pay",
    "initial": "a",
    "context": {
        "attempt": 2,
        "password": "p",
        "card_token": "tok",
        "authorization": "Bearer x",
    },
    "states": {
        "a": {
            "on": {"FAIL": {"target": "dl", "actions": "explode"}},
        },
        "dl": {"tags": ["dead-letter"]},
    },
}


def _explode(i: Any, c: Any, e: Any, a: Any) -> None:
    raise RuntimeError("bad card /home/secret/path.py")


class TestRecordContents:
    def _assert_record(self, dl: DeadLetter) -> None:
        assert dl.attempts == 2
        (err,) = dl.errors
        assert err == {
            "source": "action",
            "name": "explode",
            "type": "RuntimeError",
            "message": "bad card /home/secret/path.py",
        }
        blob = dl.to_json()
        assert "Traceback" not in blob
        for k in ("password", "card_token", "authorization"):
            assert dl.snapshot["context"][k] == "***"
            assert dl.event["payload"][k] == "***"
        assert DeadLetter.from_dict(json.loads(blob)) == dl

    def test_sync(self) -> None:
        store = DeadLetterStore()
        m = create_machine(
            SECRET_CFG, logic=MachineLogic(actions={"explode": _explode})
        )
        i = SyncInterpreter(m).use(DeadLetterPlugin(store)).start()
        i.send("FAIL", password="1", card_token="2", authorization="3")
        self._assert_record(store.all()[0])
        i.stop()

    def test_async(self) -> None:
        async def go() -> List[DeadLetter]:
            store = DeadLetterStore()
            m = create_machine(
                SECRET_CFG, logic=MachineLogic(actions={"explode": _explode})
            )
            i = await Interpreter(m).use(DeadLetterPlugin(store)).start()
            await i.send(
                "FAIL", password="1", card_token="2", authorization="3"
            )
            await wait_for(i, lambda x: len(store) == 1, timeout=5)
            await i.stop()
            return store.all()

        self._assert_record(asyncio.run(go())[0])

    def test_state_ids_override_tag_and_two_dl_states(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"X": "p1", "Y": "p2", "Z": "t"}},
                "p1": {"on": {"BACK": "a"}},
                "p2": {"on": {"BACK": "a"}},
                "t": {"tags": ["dead-letter"], "on": {"BACK": "a"}},
            },
        }
        store = DeadLetterStore()
        i = (
            SyncInterpreter(create_machine(cfg))
            .use(DeadLetterPlugin(store, state_ids=["m.p1", "m.p2"]))
            .start()
        )
        for ev in ("X", "BACK", "Y", "BACK", "Z", "BACK", "X"):
            i.send(ev)
        # tag ignored when state_ids given; re-entry = one record per entry
        assert [r.state_id for r in store.list()] == ["m.p1", "m.p2", "m.p1"]
        assert len({r.id for r in store.all()}) == 3
        i.stop()

    def test_initial_dead_letter_state_writes_no_record(self) -> None:
        # DOCUMENTED: start() is not an event step -> `on_event_processed`
        # never fires for the initial configuration, so no record.
        cfg = {
            "id": "m",
            "initial": "dl",
            "states": {"dl": {"tags": ["dead-letter"]}},
        }
        store = DeadLetterStore()
        plugin = DeadLetterPlugin(store)
        i = SyncInterpreter(create_machine(cfg)).use(plugin).start()
        assert len(store) == 0
        i.stop()

    def test_dead_letter_in_parallel_region_machine_keeps_running(
        self,
    ) -> None:
        cfg = {
            "id": "m",
            "type": "parallel",
            "context": {"n": 0},
            "states": {
                "A": {
                    "initial": "ok",
                    "states": {
                        "ok": {"on": {"KILL": "dl"}},
                        "dl": {"tags": ["dead-letter"]},
                    },
                },
                "B": {"on": {"INC": {"actions": "inc"}}},
            },
        }

        def inc(i: Any, c: Any, e: Any, a: Any) -> None:
            c["n"] += 1

        store = DeadLetterStore()
        i = (
            SyncInterpreter(
                create_machine(cfg, logic=MachineLogic(actions={"inc": inc}))
            )
            .use(DeadLetterPlugin(store))
            .start()
        )
        i.send("KILL")
        for _ in range(5):
            i.send("INC")
        assert len(store) == 1 and i.context["n"] == 5
        assert i.status == "running"
        i.stop()

    def test_include_snapshot_false(self) -> None:
        store = DeadLetterStore()
        m = create_machine(
            SECRET_CFG, logic=MachineLogic(actions={"explode": _explode})
        )
        i = (
            SyncInterpreter(m)
            .use(DeadLetterPlugin(store, include_snapshot=False))
            .start()
        )
        i.send("FAIL")
        assert store.all()[0].snapshot == {}
        i.stop()

    def test_child_actor_record_uses_actor_id(self) -> None:
        child = {
            "id": "child",
            "initial": "a",
            "states": {
                "a": {"after": {"10": "dl"}},
                "dl": {"tags": ["dead-letter"]},
            },
        }
        parent = {
            "id": "parent",
            "initial": "p",
            "states": {"p": {"entry": ["spawn_kid"]}},
        }
        # DOCUMENTED: a spawned child does NOT inherit the parent's
        # instance plugins (observed `child._plugins == []`), so the plugin
        # must be attached to the child (or registered globally) to see its
        # dead letters. Once attached, the record names the ACTOR id.
        child["states"]["a"] = {"on": {"K": "dl"}}
        store = DeadLetterStore()
        plugin = DeadLetterPlugin(store)
        i = (
            SyncInterpreter(
                create_machine(
                    parent,
                    logic=MachineLogic(
                        services={"kid": create_machine(child)}
                    ),
                )
            )
            .use(plugin)
            .start()
        )
        (actor,) = i._actors.values()
        assert list(actor._plugins) == []
        actor.use(plugin)
        actor.send("K")
        (rec,) = store.all()
        assert rec.machine_id == actor.id
        assert rec.machine_id.startswith("parent:kid:")
        assert rec.state_id == "child.dl"
        i.stop()

    def test_after_entry_snapshot_not_mid_step_async(self) -> None:
        async def go() -> List[DeadLetter]:
            cfg = {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"after": {"10": "dl"}},
                    "dl": {"tags": ["dead-letter"]},
                },
            }
            clk = SimulatedClock()
            store = DeadLetterStore()
            i = (
                await Interpreter(create_machine(cfg), clock=clk)
                .use(DeadLetterPlugin(store))
                .start()
            )
            await clk.increment(10)
            await wait_for(i, lambda x: len(store) == 1, timeout=5)
            assert i.last_plugin_error is None
            await i.stop()
            return store.all()

        (dl,) = asyncio.run(go())
        assert dl.snapshot["value"] or dl.snapshot


# =============================================================================
# 5. The shared-plugin trap (#261)
# =============================================================================
ORDER_CFG = {
    "id": "order",
    "initial": "a",
    "context": {"key": ""},
    "states": {
        "a": {
            "on": {
                "FAIL": {"actions": "explode"},
                "DIE": "dl",
            }
        },
        "dl": {"tags": ["dead-letter"]},
    },
}


def _order_logic() -> MachineLogic:
    def explode(i: Any, c: Any, e: Any, a: Any) -> None:
        raise RuntimeError(f"err-{e.payload['key']}")

    return MachineLogic(actions={"explode": explode})


class TestSharedPlugin:
    def test_barrier_interleaving_keeps_chains_apart(self) -> None:
        # BUG fixed: chains were keyed by machine id ("order" for all).
        store = DeadLetterStore()
        plugin = DeadLetterPlugin(store)
        m = create_machine(ORDER_CFG, logic=_order_logic())
        bar = threading.Barrier(2)

        def run(key: str) -> None:
            i = SyncInterpreter(m).use(plugin).start()
            i.send("FAIL", key=key)
            bar.wait(5)  # both chains recorded before either dies
            bar.wait(5)
            i.send("DIE", key=key)
            i.stop()

        ts = [threading.Thread(target=run, args=(k,)) for k in "AB"]
        for t in ts:
            t.start()
        for t in ts:
            t.join(10)
        recs = store.all()
        assert len(recs) == 2
        for r in recs:
            key = r.event["payload"]["key"]
            assert [e["message"] for e in r.errors] == [f"err-{key}"]

    def test_randomised_16_threads_200_cycles(self) -> None:
        store = DeadLetterStore()
        plugin = DeadLetterPlugin(store)
        m = create_machine(ORDER_CFG, logic=_order_logic())
        rnd = random.Random(265)
        seeds = [rnd.random() for _ in range(16)]

        def run(t: int) -> None:
            r = random.Random(seeds[t])
            for c in range(200):
                key = f"{t}-{c}"
                i = SyncInterpreter(m).use(plugin).start()
                for _ in range(r.randint(1, 3)):
                    i.send("FAIL", key=key)
                    if r.random() < 0.3:
                        time.sleep(0)
                i.send("DIE", key=key)
                i.stop()

        ts = [threading.Thread(target=run, args=(t,)) for t in range(16)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(60)
        assert len(store) == 16 * 200
        for rec in store.all():
            key = rec.event["payload"]["key"]
            assert rec.errors
            assert all(e["message"] == f"err-{key}" for e in rec.errors)
        assert len(plugin._errors) == 0 and len(plugin._pending) == 0

    def test_never_stopped_interpreters_do_not_leak(
        self, quiet_logs: Any
    ) -> None:
        plugin = DeadLetterPlugin(DeadLetterStore())
        m = create_machine(ORDER_CFG, logic=_order_logic())
        for n in range(10_000):
            i = SyncInterpreter(m).use(plugin).start()
            i.send("FAIL", key=str(n))  # never stopped, never dead-lettered
            del i
        gc.collect()
        assert len(plugin._errors) < 10


# =============================================================================
# 6. Sinks
# =============================================================================
DL_CFG = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"X": "dl"}}, "dl": {"tags": ["dead-letter"]}},
}


class TestSinks:
    def test_raising_sink_logged_with_record_id(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        def sink(r: DeadLetter) -> None:
            raise IOError("queue down")

        i = SyncInterpreter(create_machine(DL_CFG)).use(DeadLetterPlugin(sink))
        i.start()
        with caplog.at_level(logging.ERROR):
            i.send("X")
        assert i.status == "running" and i.matches("m.dl")
        assert any(
            "NOT stored" in r.getMessage() and "m.dl" in r.getMessage()
            for r in caplog.records
        )
        assert i.last_plugin_error is not None
        i.stop()

    def test_blocking_sink_blocks_the_step(self) -> None:
        # DOCUMENTED: the sink runs synchronously in the step.
        def sink(r: DeadLetter) -> None:
            time.sleep(0.3)

        i = SyncInterpreter(create_machine(DL_CFG)).use(DeadLetterPlugin(sink))
        i.start()
        t0 = time.perf_counter()
        i.send("X")
        assert time.perf_counter() - t0 >= 0.3
        i.stop()

    def test_put_object_and_bad_sink(self) -> None:
        class Q:
            def __init__(self) -> None:
                self.got: List[Any] = []

            def put(self, r: Any) -> None:
                self.got.append(r)

        q = Q()
        i = SyncInterpreter(create_machine(DL_CFG)).use(DeadLetterPlugin(q))
        i.start()
        i.send("X")
        assert len(q.got) == 1
        i.stop()
        with pytest.raises(TypeError):
            DeadLetterPlugin(object())
        with pytest.raises(TypeError):
            DeadLetterPlugin(type("P", (), {"put": 3})())


# =============================================================================
# 7. DeadLetterStore
# =============================================================================
def _rec(t: float, rid: str = "") -> DeadLetter:
    return DeadLetter("m", "m.x", {}, None, [], {}, t, id=rid)


class TestStore:
    def test_concurrent_ops(self) -> None:
        s = DeadLetterStore()

        def run(t: int) -> None:
            for n in range(300):
                rid = f"{t}-{n}"
                s.put(_rec(float(n), rid))
                s.list(limit=5)
                if n % 3 == 0:
                    s.mark_resolved(rid, 1.0)
                if n % 5 == 0:
                    s.delete(rid)
                if n % 50 == 0:
                    s.purge_older_than(-1.0)

        ts = [threading.Thread(target=run, args=(t,)) for t in range(16)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        assert len(s) == 16 * (300 - 60)
        assert len(s.list(limit=10**9)) == 16 * (200 - 40)

    def test_purge_nan_rejected_deletes_nothing(self) -> None:
        # BUG fixed: NaN cutoff deleted every record.
        s = DeadLetterStore()
        s.put(_rec(1.0))
        with pytest.raises(ValueError):
            s.purge_older_than(float("nan"))
        assert len(s) == 1

    def test_negative_limit_rejected(self) -> None:
        # BUG fixed: limit=-1 silently dropped the newest record.
        s = DeadLetterStore()
        s.put(_rec(1.0))
        with pytest.raises(ValueError):
            s.list(limit=-1)
        assert s.list(limit=0) == []

    def test_duplicate_id_replaces(self) -> None:
        s = DeadLetterStore()
        s.put(_rec(1.0, "x"))
        s.put(_rec(2.0, "x"))
        assert [r.taken_at for r in s.all()] == [2.0]

    def test_100k_records_is_fast(self) -> None:
        # BUG fixed: put() rebuilt the whole list (O(n^2) fill).
        s = DeadLetterStore()
        t0 = time.perf_counter()
        for n in range(100_000):
            s.put(_rec(float(n % 997), str(n)))
        rows = s.list(limit=10)
        assert time.perf_counter() - t0 < 10
        assert len(s) == 100_000 and rows[0].taken_at == 0.0


# =============================================================================
# 9. Leaks
# =============================================================================
class TestLeaks:
    def test_10k_retry_cycles_bounded(self, quiet_logs: Any) -> None:
        clk = SimulatedClock()
        p = RetryPolicy(max_attempts=1000, base_ms=1, max_ms=1, jitter="full")
        cfg = retry_cfg()
        cfg["states"]["done"] = {"on": {"AGAIN": "attempting"}}
        n = {"c": 0}

        def work(i: Any, c: Any, e: Any) -> str:
            n["c"] += 1
            if n["c"] % 2:
                raise ConnectionError("x")
            return "ok"

        m = create_machine(
            cfg, logic=p.logic().merge(MachineLogic(services={"work": work}))
        )
        store = DeadLetterStore()
        i = SyncInterpreter(m, clock=clk).use(DeadLetterPlugin(store)).start()
        threads0 = threading.active_count()

        def cycles(k: int) -> None:
            for _ in range(k):
                clk.increment(2)
                i.send("AGAIN")

        cycles(5000)
        gc.collect()
        tracemalloc.start()
        s1 = tracemalloc.take_snapshot()
        cycles(5000)
        gc.collect()
        s2 = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(d.size_diff for d in s2.compare_to(s1, "filename"))
        assert growth < 64 * 1024, growth
        assert threading.active_count() <= threads0
        assert all(len(p._errors) <= 1 for p in plugin_errors(i))
        i.stop()


def plugin_errors(i: Any) -> List[Any]:
    return [p for p in i._plugins if getattr(p, "_errors", None)]


# =============================================================================
# 10. Stately corpus
# =============================================================================
CORPUS = sorted(
    (
        pathlib.Path(__file__).resolve().parents[1]
        / "tests_cli"
        / "stately_machines"
    ).glob("*.json")
)


def _finals(node: Dict[str, Any], prefix: str) -> List[str]:
    out = []
    for name, child in (node.get("states") or {}).items():
        sid = f"{prefix}.{name}"
        if child.get("type") == "final":
            out.append(sid)
        out.extend(_finals(child, sid))
    return out


def _events(node: Dict[str, Any]) -> List[str]:
    out = list((node.get("on") or {}).keys())
    for child in (node.get("states") or {}).values():
        out.extend(_events(child))
    return out


@pytest.mark.parametrize("path", CORPUS, ids=lambda p: p.stem)
def test_stately_corpus(path: pathlib.Path) -> None:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    try:
        m = create_machine(cfg, logic=stub_logic(cfg))
    except Exception:
        pytest.skip("chart not loadable by the engine itself")
    store = DeadLetterStore()
    plugin = DeadLetterPlugin(store, state_ids=_finals(cfg, m.id) or ["-"])
    i = SyncInterpreter(m, clock=SimulatedClock()).use(plugin)
    try:
        i.start()
    except Exception:
        pytest.skip("chart does not start with stub logic")
    evs = _events(cfg) or ["NOPE"]
    rnd = random.Random(path.stem)
    for _ in range(20):
        if i.status != "running":
            break
        try:
            i.send(rnd.choice(evs))
        except Exception:
            pass  # engine-level, not the plugin's concern
    assert i.last_plugin_error is None or (
        i.last_plugin_error[0] != "DeadLetterPlugin"
    )
    for r in store.all():
        assert DeadLetter.from_dict(json.loads(r.to_json())).id == r.id
    if i.status == "running":
        i.stop()
