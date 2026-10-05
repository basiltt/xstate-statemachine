# tests/contrib/testing/test_battle_271_rules.py
"""#271 battle (adversary A): the generated rules and `check()`.

Pinned regressions:

* event names that collide after `_ident` (``"A.B"`` / ``"A_B"``) each
  get their own rule -- one used to overwrite the other silently;
* `state_assertions` keyed by a state the chart lacks is a `ValueError`
  at `model_test()` (a typo never ran before);
* an ``assert``-style check returning ``None`` passes; ``0`` / ``""``
  / ``False`` fail; a non-AssertionError (``KeyError``) fails through
  `_fail`, so the replay artefact is written;
* the clock rule reaches ``raise`` with ``delay`` (no ``after`` key) and
  is present with ``clock=True`` even when no ``after`` exists;
* a payload strategy producing a non-dict or a ``type`` key is a clear
  `TypeError`;
* a pending ``after`` survives the snapshot round-trip on the model clock;
* a payload-dependent guard never yields a refused send.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from src.xstate_statemachine import (  # noqa: E402
    MachineLogic,
    SyncInterpreter,
)
from src.xstate_statemachine.contrib.testing import model_test  # noqa: E402

S = settings(
    deadline=None,
    database=None,
    derandomize=True,
    suppress_health_check=list(HealthCheck),
    max_examples=40,
)


def _run(cls: Any) -> None:
    cls.TestCase("runTest").runTest()


COLLIDE = {
    "id": "m",
    "initial": "a",
    "states": {
        "a": {"on": {"A.B": "b", "A_B": "c"}},
        "b": {"type": "final"},
        "c": {"type": "final"},
    },
}


def test_colliding_event_names_get_distinct_rules() -> None:
    cls = model_test(COLLIDE, settings=S)
    rules = sorted(n for n in vars(cls) if n.startswith("send_"))
    assert rules == ["send_A_B", "send_A_B_2"]


def test_both_colliding_events_are_explored(tmp_path: pathlib.Path) -> None:
    cls = model_test(
        COLLIDE,
        settings=S,
        failing_path=tmp_path / "f.json",
        invariants={"never c": lambda i: not i.matches("c")},
    )
    with pytest.raises(AssertionError, match="never c"):
        _run(cls)
    assert json.loads((tmp_path / "f.json").read_text()) == [{"send": "A_B"}]


def test_unknown_state_assertion_key_is_value_error() -> None:
    with pytest.raises(ValueError, match="nope"):
        model_test(COLLIDE, state_assertions={"nope": lambda i: True})


def test_state_assertion_partial_and_hash_ids_accepted() -> None:
    model_test(
        COLLIDE,
        settings=S,
        state_assertions={"b": lambda i: True, "#m.c": lambda i: True},
    )


def test_assert_style_check_returning_none_passes(
    tmp_path: pathlib.Path,
) -> None:
    def ok(i: Any) -> None:
        assert i.status in ("running", "done")

    _run(
        model_test(
            COLLIDE,
            settings=S,
            invariants={"ok": ok},
            state_assertions={"b": ok},
            failing_path=tmp_path / "f.json",
        )
    )


@pytest.mark.parametrize("value", [False, 0, ""])
def test_falsy_non_none_fails(value: Any, tmp_path: pathlib.Path) -> None:
    cls = model_test(
        COLLIDE,
        settings=S,
        invariants={"x": lambda i: value},
        failing_path=tmp_path / "f.json",
    )
    with pytest.raises(AssertionError, match="violated"):
        _run(cls)


def test_raising_check_fails_with_artefact(tmp_path: pathlib.Path) -> None:
    out = tmp_path / "f.json"
    cls = model_test(
        COLLIDE,
        settings=S,
        invariants={"k": lambda i: i.context["missing"]},
        failing_path=out,
    )
    with pytest.raises(AssertionError, match="raised KeyError"):
        _run(cls)
    assert out.exists()


RAISE_DELAY = {
    "id": "t",
    "initial": "a",
    "on": {"T": ".b"},
    "states": {
        "a": {
            "entry": {
                "type": "xstate.raise",
                "params": {"event": {"type": "T"}, "delay": 500},
            }
        },
        "b": {},
    },
}


def test_clock_reaches_raise_delay() -> None:
    cls = model_test(RAISE_DELAY, settings=S, snapshot_roundtrip=False)
    assert "advance_clock" in vars(cls)
    m = cls()
    try:
        # 📝 the rule is enabled with no `after` in the chart, and its
        #    "next live timer" draw (delay=None) fires the delayed raise.
        assert m.clock.pending == 1
        cls.advance_clock.hypothesis_stateful_rule.function(
            m, delay=None, jitter=0
        )
        assert m.interp.matches("b")
        assert m.trace == [{"clock": 500.0}]
    finally:
        m.teardown()


@pytest.mark.parametrize("bad", [5, {"type": "X"}])
def test_bad_payload_strategy_is_type_error(bad: Any) -> None:
    cls = model_test(COLLIDE, settings=S, payloads={"A.B": st.just(bad)})
    with pytest.raises(TypeError, match="must produce dicts"):
        _run(cls)


AFTER = {
    "id": "w",
    "initial": "a",
    "states": {"a": {"after": {"1000": "b"}}, "b": {}},
}


def test_pending_after_survives_roundtrip(tmp_path: pathlib.Path) -> None:
    cls = model_test(
        AFTER,
        settings=S,
        invariants={"never b": lambda i: not i.matches("b")},
        failing_path=tmp_path / "f.json",
    )
    with pytest.raises(AssertionError, match="never b"):
        _run(cls)
    # 📝 the round-trip must not reset the timer: the minimal script is a
    #    single advance, never "roundtrip then advance twice".
    steps = json.loads((tmp_path / "f.json").read_text())
    assert [list(s) for s in steps] == [["clock"]]


GUARDED = {
    "id": "g",
    "initial": "a",
    "states": {
        "a": {"on": {"PAY": {"target": "b", "guard": "big"}}},
        "b": {"on": {"BACK": "a"}},
    },
}


def test_payload_dependent_guard_never_refused(
    tmp_path: pathlib.Path,
) -> None:
    denied = []
    orig = SyncInterpreter.send

    def spy(self: Any, *a: Any, **k: Any) -> Any:
        r = orig(self, *a, **k)
        if getattr(r, "denied", False):
            denied.append((a, k))
        return r

    logic = MachineLogic(guards={"big": lambda c, e: e.payload["n"] > 5})
    cls = model_test(
        GUARDED,
        logic=lambda: logic,
        settings=S,
        payloads={"PAY": st.fixed_dictionaries({"n": st.integers(0, 10)})},
        failing_path=tmp_path / "f.json",
    )
    mp = pytest.MonkeyPatch()
    mp.setattr(SyncInterpreter, "send", spy)
    try:
        _run(cls)
    finally:
        mp.undo()
    assert denied == []
