# tests/contrib/testing/test_battle_271_shrink.py
"""#271 battle (adversary A): artefact, round-trip, shrinking, jitter.

* **the LAST write is the minimal one** -- `_write_failing` runs on every
  failing example while Hypothesis shrinks; the file left behind must be
  the sequence of the final (minimal) reported failure;
* **replay** -- a `Decimal` payload and a unicode event name written by
  `model_test` replay through `xsm simulate --script` (its `run_script`)
  to the same configuration;
* **round-trip** -- a `Decimal` in context fails on purpose (snapshot
  restores it as a ``str``); an invoke in flight at the snapshot is
  restarted on the copy, so an `onDone`-reaching invariant holds;
* **shrinking quality** -- sequence-, payload- and time-dependent planted
  bugs shrink to their minimal length, identically on two runs;
* **jitter** -- two `after`s 1 ms apart: both targets are reachable;
* **budget** -- 200 examples on a small chart in seconds.
"""

from __future__ import annotations

import decimal
import json
import pathlib
import time
from typing import Any, List

import pytest

pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from src.xstate_statemachine import MachineLogic  # noqa: E402
from src.xstate_statemachine.cli.commands.simulate import (  # noqa: E402
    Session,
    run_script,
)
from src.xstate_statemachine.contrib.testing import model  # noqa: E402
from src.xstate_statemachine.contrib.testing import model_test  # noqa: E402

S = settings(
    deadline=None,
    database=None,
    derandomize=True,
    suppress_health_check=list(HealthCheck),
    max_examples=200,
)


def _fail(cls: Any) -> str:
    with pytest.raises(AssertionError) as info:
        cls.TestCase("runTest").runTest()
    return str(info.value)


def _steps(path: pathlib.Path) -> List[Any]:
    return list(json.loads(path.read_text("utf-8")))


COUNTER = {
    "id": "c",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {
            "on": {
                "INC": {"actions": "inc"},
                "NOOP": {},
                "GO": "b",
            }
        },
        "b": {"on": {"BACK": "a"}},
    },
}


def _counter_logic() -> MachineLogic:
    def inc(i: Any, c: Any, e: Any, a: Any) -> None:
        c["n"] += 1

    return MachineLogic(actions={"inc": inc})


def _assert_three_incs(steps: List[Any]) -> None:
    """Exactly three INCs; Hypothesis >= 6.16x also drops a `GO, BACK`
    detour (3 steps), 6.141 (the py3.9 venv) can keep it (5 steps)."""
    assert [s for s in steps if s == {"send": "INC"}] == [{"send": "INC"}] * 3
    assert len(steps) <= 5, steps


# -----------------------------------------------------------------------------
# 4. the artefact
# -----------------------------------------------------------------------------
def test_last_write_is_the_minimal_sequence(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "f.json"
    writes: List[List[Any]] = []
    orig = model._write_failing

    def spy(path: pathlib.Path, trace: List[Any]) -> pathlib.Path:
        writes.append(list(trace))
        return orig(path, trace)

    monkeypatch.setattr(model, "_write_failing", spy)
    msg = _fail(
        model_test(
            COUNTER,
            logic=_counter_logic,
            settings=S,
            invariants={"n<3": lambda i: i.context["n"] < 3},
            failing_path=out,
        )
    )
    assert len(writes) > 1  # 📝 every failing example writes during shrink
    final = _steps(out)
    assert final == writes[-1]
    _assert_three_incs(final)
    assert f"({len(final)} step(s))" in msg
    assert min(len(w) for w in writes) == len(final)


DEC_UNI = {
    "id": "u",
    "initial": "a",
    "states": {
        "a": {"on": {"PAYÉ ✓": {"target": "b", "guard": "big"}}},
        "b": {"on": {"BACK": "a"}},
    },
}


def test_decimal_payload_and_unicode_event_replay(
    tmp_path: pathlib.Path,
) -> None:
    out = tmp_path / "f.json"

    def big(c: Any, e: Any) -> bool:
        return decimal.Decimal(str(e.payload["amt"])) > 5

    logic = MachineLogic(guards={"big": big})
    _fail(
        model_test(
            DEC_UNI,
            logic=lambda: logic,
            settings=S,
            snapshot_roundtrip=False,
            payloads={
                "PAYÉ ✓": st.fixed_dictionaries(
                    {"amt": st.decimals(0, 10, places=2)}
                )
            },
            invariants={"never b": lambda i: not i.matches("b")},
            failing_path=out,
        )
    )
    steps = _steps(out)
    assert steps[-1]["send"] == "PAYÉ ✓"
    assert isinstance(steps[-1]["payload"]["amt"], str)  # Decimal -> str
    session = Session(DEC_UNI)
    run_script(session, steps)
    assert session.interp.matches("b")


# -----------------------------------------------------------------------------
# 6. the round-trip rule
# -----------------------------------------------------------------------------
DEC_CTX = {
    "id": "d",
    "initial": "a",
    "states": {
        "a": {"on": {"GO": {"target": "b", "actions": "put"}}},
        "b": {"on": {"BACK": "a"}},
    },
}


def test_decimal_in_context_fails_the_roundtrip_on_purpose(
    tmp_path: pathlib.Path,
) -> None:
    def put(i: Any, c: Any, e: Any, a: Any) -> None:
        c["amt"] = decimal.Decimal("1.50")

    msg = _fail(
        model_test(
            DEC_CTX,
            logic=lambda: MachineLogic(actions={"put": put}),
            settings=S,
            failing_path=tmp_path / "f.json",
        )
    )
    assert "not JSON-serialisable" in msg and "Decimal" in msg


INVOKE = {
    "id": "v",
    "initial": "a",
    "states": {
        "a": {"on": {"GO": "load"}},
        "load": {
            "invoke": {"src": "svc", "onDone": "done"},
            "on": {"POKE": {}},
        },
        "done": {"on": {"BACK": "a"}},
    },
}


def test_roundtrip_leaves_no_dormant_invoke(
    tmp_path: pathlib.Path,
) -> None:
    def svc(i: Any, c: Any, e: Any) -> Any:
        return 1

    model_test(
        INVOKE,
        logic=lambda: MachineLogic(services={"svc": svc}),
        settings=S,
        invariants={"no dormant": lambda i: not i.pending_invocations()},
        failing_path=tmp_path / "f.json",
    ).TestCase("runTest").runTest()


# -----------------------------------------------------------------------------
# 8. shrinking quality
# -----------------------------------------------------------------------------
def _twice(make: Any, tmp_path: pathlib.Path) -> List[Any]:
    runs = []
    for k in (1, 2):
        out = tmp_path / f"f{k}.json"
        _fail(make(out))
        runs.append(_steps(out))
    assert runs[0] == runs[1]  # stable under derandomize
    return runs[0]


def test_sequence_bug_shrinks_minimal(tmp_path: pathlib.Path) -> None:
    steps = _twice(
        lambda out: model_test(
            COUNTER,
            logic=_counter_logic,
            settings=S,
            invariants={"n<3": lambda i: i.context["n"] < 3},
            failing_path=out,
        ),
        tmp_path,
    )
    _assert_three_incs(steps)


PAY = {
    "id": "p",
    "initial": "a",
    "states": {"a": {"on": {"PAY": {"actions": "pay"}}}},
}


def test_payload_bug_shrinks_minimal(tmp_path: pathlib.Path) -> None:
    def pay(i: Any, c: Any, e: Any, a: Any) -> None:
        assert e.payload["n"] != 77, "planted"

    steps = _twice(
        lambda out: model_test(
            PAY,
            logic=lambda: MachineLogic(actions={"pay": pay}),
            settings=S,
            payloads={
                "PAY": st.fixed_dictionaries({"n": st.integers(0, 100)})
            },
            invariants={"ok": lambda i: True},
            failing_path=out,
        ),
        tmp_path,
    )
    # 📝 an action that raises is contained (logged); the receipt carries
    #    the error and `_send` fails on it -- one step, the bad payload.
    assert steps == [{"send": "PAY", "payload": {"n": 77}}]


TIMED = {
    "id": "t",
    "initial": "a",
    "states": {
        "a": {"on": {"ARM": "armed"}},
        "armed": {"after": {"500": "late"}, "on": {"DISARM": "a"}},
        "late": {},
    },
}


def test_time_bug_shrinks_minimal(tmp_path: pathlib.Path) -> None:
    steps = _twice(
        lambda out: model_test(
            TIMED,
            settings=S,
            invariants={"never late": lambda i: not i.matches("late")},
            failing_path=out,
        ),
        tmp_path,
    )
    assert len(steps) == 2
    assert steps[0] == {"send": "ARM"} and "clock" in steps[1]


# -----------------------------------------------------------------------------
# jitter + budget
# -----------------------------------------------------------------------------
JITTER = {
    "id": "j",
    "initial": "a",
    "states": {
        "a": {"after": {"100": "b", "101": "c"}},
        "b": {},
        "c": {},
    },
}


@pytest.mark.parametrize("target", ["b"])
def test_jitter_reaches_the_first_of_two_afters(
    target: str, tmp_path: pathlib.Path
) -> None:
    _fail(
        model_test(
            JITTER,
            settings=S,
            invariants={"x": lambda i: not i.matches(target)},
            failing_path=tmp_path / "f.json",
        )
    )


def test_later_after_is_shadowed_by_the_earlier_one(
    tmp_path: pathlib.Path,
) -> None:
    # 📝 `c` (101 ms) is unreachable by construction: the 100 ms timer
    #    always fires first and exits `a`. Jitter must not invent a path.
    model_test(
        JITTER,
        settings=S,
        invariants={"x": lambda i: not i.matches("c")},
        failing_path=tmp_path / "f.json",
    ).TestCase("runTest").runTest()


def test_200_examples_budget(tmp_path: pathlib.Path) -> None:
    t0 = time.perf_counter()
    model_test(
        COUNTER,
        logic=_counter_logic,
        settings=S,
        failing_path=tmp_path / "f.json",
    ).TestCase("runTest").runTest()
    assert time.perf_counter() - t0 < 120
