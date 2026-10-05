"""Battle test #271 (B): ``xsm simulate --script`` replay.

The ``model_test`` failing artefact is only useful if ``--script`` replays
it faithfully and refuses malformed input in ONE line (exit 2), never a
traceback. Before the fix every malformed shape below escaped as a Python
traceback (exit 1), and ``--script`` + ``--events`` silently concatenated
(the events ran FIRST, so a replay was not the recorded run).
"""

from __future__ import annotations

import io
import json
import pathlib
import time
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from typing import Any, Dict, List, Tuple

import pytest

from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.simulate import (
    load_script,
    run_simulate,
)

HERE = pathlib.Path(__file__).resolve().parent
REFUND = (
    HERE.parent / "contrib" / "testing" / "examples" / "refund.json"
).resolve()

GUARDED = {
    "id": "g",
    "initial": "a",
    "context": {"n": 0},
    "states": {
        "a": {
            "on": {
                "GÖ→": {"target": "b", "guard": "ok"},
                "TICK": {
                    "actions": {
                        "type": "xstate.assign",
                        "params": {"assignment": {"n": 1}},
                    }
                },
            }
        },
        "b": {"after": {"500": "c"}},
        "c": {},
    },
}


def _sim(tmp_path, script: Any, *args, chart=None, **kw) -> Tuple[int, str]:
    path = tmp_path / "s.json"
    if isinstance(script, str):
        path.write_text(script, encoding="utf-8")
    else:
        path.write_text(json.dumps(script), encoding="utf-8")
    if chart is None:
        machine = REFUND
    else:
        machine = tmp_path / "m.json"
        machine.write_text(json.dumps(chart), encoding="utf-8")
    out, err = io.StringIO(), io.StringIO()
    code = 0
    reset_console()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            run_simulate(str(machine), script=str(path), **kw)
        except SystemExit as exc:
            code = int(exc.code or 0)
        finally:
            reset_console()
    return code, out.getvalue() + err.getvalue()


# =============================================================================
# malformed scripts: one line, exit 2
# =============================================================================
BAD: List[Tuple[str, str, str]] = [
    ("bad-json", "{bad", "not valid JSON"),
    ("object", '{"send": "ADD"}', "expected a JSON list"),
    ("int-step", "[1]", "step 1: expected an object"),
    ("no-send", '[{"payload": {}}]', "unknown command"),
    ("empty-send", '[{"send": ""}]', "'send' must be an event name"),
    ("list-payload", '[{"send": "ADD", "payload": [1]}]', "'payload'"),
    ("neg-clock", '[{"send": "ADD"}, {"clock": -5}]', "step 2"),
    ("str-clock", '[{"clock": "abc"}]', "'clock' must be a number"),
    ("bool-clock", '[{"clock": true}]', "'clock' must be a number"),
    ("inf-clock", '[{"clock": 1e999}]', "non-negative"),
    ("str-value", '[{"guard": "g", "value": "false"}]', "true or false"),
]


@pytest.mark.parametrize(
    "body, needle", [b[1:] for b in BAD], ids=[b[0] for b in BAD]
)
def test_malformed_script_is_one_line_exit_2(tmp_path, body, needle):
    code, out = _sim(tmp_path, body)
    assert code == 2
    assert needle in out
    assert "Traceback" not in out


def test_missing_script_file_is_exit_2(tmp_path) -> None:
    out = io.StringIO()
    reset_console()
    with redirect_stdout(out), redirect_stderr(out):
        with pytest.raises(SystemExit) as exc:
            run_simulate(str(REFUND), script=str(tmp_path / "nope.json"))
        reset_console()
    assert exc.value.code == 2
    assert "--script" in out.getvalue()


def test_script_plus_events_is_refused(tmp_path) -> None:
    code, out = _sim(tmp_path, [{"send": "ADD"}], events="ADD")
    assert code == 2
    assert "cannot be combined" in out


def test_loader_never_evaluates(tmp_path) -> None:
    p = tmp_path / "s.json"
    p.write_text("[{\"send\": \"__import__('os').system('x')\"}]", "utf-8")
    assert load_script(str(p))[0]["send"].startswith("__import__")


# =============================================================================
# faithful replay
# =============================================================================
def test_refund_artefact_replays_to_the_violation(tmp_path) -> None:
    trace = [{"send": e} for e in ("ADD", "PAY", "REFUND", "REFUND")]
    code, out = _sim(tmp_path, trace, as_json=True)
    assert code == 0
    data = json.loads(out)
    assert data["context"] == {"total": -10}
    assert data["active"] == ["refund.refunded"]


def test_unicode_event_guard_flip_and_clock(tmp_path) -> None:
    script = [
        {"send": "GÖ→"},  # guard True by default in sim
        {"undo": True},
        {"guard": "ok", "value": False},
        {"send": "GÖ→"},
        {"guard": "ok", "value": True},
        {"send": "GÖ→"},
        {"clock": 500},
    ]
    code, out = _sim(tmp_path, script, chart=GUARDED, as_json=True)
    assert code == 0, out
    data = json.loads(out)
    assert data["active"] == ["g.c"]
    assert data["clock_ms"] == 500


def test_script_guard_flip_overrides_guards_false(tmp_path) -> None:
    """``--guards-false`` is the starting value; a script flip wins from
    its step on (documented precedence)."""
    script = [{"send": "GÖ→"}, {"guard": "ok", "value": True}, {"send": "GÖ→"}]
    code, out = _sim(
        tmp_path, script, chart=GUARDED, as_json=True, guards_false="ok"
    )
    data = json.loads(out)
    assert [h["label"] for h in data["history"]] == ["GÖ→", "GÖ→"]
    assert data["active"] == ["g.b"]
    assert data["history"][0]["after"] == ["g.a"]


def test_payload_with_decimal_and_nested_values(tmp_path) -> None:
    trace: List[Dict[str, Any]] = [
        {
            "send": "ADD",
            "payload": {"amount": Decimal("1.10"), "x": {"y": ["é", None]}},
        }
    ]
    blob = json.dumps(trace, default=str)  # exactly what the writer does
    code, out = _sim(tmp_path, blob, as_json=True)
    assert code == 0
    assert json.loads(out)["context"] == {"total": 10}


def test_json_output_is_valid_and_ends_in_state_and_context(tmp_path):
    code, out = _sim(tmp_path, [{"send": "ADD"}], as_json=True)
    data = json.loads(out)
    assert {"active", "context", "status"} <= set(data)


def test_ten_thousand_step_script_is_fast(tmp_path) -> None:
    script = [{"send": "ADD"}] + [{"send": "ADD"}] * 9_999
    start = time.perf_counter()
    code, out = _sim(tmp_path, script, as_json=True)
    elapsed = time.perf_counter() - start
    assert code == 0
    assert len(json.loads(out)["history"]) == 10_000
    assert elapsed < 60, elapsed
