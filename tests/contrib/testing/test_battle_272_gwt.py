"""Battle-test #272 (adversary B): `given()` / `Scenario` as a user.

Pins the defects found attacking ``contrib/testing/gwt.py`` and the BDD
recipe's skip path.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from xstate_statemachine import Event, MachineLogic, create_machine
from xstate_statemachine.contrib.testing import Scenario, given
from xstate_statemachine.exceptions import UnknownEventError

ROOT = Path(__file__).resolve().parents[3]
BDD = Path(__file__).with_name("bdd_order_specs")

CHART: Dict[str, Any] = {
    "id": "m",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {
            "entry": "seen",
            "on": {"GO": "b", "X": {"actions": "boom"}, "T": "timed"},
        },
        "b": {
            "initial": "a",
            "states": {"a": {}, "c": {"type": "final"}},
            "on": {"FIN": "done"},
        },
        "timed": {"after": {"100": "done"}},
        "p": {
            "type": "parallel",
            "states": {
                "r1": {"initial": "x", "states": {"x": {}}},
                "r2": {
                    "initial": "y",
                    "states": {"y": {}, "h": {"type": "history"}},
                },
            },
        },
        "done": {"type": "final"},
    },
}


def _boom(i: Any, c: Any, e: Any, a: Any) -> None:
    raise ValueError("bad")


@pytest.fixture
def seen() -> List[Dict[str, Any]]:
    return []


@pytest.fixture
def m(seen: List[Dict[str, Any]]) -> Any:
    def _seen(i: Any, c: Any, e: Any, a: Any) -> None:
        seen.append(dict(c))

    return create_machine(
        CHART, logic=MachineLogic(actions={"seen": _seen, "boom": _boom})
    )


# -- given ---------------------------------------------------------------
def test_with_context_on_fresh_start_is_seen_by_entry_actions(
    m: Any, seen: List[Dict[str, Any]]
) -> None:
    given(m).with_context(n=5).then_state("m.a")
    assert seen == [{"n": 5}]


def test_in_state_runs_no_entry_actions(
    m: Any, seen: List[Dict[str, Any]]
) -> None:
    given(m).in_state("m.a").then_state("m.a")
    assert seen == []  # 📝 "you supply the context the chart would have"


def test_ambiguous_and_unknown_leaf_names_are_valueerrors(m: Any) -> None:
    with pytest.raises(ValueError, match="ambiguous"):
        given(m).in_state("a")
    with pytest.raises(ValueError, match="no state named 'zz'"):
        given(m).in_state("zz")


def test_parallel_configuration_and_ancestor_ids(m: Any) -> None:
    given(m).in_state("x", "y").then_state("p", "x", "y", "m").then_not_state(
        "b"
    )


def test_history_state_is_refused_with_a_clear_message(m: Any) -> None:
    # 🔥 was from_state_ids' "conflict ... different branches" message
    with pytest.raises(ValueError, match="history pseudostate"):
        given(m).in_state("h")


def test_in_state_needs_a_state(m: Any) -> None:
    with pytest.raises(ValueError, match="at least one"):
        given(m).in_state()


def test_in_state_top_level_final_is_done(m: Any) -> None:
    # 🔥 was status 'running' parked in a final state
    given(m).in_state("done").then_done()


def test_in_state_nested_final_is_running(m: Any) -> None:
    s = given(m).in_state("b.c")
    s.then_state("b")
    assert s.interp.status == "running"


def test_given_after_when_is_refused(m: Any) -> None:
    with pytest.raises(RuntimeError, match="before the first when"):
        given(m).when("GO").in_state("p")
    with pytest.raises(RuntimeError, match="before the first when"):
        given(m).when("GO").with_context(n=1)


def test_context_validator_refusal_surfaces_on_the_receipt() -> None:
    def v(ctx: Any) -> None:
        if ctx.get("n", 0) < 0:
            raise ValueError("neg")

    cfg = {
        "id": "v",
        "initial": "a",
        "context": {"n": 0},
        "states": {"a": {"on": {"GO": {"target": "b", "actions": "k"}}}},
    }
    cfg["states"]["b"] = {}
    mv = create_machine(
        cfg,
        logic=MachineLogic(actions={"k": lambda i, c, e, a: c.update(k=1)}),
        context_validator=v,
    )
    # 📝 the validator runs after actions, not at with_context()
    given(mv).with_context(n=-1).when("GO").then_error(ValueError)
    given(mv).in_state("a").with_context(n=-1).when("GO").then_error(
        ValueError
    )


# -- when / after --------------------------------------------------------
def test_when_accepts_event_dict_and_payload(m: Any) -> None:
    given(m).when(Event("GO")).then_state("b")
    s = given(m).when({"type": "GO"}, x=1)
    assert s.receipt is not None and s.receipt.changed


def test_strict_unknown_event_raises_the_engines_error() -> None:
    cfg = {"id": "s", "strict": True, "initial": "a", "states": {"a": {}}}
    with pytest.raises(UnknownEventError, match="NOPE"):
        given(create_machine(cfg)).when("NOPE")


def test_after_fires_timers_and_refuses_non_finite(m: Any) -> None:
    given(m).when("T").after(99).then_state("timed").after(1).then_done()
    with pytest.raises(ValueError, match="finite"):
        given(m).after(float("nan"))
    with pytest.raises(ValueError):
        given(m).after(-1)  # 📝 the clock's own refusal


def test_when_after_stop_is_refused_not_a_silent_noop(m: Any) -> None:
    s = given(m).when("GO")
    s.stop()
    with pytest.raises(RuntimeError, match="'stopped', not running"):
        s.when("FIN")
    with pytest.raises(RuntimeError, match="not running"):
        s.after(1)


def test_when_after_done_is_refused(m: Any) -> None:
    s = given(m).when("GO").when("FIN").then_done()
    with pytest.raises(RuntimeError, match="'done'"):
        s.when("GO")


# -- then ----------------------------------------------------------------
def _msg(fn: Any) -> str:
    with pytest.raises(AssertionError) as ei:
        fn()
    return str(ei.value)


def test_failure_messages_name_steps_expected_and_actual(m: Any) -> None:
    msg = _msg(lambda: given(m).in_state("m.a").when("GO").then_state("done"))
    assert msg.startswith("in_state('m.a') -> when('GO'):")
    assert "['done']" in msg and "m.b.a" in msg
    msg = _msg(lambda: given(m).when("GO").then_context(zz=1, n=2))
    assert "zz: expected 1, got '<missing>'" in msg
    assert "n: expected 2, got 0" in msg
    msg = _msg(lambda: given(m).with_context(n=1).then_done())
    assert msg.startswith("with_context(n):") and "'running'" in msg
    assert _msg(lambda: given(m).then_not_state("m.a")).startswith("given()")


def test_then_context_nested_values(m: Any) -> None:
    s = given(m).with_context(n={"a": [1, 2]})
    s.then_context(n={"a": [1, 2]})
    assert "expected {'a': [1]}" in _msg(lambda: s.then_context(n={"a": [1]}))


def test_changed_false_vs_denied(m: Any) -> None:
    s = given(m).when("FIN")  # unhandled in m.a: no-op, not denied
    s.then_changed(False)
    assert "denied" in _msg(s.then_denied)
    s = given(m).when("X").then_error(ValueError)
    assert "ZeroDivisionError" in _msg(lambda: s.then_error(ZeroDivisionError))
    assert "unexpected error" in _msg(s.then_no_error)


def test_then_receipt_steps_need_a_when(m: Any) -> None:
    for step in ("then_changed", "then_denied", "then_error"):
        with pytest.raises(RuntimeError, match="needs a preceding when"):
            getattr(given(m), step)()


def test_two_scenarios_on_one_machine_are_independent(m: Any) -> None:
    a, b = given(m), given(m)
    a.when("GO")
    b.when("T")
    a.then_state("b")
    b.then_state("timed").after(100).then_done()
    a.then_state("b")


def test_context_manager_stops(m: Any) -> None:
    with given(m) as s:
        s.when("GO")
    assert s.interp.status == "stopped"
    assert isinstance(s, Scenario)


# -- BDD recipe skip path -----------------------------------------------
def test_bdd_recipe_skips_without_pytest_bdd(tmp_path: Path) -> None:
    # 📝 simulate "not installed": a sitecustomize-free `-c` that poisons
    #    the import before pytest collects the folder.
    code = (
        "import sys; sys.modules['pytest_bdd'] = None; import pytest; "
        "sys.exit(pytest.main(['-q', '-p', 'no:cacheprovider', "
        f"{str(BDD)!r}]))"
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONUTF8": "1",
        # 📝 entry-point autoload would import pytest_bdd's own plugin
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
    }
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = r.stdout + r.stderr
    assert r.returncode in (0, 5), out
    assert "skipped" in out and "failed" not in out, out
