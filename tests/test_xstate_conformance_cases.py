# /tests/test_xstate_conformance_cases.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: the shared XState v5 conformance cases
# -----------------------------------------------------------------------------
# The Rust port (`xstate-statemachine-rs`) keeps an executable specification
# of the statechart engine in `conformance/cases/*.json`: a machine, stubbed
# logic, a list of steps and the observations the REAL XState engine
# (xstate 5.33.3 under Node) made -- `expected.xstate`. This module replays
# every case on the Python engine and asserts it observes exactly what XState
# did, so the engine's XState parity is a permanent regression test.
#
# 🔗 Sibling-checkout test, the same convention as the Rust repository's
#    `XSM_PYTHON`: the cases are read from `XSM_CONFORMANCE_CASES` (a
#    directory) when set, else from the Rust checkout next to this one
#    (`../../RustProjects/xstate-statemachine-rs/conformance/cases`). Without
#    either the whole module is skipped with a message saying so.
#
# The harness mirrors `conformance/tools/generate_expected.py`'s Python
# oracle: `stub_logic` with the case's guards / service results, failing
# services for `{"error": ...}`, named delays, a `SimulatedClock`, and one
# observation after `start()` and after every step.
# -----------------------------------------------------------------------------
"""Replay the shared conformance cases and compare with XState v5."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from src.xstate_statemachine import (
    SimulatedClock,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.testing_utils import stub_logic

ROOT = Path(__file__).resolve().parents[1]
_SIBLING = (
    ROOT.parents[1]
    / "RustProjects"
    / "xstate-statemachine-rs"
    / "conformance"
    / "cases"
)
CASES_DIR = Path(os.environ.get("XSM_CONFORMANCE_CASES") or _SIBLING)

#: The keys of an observation the comparison covers (as the generator's).
OBSERVATION_KEYS = ("state_ids", "context", "actions", "status", "guards")


def _load_cases() -> List[Dict[str, Any]]:
    if not CASES_DIR.is_dir():
        return []
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(CASES_DIR.glob("*.json"))
    ]


CASES = _load_cases()

pytestmark = pytest.mark.skipif(
    not CASES,
    reason=(
        f"conformance cases not found at {CASES_DIR} -- check out "
        f"xstate-statemachine-rs next to this repository or set "
        f"XSM_CONFORMANCE_CASES to its conformance/cases directory"
    ),
)


def _build(
    case: Dict[str, Any], ran: List[str], guard_log: Optional[List[str]]
) -> Any:
    """The case's machine with the generator's stub logic."""
    config = json.loads(json.dumps(case["machine"]))  # private deep copy
    spec = case.get("logic", {})
    services = spec.get("services", {})
    logic = stub_logic(
        config,
        ran=ran,
        guards=dict(spec.get("guards", {})),
        service_results={
            name: entry.get("result")
            for name, entry in services.items()
            if "error" not in entry
        },
        guard_log=guard_log,
    )
    for name, entry in services.items():
        if "error" in entry:
            message = str(entry["error"])

            def failing(*_args: Any, _m: str = message, **_kw: Any) -> Any:
                raise RuntimeError(_m)

            logic.services[name] = failing  # type: ignore[index]
    for name, ms in spec.get("delays", {}).items():
        logic.delays[name] = ms  # type: ignore[index]
    return create_machine(config, logic=logic)


def _replay(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Observations after `start()` and after every step."""
    ran: List[str] = []
    # `logic.record_guards`: every guard evaluation, in order.
    guard_log: Optional[List[str]] = (
        [] if case.get("logic", {}).get("record_guards") is True else None
    )
    clock = SimulatedClock()
    interp = SyncInterpreter(_build(case, ran, guard_log), clock=clock)

    def observe() -> Dict[str, Any]:
        out = {
            "state_ids": sorted(interp.current_state_ids),
            "context": json.loads(json.dumps(interp.context)),
            "actions": ran[:],
            "status": interp.status,
        }
        del ran[:]
        if interp.status == "done":
            out["output"] = getattr(interp, "output", None)
        if guard_log is not None:
            out["guards"] = guard_log[:]
            del guard_log[:]
        return out

    interp.start()
    observations = [observe()]
    for step in case.get("steps", []):
        if "send" in step:
            event = step["send"]
            if isinstance(event, str):
                interp.send(event)
            else:
                payload = {k: v for k, v in event.items() if k != "type"}
                interp.send(event["type"], **payload)
        elif "send_batch" in step:
            # Queued together, then processed in one drain.
            interp.send_events(list(step["send_batch"]))
        elif "advance_ms" in step:
            clock.increment(step["advance_ms"])
        else:  # pragma: no cover - a malformed fixture
            raise AssertionError(f"{case['name']}: unknown step {step!r}")
        observations.append(observe())
    return observations


@pytest.fixture(autouse=True)
def _quiet() -> Any:
    # Failing stub services are expected in the error-path cases.
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


@pytest.mark.parametrize(
    "case", CASES, ids=[case["name"] for case in CASES] or None
)
def test_python_engine_observes_what_xstate_observed(
    case: Dict[str, Any],
) -> None:
    expected = case["expected"]["xstate"]
    want = [expected["initial"], *expected["steps"]]
    got = _replay(case)
    assert len(got) == len(want)
    for index, (observed, oracle) in enumerate(zip(got, want)):
        label = "initial" if index == 0 else f"step {index - 1}"
        for key in OBSERVATION_KEYS:
            assert observed.get(key) == oracle.get(key), (
                f"{case['name']} {label}: {key}: "
                f"xstate={oracle.get(key)!r} python={observed.get(key)!r}"
            )
        if oracle["status"] == "done":
            assert observed.get("output") == oracle.get(
                "output"
            ), f"{case['name']} {label}: output"


def test_every_case_was_loaded() -> None:
    """The directory is the Rust repository's, not an empty stand-in."""
    names = [case["name"] for case in CASES]
    assert len(names) == len(set(names))
    assert len(names) >= 37
