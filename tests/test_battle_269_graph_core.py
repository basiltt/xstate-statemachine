# tests/test_battle_269_graph_core.py
"""#269 battle, adversary A: the explorer core (`graph.py`).

Pins the defects found attacking the prefix-snapshot cache and the
traversal:

* the caller's machine is never mutated -- a traversal used to swap
  ``machine.logic`` for stubs, so a concurrent interpreter (or a second
  thread generating paths) ran on all-True stubs;
* the library logger level survives overlapping traversals on threads;
* BFS snapshots one prefix per configuration (cache hit rate ~100 %,
  was 77 % on `addressFields` once ``_CACHE_MAX`` filled);
* ``max_configs`` bounds a combinatorial chart with a typed error;
* wildcard handlers are explored;
* negative bounds are ``ValueError``.

Plus confirmations: cache ≡ replay on adversarial shapes (history, onDone,
named delays, delayed raise, assign, child machine, always loops).
"""

from __future__ import annotations

import json
import logging
import pathlib
import threading
from typing import Any, Dict, FrozenSet

import pytest

import src.xstate_statemachine.graph as graph
from src.xstate_statemachine import (
    MachineLogic,
    SimulatedClock,
    SyncInterpreter,
    create_machine,
    stub_logic,
)
from src.xstate_statemachine.graph import (
    ExplorationLimitError,
    Path,
    shortest_paths,
    simple_paths,
)

CORPUS = pathlib.Path(__file__).parent / "tests_cli" / "stately_machines"
pytestmark = pytest.mark.timeout(600)

GUARDED = {
    "id": "m",
    "initial": "a",
    "states": {
        "a": {"on": {"GO": {"target": "b", "guard": "g"}}},
        "b": {"on": {"GO": "a"}},
    },
}


def _machine(raw: Dict[str, Any]) -> Any:
    return create_machine(raw, logic=stub_logic(raw))


def _canon(paths: Dict[FrozenSet[str], Path]) -> Dict[Any, Any]:
    return {
        tuple(sorted(c)): tuple(
            (s.event, s.delay_ms, tuple(sorted(s.to_states)), s.assumptions)
            for s in p.steps
        )
        for c, p in paths.items()
    }


def _real_guarded() -> Any:
    return create_machine(
        GUARDED, logic=MachineLogic(guards={"g": lambda c, e: False})
    )


# -----------------------------------------------------------------------------
# 1. cache ≡ replay on adversarial shapes (incl. a 3-entry cache)
# -----------------------------------------------------------------------------
SHAPES = {
    "always_after_forced": {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "type": "parallel",
                "states": {
                    "r1": {
                        "initial": "a",
                        "states": {
                            "a": {
                                "on": {
                                    "GO": [
                                        {"target": "b", "guard": "g"},
                                        {"target": "c"},
                                    ]
                                }
                            },
                            "b": {},
                            "c": {"always": {"target": "d", "guard": "g"}},
                            "d": {},
                        },
                    },
                    "r2": {
                        "initial": "x",
                        "states": {
                            "x": {"on": {"T": "y"}},
                            "y": {"on": {"T": "x"}},
                        },
                    },
                },
            }
        },
    },
    "service_error_always": {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {"on": {"GO": "l"}},
            "l": {"invoke": {"src": "f", "onDone": "ok", "onError": "err"}},
            "ok": {},
            "err": {"always": {"target": "fin", "guard": "h"}},
            "fin": {"on": {"X": "a"}},
        },
    },
    "deep_history": {
        "id": "m",
        "initial": "c",
        "states": {
            "c": {
                "initial": "a",
                "states": {
                    "a": {"on": {"N": "b"}},
                    "b": {
                        "initial": "b1",
                        "states": {"b1": {"on": {"N": "b2"}}, "b2": {}},
                    },
                    "h": {"type": "history", "history": "deep"},
                },
                "on": {"OUT": "o"},
            },
            "o": {"on": {"BACK": "c.h"}},
        },
    },
    "on_done": {
        "id": "m",
        "initial": "c",
        "states": {
            "c": {
                "initial": "a",
                "states": {"a": {"on": {"N": "f"}}, "f": {"type": "final"}},
                "onDone": "d",
            },
            "d": {"on": {"R": "c"}},
        },
    },
    "timer_chain": {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {"after": {"1000": "b"}},
            "b": {"after": {"500": "c"}},
            "c": {"after": {"2000": "a"}, "on": {"X": "d"}},
            "d": {},
        },
    },
    "delayed_raise": {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {
                "entry": {
                    "type": "xstate.raise",
                    "params": {"event": {"type": "PING"}, "delay": 1000},
                },
                "on": {"PING": "b", "GO": "c"},
            },
            "b": {},
            "c": {"on": {"PING": "d"}},
            "d": {},
        },
    },
}


@pytest.mark.parametrize("name", sorted(SHAPES))
@pytest.mark.parametrize("mode", ["true", "both", "false"])
def test_cache_equals_replay_on_adversarial_shapes(
    name: str, mode: str, monkeypatch: Any
) -> None:
    m = _machine(SHAPES[name])
    cached = shortest_paths(m, guards=mode)
    monkeypatch.setattr(graph, "_CACHE_MAX", 0)
    plain = shortest_paths(m, guards=mode)
    monkeypatch.setattr(graph, "_CACHE_MAX", 3)
    tiny = shortest_paths(m, guards=mode)
    assert _canon(cached) == _canon(plain) == _canon(tiny)
    for config, path in cached.items():
        clock = SimulatedClock()
        interp = SyncInterpreter(m, clock=clock)
        path.replay(interp, clock)
        assert frozenset(interp.current_state_ids) == config
        interp.stop()


def test_bfs_snapshots_one_prefix_per_configuration(
    monkeypatch: Any,
) -> None:
    """Every `run()` after the first restores from a snapshot."""
    raw = json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
    m = _machine(raw)
    misses = []
    orig = graph._Explorer.run

    def run(self: Any, steps: Any) -> Any:
        if steps not in self._snapshots:
            misses.append(steps)
        return orig(self, steps)

    monkeypatch.setattr(graph._Explorer, "run", run)
    found = shortest_paths(m)
    assert len(found) >= 3
    assert misses == [()]  # only the root


# -----------------------------------------------------------------------------
# 2. semantics
# -----------------------------------------------------------------------------
def test_wildcard_handlers_are_explored() -> None:
    raw = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {"on": {"*": "any", "mouse.*": "mouse", "GO": "b"}},
            "b": {},
            "any": {},
            "mouse": {},
        },
    }
    m = _machine(raw)
    found = shortest_paths(m)
    leaves = {next(iter(c)) for c in found}
    assert leaves == {"m.a", "m.b", "m.any", "m.mouse"}
    for config, path in found.items():
        clock = SimulatedClock()
        interp = SyncInterpreter(m, clock=clock)
        path.replay(interp, clock)
        assert frozenset(interp.current_state_ids) == config


def test_always_loop_and_trivial_charts_terminate() -> None:
    loop = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {"on": {"GO": "b"}},
            "b": {"always": "c"},
            "c": {"always": "b"},
        },
    }
    assert len(shortest_paths(_machine(loop))) >= 1
    final = {"id": "m", "initial": "f", "states": {"f": {"type": "final"}}}
    assert list(shortest_paths(_machine(final))) == [frozenset({"m.f"})]
    assert simple_paths(_machine(final)) == []
    inert = {"id": "m", "initial": "a", "states": {"a": {}}}
    assert len(shortest_paths(_machine(inert))) == 1


# -----------------------------------------------------------------------------
# 3. bounds
# -----------------------------------------------------------------------------
def test_max_configs_bounds_a_combinatorial_chart() -> None:
    grid = {
        "id": "g",
        "type": "parallel",
        "states": {
            f"r{i}": {
                "initial": "a",
                "states": {"a": {"on": {f"T{i}": "b"}}, "b": {}},
            }
            for i in range(16)
        },
    }
    with pytest.raises(ExplorationLimitError) as info:
        shortest_paths(_machine(grid), max_configs=200)
    assert len(info.value.found) == 201
    assert info.value.limit == 200
    with pytest.raises(ExplorationLimitError):
        shortest_paths(_machine(grid), max_configs=50, weight="time")


def test_zero_and_negative_bounds() -> None:
    m = _machine(GUARDED)
    assert len(shortest_paths(m, max_depth=0)) == 1
    assert simple_paths(m, max_paths=0) == []
    for kw in ({"max_depth": -1}, {"max_configs": -1}):
        with pytest.raises(ValueError):
            shortest_paths(m, **kw)
    with pytest.raises(ValueError):
        simple_paths(m, max_paths=-1)


def test_thousand_state_chain_is_iterative() -> None:
    states: Dict[str, Any] = {
        f"s{i}": {"on": {"NEXT": f"s{i + 1}"}} for i in range(1000)
    }
    states["s1000"] = {"type": "final"}
    m = _machine({"id": "c", "initial": "s0", "states": states})
    assert len(shortest_paths(m, max_depth=1001)) == 1001


# -----------------------------------------------------------------------------
# 4. / 5. the caller's machine and logger are never touched
# -----------------------------------------------------------------------------
def test_traversal_never_mutates_the_callers_machine(
    monkeypatch: Any,
) -> None:
    """A live interpreter on the same machine keeps its REAL guard while
    a traversal is in flight (it used to see the all-True stubs)."""
    m = _real_guarded()
    real = m.logic
    inside, release = threading.Event(), threading.Event()
    orig = graph._Explorer.initial

    def slow(self: Any) -> Any:
        inside.set()
        release.wait(10)
        return orig(self)

    monkeypatch.setattr(graph._Explorer, "initial", slow)
    worker = threading.Thread(target=shortest_paths, args=(m,))
    worker.start()
    assert inside.wait(10)
    try:
        assert m.logic is real
        interp = SyncInterpreter(m).start()
        interp.send("GO")
        assert interp.current_state_ids == {"m.a"}  # real guard: False
        interp.stop()
    finally:
        release.set()
        worker.join()


def test_concurrent_traversals_on_one_machine() -> None:
    m = _real_guarded()
    real = m.logic
    barrier = threading.Barrier(6)
    results = []

    def work() -> None:
        barrier.wait()
        for _ in range(10):
            results.append(len(shortest_paths(m, guards="both")))

    threads = [threading.Thread(target=work) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert set(results) == {2}
    assert m.logic is real and m.logic.guards["g"](None, None) is False


def test_logger_level_survives_overlapping_traversals(
    monkeypatch: Any,
) -> None:
    lib = logging.getLogger("xstate_statemachine")
    monkeypatch.setattr(lib, "level", logging.INFO)
    m = _machine(GUARDED)
    a_in, b_done = threading.Event(), threading.Event()
    orig = graph._Explorer.initial
    calls = []

    def gate(self: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:  # A: hold until B has finished
            a_in.set()
            b_done.wait(10)
        return orig(self)

    monkeypatch.setattr(graph._Explorer, "initial", gate)
    a = threading.Thread(target=shortest_paths, args=(m,))
    a.start()
    assert a_in.wait(10)
    shortest_paths(m)  # B enters after A, leaves before A
    b_done.set()
    a.join()
    assert lib.level == logging.INFO


def test_exception_mid_traversal_leaves_machine_and_logger(
    monkeypatch: Any,
) -> None:
    lib = logging.getLogger("xstate_statemachine")
    monkeypatch.setattr(lib, "level", logging.WARNING)
    m = _real_guarded()
    real = m.logic

    def boom(*a: Any, **k: Any) -> Any:
        raise KeyboardInterrupt

    monkeypatch.setattr(graph._Explorer, "successors", boom)
    with pytest.raises(KeyboardInterrupt):
        shortest_paths(m)
    assert m.logic is real and lib.level == logging.WARNING


def test_private_copy_keeps_post_parse_attributes() -> None:
    seen = []
    m = create_machine(
        {"id": "m", "initial": "a", "context": {"n": 0}, "states": {"a": {}}},
        context_validator=lambda ctx: seen.append(ctx),
    )
    private = graph._private_copy(m, MachineLogic())
    assert private is not m
    assert private.context_validator is m.context_validator
    assert private.states["a"].machine is private
