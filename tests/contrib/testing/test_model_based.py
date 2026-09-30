"""`model_test` / `events_strategy` (#271): Hypothesis model-based testing
generated from the chart."""

from __future__ import annotations

import io
import json
import logging
import pathlib
import sys
import textwrap
from contextlib import redirect_stdout
from typing import Any, Dict, List

import pytest

hypothesis = pytest.importorskip("hypothesis")

from hypothesis import HealthCheck, given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402
from hypothesis.stateful import run_state_machine_as_test  # noqa: E402

from src.xstate_statemachine import (  # noqa: E402
    MachineLogic,
    PluginBase,
    SyncInterpreter,
    create_machine,
    plugins,
)
from src.xstate_statemachine.clock import SimulatedClock  # noqa: E402
from src.xstate_statemachine.contrib.testing import (
    model as model_mod,
)  # noqa: E402
from src.xstate_statemachine.contrib.testing.model import (  # noqa: E402
    events_strategy,
    model_test,
    payload_strategy,
)
from src.xstate_statemachine.coverage import CoverageCollector  # noqa: E402
from src.xstate_statemachine.exceptions import MissingExtraError  # noqa: E402

from .conftest import run  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REFUND = HERE / "examples" / "refund.json"
FAST = settings(
    max_examples=150,
    derandomize=True,
    database=None,
    suppress_health_check=list(HealthCheck),
)


@pytest.fixture(autouse=True)
def _quiet():
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


def _run(cls: Any) -> None:
    run_state_machine_as_test(cls, settings=cls.TestCase.settings)


def _cli(argv: List[str]) -> str:
    from src.xstate_statemachine.cli.__main__ import main
    from src.xstate_statemachine.cli.commands import reset_console

    reset_console()
    saved, sys.argv = sys.argv, ["xsm", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            try:
                main()
            except SystemExit:
                pass
    finally:
        sys.argv = saved
        reset_console()
    return buf.getvalue()


class _Receipts(PluginBase):
    def __init__(self) -> None:
        self.receipts: List[Any] = []
        self.unhandled: List[str] = []

    def on_event_processed(self, interpreter, event, receipt) -> None:
        self.receipts.append((event.type, receipt))

    def on_unhandled_event(self, interpreter, event, *a: Any) -> None:
        self.unhandled.append(event.type)


@pytest.fixture
def observe():
    rec = _Receipts()
    plugins.register_global(rec)
    yield rec
    plugins.unregister_global(rec)


# =============================================================================
# The seeded bug
# =============================================================================
def test_seeded_refund_bug_is_found_shrunk_and_replayable(tmp_path) -> None:
    failing = tmp_path / "failing.json"
    cls = model_test(
        REFUND,
        invariants={"total >= 0": lambda i: i.context["total"] >= 0},
        settings=FAST,
        failing_path=failing,
    )
    with pytest.raises(AssertionError) as info:
        _run(cls)
    message = str(info.value)
    assert "invariant 'total >= 0' violated" in message
    assert str(failing) in message
    assert "xsm simulate" in message
    script = json.loads(failing.read_text("utf-8"))
    assert 1 <= len(script) <= 4
    assert [c.get("send") for c in script] == [
        "ADD",
        "PAY",
        "REFUND",
        "REFUND",
    ]
    out = _cli(["simulate", str(REFUND), "--script", str(failing), "--json"])
    state = json.loads(out)
    assert state["context"]["total"] < 0  # the same violation, replayed
    assert state["active"] == ["refund.refunded"]


def test_default_failing_path_is_next_to_the_caller_or_failing_dir(
    tmp_path, monkeypatch
) -> None:
    cls = model_test(
        REFUND, invariants={"neg": lambda i: i.context["total"] >= 0}
    )
    cls.TestCase.settings = FAST
    monkeypatch.setattr(model_mod, "FAILING_DIR", tmp_path)
    with pytest.raises(AssertionError):
        _run(cls)
    assert (tmp_path / "failing.json").is_file()
    monkeypatch.setattr(model_mod, "FAILING_DIR", None)
    assert model_mod._failing_path(HERE) == HERE / "failing.json"


# =============================================================================
# Only legal sequences; payload-first can()
# =============================================================================
GATED = {
    "id": "gated",
    "initial": "idle",
    "context": {"n": 0},
    "states": {
        "idle": {
            "on": {
                "ADD": {
                    "target": "busy",
                    "guard": "positive",
                    "actions": "add",
                }
            }
        },
        "busy": {
            "on": {
                "DONE": "idle",
                "ADD": {"guard": "positive", "actions": "add"},
            }
        },
    },
}


def _gated_logic() -> MachineLogic:
    def positive(ctx: Dict[str, Any], e: Any) -> bool:
        return e.payload.get("qty", 0) > 0

    def add(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        ctx["n"] += e.payload["qty"]

    return MachineLogic(guards={"positive": positive}, actions={"add": add})


def test_only_legal_sequences_with_real_payload_guards(observe) -> None:
    cls = model_test(
        GATED,
        logic=_gated_logic,
        payloads={"ADD": st.fixed_dictionaries({"qty": st.integers(-3, 3)})},
        invariants={"n never negative": lambda i: i.context["n"] >= 0},
        settings=FAST,
    )
    _run(cls)
    sent = [(t, r) for t, r in observe.receipts if t in ("ADD", "DONE")]
    assert sent, "nothing was generated"
    assert not [r for _, r in sent if r.denied]
    assert observe.unhandled == []


def test_allow_denied_sends_refused_events(observe) -> None:
    cls = model_test(
        GATED,
        logic=_gated_logic(),
        payloads={"ADD": st.fixed_dictionaries({"qty": st.integers(-3, 3)})},
        allow_denied=True,
        settings=FAST,
    )
    _run(cls)
    assert any(r.denied for t, r in observe.receipts if t == "ADD")


# =============================================================================
# snapshot_roundtrip, clock, parallel, guard_flip
# =============================================================================
def test_snapshot_roundtrip_catches_unserialisable_context(tmp_path) -> None:
    cfg = {
        "id": "leaky",
        "initial": "a",
        "context": {},
        "states": {
            "a": {"on": {"GO": {"target": "b", "actions": "grab"}}},
            "b": {},
        },
    }

    def grab(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        ctx["conn"] = object()

    logic = MachineLogic(actions={"grab": grab})
    cls = model_test(
        cfg, logic=logic, settings=FAST, failing_path=tmp_path / "f.json"
    )
    with pytest.raises(AssertionError, match="not JSON-serialisable"):
        _run(cls)
    no_rt = model_test(
        cfg, logic=logic, settings=FAST, snapshot_roundtrip=False
    )
    _run(no_rt)  # the same machine passes without the round-trip rule


TIMED = {
    "id": "timed",
    "initial": "idle",
    "states": {
        "idle": {"on": {"START": "waiting"}},
        "waiting": {
            "on": {"CANCEL": "idle"},
            "after": {"1000": "expired"},
        },
        "expired": {"on": {"RESET": "idle"}, "after": {"slow": "idle"}},
    },
}


def test_clock_rule_hits_after_transitions_in_the_coverage_report() -> None:
    cov = CoverageCollector()
    plugins.register_global(cov)
    try:
        cfg = json.loads(json.dumps(TIMED))
        from src.xstate_statemachine.testing_utils import stub_logic

        logic = stub_logic(cfg)
        logic.delays["slow"] = 5000
        _run(model_test(cfg, logic=logic, settings=FAST))
    finally:
        plugins.unregister_global(cov)
    (machine,) = cov.machines()
    labels = {lbl for _, lbl, _ in cov.report(machine).unhit}
    assert "after '1000'" not in labels and "after 1000" not in labels
    report = cov.report(machine)
    assert report.transitions_hit == report.transitions_total


def test_clock_false_never_fires_timers() -> None:
    cov = CoverageCollector()
    plugins.register_global(cov)
    try:
        _run(model_test(TIMED, clock=False, settings=FAST))
    finally:
        plugins.unregister_global(cov)
    (machine,) = cov.machines()
    assert "timed.expired" in cov.report(machine).unvisited


PARALLEL = {
    "id": "par",
    "type": "parallel",
    "states": {
        "r1": {
            "initial": "off",
            "states": {"off": {"on": {"A": "on"}}, "on": {}},
        },
        "r2": {
            "initial": "off",
            "states": {"off": {"on": {"B": "on"}}, "on": {}},
        },
    },
}


def test_state_assertions_run_in_parallel_configurations(tmp_path) -> None:
    seen: List[str] = []

    def r1_on(interp: Any) -> bool:
        seen.append("r1")
        return not interp.matches("par.r2.on")

    cls = model_test(
        PARALLEL,
        state_assertions={"par.r1.on": r1_on},
        settings=FAST,
        failing_path=tmp_path / "f.json",
    )
    with pytest.raises(AssertionError, match="state assertion 'par.r1.on'"):
        _run(cls)
    assert seen
    script = json.loads((tmp_path / "f.json").read_text("utf-8"))
    assert sorted(c["send"] for c in script) == ["A", "B"]


def test_guard_flip_explores_the_false_branch(tmp_path) -> None:
    cfg = {
        "id": "flip",
        "initial": "a",
        "states": {
            "a": {
                "on": {
                    "GO": [
                        {"target": "ok", "guard": "allowed"},
                        {"target": "no"},
                    ]
                }
            },
            "ok": {},
            "no": {},
        },
    }
    never_no = {"never no": lambda i: not i.matches("flip.no")}
    _run(model_test(cfg, invariants=never_no, settings=FAST))  # guard True
    failing = tmp_path / "f.json"
    cls = model_test(
        cfg,
        invariants=never_no,
        guard_flip=True,
        settings=FAST,
        failing_path=failing,
    )
    with pytest.raises(AssertionError):
        _run(cls)
    script = json.loads(failing.read_text("utf-8"))
    assert {"guard": "allowed", "value": False} in script
    path = tmp_path / "flip.json"
    path.write_text(json.dumps(cfg), "utf-8")
    state = json.loads(
        _cli(["simulate", str(path), "--script", str(failing), "--json"])
    )
    assert state["active"] == ["flip.no"]


# =============================================================================
# Payload inference, events_strategy, errors
# =============================================================================
def test_payload_inferred_from_pydantic_event_models() -> None:
    pytest.importorskip("pydantic")
    from typing import Literal, Optional

    from src.xstate_statemachine.contrib.pydantic import (
        EventModel,
        events_union,
    )

    class Add(EventModel):
        type: Literal["ADD"] = "ADD"
        qty: int
        note: Optional[str] = None
        kind: Literal["a", "b"] = "a"

    seen: List[Dict[str, Any]] = []

    def positive(ctx: Any, e: Any) -> bool:
        seen.append(dict(e.payload))
        return e.payload["qty"] > 0

    cfg = {
        "id": "typed",
        "initial": "idle",
        "states": {
            "idle": {"on": {"ADD": {"target": "done", "guard": "positive"}}},
            "done": {},
        },
    }
    machine = create_machine(
        cfg,
        logic=MachineLogic(guards={"positive": positive}),
        event_schemas=events_union(Add),
    )
    _run(model_test(machine, settings=FAST))
    assert seen and all(isinstance(p["qty"], int) for p in seen)
    assert any(p["qty"] > 0 for p in seen)

    class Blob(EventModel):
        type: Literal["BLOB"] = "BLOB"
        data: Dict[str, Any]

    with pytest.raises(ValueError, match="cannot infer"):
        payload_strategy(Blob)
    assert payload_strategy(object()) is not None


@given(seq=events_strategy(TIMED, length=6))
@settings(max_examples=40, database=None, deadline=None)
def test_events_strategy_yields_legal_sequences(seq: List[str]) -> None:
    from src.xstate_statemachine.testing_utils import stub_logic

    m = create_machine(TIMED, logic=stub_logic(TIMED))
    interp = SyncInterpreter(m, clock=SimulatedClock()).start()
    for ev in seq:
        assert interp.can(ev), (seq, ev)
        interp.send(ev)
    assert len(seq) <= 6


def test_configuration_errors_are_loud() -> None:
    real = MachineLogic(
        guards={"positive": lambda c, e: True},
        actions={"add": lambda *a: None},
    )
    with pytest.raises(ValueError, match="guard_flip"):
        model_test(GATED, logic=real, guard_flip=True)
    with pytest.raises(ValueError, match="does not declare"):
        model_test(GATED, payloads={"NOPE": st.just({})})
    with pytest.raises(TypeError):
        model_test(42)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="MachineLogic"):
        model_test(GATED, logic=lambda: 1)
    with pytest.raises(ValueError, match="already built"):
        model_test(create_machine(TIMED, logic=MachineLogic()), logic=real)


def test_missing_hypothesis_raises_missing_extra(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "hypothesis", None)
    with pytest.raises(MissingExtraError, match="testing"):
        model_test(REFUND)
    with pytest.raises(MissingExtraError):
        events_strategy(REFUND)


# =============================================================================
# pytest collection
# =============================================================================
def test_model_test_class_is_collected_by_pytest(xsm_pytester) -> None:
    (xsm_pytester.path / "refund.json").write_text(
        REFUND.read_text("utf-8"), "utf-8"
    )
    xsm_pytester.makepyfile(textwrap.dedent("""
        import pathlib
        from hypothesis import settings
        from xstate_statemachine.contrib.testing import model_test

        HERE = pathlib.Path(__file__).parent
        S = settings(max_examples=100, database=None, derandomize=True)
        TestGood = model_test(HERE / "refund.json", settings=S)
        TestBad = model_test(
            HERE / "refund.json",
            invariants={"neg": lambda i: i.context["total"] >= 0},
            settings=S,
        )
        """))
    out = xsm_pytester.path / "out"
    result = run(xsm_pytester, f"--xsm-failing-dir={out}")
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["*written to*failing.json*"])
    assert (out / "failing.json").is_file()
    assert model_mod.FAILING_DIR is None  # reset at unconfigure
