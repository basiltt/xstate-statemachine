# tests/contrib/testing/test_battle_270_coverage_gate.py
"""#270 battle: the orders team gates CI on state & transition coverage.

Line coverage said 100 %; the chart had never seen `paymentFailed` or a
`CANCEL` from `awaitingPayment`. The team turns on `--xsm-coverage` with
fail-under gates and runs it the way CI does. Every leg is a `pytester`
session on the shipped `fastapi_orders/machine.json`. Pinned:

* **the gate catches the gap** -- a suite that only pays reports exactly
  the unvisited states / unhit transitions by name (`paymentFailed`,
  `awaitingPayment --CANCEL--> cancelled`, the `retryDelay` timers), and
  exits non-zero under `--xsm-fail-under-state-coverage=100`; adding the
  missing tests makes it pass;
* **every reporter agrees** -- `term`, `json:` and `html:` carry the same
  numbers; the JSON is `version: 1`, stable (two runs → byte-identical),
  round-trips through `reports_from_json`; the HTML is one file with no
  external refs;
* **`xsm coverage` CLI** renders the JSON (plain + styled), `--fail-under`
  exits 1, a corrupt file is one line;
* **what counts** -- a restored interpreter (`from_snapshot`) counts its
  configuration at `start()`; parallel configurations mark leaves AND
  ancestors; history pseudo-states are not in the denominator; a
  transition taken via `xsm_path.replay` counts; interpreters built
  directly (no fixture) count through the global registry; a machine
  rebuilt from the same JSON merges with the first (same key);
* **isolation** -- without `--xsm-coverage` nothing is registered
  (`plugins` global list untouched before/after), `-p
  no:xstate_statemachine` never fails the session, and two sessions in one
  process do not share counters;
* **xdist** -- `-n 2` merges workers; gate exit code identical to serial.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import textwrap
from typing import Any

import pytest

from .conftest import PLUGIN_ARGS, run

ROOT = pathlib.Path(__file__).resolve().parents[3]
CHART = ROOT / "examples" / "integrations" / "fastapi_orders" / "machine.json"
HAS_XDIST = importlib.util.find_spec("xdist") is not None

pytestmark = pytest.mark.timeout(300)

PRELUDE = (
    f"import json, sys, pytest\nsys.path.insert(0, {str(CHART.parent)!r})\n"
    f"CHART = {str(CHART)!r}\n"
)


def _mod(body: str) -> str:
    return PRELUDE + textwrap.dedent(body)


ONLY_PAY = """
@pytest.mark.xstate_machine(CHART)
def test_pay(xsm_interp, xsm_send_all):
    xsm_interp.send("ADD_ITEM", sku="tea", qty=1)
    xsm_send_all(xsm_interp, "CHECKOUT", "PAY")
    assert xsm_interp.matches("order.paid")
"""

FULL = ONLY_PAY + """
@pytest.mark.xstate_machine(CHART)
def test_every_configuration(xsm_path, xsm_interp, xsm_clock):
    xsm_path.replay(xsm_interp, xsm_clock)

@pytest.mark.xstate_machine(CHART)
def test_cancel_while_waiting(xsm_interp, xsm_send_all):
    xsm_interp.send("ADD_ITEM", sku="tea", qty=1)
    xsm_send_all(xsm_interp, "CHECKOUT", "CANCEL")
    assert xsm_interp.matches("order.cancelled")

@pytest.mark.xstate_machine(CHART, logic="logic:build_logic")
def test_retries_exhausted(xsm_interp, xsm_send_all, xsm_clock):
    # real logic: a declined card fails every attempt -> paymentFailed
    xsm_interp.send("ADD_ITEM", sku="tea", qty=1)
    xsm_interp.send("CHECKOUT")
    xsm_interp.send("PAY", card_token="tok_declined")
    for _ in range(6):
        xsm_clock.increment(60_000)
        if xsm_interp.matches("order.paymentFailed"):
            break
    assert xsm_interp.matches("order.paymentFailed")
    xsm_interp.send("CANCEL")
"""


def _json_report(pytester: Any) -> dict:
    return json.loads((pytester.path / "cov.json").read_text("utf-8"))


# -----------------------------------------------------------------------------
# 1. the gate catches the gap, by name
# -----------------------------------------------------------------------------
class TestGate:
    def test_only_pay_fails_the_gate_and_names_the_gap(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod(ONLY_PAY))
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=json:cov.json",
            "--xsm-fail-under-state-coverage=100",
        )
        assert r.ret != 0
        out = r.stdout.str()
        assert "FAIL xstate coverage" in out and "state coverage" in out
        rep = _json_report(xsm_pytester)["machines"][0]
        assert "order.paymentFailed" in rep["states"]["unvisited"]
        unhit = json.dumps(rep["transitions"]["unhit"])
        assert "retryDelay" in unhit and "CANCEL" in unhit
        assert rep["states"]["visited"] < rep["states"]["total"]

    def test_full_suite_passes_the_gate(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(_mod(FULL))
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=json:cov.json",
            "--xsm-fail-under-state-coverage=100",
        )
        rep = _json_report(xsm_pytester)["machines"][0]
        assert rep["states"]["unvisited"] == [], rep
        assert r.ret == 0, r.stdout.str()
        # transitions: everything the engine can take under stub logic
        assert rep["transitions"]["hit"] >= 13, rep["transitions"]["unhit"]

    def test_transition_gate_threshold_semantics(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod(ONLY_PAY))
        ok = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-transition-coverage=10",
        )
        assert ok.ret == 0
        bad = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-transition-coverage=90",
        )
        assert bad.ret != 0
        for weird in ("abc", "nan"):
            r = run(
                xsm_pytester,
                "--xsm-coverage",
                f"--xsm-fail-under-state-coverage={weird}",
            )
            assert r.ret != 0, weird
            assert "Traceback" not in r.stderr.str(), weird


# -----------------------------------------------------------------------------
# 2. reporters agree; JSON stable; HTML self-contained
# -----------------------------------------------------------------------------
class TestReporters:
    def test_term_json_html_agree_and_json_is_stable(
        self, xsm_pytester: Any
    ) -> None:
        from src.xstate_statemachine.coverage import reports_from_json

        xsm_pytester.makepyfile(_mod(ONLY_PAY))
        args = ("--xsm-coverage", "--xsm-coverage-report=json:cov.json")
        run(xsm_pytester, *args)
        first = (xsm_pytester.path / "cov.json").read_bytes()
        run(xsm_pytester, *args)
        assert (xsm_pytester.path / "cov.json").read_bytes() == first
        doc = json.loads(first)
        assert doc["version"] == 1
        reps = reports_from_json(first.decode("utf-8"))
        assert len(reps) == 1
        rep = reps[0]
        term = run(xsm_pytester, "--xsm-coverage").stdout.str()
        assert "---- xstate coverage ----" in term
        assert "paymentFailed" in term
        assert f"{rep.states_visited}/{rep.states_total}" in term
        assert f"{rep.transitions_hit}/{rep.transitions_total}" in term
        run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=html:cov.html",
        )
        html = (xsm_pytester.path / "cov.html").read_text("utf-8")
        assert "<html" in html.lower()
        assert 'src="http' not in html and 'href="http' not in html
        assert f"{rep.states_visited}/{rep.states_total}" in html
        assert "order.paymentFailed" in html

    def test_bad_report_spec_is_a_usage_error(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(_mod(ONLY_PAY))
        for spec in ("xml:out.xml", "term:foo", ""):
            r = run(
                xsm_pytester, "--xsm-coverage", f"--xsm-coverage-report={spec}"
            )
            assert r.ret != 0, spec
            assert "Traceback" not in r.stderr.str(), spec


# -----------------------------------------------------------------------------
# 3. xsm coverage CLI
# -----------------------------------------------------------------------------
class TestCLI:
    def test_render_plain_styled_fail_under_and_corrupt(
        self, xsm_pytester: Any, tmp_path: pathlib.Path
    ) -> None:
        import os
        import subprocess
        import sys

        xsm_pytester.makepyfile(_mod(ONLY_PAY))
        run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=json:cov.json",
        )
        cov = str(xsm_pytester.path / "cov.json")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

        def cli(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "xstate_statemachine",
                    "coverage",
                    *args,
                ],
                capture_output=True,
                text=True,
                errors="replace",
                env=env,
                cwd=str(ROOT),
                timeout=120,
            )

        plain = cli(cov, "--plain")
        assert plain.returncode == 0, plain.stderr
        assert "paymentFailed" in plain.stdout
        styled = cli(cov)
        assert styled.returncode == 0
        gate = cli(cov, "--plain", "--fail-under", "100")
        assert gate.returncode == 1 and "fail-under" in (
            gate.stderr + gate.stdout
        )
        bad = tmp_path / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        r = cli(str(bad), "--plain")
        assert r.returncode != 0 and "Traceback" not in r.stderr
        r = cli(str(tmp_path / "missing.json"), "--plain")
        assert r.returncode != 0 and "Traceback" not in r.stderr
        wrong = tmp_path / "v9.json"
        wrong.write_text(
            json.dumps({"version": 9, "machines": []}), encoding="utf-8"
        )
        r = cli(str(wrong), "--plain")
        assert r.returncode != 0 and "version" in (r.stderr + r.stdout)


# -----------------------------------------------------------------------------
# 4. what counts
# -----------------------------------------------------------------------------
class TestWhatCounts:
    def test_restored_direct_and_rebuilt_interpreters_count(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            from xstate_statemachine import (
                SyncInterpreter, SimulatedClock, create_machine, stub_logic,
            )
            RAW = json.loads(open(CHART, encoding="utf-8").read())

            @pytest.mark.xstate_machine(CHART)
            def test_restore_counts_configuration(xsm_interp, xsm_machine):
                xsm_interp.send("ADD_ITEM", sku="tea", qty=1)
                xsm_interp.send("CHECKOUT")
                blob = xsm_interp.get_snapshot()
                # a DIRECT interpreter on a REBUILT machine, from a snapshot:
                # counts awaitingPayment at start() through the global plugin
                m2 = create_machine(RAW, logic=stub_logic(RAW))
                r = SyncInterpreter.from_snapshot(blob, m2).start()
                r.send("CANCEL")
                assert r.matches("order.cancelled")
                r.stop()
            """))
        run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=json:cov.json",
        )
        doc = _json_report(xsm_pytester)
        assert len(doc["machines"]) == 1  # same key: merged, not two rows
        rep = doc["machines"][0]
        assert "order.cancelled" not in rep["states"]["unvisited"]
        assert "order.awaitingPayment" not in rep["states"]["unvisited"]
        assert not any(
            u["from"] == "order.awaitingPayment" and "CANCEL" in u["label"]
            for u in rep["transitions"]["unhit"]
        )

    def test_parallel_and_history_accounting(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(_mod("""
            CFG = {
              "id": "p", "initial": "work",
              "states": {
                "work": {"type": "parallel",
                         "on": {"PAUSE": "paused"},
                         "states": {
                           "a": {"initial": "a1", "states": {"a1": {"on": {"A": "a2"}}, "a2": {}}},
                           "b": {"initial": "b1", "states": {"b1": {"on": {"B": "b2"}}, "b2": {}}}}},
                "paused": {"on": {"RESUME": "work.hist"}},
              }}
            CFG["states"]["work"]["states"]["hist"] = {"type": "history", "history": "deep"}

            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_interp):
                xsm_interp.send("A")
                xsm_interp.send("PAUSE")
                xsm_interp.send("RESUME")
                assert xsm_interp.current_state_ids == {"p.work.a.a2", "p.work.b.b1"}
            """))
        run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=json:cov.json",
        )
        rep = _json_report(xsm_pytester)["machines"][0]
        # history pseudo-state is not a target; b2 was never visited
        assert rep["states"]["unvisited"] == ["p.work.b.b2"], rep["states"][
            "unvisited"
        ]
        assert rep["states"]["total"] == 8  # work,a,a1,a2,b,b1,b2,paused
        assert rep["transitions"]["hit"] >= 3  # A, PAUSE, RESUME


# -----------------------------------------------------------------------------
# 5. isolation
# -----------------------------------------------------------------------------
class TestIsolation:
    def test_no_flag_registers_nothing_and_opt_out_is_safe(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod(ONLY_PAY) + textwrap.dedent("""
                def test_registry_untouched():
                    from xstate_statemachine import plugins
                    assert not [
                        p for p in plugins.global_plugins()
                        if type(p).__name__ == "CoverageCollector"
                    ]
                """))
        r = run(xsm_pytester)
        r.assert_outcomes(passed=2)
        assert "xstate coverage" not in r.stdout.str()
        r2 = xsm_pytester.runpytest_inprocess(
            "-p",
            "no:xstate_statemachine",
            "-p",
            "no:django",
            "-q",
            "--xsm-coverage",
        )
        # the option does not exist without the plugin: usage error, no crash
        assert r2.ret != 0 and "Traceback" not in r2.stderr.str()

    def test_two_sessions_do_not_share_counters(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod(ONLY_PAY))
        run(
            xsm_pytester, "--xsm-coverage", "--xsm-coverage-report=json:a.json"
        )
        xsm_pytester.makepyfile(_mod("""
            @pytest.mark.xstate_machine(CHART)
            def test_nothing(xsm_interp):
                pass  # started only: the initial configuration
            """))
        run(
            xsm_pytester, "--xsm-coverage", "--xsm-coverage-report=json:b.json"
        )
        a = json.loads((xsm_pytester.path / "a.json").read_text("utf-8"))
        b = json.loads((xsm_pytester.path / "b.json").read_text("utf-8"))
        assert (
            a["machines"][0]["states"]["visited"]
            > b["machines"][0]["states"]["visited"]
        )


# -----------------------------------------------------------------------------
# 6. xdist
# -----------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_XDIST, reason="pytest-xdist not installed")
def test_xdist_merge_matches_serial(xsm_pytester: Any) -> None:
    xsm_pytester.makepyfile(_mod(FULL))
    run(
        xsm_pytester,
        "--xsm-coverage",
        "--xsm-coverage-report=json:serial.json",
    )
    r = xsm_pytester.runpytest_subprocess(
        *PLUGIN_ARGS,
        "-q",
        "-n",
        "2",
        "-p",
        "no:django",
        "--xsm-coverage",
        "--xsm-coverage-report=json:par.json",
        "--xsm-fail-under-state-coverage=100",
    )
    assert r.ret == 0, r.stdout.str()[-1500:]
    s = json.loads((xsm_pytester.path / "serial.json").read_text("utf-8"))
    p = json.loads((xsm_pytester.path / "par.json").read_text("utf-8"))
    assert s == p
