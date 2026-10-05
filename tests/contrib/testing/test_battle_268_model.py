"""Battle #268 (adversary B): model-based testing (`model_test`).

Defects pinned here:

* a chart whose root reaches a top-level final state (`status == "done"`)
  kept its last configuration, so event rules stayed enabled and the model
  FAILED with `InterpreterStoppedError` ("event dropped") -- a false bug
  report on every chart with a reachable root final (`DebtState.json`).
* a transition that is taken but lands back on the same configuration via
  `always` reported `Receipt(changed=False, denied=True)` (a sibling guard
  was refused on the way) and the model failed with "generated a denied
  event" although `can()` had accepted it (`Hierarchy.json`).

Confirmed behaviour: a planted 3-event bug is found and SHRUNK to exactly
those 3 events; `deadline=None` is pinned whatever `settings=` says; on
small corpus charts the model reaches every state BFS reaches.
"""

from __future__ import annotations

import json
import pathlib

import pytest

pytest.importorskip("hypothesis")

from hypothesis import settings  # noqa: E402
from hypothesis.stateful import run_state_machine_as_test  # noqa: E402

from xstate_statemachine import MachineLogic, create_machine  # noqa: E402
from xstate_statemachine.contrib.testing import model_test  # noqa: E402
from xstate_statemachine.graph import reachable_states  # noqa: E402
from xstate_statemachine.testing_utils import stub_logic  # noqa: E402

from .conftest import CORPUS  # noqa: E402

pytestmark = pytest.mark.timeout(300)


def _settings(n: int = 100) -> settings:
    return settings(max_examples=n, derandomize=True, database=None)


def _run(cls: object) -> None:
    run_state_machine_as_test(cls, settings=cls.TestCase.settings)


class TestFalseFailures:
    def test_root_final_settles_instead_of_failing(self, tmp_path) -> None:
        cfg = {
            "id": "done",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": "end", "STAY": "a"}},
                "end": {"type": "final", "on": {"STAY": "a"}},
            },
        }
        _run(
            model_test(
                cfg, settings=_settings(), failing_path=tmp_path / "f.json"
            )
        )
        assert not (tmp_path / "f.json").exists()

    def test_debtstate_corpus(self, tmp_path) -> None:
        _run(
            model_test(
                CORPUS / "DebtState.json",
                settings=_settings(),
                failing_path=tmp_path / "f.json",
            )
        )

    def test_always_roundtrip_is_not_denied(self, tmp_path) -> None:
        _run(
            model_test(
                CORPUS / "Hierarchy.json",
                settings=_settings(),
                failing_path=tmp_path / "f.json",
            )
        )


class TestShrinking:
    def test_planted_three_event_bug_shrinks(self, tmp_path) -> None:
        cfg = {
            "id": "p",
            "initial": "s",
            "context": {"n": 0, "seq": []},
            "states": {"s": {"on": {k: {"actions": "rec"} for k in "ABCD"}}},
        }

        def rec(i, ctx, e, a) -> None:
            ctx["seq"] = (ctx["seq"] + [e.type])[-3:]
            if ctx["seq"] == ["A", "B", "C"]:
                ctx["n"] = -1

        out = tmp_path / "f.json"
        cls = model_test(
            cfg,
            logic=lambda: MachineLogic(actions={"rec": rec}),
            invariants={"nonneg": lambda i: i.context["n"] >= 0},
            settings=_settings(500),
            failing_path=out,
        )
        with pytest.raises(AssertionError, match="nonneg"):
            _run(cls)
        steps = [c for c in json.loads(out.read_text()) if "send" in c]
        assert [c["send"] for c in steps] == ["A", "B", "C"]

    def test_deadline_pinned_to_none(self) -> None:
        cfg = {"id": "t", "initial": "a", "states": {"a": {}}}
        cls = model_test(cfg, settings=settings(deadline=50))
        assert cls.TestCase.settings.deadline is None


class TestGuardsAndTimers:
    def test_refused_guard_is_not_sent(self, tmp_path) -> None:
        cfg = {
            "id": "g",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": {"target": "b", "guard": "no"}}},
                "b": {},
            },
        }
        cls = model_test(
            cfg,
            logic=lambda: MachineLogic(guards={"no": lambda c, e: False}),
            invariants={"never b": lambda i: not i.matches("b")},
            settings=_settings(),
            failing_path=tmp_path / "f.json",
        )
        _run(cls)

    def test_after_timer_reached_by_clock_rule(self, tmp_path) -> None:
        cfg = {
            "id": "t",
            "initial": "a",
            "states": {"a": {"after": {"1000": "b"}}, "b": {}},
        }
        cls = model_test(
            cfg,
            invariants={"never b": lambda i: not i.matches("b")},
            settings=_settings(),
            failing_path=tmp_path / "f.json",
        )
        with pytest.raises(AssertionError, match="never b"):
            _run(cls)

    def test_parallel_regions(self, tmp_path) -> None:
        cfg = {
            "id": "par",
            "type": "parallel",
            "states": {
                "x": {
                    "initial": "x1",
                    "states": {"x1": {"on": {"X": "x2"}}, "x2": {}},
                },
                "y": {
                    "initial": "y1",
                    "states": {"y1": {"on": {"Y": "y2"}}, "y2": {}},
                },
            },
        }
        cls = model_test(
            cfg,
            invariants={
                "not both": lambda i: not (
                    i.matches("x.x2") and i.matches("y.y2")
                )
            },
            settings=_settings(),
            failing_path=tmp_path / "f.json",
        )
        with pytest.raises(AssertionError, match="not both"):
            _run(cls)


@pytest.mark.parametrize(
    "chart",
    [
        "AdvancePayment.json",
        "AuthenticationFull.json",
        "HelloWorld.json",
        "HeizstabNoAI.json",
        "Joyride.json",
    ],
)
def test_reaches_every_bfs_state(chart: str, tmp_path: pathlib.Path) -> None:
    path = CORPUS / chart
    cfg = json.loads(path.read_text(encoding="utf-8"))
    bfs = set(reachable_states(create_machine(cfg, logic=stub_logic(cfg))))
    seen: set = set()

    def record(i: object) -> bool:
        seen.update(n.id for n in i._active_state_nodes)  # type: ignore
        return True

    _run(
        model_test(
            path,
            invariants={"record": record},
            settings=_settings(500),
            failing_path=tmp_path / "f.json",
        )
    )
    assert bfs <= seen, sorted(bfs - seen)
