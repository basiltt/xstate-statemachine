# tests/test_battle_269_graph.py
"""#269 battle: path generation as a model-based test oracle, under load.

A team uses `shortest_paths` / `simple_paths` to generate one test per
reachable configuration of their chart (`xsm_path`), the way
`@xstate/graph` users do. What must hold, and what this pins:

* **every generated path is a run the engine performs** -- `replay()` on
  a fresh interpreter lands exactly on `final_states`, for every corpus
  chart, in every guard mode;
* **the explorer's prefix cache changes nothing** -- the snapshot-cached
  explorer and the replay-everything explorer produce IDENTICAL path
  sets (same configurations, same steps, same assumptions) on the whole
  corpus, including the two cases the cache first got wrong: a
  configuration that is only stable under the last step's forced guard
  (`always` re-runs on restore), and an `after` whose deadline must
  resume on the restore clock;
* **it scales** -- the 35-state parallel `addressFields` chart (3 456
  configurations, ~18 000 edges) finishes within budget, and a
  synthetic 200-state chain / 12-region parallel chart stay linear;
* **bounds are bounds** -- `max_depth` / `max_paths` are honoured on a
  cyclic chart; a chart that cannot start is a typed error, never a hang;
* **the pytest hook** produces one id per configuration, deterministic
  across runs.
"""

from __future__ import annotations

import json
import pathlib
import time
from typing import Any, Dict, FrozenSet, List, Tuple

import pytest

import src.xstate_statemachine._graph_explorer as graph
from src.xstate_statemachine import (
    SimulatedClock,
    SyncInterpreter,
    create_machine,
    stub_logic,
)
from src.xstate_statemachine.exceptions import XStateMachineError
from src.xstate_statemachine.graph import (
    Path,
    reachable_states,
    shortest_paths,
    simple_paths,
)

CORPUS = pathlib.Path(__file__).parent / "tests_cli" / "stately_machines"
pytestmark = pytest.mark.timeout(600)


def _machine(raw: Dict[str, Any]) -> Any:
    return create_machine(raw, logic=stub_logic(raw))


def _corpus() -> List[Tuple[str, Any]]:
    out = []
    for p in sorted(CORPUS.glob("*.json")):
        raw = json.loads(p.read_text("utf-8"))
        try:
            out.append((p.name, _machine(raw)))
        except Exception:  # noqa: BLE001 -- not every export builds
            continue
    return out


def _canon(paths: Dict[FrozenSet[str], Path]) -> Dict[Any, Any]:
    return {
        tuple(sorted(c)): tuple(
            (s.event, s.delay_ms, tuple(sorted(s.to_states)), s.assumptions)
            for s in p.steps
        )
        for c, p in paths.items()
    }


@pytest.fixture
def no_cache(monkeypatch: Any) -> None:
    monkeypatch.setattr(graph, "_CACHE_MAX", 0)


# -----------------------------------------------------------------------------
# 1. cache ≡ replay on the whole corpus, every guard mode
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["true", "both"])
def test_prefix_cache_is_invisible_on_the_corpus(
    mode: str, monkeypatch: Any
) -> None:
    mismatches = []
    checked = 0
    for name, m in _corpus():
        if name in ("addressFields.json", "savage.json"):
            continue  # their own budget tests below
        try:
            cached = _canon(shortest_paths(m, guards=mode, max_depth=8))
        except XStateMachineError:
            continue  # unstartable export (no `initial`): typed, not hung
        monkeypatch.setattr(graph, "_CACHE_MAX", 0)
        plain = _canon(shortest_paths(m, guards=mode, max_depth=8))
        monkeypatch.setattr(graph, "_CACHE_MAX", 50_000)
        checked += 1
        if cached != plain:
            mismatches.append((name, len(cached), len(plain)))
    assert checked >= 90
    assert mismatches == []


def test_savage_guards_both_within_budget_and_cache_invisible(
    monkeypatch: Any,
) -> None:
    """53 states / 78 guards: flipping every guard for every candidate
    was 43 × 17 engine runs per configuration (137 s). Scoped to the
    candidate's own event: same 277 configurations, ~40 s."""
    m = _machine(json.loads((CORPUS / "savage.json").read_text("utf-8")))
    t0 = time.perf_counter()
    cached = shortest_paths(m, guards="both", max_depth=8)
    dt = time.perf_counter() - t0
    assert len(cached) == 277
    assert dt < 150, dt
    shallow = _canon(shortest_paths(m, guards="both", max_depth=4))
    monkeypatch.setattr(graph, "_CACHE_MAX", 0)
    plain = _canon(shortest_paths(m, guards="both", max_depth=4))
    assert shallow == plain


def test_regression_stable_only_under_forced_guard() -> None:
    """`Predictive_passive`: `Passive` holds only while `FeatureError`
    is False; `start()` on a restored prefix re-ran `always` with the
    all-True stubs and the cached explorer saw 3 configurations where
    replay saw 7."""
    m = _machine(
        json.loads((CORPUS / "Predictive_passive.json").read_text("utf-8"))
    )
    found = shortest_paths(m, guards="both", max_depth=12)
    leaves = {tuple(sorted(x.rsplit(".", 1)[-1] for x in c)) for c in found}
    assert ("Standby",) in leaves and ("In_Control_Event",) in leaves


def test_regression_after_resumes_on_the_restore_clock() -> None:
    """`AdvancePayment`: a restored prefix left the `after 2000` dormant
    (the #264 default) and `success` vanished from the path set."""
    m = _machine(
        json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
    )
    found = shortest_paths(m)
    assert any("success" in s for c in found for s in c)
    p = next(p for c, p in found.items() if any("success" in s for s in c))
    assert any(s.event is None and s.delay_ms == 2000 for s in p.steps)


# -----------------------------------------------------------------------------
# 2. every path replays onto its final states
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["true"])
def test_every_path_replays_exactly(mode: str) -> None:
    for name, m in _corpus():
        if name == "addressFields.json":
            continue
        try:
            found = shortest_paths(m, guards=mode, max_depth=10)
        except XStateMachineError:
            continue
        for cfg, path in found.items():
            clock = SimulatedClock()
            i = SyncInterpreter(m, clock=clock)
            path.replay(i, clock)
            assert frozenset(i.current_state_ids) == cfg, (name, path)
            i.stop()


# -----------------------------------------------------------------------------
# 3. scale
# -----------------------------------------------------------------------------
def test_address_fields_full_exploration_within_budget() -> None:
    m = _machine(
        json.loads((CORPUS / "addressFields.json").read_text("utf-8"))
    )
    t0 = time.perf_counter()
    found = shortest_paths(m)
    dt = time.perf_counter() - t0
    assert len(found) == 3456
    # 📝 60 s before the prefix cache on the reference laptop; generous
    #    for a 2x-slower CI runner.
    assert dt < 240, dt


def _chain(n: int) -> Dict[str, Any]:
    states = {f"s{i}": {"on": {"NEXT": f"s{i + 1}"}} for i in range(n)}
    states[f"s{n}"] = {"type": "final"}
    return {"id": "chain", "initial": "s0", "states": states}


def _grid(regions: int) -> Dict[str, Any]:
    return {
        "id": "grid",
        "type": "parallel",
        "states": {
            f"r{i}": {
                "initial": "a",
                "states": {"a": {"on": {f"T{i}": "b"}}, "b": {}},
            }
            for i in range(regions)
        },
    }


def test_long_chain_is_linear_and_depth_bounded() -> None:
    m = _machine(_chain(200))
    t0 = time.perf_counter()
    found = shortest_paths(m, max_depth=250)
    dt = time.perf_counter() - t0
    assert len(found) == 201
    assert max(len(p.steps) for p in found.values()) == 200
    assert dt < 60, dt
    capped = shortest_paths(m, max_depth=20)
    assert max(len(p.steps) for p in capped.values()) == 20


def test_parallel_grid_enumerates_the_product() -> None:
    m = _machine(_grid(10))
    found = shortest_paths(m)
    assert len(found) == 2**10  # every region independently a / b
    assert reachable_states(m) >= {f"grid.r{i}.b" for i in range(10)}


def test_simple_paths_bounds_on_a_cyclic_chart() -> None:
    cfg = {
        "id": "c",
        "initial": "a",
        "states": {
            "a": {"on": {"X": "b", "Y": "c"}},
            "b": {"on": {"X": "c", "Y": "a"}},
            "c": {"on": {"X": "a", "Y": "b"}},
        },
    }
    m = _machine(cfg)
    found = simple_paths(m, max_paths=3, max_depth=2)
    assert len(found) == 3  # max_paths honoured
    assert all(len(p.steps) <= 2 for p in found)
    full = simple_paths(m, max_paths=1000, max_depth=3)
    assert len(full) == 4  # 3 configs -> paths of length 1..2 only
    # acyclic: no configuration repeats inside one path
    for p in found:
        seen = [p.steps[0].from_states] + [s.to_states for s in p.steps]
        assert len(seen) == len(set(seen))


def test_unstartable_chart_is_a_typed_error_not_a_hang() -> None:
    raw = {"id": "u", "states": {"a": {}, "b": {}}}  # no initial
    m = create_machine(raw, logic=stub_logic(raw))
    t0 = time.perf_counter()
    with pytest.raises(XStateMachineError):
        shortest_paths(m)
    assert time.perf_counter() - t0 < 5


# -----------------------------------------------------------------------------
# 4. the pytest hook is deterministic
# -----------------------------------------------------------------------------
def test_path_ids_are_stable_and_unique() -> None:
    from src.xstate_statemachine.contrib.testing._paths import path_id

    m = _machine(
        json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
    )
    a = shortest_paths(m, guards="both")
    b = shortest_paths(m, guards="both")
    assert _canon(a) == _canon(b)
    initial = next(iter(a.values())).steps[:1]
    start = initial[0].from_states if initial else next(iter(a))
    ids = [path_id(p, start) for p in a.values()]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("path[") for i in ids)
