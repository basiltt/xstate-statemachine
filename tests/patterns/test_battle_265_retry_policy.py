# tests/patterns/test_battle_265_retry_policy.py
# -----------------------------------------------------------------------------
# ⚔️ #265 battle (agent A): RetryPolicy (part 1 of 2)
# -----------------------------------------------------------------------------
# 🏛️ Attacks the delay formulas as properties, the retry chart end-to-end on
#    both engines with `SimulatedClock`, the persistence interplay (durable
#    `after` + `DueTimerScanner`), the dead-letter record contents and X0.5
#    redaction, the shared-plugin trap (#261: every order has machine id
#    `order`), sink failures, store concurrency / NaN / limit edge cases,
#    leaks, and the Stately corpus.
# -----------------------------------------------------------------------------
"""#265 battle, part 1: RetryPolicy formulas, the retry chart on both
engines, and the persistence interplay. Part 2 (`_dead_letter.py`) covers
the DeadLetterPlugin / DeadLetterStore and imports the shared helpers
(`retry_cfg`, `quiet_logs`) from here."""

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
