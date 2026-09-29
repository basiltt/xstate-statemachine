"""`--xsm-coverage` of the `[testing]` plugin (#270), exercised through
throw-away `pytester` sessions."""

from __future__ import annotations

import json
import textwrap

from .conftest import CORPUS, run

PAYMENT = (CORPUS / "AdvancePayment.json").as_posix()

TOGGLE = {
    "id": "toggle",
    "initial": "off",
    "states": {
        "off": {"on": {"TOGGLE": "on"}},
        "on": {"on": {"TOGGLE": "off", "RESET": "off"}},
    },
}


TRIANGLE = {
    "id": "tri",
    "initial": "off",
    "states": {
        "off": {"on": {"GO": "on", "SKIP": "mid"}},
        "on": {"on": {"GO": "mid"}},
        "mid": {"on": {"BACK": "on"}},
    },
}


def _mod(body: str) -> str:
    return "import pytest\n" + textwrap.dedent(body)


# =============================================================================
# --xsm-coverage
# =============================================================================
NEVER_RESET = _mod(f"""
    CFG = {TOGGLE!r}
    @pytest.mark.xstate_machine(CFG)
    def test_toggle(xsm_interp, xsm_send_all):
        xsm_send_all(xsm_interp, "TOGGLE", "TOGGLE")
    """)


class TestCoverage:
    def test_noop_without_the_flag(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(NEVER_RESET)
        result = run(xsm_pytester)
        result.assert_outcomes(passed=1)
        assert "xstate coverage" not in result.stdout.str()
        from xstate_statemachine.plugins import global_plugins

        assert global_plugins() == []

    def test_unhit_reset_reported_and_gate_fails(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(NEVER_RESET)
        result = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-transition-coverage=100",
        )
        result.assert_outcomes(passed=1)
        assert result.ret == 1
        result.stdout.fnmatch_lines(
            [
                "---- xstate coverage ----",
                "toggle*states 2/2 (100%)  transitions 2/3 (66.7%)",
                "  unhit:     on --RESET--> off",
                "FAIL xstate coverage: toggle: transition coverage*",
            ]
        )
        from xstate_statemachine.plugins import global_plugins

        assert global_plugins() == []  # unregistered at session end

    def test_gate_passes_when_met(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(NEVER_RESET)
        result = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-state-coverage=100",
            "--xsm-fail-under-transition-coverage=60",
        )
        assert result.ret == 0

    def test_directly_built_interpreters_are_collected(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_mod(f"""
                import threading
                from xstate_statemachine import create_machine, SyncInterpreter
                CFG = {TOGGLE!r}
                def test_direct():
                    m = create_machine(CFG)
                    def work():
                        i = SyncInterpreter(m).start()
                        i.send("TOGGLE"); i.send("RESET")
                    t = threading.Thread(target=work); t.start(); t.join()
                """))
        path = xsm_pytester.path / "out" / "cov.json"
        result = run(
            xsm_pytester,
            "--xsm-coverage",
            f"--xsm-coverage-report=json:{path}",
            "--xsm-coverage-report=term",
        )
        assert result.ret == 0
        doc = json.loads(path.read_text("utf-8"))
        assert doc["version"] == 1
        (entry,) = doc["machines"]
        assert entry["machine"] == "toggle"
        assert entry["transitions"]["hit"] == 2
        assert entry["transitions"]["unhit"] == [
            {"from": "toggle.on", "label": "on 'TOGGLE'", "to": "toggle.off"}
        ]
        result.stdout.fnmatch_lines(["xstate coverage written to *cov.json"])

    def test_html_report_is_self_contained(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(NEVER_RESET)
        path = xsm_pytester.path / "cov.html"
        result = run(
            xsm_pytester,
            "--xsm-coverage",
            f"--xsm-coverage-report=html:{path}",
        )
        assert result.ret == 0
        text = path.read_text("utf-8")
        assert text.startswith("<!DOCTYPE html>")
        for external in ("<script", "<link", "src=", "http://", "https://"):
            assert external not in text
        assert "on --RESET--&gt; off" in text
        # only html requested: no terminal table
        assert "---- xstate coverage ----" not in result.stdout.str()

    def test_bad_report_spec_is_a_usage_error(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(NEVER_RESET)
        result = run(
            xsm_pytester, "--xsm-coverage", "--xsm-coverage-report=xml"
        )
        assert result.ret == 4
