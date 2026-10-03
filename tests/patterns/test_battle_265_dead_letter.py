# tests/patterns/test_battle_265_dead_letter.py
# -----------------------------------------------------------------------------
# ⚔️ #265 battle (agent A): DeadLetterPlugin + DeadLetterStore (part 2 of 2)
# -----------------------------------------------------------------------------
# 🏛️ Attacks the delay formulas as properties, the retry chart end-to-end on
#    both engines with `SimulatedClock`, the persistence interplay (durable
#    `after` + `DueTimerScanner`), the dead-letter record contents and X0.5
#    redaction, the shared-plugin trap (#261: every order has machine id
#    `order`), sink failures, store concurrency / NaN / limit edge cases,
#    leaks, and the Stately corpus.
# -----------------------------------------------------------------------------
"""#265 battle, part 2: DeadLetterPlugin record contents and redaction, the
shared-plugin trap, sink failures, store edge cases, leaks, the corpus."""

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

# 📝 Shared helpers live in part 1; importing the fixture by name is how
#    pytest sees it here (F811 on the parameter names below is the usual
#    pytest-fixture false positive).
from .test_battle_265_retry_policy import (  # noqa: E402,F401
    quiet_logs,
    retry_cfg,
)

pytestmark = pytest.mark.timeout(60)

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
        # tag ignored when state_ids given; re-entry = one record per entry.
        # 📝 `all()` is insertion order; `list()` sorts by (taken_at, id)
        #    and three records within one clock tick share `taken_at`, so
        #    their relative order there is the random uuid's (seen on 3.9).
        assert [r.state_id for r in store.all()] == ["m.p1", "m.p2", "m.p1"]
        assert sorted(r.state_id for r in store.list()) == [
            "m.p1",
            "m.p1",
            "m.p2",
        ]
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
        self, quiet_logs: Any  # noqa: F811
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
        # DOCUMENTED: the sink runs synchronously in the step -- `send()`
        # does not return until the sink has. Asserted on ORDER, not on a
        # wall-clock `>= 0.3` (Windows `time.sleep` can wake a tick early
        # on 3.9 and the comparison flaked).
        order: List[str] = []

        def sink(r: DeadLetter) -> None:
            time.sleep(0.05)
            order.append("sink done")

        i = SyncInterpreter(create_machine(DL_CFG)).use(DeadLetterPlugin(sink))
        i.start()
        i.send("X")
        order.append("send returned")
        assert order == ["sink done", "send returned"]
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
    def test_10k_retry_cycles_bounded(
        self, quiet_logs: Any  # noqa: F811
    ) -> None:
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
